from __future__ import annotations

import asyncio
import inspect
import time
from typing import Dict, Any, Optional, List

from pymilvus import (
    MilvusClient,
    CollectionSchema,
    DataType,
    FieldSchema,
    Function,
    FunctionType,
)
from pymilvus.milvus_client import IndexParams

from app.core.constants import MilvusField
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.schemas import ChunkRecord
from app.services.vectorization.embedder import Embedder, build_default_embedder

logger = get_logger(__name__)

CONTENT_MAX_LENGTH = (
    get_settings().VS_CONTENT_MAX_LEN
)  # Milvus VARCHAR 字段最大长度限制
SECTION_MAX_LENGTH = (
    get_settings().VS_SECTION_MAX_LEN  # Milvus VARCHAR 字段最大长度限制，章节信息通常较短，但在部分文档中可能超过 255
)
FILE_MD5_MAX_LENGTH = (
    get_settings().VS_FILE_MD5_MAX_LEN
)  # 文件MD5长度限制，通常为32字符，但留有余量以防止意外情况


class MilvusVectorStore:
    def __init__(
            self,
            *,
            uri: str,
            collection_name: str,
            dim: int = 1024,
            metric_type: str = "COSINE",
            alias: str = "default",
            embedder: Embedder | None = None,
    ):
        self.collection_created = False  # 标记集合是否已创建，避免重复创建
        self.uri = uri
        self.collection_name = collection_name
        self.dim = dim
        self.metric_type = metric_type
        self.alias = alias
        self.client: Optional[MilvusClient] = None
        self.embedder: Optional[Embedder] = embedder

        self.client = self._setup_milvus_client()
        self.embedder = self._setup_embedding_model()

    async def init_collection(self, is_renew_collection=False) -> None:
        """
        初始化集合：如果不存在，则创建，否则加载。这应该在应用启动时调用。

        Args:
            is_renew_collection: 是否强制重新创建集合（会删除已存在的集合）
        """
        try:
            if is_renew_collection:
                await self.delete_collection()

            exists = await self.has_collection()
            if not exists:
                logger.info(f'集合 "{self.collection_name}" 不存在. 正在尝试创建...')
                await self._create_collection(force_recreate=True)
            else:
                logger.info(f'集合 "{self.collection_name}" 已存在. 正在加载中...')
                await self.load_collection()

            self.collection_created = True
        except Exception as e:
            logger.error(f'无法初始化集合 "{self.collection_name}": {e}')
            raise

    def _require_client(self) -> MilvusClient:
        if self.client is None:
            raise RuntimeError("Milvus client is not initialized")
        return self.client

    def _require_embedding(self) -> Embedder:
        if self.embedder is None:
            raise RuntimeError("Embedding model is not initialized")
        return self.embedder

    def _setup_milvus_client(self) -> Optional[MilvusClient]:
        if self.client is not None:
            return self.client
        logger.info(f"正在连接 Milvus 服务器: {self.uri}...")
        try:
            # connections.connect(alias=self.alias, uri=self.uri)
            client: MilvusClient = MilvusClient(uri=self.uri)
            logger.info(
                "Milvus 连接成功, 当前集合列表: {}",
                client.list_collections(using=self.alias),
            )
            return client
        except Exception as e:
            logger.error(f"连接 Milvus 失败: {e}")
            raise

    def _setup_embedding_model(self) -> Optional[Embedder]:
        """初始化默认的嵌入模型（OpenAIEmbeddings 远程调用）"""
        if self.embedder is not None:
            return self.embedder  # 如果已经有了，就直接用

        settings = get_settings()
        logger.info(
            "初始化 Embedding 客户端: model={}, dim={} (remote)",
            settings.EMBEDDING_MODEL_NAME,
            settings.EMBEDDING_DIM,
        )
        embedder = build_default_embedder()
        if embedder.dim != self.dim:
            raise ValueError(
                f"Embedding dim mismatch: model={embedder.dim}, config={self.dim}"
            )
        return embedder

    async def _create_collection(self, force_recreate: bool = False) -> bool:
        """
        创建Milvus集合

        Args:
            force_recreate: 是否强制重新创建集合

        Returns:
            是否创建成功
        """
        try:
            client = self._require_client()
            # 检查集合是否存在
            if await self.has_collection():
                if force_recreate:
                    logger.info(f"删除已存在的集合: {self.collection_name}")
                    await self.delete_collection()
                else:
                    logger.info(f"集合 {self.collection_name} 已存在")
                    self.collection_created = True
                    return True

            # 创建 schema
            schema = await self._create_collection_schema()

            await self._maybe_await(
                client.create_collection(
                    collection_name=self.collection_name,
                    schema=schema,
                    metric_type="COSINE",  # 使用余弦相似度
                    consistency_level="Strong",
                )
            )

            logger.info(f"成功创建集合: {self.collection_name}")
            self.collection_created = True

            await self._create_index(skip_if_exists=True)

            return True

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False

    async def _create_collection_schema(self) -> CollectionSchema:
        """
        创建集合模式

        Returns:
            集合模式对象
        """
        # 通过 analyzer_params 定义文本分析器的参数.
        analyzer_params = {
            "tokenizer": "icu",  # 使用 ICU 分词器，支持多语言文本的分词，特别适合处理中文文本，可以更准确地将文本切分成词语，从而提高搜索和匹配的效果
        }

        fields = [
            FieldSchema(
                name=MilvusField.PK.value,
                dtype=DataType.INT64,
                description="主键id",
                is_primary=True,
                auto_id=True,
            ),
            FieldSchema(
                name=MilvusField.FILE_ID.value,
                dtype=DataType.INT64,
                description="文件id",
            ),
            FieldSchema(
                name=MilvusField.FILE_MD5.value,
                dtype=DataType.VARCHAR,
                max_length=FILE_MD5_MAX_LENGTH,
                description="文件md5",
            ),
            FieldSchema(
                name=MilvusField.CHUNK_INDEX.value,
                dtype=DataType.INT64,
                description="文件块索引(防止大文件被切分成多个块时的重复)",
            ),
            FieldSchema(
                name=MilvusField.PAGE_NO.value,
                dtype=DataType.INT64,
                is_nullable=True,
                description="页码",
            ),
            FieldSchema(
                name=MilvusField.SECTION.value,
                dtype=DataType.VARCHAR,
                max_length=SECTION_MAX_LENGTH,
                is_nullable=True,
                description="章节信息",
            ),
            FieldSchema(
                name=MilvusField.CONTENT.value,
                dtype=DataType.VARCHAR,
                max_length=CONTENT_MAX_LENGTH,
                is_nullable=True,
                description="文本块内容",
                enable_analyzer=True,  # 启用文本分析器，支持基于文本内容的搜索和过滤
                enable_match=True,  # 启用基于文本内容的匹配功能，允许在搜索时直接使用文本内容进行过滤和排序
                analyzer_params=analyzer_params,
            ),
            FieldSchema(
                name=MilvusField.SPARSE_VECTOR.value,
                dtype=DataType.SPARSE_FLOAT_VECTOR,
                description="文本块的稀疏向量表示",
            ),
            FieldSchema(
                name=MilvusField.DENSE_VECTOR.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dim,
                description="文本块的稠密向量表示",
            ),
            FieldSchema(
                name=MilvusField.METADATA.value,
                dtype=DataType.JSON,
                is_nullable=True,
                description="其他元信息(可选)",
            ),
        ]

        # 利用 Milvus 的 Function 定义 BM25 函数，输入为文本内容，输出为稀疏向量。这样可以在 Milvus 内部直接使用 BM25 进行相似度搜索，无需在应用层进行额外处理。
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=[
                MilvusField.CONTENT.value
            ],  # 输入字段为MilvusField.CONTENT.value，即文本内容
            output_field_names=[
                MilvusField.SPARSE_VECTOR.value
            ],  # 输出字段为MilvusField.SPARSE_VECTOR.value，即 BM25 转换后的稀疏向量
            function_type=FunctionType.BM25,
            description="BM25 函数，用于将文本内容转换为稀疏向量，以支持基于 BM25 的相似度搜索",
        )

        schema = CollectionSchema(
            fields, functions=[bm25_function], description="知识库向量数据表"
        )

        logger.info(
            "集合 schema 创建完成，包含字段: {}", [field.name for field in fields]
        )
        return schema

    async def _create_index(self, *, skip_if_exists: bool = True) -> bool:
        """
        创建向量索引

        Args:
            skip_if_exists: 如果索引已存在，是否跳过创建

        Returns:
            是否创建成功
        """
        try:
            if not self.collection_created:
                raise ValueError("请先创建集合")

            # 使用prepare_index_params创建正确的IndexParams对象
            # 添加向量字段索引时，确保使用正确的参数结构和类型，以满足 Milvus 的要求。
            client = self._require_client()
            if skip_if_exists:
                existing = await self._maybe_await(
                    client.list_indexes(collection_name=self.collection_name)
                )
                if existing:
                    logger.info("向量索引已存在，跳过创建")
                    return True
            index_params: IndexParams = await self._maybe_await(
                client.prepare_index_params()
            )
            index_params.add_index(
                field_name=MilvusField.SPARSE_VECTOR.value,
                index_name="sparse_vector_bm25_index",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
                params={
                    "inverted_index_algo": "DAAT_MAXSCORE",
                    "bm25_k1": 1.2,  # 控制词频饱和度。数值越高，术语频率在文档排名中的重要性就越大。取值范围[1.2, 2.0].
                    "bm25_b": 0.75,  # 控制文档长度的标准化程度。通常使用 0 到 1 之间的值，默认值为 0.75 左右。值为 1 表示不进行长度归一化，值为 0 表示完全归一化。
                },
            )

            index_params.add_index(
                field_name=MilvusField.DENSE_VECTOR.value,
                index_name="dense_vector_hnsw_index",
                index_type="HNSW",
                metric_type="COSINE",
                params={
                    "M": 16,  # 每个节点的连接数，较小的 M 可以提高搜索效率，但可能降低召回率；较大的 M 可以提高召回率，
                    "efConstruction": 200,  # 构建索引时的搜索深度，较大的 efConstruction 可以提高索引质量，但会增加构建时间和内存使用.
                },
            )

            await self._maybe_await(
                client.create_index(
                    collection_name=self.collection_name,
                    index_params=index_params,
                )
            )

            logger.info("向量索引创建成功")
            return True

        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return False

    @staticmethod
    def _safe_truncate(text: Optional[str], max_length: int) -> str:
        """严格截断到 max_length（保证返回字符串长度绝不超过 max_length）。
        Args:
            text: 输入文本
            max_length: 最大长度限制

        Returns:
            截断后的文本，长度不超过 max_length

        注意：如果你希望保留省略号用于展示，请用 `_preview_truncate`。
        """
        if text is None:
            return ""
        s = str(text)
        # return s[:max_length]
        raw = s.encode("utf-8")
        if len(raw) <= max_length:
            return s
        return raw[:max_length].decode("utf-8", errors="ignore")

    @staticmethod
    def _preview_truncate(text: Optional[str], max_length: int) -> str:
        """用于日志/展示的截断：最多 max_length 字符（包含省略号）。"""
        if text is None:
            return ""
        s = str(text)
        if len(s) <= max_length:
            return s
        if max_length <= 3:
            return s[:max_length]
        return s[: max_length - 3] + "..."

    @staticmethod
    async def _maybe_await(result: Any) -> Any:
        if inspect.isawaitable(result):
            return await result
        return result

    async def build_vector_index(self, chunks: List[ChunkRecord]) -> bool:
        """
        构建向量索引
        build_vector_index: 完整流程，包含
            创建集合（create_collection）
            生成 embedding
            分批插入
            创建索引（create_index）
            加载集合到内存（load_collection）
            等待索引构建（当前用 time.sleep(2)）

        Args:
            chunks: 文档块列表

        Returns:
            是否构建成功
        """
        logger.info(f"正在构建Milvus向量索引，文档数量: {len(chunks)}...")

        if not chunks:
            raise ValueError("文档块列表不能为空")

        try:
            # 1. 创建集合
            if not await self._create_collection(force_recreate=False):
                logger.error("创建集合失败，终止构建索引")
                return False

            # 2. 准备数据
            logger.info(f"正在生成 {len(chunks)} 个文档的向量embeddings...")
            start_time = time.time()
            texts: list[str] = [chunk.content or "" for chunk in chunks]
            vectors = await self._require_embedding().aembed_documents(texts)
            logger.info(f"向量生成完成，耗时: {time.time() - start_time:.2f}s")

            # 3. 准备插入数据
            entities = []
            dense_vectors = vectors
            for i, chunk in enumerate(chunks):
                dense_vector = dense_vectors[i] if i < len(dense_vectors) else None
                entity = {
                    MilvusField.FILE_ID.value: chunk.file_id,
                    MilvusField.FILE_MD5.value: self._safe_truncate(
                        chunk.file_md5, FILE_MD5_MAX_LENGTH
                    ),
                    MilvusField.CHUNK_INDEX.value: chunk.chunk_index,
                    MilvusField.PAGE_NO.value: chunk.page_no or 0,
                    MilvusField.SECTION.value: self._safe_truncate(
                        chunk.section, SECTION_MAX_LENGTH
                    ),
                    MilvusField.CONTENT.value: self._safe_truncate(
                        chunk.content, CONTENT_MAX_LENGTH
                    ),
                    MilvusField.DENSE_VECTOR.value: dense_vector,
                    MilvusField.METADATA.value: chunk.metadata or {},
                }
                entities.append(entity)

            logger.info(f"数据准备完成，共 {len(entities)} 条记录")

            # 4. 批量插入数据
            logger.info("开始批量插入向量数据...")
            insert_start_time = time.time()
            batch_size = get_settings().VS_BATCH_SIZE
            total_inserted = 0
            for i in range(0, len(entities), batch_size):
                batch = entities[i: i + batch_size]
                await self._maybe_await(
                    self._require_client().insert(
                        collection_name=self.collection_name, data=batch
                    )
                )
                total_inserted += len(batch)
                logger.info(
                    f"已插入进度: {total_inserted}/{len(entities)} ({total_inserted / len(entities):.1%})"
                )
            logger.info(f"批量插入完成，耗时: {time.time() - insert_start_time:.2f}s")

            # 5. 创建索引
            logger.info("开始创建/确认向量索引...")
            index_start_time = time.time()
            if not await self._create_index():
                logger.error("创建索引失败")
                return False
            logger.info(
                f"索引创建/确认完成，耗时: {time.time() - index_start_time:.2f}s"
            )

            # 6. 加载集合到内存
            logger.info("正在加载集合到内存...")
            load_start_time = time.time()
            await self._maybe_await(
                self._require_client().load_collection(self.collection_name)
            )
            logger.info(f"集合加载完成，耗时: {time.time() - load_start_time:.2f}s")

            # 7. 等待索引构建完成
            logger.info("等待索引构建完成...")
            time.sleep(2)

            logger.info(f"向量索引构建完成，包含 {len(chunks)} 个向量")
            return True

        except Exception as e:
            logger.error(f"构建向量索引失败: {e}")
            return False

    async def add_documents(self, new_chunks: List[ChunkRecord]) -> bool:
        """
        向现有索引添加新文档

        Args:
            new_chunks: 新的文档块列表

        Returns:
            是否添加成功
        """
        logger.info(f"准备添加 {len(new_chunks)} 个新文档到索引...")
        start_time = time.time()

        try:
            # 生成向量
            logger.debug("正在生成新文档的 embeddings...")
            texts: list[str] = [chunk.content or "" for chunk in new_chunks]
            vectors = await self._require_embedding().aembed_documents(texts)
            logger.debug(f"Embeddings 生成耗时: {time.time() - start_time:.2f}s")

            # 准备插入数据
            entities = []
            dense_vectors = vectors
            for i, chunk in enumerate(new_chunks):
                dense_vector = dense_vectors[i] if i < len(dense_vectors) else None
                entity = {
                    MilvusField.FILE_ID.value: chunk.file_id,
                    MilvusField.FILE_MD5.value: self._safe_truncate(
                        chunk.file_md5, FILE_MD5_MAX_LENGTH
                    ),
                    MilvusField.CHUNK_INDEX.value: chunk.chunk_index,
                    MilvusField.PAGE_NO.value: chunk.page_no or 0,
                    MilvusField.SECTION.value: self._safe_truncate(
                        chunk.section, SECTION_MAX_LENGTH
                    ),
                    MilvusField.CONTENT.value: self._safe_truncate(
                        chunk.content, CONTENT_MAX_LENGTH
                    ),
                    MilvusField.DENSE_VECTOR.value: dense_vector,
                    MilvusField.METADATA.value: chunk.metadata or {},
                }
                entities.append(entity)

            # 插入数据
            insert_start = time.time()
            logger.info(
                f"正在向集合 {self.collection_name} 插入 {len(entities)} 条数据..."
            )
            await self._maybe_await(
                self._require_client().insert(
                    collection_name=self.collection_name, data=entities
                )
            )
            logger.info(f"插入完成，耗时: {time.time() - insert_start:.2f}s")
            logger.info(f"新文档添加流程总耗时: {time.time() - start_time:.2f}s")
            return True

        except Exception as e:
            logger.error(f"添加新文档失败: {e}", exc_info=True)
            return False

    async def search_dense(
            self,
            *,
            query_vector: list[float],
            k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        try:
            filter_expr = self._build_filter_expr(filters)
            logger.debug(f"语义检索开始，过滤条件: {filter_expr}, top_k: {k}")

            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64},
            }

            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query_vector],
                "anns_field": MilvusField.DENSE_VECTOR.value,
                "limit": k,
                "output_fields": [
                    MilvusField.PK.value,
                    MilvusField.FILE_ID.value,
                    MilvusField.FILE_MD5.value,
                    MilvusField.CHUNK_INDEX.value,
                    MilvusField.PAGE_NO.value,
                    MilvusField.SECTION.value,
                    MilvusField.CONTENT.value,
                    MilvusField.METADATA.value,
                ],
                "search_params": search_params,
            }
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            # results = data [[{'pk': 4123..., 'distance': 3.1314..., 'entity': {'file_id': 123, 'chunk_index': 0, 'content': 'xxx', ...}}]]
            results = await self._maybe_await(
                self._require_client().search(**search_kwargs)
            )
            formatted = self._format_results(results)
            logger.info(
                f"语义检索完成，耗时: {time.time() - start_time:.4f}s, 返回 Top-{len(formatted)} 条结果"
            )
            return formatted
        except Exception as e:
            logger.error(f"语义检索失败: {e}", exc_info=True)
            return []

    async def search_bm25(
            self,
            *,
            query: str,
            k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        try:
            filter_expr = self._build_filter_expr(filters)
            # 对超长query进行截断，方便日志展示
            display_query = (query[:50] + "...") if len(query) > 50 else query
            logger.debug(
                f"BM25检索开始，Query: {display_query}, 过滤条件: {filter_expr}, top_k: {k}"
            )

            search_params = {"metric_type": "BM25", "params": {}}
            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query],
                "anns_field": MilvusField.SPARSE_VECTOR.value,
                "limit": k,
                "output_fields": [  # 检索到后需要返回这些字段以供后续使用
                    MilvusField.PK.value,
                    MilvusField.FILE_ID.value,
                    MilvusField.FILE_MD5.value,
                    MilvusField.CHUNK_INDEX.value,
                    MilvusField.PAGE_NO.value,
                    MilvusField.SECTION.value,
                    MilvusField.CONTENT.value,
                    MilvusField.METADATA.value,
                ],
                "search_params": search_params,
            }
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            # results = data [[{'pk': 4123..., 'distance': 3.1314..., 'entity': {'file_id': 123, 'chunk_index': 0, 'content': 'xxx', ...}}]]
            results = await self._maybe_await(
                self._require_client().search(**search_kwargs)
            )
            formatted = self._format_results(results)
            logger.info(
                f"BM25检索完成，耗时: {time.time() - start_time:.4f}s, 返回 Top-{len(formatted)} 条结果"
            )
            return formatted
        except Exception as e:
            logger.error(f"BM25 检索失败: {e}", exc_info=True)
            return []

    async def search_hybrid(
            self,
            *,
            query: str,
            query_vector: list[float],
            k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
            alpha: float = 0.7,
    ) -> List[Dict[str, Any]]:
        start_time = time.time()
        logger.info(f"混合检索开始，alpha={alpha}, top_k={k}")

        # 并行执行向量检索和全文检索
        dense_results, bm25_results = await asyncio.gather(
            self.search_dense(query_vector=query_vector, k=k, filters=filters),
            self.search_bm25(query=query, k=k, filters=filters),
        )

        merged: dict[str, dict[str, Any]] = {}

        for result in dense_results:
            self._merge_hybrid_result(merged, result, "dense")
        for result in bm25_results:
            self._merge_hybrid_result(merged, result, "bm25")
        logger.debug(
            "[自定义的合并方法] 混合检索结果合并完成，准备计算融合分数和排序..."
        )

        reranked: list[dict[str, Any]] = []
        for entry in merged.values():
            dense_score = float(entry.get("dense", 0.0) or 0.0)
            bm25_score = float(entry.get("bm25", 0.0) or 0.0)
            score = alpha * dense_score + (1 - alpha) * bm25_score

            result_item = dict(entry.get("result") or {})
            result_item["score"] = score
            reranked.append(result_item)
        reranked.sort(
            key=lambda item_: float(item_.get("score", 0.0) or 0.0), reverse=True
        )
        logger.debug("[自定义的重排序方法] 混合检索结果重排序完成，准备截取 Top-k...")

        final_results = reranked[:k]
        logger.info(
            f"混合检索完成，耗时: {time.time() - start_time:.4f}s, 最终返回: {len(final_results)}"
        )
        return final_results

    @staticmethod
    def _merge_hybrid_result(
            merged: dict[str, dict[str, Any]],
            result: Dict[str, Any],
            score_key: str,
    ) -> None:
        """
        将单个检索结果合并到混合结果中，更新对应的分数

        假设：
        dense_results 返回 2 条：
            A：file_id=1, chunk_index=0, score=0.9
            B：file_id=1, chunk_index=1, score=0.8

        bm25_results 返回 2 条：
            A：file_id=1, chunk_index=0, score=12.0
            C：file_id=2, chunk_index=0, score=9.0

        合并过程（merged 以 key 为索引）：
            1. 处理 dense A（key=1:0）
               merged["1:0"] = {"result": A, "dense": 0.9, "bm25": 0.0}
            2. 处理 dense B（key=1:1）
               merged["1:1"] = {"result": B, "dense": 0.8, "bm25": 0.0}
            3. 处理 bm25 A（key=1:0）
               找到已有 merged["1:0"]，只更新 bm25 分数：
               merged["1:0"]["bm25"] = 12.0
            4. 处理 bm25 C（key=2:0）
               merged["2:0"] = {"result": C, "dense": 0.0, "bm25": 9.0}

        最终 merged 里有 3 个 key：A、B、C；其中 A 同时拥有 dense 和 bm25 分数，B 只有 dense，C 只有 bm25。
        之后 search_hybrid() 会对每个 entry 计算融合分数：
            score = alpha * dense + (1 - alpha) * bm25 然后按 score 排序取 Top-k。
        """
        meta = result.get(MilvusField.METADATA.value, {}) or {}
        file_id = meta.get(MilvusField.FILE_ID.value)
        chunk_index = meta.get(MilvusField.CHUNK_INDEX.value)
        key = (
            f"{file_id}:{chunk_index}" if file_id is not None else str(result.get("id"))
        )

        entry = merged.get(key)
        if entry is None:
            entry = {"result": result, "dense": 0.0, "bm25": 0.0}
            merged[key] = entry

        current = float(entry.get(score_key, 0.0) or 0.0)
        incoming = float(result.get("score") or 0.0)
        entry[score_key] = max(current, incoming)

    @staticmethod
    def _build_filter_expr(filters: Optional[Dict[str, Any]]) -> str:
        if not filters:
            return ""
        filter_conditions = []
        for key, value in filters.items():
            if isinstance(value, str):
                filter_conditions.append(f'{key} == "{value}"')
            elif isinstance(value, (int, float)):
                filter_conditions.append(f"{key} == {value}")
            elif isinstance(value, list):
                if all(isinstance(v, str) for v in value):
                    value_str = '", "'.join(value)
                    filter_conditions.append(f'{key} in ["{value_str}"]')
                else:
                    value_str = ", ".join(map(str, value))
                    filter_conditions.append(f"{key} in [{value_str}]")
        return " and ".join(filter_conditions)

    def _format_results(self, results: Any) -> List[Dict[str, Any]]:
        formatted_results = []
        if results and len(results) > 0:
            for hit in results[0]:
                entity = hit.get("entity", {}) if isinstance(hit, dict) else hit
                result = {
                    "pk": hit.get("pk") if isinstance(hit, dict) else None,
                    "score": hit.get("distance") if isinstance(hit, dict) else None,
                    "text": entity.get(MilvusField.CONTENT.value),
                    MilvusField.METADATA.value: {
                        MilvusField.FILE_ID.value: entity.get(
                            MilvusField.FILE_ID.value
                        ),
                        MilvusField.FILE_MD5.value: entity.get(
                            MilvusField.FILE_MD5.value
                        ),
                        MilvusField.CHUNK_INDEX.value: entity.get(
                            MilvusField.CHUNK_INDEX.value
                        ),
                        MilvusField.PAGE_NO.value: entity.get(
                            MilvusField.PAGE_NO.value
                        ),
                        MilvusField.SECTION.value: entity.get(
                            MilvusField.SECTION.value
                        ),
                        # MilvusField.CONTENT.value: entity.get(MilvusField.CONTENT.value), # 和上方的 "text" 字段重复了，这里就不放在 metadata 里了
                        MilvusField.METADATA.value: entity.get(
                            MilvusField.METADATA.value
                        ),
                    },
                }
                formatted_results.append(result)
        return formatted_results

    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息字典
        """
        try:
            if not self.collection_created:
                return {"error": "集合未创建"}

            stats = await self._maybe_await(
                self._require_client().get_collection_stats(self.collection_name)
            )
            return {
                "collection_name": self.collection_name,
                "row_count": stats.get("row_count", 0),
                "index_building_progress": stats.get("index_building_progress", 0),
                "stats": stats,
            }

        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {"error": str(e)}

    async def _ensure_collection_loaded(self) -> None:
        """确保集合已加载到内存，避免查询时报 collection not loaded。"""
        try:
            await self._maybe_await(
                self._require_client().load_collection(self.collection_name)
            )
            logger.debug("Milvus 集合已加载：{}", self.collection_name)
        except Exception as e:
            logger.warning("Milvus 集合加载失败：{}, error={}", self.collection_name, e)

    async def delete_collection(self) -> bool:
        """
        删除集合

        Returns:
            是否删除成功
        """
        try:
            client = self._require_client()
            if await self.has_collection():
                await self._maybe_await(client.drop_collection(self.collection_name))
                logger.info(f"集合 {self.collection_name} 已删除")
                self.collection_created = False
                return True
            else:
                logger.info(f"集合 {self.collection_name} 不存在")
                return True

        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    async def has_collection(self) -> bool:
        """
        检查集合是否存在

        Returns:
            集合是否存在
        """
        try:
            result = await self._maybe_await(
                self._require_client().has_collection(self.collection_name)
            )
            return bool(result)
        except Exception as e:
            logger.error(f"检查集合存在性失败: {e}")
            return False

    async def load_collection(self) -> bool:
        """
        加载集合到内存

        Returns:
            是否加载成功
        """
        try:
            client = self._require_client()
            if not await self.has_collection():
                logger.error(f"集合 {self.collection_name} 不存在")
                return False

            await self._maybe_await(client.load_collection(self.collection_name))
            self.collection_created = True
            logger.info(f"集合 {self.collection_name} 已加载到内存")
            return True

        except Exception as e:
            logger.error(f"加载集合失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if hasattr(self, "client") and self.client:
            # Milvus客户端不需要显式关闭
            logger.info("Milvus连接已关闭")

    def __del__(self):
        """析构函数"""
        self.close()

    async def delete_by_file_id(self, file_id: int) -> int:
        """按 file_id 删除向量数据。

        Returns:
            删除的记录数（Milvus 返回的删除数量）
        """
        try:
            await self._ensure_collection_loaded()
            expr = f"{MilvusField.FILE_ID.value} == {file_id}"
            logger.info("删除 Milvus 向量数据：file_id={}, expr={}", file_id, expr)
            result = await self._maybe_await(
                self._require_client().delete(
                    collection_name=self.collection_name, filter=expr
                )
            )
            # Milvus delete 返回值可能是 dict，包含 delete_count
            deleted_count = 0
            if isinstance(result, dict):
                deleted_count = int(result.get("delete_count", 0) or 0)
            logger.info(
                "Milvus 向量删除完成：file_id={}, deleted_count={}", file_id, deleted_count
            )
            return deleted_count
        except Exception as e:
            logger.error(
                "Milvus 向量删除失败：file_id={}, error={}", file_id, e, exc_info=True
            )
            return 0

    async def count_by_file_id(self, file_id: int) -> int:
        """统计指定 file_id 的向量数量，用于一致性检查。"""
        try:
            await self._ensure_collection_loaded()
            expr = f"{MilvusField.FILE_ID.value} == {file_id}"
            result = await self._maybe_await(
                self._require_client().query(
                    collection_name=self.collection_name,
                    filter=expr,
                    output_fields=[MilvusField.FILE_ID.value],
                )
            )
            if isinstance(result, list):
                return len(result)
            return 0
        except Exception as e:
            logger.error(
                "Milvus 向量统计失败：file_id={}, error={}", file_id, e, exc_info=True
            )
            return 0
