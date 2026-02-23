from typing import Iterable

import pytest
from unstructured.documents.elements import Element

from app.schemas import TextChunk, ChunkRecord
from app.services.vectorization import BgeM3Embedder, DocumentParser, TextChunker
from app.services.vectorization import MilvusVectorStore


@pytest.mark.integration
async def test_hybrid_search():
    client = MilvusVectorStore(uri="http://localhost:19530", collection_name="knowledge_base", dim=1024)
    parser = DocumentParser()
    chunker = TextChunker(chunk_size=1000, overlap=200)

    # ================== 确保 Milvus collection 已创建 ==================
    if not client.collection_created:
        await client.create_collection(force_recreate=True)
        await client.create_index(skip_if_exists=True)

    # ================== 解析文档，得到 Element 列表 ==================
    file_path = r"E:\WorkSpace\PyCharmProject\My-RAG-Demo\backend\app\tests\data\C2\md\派聪明RAG知识库检索面试题预测.md"
    elements: list[Element] = parser.parse(file_path=file_path,
                                           content_type="text/markdown")

    # ==================== 通过标题划分文本 ==================
    chunk_iter: Iterable[TextChunk] = chunker.chunk_elements_by_title(elements=elements)

    # ================== 写入向量数据库 ==================
    records: list[ChunkRecord] = []
    batch_size = 128
    for chunk in chunk_iter:
        records.append(
            ChunkRecord(
                file_id=666,
                file_md5="unknown",
                content=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                chunk_size=chunk.chunk_size,
                page_no=chunk.metadata.page_number
                if chunk.metadata is not None
                else None,
                section=chunk.metadata.page_title
                if chunk.metadata is not None
                else None,
                metadata=chunk.metadata,
            )
        )

        if len(records) >= batch_size:
            await client.add_documents(records)
            records = []

    if records:
        await client.add_documents(records)

    # ================== 加载 Milvus collection ==================
    await client.load_collection()

    # ================== 执行 BM25 搜索和 Dense 搜索 ==================
    query_text = "为什么先用ES，而不是直接用FAISS？"

    embedder = BgeM3Embedder(model_name="BAAI/bge-m3", device="cpu", use_fp16=False)
    vector = embedder.encode_queries(texts=[query_text])
    dense_vector = vector.get("dense")[0]

    res_bm25 = await client.search_bm25(query=query_text, k=1)
    res_dense = await client.search_dense(query_vector=dense_vector, k=1)

    print(res_bm25 or "没有 BM25 搜索结果")
    print("\n\n======================")
    print(res_dense or "没有 Dense 搜索结果")


@pytest.mark.integration
async def test_hybrid_search_2():
    client = MilvusVectorStore(uri="http://localhost:19530", collection_name="knowledge_base", dim=1024)
    # ================== 确保 Milvus collection 已创建 ==================
    if not client.collection_created:
        await client.create_collection(force_recreate=False)

    # ================== 执行 BM25 搜索和 Dense 搜索 ==================
    query_text = "请详细描述完整的RAG系统架构，包括主要组件和数据流向"

    embedder = BgeM3Embedder(model_name="BAAI/bge-m3", device="cpu", use_fp16=False)
    vector = embedder.encode_queries(texts=[query_text])
    dense_vector = vector.get("dense")[0]

    res_bm25 = await client.search_bm25(query=query_text, k=1)
    res_dense = await client.search_dense(query_vector=dense_vector, k=1)

    print(res_bm25 or "没有 BM25 搜索结果")
    print("\n\n======================")
    print(res_dense or "没有 Dense 搜索结果")