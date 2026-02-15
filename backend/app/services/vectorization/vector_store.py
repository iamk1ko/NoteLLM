from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from pymilvus.milvus_client import IndexParams

from app.core.logging import get_logger

logger = get_logger(__name__)

from pymilvus.model.hybrid.bge_m3 import BGEM3EmbeddingFunction
from pymilvus import (
    MilvusClient,
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    utility,
    connections,
    Function,
    FunctionType
)


@dataclass
class ChunkRecord:
    file_id: int
    file_md5: str
    chunk_index: int
    # chunk_text: str
    # chunk_tokens: int
    page_no: int | None
    section: str | None
    content: str | None
    sparse_vector: list[float] | None
    dense_vector: list[float] | None
    metadata: list[dict[str, str]] | dict[str, str] | None


class MilvusVectorStore:
    def __init__(
            self,
            *,
            uri: str,
            collection_name: str,
            dim: int = 1024,
            metric_type: str = "COSINE",
            alias: str = "default",
    ):
        self.collection_created = None  # 标记集合是否已创建，避免重复创建
        self.uri = uri
        self.collection_name = collection_name
        self.dim = dim
        self.metric_type = metric_type
        self.alias = alias

        # MilvusClient does NOT automatically create the ORM default connection used by utility/Collection.
        # Create (or reuse) a named connection explicitly.
        try:
            connections.connect(alias=self.alias, uri=self.uri)
        except Exception as e:
            logger.error("Failed to connect to Milvus at {}: {}", self.uri, e)
            raise

        self.client = self._setup_milvus_client()
        self.embedding_model = self._setup_embedding_model()

    @staticmethod
    def _safe_truncate(text: str, max_length: int) -> str:
        """
        安全截取字符串，处理None值

        Args:
            text: 输入文本
            max_length: 最大长度

        Returns:
            截取后的字符串
        """
        if text is None:
            return ""
        return str(text)[:max_length]

    def _setup_milvus_client(self) -> Optional[MilvusClient]:
        if self.client is None:
            logger.info(f"正在连接 Milvus 服务器: {self.uri}...")
            try:
                connections.connect(alias=self.alias, uri=self.uri)
                client: MilvusClient = MilvusClient(uri=self.uri)
                logger.info("Milvus 连接成功, 当前集合列表: {}", client.list_collections(using=self.alias))
                return client
            except Exception as e:
                logger.error(f"连接 Milvus 失败: {e}")
                raise
        return None

    def _setup_embedding_model(self) -> Optional[BGEM3EmbeddingFunction]:
        if self.embedding_model is None:
            logger.info("正在初始化 BGE-M3 嵌入模型...")
            embedding_model: BGEM3EmbeddingFunction = BGEM3EmbeddingFunction(
                model_name='BAAI/bge-m3',  # 指定模型名称
                device='cpu',  # 指定要使用的设备，例如 'cpu' 或 'cuda:0'
                use_fp16=False  # 指定是否使用 fp16。如果 `device` 是 `cpu`，则设置为 `False`。
            )
            logger.info(f"嵌入模型初始化完成。密集向量维度: {embedding_model.dim['dense']}")
            assert embedding_model.dim == self.dim  # 确保模型维度与配置一致
            return embedding_model
        return None

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
            FieldSchema(name="pk", dtype=DataType.INT64, description="主键id", is_primary=True, auto_id=True),
            FieldSchema(name="file_id", dtype=DataType.INT64, description="文件id"),
            FieldSchema(name="file_md5", dtype=DataType.VARCHAR, max_length=64, description="文件md5"),
            FieldSchema(name="chunk_index", dtype=DataType.INT64,
                        description="文件块索引(防止大文件被切分成多个块时的重复)"),
            FieldSchema(name="page_no", dtype=DataType.INT64, is_nullable=True, description="页码"),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=255, is_nullable=True,
                        description="章节信息"),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096, is_nullable=True,
                        description="文本块内容",
                        enable_analyzer=True,  # 启用文本分析器，支持基于文本内容的搜索和过滤
                        enable_match=True,  # 启用基于文本内容的匹配功能，允许在搜索时直接使用文本内容进行过滤和排序
                        analyzer_params=analyzer_params),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR, description="文本块的稀疏向量表示"),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim,
                        description="文本块的稠密向量表示"),
            FieldSchema(name="metadata", dtype=DataType.JSON, is_nullable=True, description="其他元信息(可选)"),
        ]

        # 利用 Milvus 的 Function 定义 BM25 函数，输入为文本内容，输出为稀疏向量。这样可以在 Milvus 内部直接使用 BM25 进行相似度搜索，无需在应用层进行额外处理。
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["content"],  # 输入字段为"content"，即文本内容
            output_field_names=["sparse_vector"],  # 输出字段为"sparse_vector"，即 BM25 转换后的稀疏向量
            function_type=FunctionType.BM25,
            description="BM25 函数，用于将文本内容转换为稀疏向量，以支持基于 BM25 的相似度搜索"
        )

        schema = CollectionSchema(fields, functions=[bm25_function], description="知识库向量数据表")
        return schema

    def create_collection(self, force_recreate: bool = False) -> bool:
        """
        创建Milvus集合

        Args:
            force_recreate: 是否强制重新创建集合

        Returns:
            是否创建成功
        """
        try:
            # 检查集合是否存在
            if self.client.has_collection(self.collection_name):
                if force_recreate:
                    logger.info(f"删除已存在的集合: {self.collection_name}")
                    self.client.drop_collection(self.collection_name)
                else:
                    logger.info(f"集合 {self.collection_name} 已存在")
                    self.collection_created = True
                    return True

            # 创建集合
            schema = self._create_collection_schema()

            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                metric_type="COSINE",  # 使用余弦相似度
                consistency_level="Strong"
            )

            logger.info(f"成功创建集合: {self.collection_name}")
            self.collection_created = True

            return True

        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False

    def create_index(self) -> bool:
        """
        创建向量索引

        Returns:
            是否创建成功
        """
        try:
            if not self.collection_created:
                raise ValueError("请先创建集合")

            # 使用prepare_index_params创建正确的IndexParams对象
            # 添加向量字段索引时，确保使用正确的参数结构和类型，以满足 Milvus 的要求。
            sparse_index_params: IndexParams = self.client.prepare_index_params()
            sparse_index_params.add_index(
                field_name="sparse_vector",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
                params={
                    "inverted_index_algo": "DAAT_MAXSCORE",
                    "bm25_k1": 1.2,  # 控制词频饱和度。数值越高，术语频率在文档排名中的重要性就越大。取值范围[1.2, 2.0].
                    "bm25_b": 0.75  # 控制文档长度的标准化程度。通常使用 0 到 1 之间的值，默认值为 0.75 左右。值为 1 表示不进行长度归一化，值为 0 表示完全归一化。
                }
            )
            self.client.create_index(
                collection_name=self.collection_name,
                index_params=sparse_index_params
            )

            dense_index_params: IndexParams = self.client.prepare_index_params()
            dense_index_params.add_index(
                field_name="dense_vector",
                index_type="HNSW",
                metric_type="COSINE",
                params={
                    "M": 16,  # 每个节点的连接数，较小的 M 可以提高搜索效率，但可能降低召回率；较大的 M 可以提高召回率，
                    "efConstruction": 200  # 构建索引时的搜索深度，较大的 efConstruction 可以提高索引质量，但会增加构建时间和内存使用.
                }
            )

            self.client.create_index(
                collection_name=self.collection_name,
                index_params=dense_index_params
            )

            logger.info("向量索引创建成功")
            return True

        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return False

    def build_vector_index(self, chunks: List[ChunkRecord]) -> bool:
        """
        构建向量索引

        Args:
            chunks: 文档块列表

        Returns:
            是否构建成功
        """
        logger.info(f"正在构建Milvus向量索引，文档数量: {len(chunks)}...")

        if not chunks:
            raise ValueError("文档块列表不能为空")

        try:
            # 1. 创建集合（如果schema不兼容则强制重新创建）
            if not self.create_collection(force_recreate=True):
                return False

            # 2. 准备数据
            logger.info("正在生成向量embeddings...")
            texts = [chunk.content for chunk in chunks]
            vectors = self.embedding_model(texts)

            # 3. 准备插入数据
            entities = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                entity = {
                    "file_id": chunk.file_id,
                    "file_md5": self._safe_truncate(chunk.file_md5, 64),
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "section": self._safe_truncate(chunk.section, 255),
                    "content": self._safe_truncate(chunk.content, 4096),
                    "sparse_vector": vector["sparse"],
                    "dense_vector": vector["dense"],
                    "metadata": chunk.metadata or {}
                }
                entities.append(entity)

            # 4. 批量插入数据
            logger.info("正在插入向量数据...")
            batch_size = 100
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i + batch_size]
                self.client.insert(
                    collection_name=self.collection_name,
                    data=batch
                )
                logger.info(f"已插入 {min(i + batch_size, len(entities))}/{len(entities)} 条数据")

            # 5. 创建索引
            if not self.create_index():
                return False

            # 6. 加载集合到内存
            self.client.load_collection(self.collection_name)
            logger.info("集合已加载到内存")

            # 7. 等待索引构建完成
            logger.info("等待索引构建完成...")
            time.sleep(2)

            logger.info(f"向量索引构建完成，包含 {len(chunks)} 个向量")
            return True

        except Exception as e:
            logger.error(f"构建向量索引失败: {e}")
            return False

    def add_documents(self, new_chunks: List[ChunkRecord]) -> bool:
        """
        向现有索引添加新文档

        Args:
            new_chunks: 新的文档块列表

        Returns:
            是否添加成功
        """
        if not self.collection_created:
            raise ValueError("请先构建向量索引")

        logger.info(f"正在添加 {len(new_chunks)} 个新文档到索引...")

        try:
            # 生成向量
            texts: list[str] = [chunk.content for chunk in new_chunks]
            vectors = self.embedding_model(texts)

            # 准备插入数据
            entities = []
            for i, (chunk, vector) in enumerate(zip(new_chunks, vectors)):
                entity = {
                    "file_id": chunk.file_id,
                    "file_md5": self._safe_truncate(chunk.file_md5, 64),
                    "chunk_index": chunk.chunk_index,
                    "page_no": chunk.page_no or 0,
                    "section": self._safe_truncate(chunk.section, 255),
                    "content": self._safe_truncate(chunk.content, 4096),
                    "sparse_vector": vector["sparse"],
                    "dense_vector": vector["dense"],
                    "metadata": chunk.metadata or {}
                }
                entities.append(entity)

            # 插入数据
            self.client.insert(
                collection_name=self.collection_name,
                data=entities
            )

            logger.info("新文档添加完成")
            return True

        except Exception as e:
            logger.error(f"添加新文档失败: {e}")
            return False

    def similarity_search(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[
        Dict[str, Any]]:
        """
        TODO: 相似度搜索(还未完善)

        Args:
            query: 查询文本
            k: 返回结果数量
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        if not self.collection_created:
            raise ValueError("请先构建或加载向量索引")

        try:
            # 生成查询向量
            query_vector = self.embedding_model([query])["dense"][0]

            # 构建过滤表达式
            filter_expr = ""
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        filter_conditions.append(f'{key} == "{value}"')
                    elif isinstance(value, (int, float)):
                        filter_conditions.append(f'{key} == {value}')
                    elif isinstance(value, list):
                        # 支持IN操作
                        if all(isinstance(v, str) for v in value):
                            value_str = '", "'.join(value)
                            filter_conditions.append(f'{key} in ["{value_str}"]')
                        else:
                            value_str = ', '.join(map(str, value))
                            filter_conditions.append(f'{key} in [{value_str}]')

                if filter_conditions:
                    filter_expr = " and ".join(filter_conditions)

            # 执行搜索 - 修复参数传递
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64}  # HNSW搜索参数，ef值越大召回率越高，但搜索速度越慢。可以根据需要调整这个值以平衡性能和准确性。
            }

            # 构建搜索参数，避免重复传递
            search_kwargs = {
                "collection_name": self.collection_name,
                "data": [query_vector],
                "anns_field": "vector",
                "limit": k,
                "output_fields": ["file_id", "file_md5", "chunk_index", "page_no", "section", "content", "metadata"],
                "search_params": search_params
            }

            # 只在有过滤条件时添加filter参数
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            results = self.client.search(**search_kwargs)

            # 处理结果
            formatted_results = []
            if results and len(results) > 0:
                for hit in results[0]:  # results[0]因为我们只发送了一个查询向量
                    result = {
                        "id": hit["id"],
                        "score": hit["distance"],  # 注意：在COSINE距离中，值越大相似度越高
                        "text": hit["entity"]["text"],
                        "metadata": {
                            "file_id": hit["entity"]["file_id"],
                            "file_md5": hit["entity"]["file_md5"],
                            "chunk_index": hit["entity"]["chunk_index"],
                            "page_no": hit["entity"]["page_no"],
                            "section": hit["entity"]["section"],
                            "content": hit["entity"]["content"],
                            "metadata": hit["entity"]["metadata"],
                        }
                    }
                    formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息字典
        """
        try:
            if not self.collection_created:
                return {"error": "集合未创建"}

            stats = self.client.get_collection_stats(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "row_count": stats.get("row_count", 0),
                "index_building_progress": stats.get("index_building_progress", 0),
                "stats": stats
            }

        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {"error": str(e)}

    def delete_collection(self) -> bool:
        """
        删除集合

        Returns:
            是否删除成功
        """
        try:
            if self.client.has_collection(self.collection_name):
                self.client.drop_collection(self.collection_name)
                logger.info(f"集合 {self.collection_name} 已删除")
                self.collection_created = False
                return True
            else:
                logger.info(f"集合 {self.collection_name} 不存在")
                return True

        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    def has_collection(self) -> bool:
        """
        检查集合是否存在

        Returns:
            集合是否存在
        """
        try:
            return self.client.has_collection(self.collection_name)
        except Exception as e:
            logger.error(f"检查集合存在性失败: {e}")
            return False

    def load_collection(self) -> bool:
        """
        加载集合到内存

        Returns:
            是否加载成功
        """
        try:
            if not self.client.has_collection(self.collection_name):
                logger.error(f"集合 {self.collection_name} 不存在")
                return False

            self.client.load_collection(self.collection_name)
            self.collection_created = True
            logger.info(f"集合 {self.collection_name} 已加载到内存")
            return True

        except Exception as e:
            logger.error(f"加载集合失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if hasattr(self, 'client') and self.client:
            # Milvus客户端不需要显式关闭
            logger.info("Milvus连接已关闭")

    def __del__(self):
        """析构函数"""
        self.close()
