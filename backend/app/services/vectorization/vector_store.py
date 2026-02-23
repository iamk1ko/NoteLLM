from __future__ import annotations

import inspect
import time
from typing import Dict, Any, Optional, List

from pymilvus import (
    MilvusClient,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    Function,
    FunctionType,
)
from pymilvus.milvus_client import IndexParams

from app.core.logging import get_logger
from app.schemas import ChunkRecord
from app.services.vectorization.embedder import BgeM3Embedder, Embedder

logger = get_logger(__name__)

CONTENT_MAX_LENGTH = 4096  # Milvus VARCHAR 字段最大长度限制
SECTION_MAX_LENGTH = 512  # Milvus VARCHAR 字段最大长度限制，章节信息通常较短，但在部分文档中可能超过 255
FILE_MD5_MAX_LENGTH = 64  # 文件MD5长度限制，通常为32字符，但留有余量以防止意外情况


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

    def ensure_collection(self, *, force_recreate: bool = False) -> bool:
        """同步场景下确保集合存在。

        注意：本项目同时存在同步/异步调用路径。`create_collection()` 是 async，
        但有些调用方（例如初始化阶段/测试）可能在同步上下文里使用。

        这里做一个安全包装：
        - 如果当前线程没有 event loop：直接 asyncio.run
        - 如果已经在 event loop 内：返回 False，并让调用方走 async 版本
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # 在事件循环内不要强行 run_until_complete，避免死锁
            return self.collection_created

        return asyncio.run(self.create_collection(force_recreate=force_recreate))

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

    def _require_client(self) -> MilvusClient:
        if self.client is None:
            raise RuntimeError("Milvus client is not initialized")
        return self.client

    def _require_embedding(self) -> Embedder:
        if self.embedder is None:
            raise RuntimeError("Embedding model is not initialized")
        return self.embedder

    @staticmethod
    async def _maybe_await(result: Any) -> Any:
        if inspect.isawaitable(result):
            return await result
        return result

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
        if self.embedder is not None:
            return self.embedder
        logger.info("正在初始化 BGE-M3 嵌入模型...")
        embedder = BgeM3Embedder(model_name="BAAI/bge-m3", device="cpu", use_fp16=False)
        logger.info(f"嵌入模型初始化完成。密集向量维度: {embedder.dim}")
        if embedder.dim != self.dim:
            raise ValueError(
                f"Embedding dim mismatch: model={embedder.dim}, config={self.dim}"
            )
        return embedder

    def _create_collection_schema(self) -> CollectionSchema:
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
                name="pk",
                dtype=DataType.INT64,
                description="主键id",
                is_primary=True,
                auto_id=True,
            ),
            FieldSchema(name="file_id", dtype=DataType.INT64, description="文件id"),
            FieldSchema(
                name="file_md5",
                dtype=DataType.VARCHAR,
                max_length=FILE_MD5_MAX_LENGTH,
                description="文件md5",
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64,
                description="文件块索引(防止大文件被切分成多个块时的重复)",
            ),
            FieldSchema(
                name="page_no",
                dtype=DataType.INT64,
                is_nullable=True,
                description="页码",
            ),
            FieldSchema(
                name="section",
                dtype=DataType.VARCHAR,
                max_length=SECTION_MAX_LENGTH,
                is_nullable=True,
                description="章节信息",
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=CONTENT_MAX_LENGTH,
                is_nullable=True,
                description="文本块内容",
                enable_analyzer=True,  # 启用文本分析器，支持基于文本内容的搜索和过滤
                enable_match=True,  # 启用基于文本内容的匹配功能，允许在搜索时直接使用文本内容进行过滤和排序
                analyzer_params=analyzer_params,
            ),
            FieldSchema(
                name="sparse_vector",
                dtype=DataType.SPARSE_FLOAT_VECTOR,
                description="文本块的稀疏向量表示",
            ),
            FieldSchema(
                name="dense_vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dim,
                description="文本块的稠密向量表示",
            ),
            FieldSchema(
                name="metadata",
                dtype=DataType.JSON,
                is_nullable=True,
                description="其他元信息(可选)",
            ),
        ]

        # 利用 Milvus 的 Function 定义 BM25 函数，输入为文本内容，输出为稀疏向量。这样可以在 Milvus 内部直接使用 BM25 进行相似度搜索，无需在应用层进行额外处理。
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["content"],  # 输入字段为"content"，即文本内容
            output_field_names=[
                "sparse_vector"
            ],  # 输出字段为"sparse_vector"，即 BM25 转换后的稀疏向量
            function_type=FunctionType.BM25,
            description="BM25 函数，用于将文本内容转换为稀疏向量，以支持基于 BM25 的相似度搜索",
        )

        schema = CollectionSchema(
            fields, functions=[bm25_function], description="知识库向量数据表"
        )

        logger.info("集合 schema 创建完成，包含字段: {}", [field.name for field in fields])
        return schema

    async def create_collection(self, force_recreate: bool = False) -> bool:
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
            if await self._maybe_await(client.has_collection(self.collection_name)):
                if force_recreate:
                    logger.info(f"删除已存在的集合: {self.collection_name}")
                    await self._maybe_await(client.drop_collection(self.collection_name))
                else:
                    logger.info(f"集合 {self.collection_name} 已存在")
                    self.collection_created = True
                    return True

            # 创建集合
            schema = self._create_collection_schema()

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

            return True

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False

    async def create_index(self, *, skip_if_exists: bool = True) -> bool:
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
                field_name="sparse_vector",
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
                field_name="dense_vector",
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
            if not await self.create_collection(force_recreate=False):
                return False

            # 2. 准备数据
            logger.info("正在生成向量embeddings...")
            texts: list[str] = [chunk.content or "" for chunk in chunks]
            vectors = self._require_embedding().encode_documents(texts)

            # 3. 准备插入数据
            entities = []
            dense_vectors = vectors.get("dense", [])
            for i, chunk in enumerate(chunks):
                dense_vector = dense_vectors[i] if i < len(dense_vectors) else None
                entity = {
                    "file_id": chunk.file_id,
                    "file_md5": self._safe_truncate(
                        chunk.file_md5, FILE_MD5_MAX_LENGTH
                    ),
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "section": self._safe_truncate(chunk.section, SECTION_MAX_LENGTH),
                    "content": self._safe_truncate(chunk.content, CONTENT_MAX_LENGTH),
                    "dense_vector": dense_vector,
                    "metadata": chunk.metadata or {},
                }
                entities.append(entity)

            # 4. 批量插入数据
            logger.info("正在插入向量数据...")
            batch_size = 100
            for i in range(0, len(entities), batch_size):
                batch = entities[i: i + batch_size]
                await self._maybe_await(
                    self._require_client().insert(
                        collection_name=self.collection_name, data=batch
                    )
                )
                logger.info(
                    f"已插入 {min(i + batch_size, len(entities))}/{len(entities)} 条数据"
                )

            # 5. 创建索引
            if not await self.create_index():
                return False

            # 6. 加载集合到内存
            await self._maybe_await(
                self._require_client().load_collection(self.collection_name)
            )
            logger.info("集合已加载到内存")

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
        # 自动确保集合存在（首次写入时）
        if not self.collection_created:
            ok = await self.create_collection(force_recreate=False)
            if not ok:
                raise ValueError("请先构建向量索引")

        logger.info(f"正在添加 {len(new_chunks)} 个新文档到索引...")

        try:
            # 生成向量
            texts: list[str] = [chunk.content or "" for chunk in new_chunks]
            vectors = self._require_embedding().encode_documents(texts)

            # 准备插入数据
            entities = []
            dense_vectors = vectors.get("dense", [])
            for i, chunk in enumerate(new_chunks):
                dense_vector = dense_vectors[i] if i < len(dense_vectors) else None
                entity = {
                    "file_id": chunk.file_id,
                    "file_md5": self._safe_truncate(
                        chunk.file_md5, FILE_MD5_MAX_LENGTH
                    ),
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "section": self._safe_truncate(chunk.section, SECTION_MAX_LENGTH),
                    "content": self._safe_truncate(chunk.content, CONTENT_MAX_LENGTH),
                    "dense_vector": dense_vector,
                    "metadata": chunk.metadata or {},
                }
                entities.append(entity)

            # 插入数据
            await self._maybe_await(
                self._require_client().insert(
                    collection_name=self.collection_name, data=entities
                )
            )

            logger.info("新文档添加完成")
            return True

        except Exception as e:
            logger.error(f"添加新文档失败: {e}")
            return False

    async def search_dense(
            self,
            *,
            query_vector: list[float],
            k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.collection_created:
            raise ValueError("请先构建或加载向量索引")

        try:
            filter_expr = self._build_filter_expr(filters)
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64},
            }

            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query_vector],
                "anns_field": "dense_vector",
                "limit": k,
                "output_fields": [
                    "pk",
                    "file_id",
                    "file_md5",
                    "chunk_index",
                    "page_no",
                    "section",
                    "content",
                    "metadata",
                ],
                "search_params": search_params,
            }
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            results = await self._maybe_await(
                self._require_client().search(**search_kwargs)
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return []

    async def search_bm25(
            self,
            *,
            query: str,
            k: int = 5,
            filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.collection_created:
            raise ValueError("请先构建或加载向量索引")

        try:
            filter_expr = self._build_filter_expr(filters)
            search_params = {"metric_type": "BM25", "params": {}}
            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query],
                "anns_field": "sparse_vector",
                "limit": k,
                "output_fields": [  # 检索到后需要返回这些字段以供后续使用
                    "pk",
                    "file_id",
                    "file_md5",
                    "chunk_index",
                    "page_no",
                    "section",
                    "content",
                    "metadata",
                ],
                "search_params": search_params,
            }
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            results = await self._maybe_await(
                self._require_client().search(**search_kwargs)
            )
            return self._format_results(results)
        except Exception as e:
            logger.error(f"BM25 检索失败: {e}")
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
        dense_results = await self.search_dense(
            query_vector=query_vector, k=k, filters=filters
        )
        bm25_results = await self.search_bm25(query=query, k=k, filters=filters)

        merged: dict[str, Dict[str, Any]] = {}

        def merge(result: Dict[str, Any], score_key: str) -> None:
            meta = result.get("metadata", {})
            file_id = meta.get("file_id")
            chunk_index = meta.get("chunk_index")
            key = (
                f"{file_id}:{chunk_index}"
                if file_id is not None
                else str(result.get("id"))
            )
            if key not in merged:
                merged[key] = {
                    "result": result,
                    "dense": 0.0,
                    "bm25": 0.0,
                }
            merged[key][score_key] = max(
                merged[key][score_key], float(result.get("score") or 0.0)
            )

        for result in dense_results:
            merge(result, "dense")
        for result in bm25_results:
            merge(result, "bm25")

        reranked = []
        for entry in merged.values():
            dense_score = entry["dense"]
            bm25_score = entry["bm25"]
            score = alpha * dense_score + (1 - alpha) * bm25_score
            item = entry["result"].copy()
            item["score"] = score
            reranked.append(item)

        reranked.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return reranked[:k]

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
                    "id": hit.get("id") if isinstance(hit, dict) else None,
                    "score": hit.get("distance") if isinstance(hit, dict) else None,
                    "text": entity.get("content"),
                    "metadata": {
                        "file_id": entity.get("file_id"),
                        "file_md5": entity.get("file_md5"),
                        "chunk_index": entity.get("chunk_index"),
                        "page_no": entity.get("page_no"),
                        "section": self._preview_truncate(entity.get("section"), 50),
                        "content": self._preview_truncate(entity.get("content"), 100),
                        "metadata": entity.get("metadata"),
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

    async def delete_collection(self) -> bool:
        """
        删除集合

        Returns:
            是否删除成功
        """
        try:
            client = self._require_client()
            if await self._maybe_await(client.has_collection(self.collection_name)):
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
            if not await self._maybe_await(client.has_collection(self.collection_name)):
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
