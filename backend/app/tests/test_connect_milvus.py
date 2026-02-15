import pytest
from pymilvus import MilvusClient, connections, utility
from app.services.vectorization import MilvusVectorStore

from app.core.settings import get_settings


@pytest.mark.integration
def test_connect_milvus():
    # 测试连接 Milvus 并获取集合列表
    try:
        settings = get_settings()
        MilvusVectorStore(uri=settings.MILVUS_URI, collection_name="knowledge_base", dim=settings.EMBEDDING_DIM)

        alias = "default"
        connections.connect(alias=alias, uri=settings.MILVUS_URI)
        print(utility.list_collections(using=alias))

        client = MilvusClient(uri=settings.MILVUS_URI)
        print(client.list_collections())
        print(client.describe_collection(collection_name="knowledge_base"))

        client.drop_collection(collection_name="knowledge_base")
        print(client.list_collections())

    except Exception as e:
        pytest.fail(f"Failed to connect to Milvus: {e}")


@pytest.mark.integration
def test_milvus_tokenizer():
    analyzer_params = {
        "tokenizer": "icu",
    }

    settings = get_settings()

    connections.connect(uri=settings.MILVUS_URI)
    client = MilvusClient(uri=settings.MILVUS_URI)

    text = "Java语言相比于Python语言更适合开发大型企业级应用，因为它具有更强的类型安全性和更丰富的库支持。"

    result = client.run_analyzer(
        text,
        analyzer_params
    )

    print(result)


@pytest.mark.integration
def test_milvus_bgem3_embedding():
    print("--> 正在初始化 BGE-M3 嵌入模型...")
    from pymilvus.model.hybrid import BGEM3EmbeddingFunction

    bge_m3_ef = BGEM3EmbeddingFunction(
        model_name='BAAI/bge-m3',  # 指定模型名称
        device='cpu',  # 指定要使用的设备，例如 'cpu' 或 'cuda:0'
        use_fp16=False  # 指定是否使用 fp16。如果 `device` 是 `cpu`，则设置为 `False`。
    )
    print(f"--> 嵌入模型初始化完成。密集向量维度: {bge_m3_ef.dim['dense']}")

    docs = [
        "Artificial intelligence was founded as an academic discipline in 1956.",
        "Alan Turing was the first person to conduct substantial research in AI.",
        "Born in Maida Vale, London, Turing was raised in southern England.",
    ]

    docs_embeddings = bge_m3_ef.encode_documents(docs)

    # 打印嵌入向量
    print("Embeddings:", docs_embeddings.keys())
    # 打印密集嵌入向量的维度
    print("Dense document dim:", bge_m3_ef.dim["dense"], docs_embeddings["dense"][0].shape)
    # 由于稀疏嵌入向量是 2D csr_array 格式，我们将其转换为列表以便于操作。
    print("Sparse document dim:", bge_m3_ef.dim["sparse"], list(docs_embeddings["sparse"])[0].shape)

    print(f"--> 正在编码查询...")
    queries = ["When was artificial intelligence founded",
               "Where was Alan Turing born?"]

    query_embeddings = bge_m3_ef.encode_queries(queries)

    # 打印嵌入向量
    print("Embeddings:", query_embeddings)
    # 打印密集嵌入向量的维度
    print("Dense query dim:", bge_m3_ef.dim["dense"], query_embeddings["dense"][0].shape)
    # 由于稀疏嵌入向量是 2D csr_array 格式，我们将其转换为列表以便于操作。
    print("Sparse query dim:", bge_m3_ef.dim["sparse"], list(query_embeddings["sparse"])[0].shape)
