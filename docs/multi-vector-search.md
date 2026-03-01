# 多向量混合搜索

在许多应用中，可以通过标题和描述等丰富的信息集或文本、图像和音频等多种模式来搜索对象。例如，如果文本或图片与搜索查询的语义相符，就可以搜索包含一段文本和一张图片的推文。混合搜索将这些不同领域的搜索结合在一起，从而增强了搜索体验。Milvus 允许在多个向量场上进行搜索，同时进行多个近似近邻（ANN）搜索，从而支持这种搜索。如果要同时搜索文本和图像、描述同一对象的多个文本字段或密集和稀疏向量以提高搜索质量，多向量混合搜索尤其有用。

![Hybrid Search Workflow](https://milvus.io/docs/v2.6.x/assets/hybrid-search-workflow.png)混合搜索工作流程

多向量混合搜索集成了不同的搜索方法或跨越了各种模态的 Embeddings：

- **稀疏-密集向量搜索**：[密集向量](https://milvus.io/docs/zh/dense-vector.md)是捕捉语义关系的绝佳方法，而[稀疏向量](https://milvus.io/docs/zh/sparse_vector.md)则是精确匹配关键词的高效方法。混合搜索结合了这些方法，既能提供广泛的概念理解，又能提供精确的术语相关性，从而改善搜索结果。通过利用每种方法的优势，混合搜索克服了单独方法的局限性，为复杂查询提供了更好的性能。以下是结合语义搜索和全文搜索的混合检索的详细[指南](https://milvus.io/docs/zh/full_text_search_with_milvus.md)。
- **多模态向量搜索**：多模态向量搜索是一种功能强大的技术，可以跨文本、图像、音频等各种数据类型进行搜索。这种方法的主要优势在于它能将不同的模式统一为一种无缝、连贯的搜索体验。例如，在产品搜索中，用户可能会输入一个文本查询来查找用文本和图像描述的产品。通过混合搜索方法将这些模式结合起来，可以提高搜索准确性或丰富搜索结果。

## 示例

让我们考虑一个真实世界的使用案例，其中每个产品都包含文字描述和图片。根据可用数据，我们可以进行三种类型的搜索：

- **语义文本搜索：**这涉及使用密集向量查询产品的文本描述。可以使用[BERT](https://zilliz.com/learn/explore-colbert-token-level-embedding-and-ranking-model-for-similarity-search?_gl=1*d243m9*_gcl_au*MjcyNTAwMzUyLjE3NDMxMzE1MjY.*_ga*MTQ3OTI4MDc5My4xNzQzMTMxNTI2*_ga_KKMVYG8YF2*MTc0NTkwODU0Mi45NC4xLjE3NDU5MDg4MzcuMC4wLjA.&__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b#A-Quick-Recap-of-BERT)和[Transformers](https://zilliz.com/learn/NLP-essentials-understanding-transformers-in-AI?_gl=1*d243m9*_gcl_au*MjcyNTAwMzUyLjE3NDMxMzE1MjY.*_ga*MTQ3OTI4MDc5My4xNzQzMTMxNTI2*_ga_KKMVYG8YF2*MTc0NTkwODU0Mi45NC4xLjE3NDU5MDg4MzcuMC4wLjA.&__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b)等模型或[OpenAI](https://zilliz.com/learn/guide-to-using-openai-text-embedding-models?__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b) 等服务生成文本嵌入。
- **全文搜索**：在这里，我们使用稀疏向量的关键词匹配来查询产品的文本描述。[BM25](https://zilliz.com/learn/mastering-bm25-a-deep-dive-into-the-algorithm-and-application-in-milvus?__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b)等算法或[BGE-M3](https://zilliz.com/learn/bge-m3-and-splade-two-machine-learning-models-for-generating-sparse-embeddings?_gl=1*1cde1oq*_gcl_au*MjcyNTAwMzUyLjE3NDMxMzE1MjY.*_ga*MTQ3OTI4MDc5My4xNzQzMTMxNTI2*_ga_KKMVYG8YF2*MTc0NTkwODU0Mi45NC4xLjE3NDU5MDg4MzcuMC4wLjA.&__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b#BGE-M3)或[SPLADE](https://zilliz.com/learn/bge-m3-and-splade-two-machine-learning-models-for-generating-sparse-embeddings?_gl=1*ov2die*_gcl_au*MjcyNTAwMzUyLjE3NDMxMzE1MjY.*_ga*MTQ3OTI4MDc5My4xNzQzMTMxNTI2*_ga_KKMVYG8YF2*MTc0NTkwODU0Mi45NC4xLjE3NDU5MDg4MzcuMC4wLjA.&__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b#SPLADE)等稀疏嵌入模型可用于此目的。
- **多模态图像搜索：**这种方法使用带有密集向量的文本查询对图像进行查询。可以使用[CLIP](https://zilliz.com/learn/exploring-openai-clip-the-future-of-multimodal-ai-learning?__hstc=175614333.513b174d691b949c7f33116c91c0e029.1770622204106.1772093953084.1772379450027.19&__hssc=175614333.2.1772379450027&__hsfp=fd8a7967bb1a6a3c0c50028297922b7b) 等模型生成图像嵌入。

本指南将引导您通过一个结合上述搜索方法的多模态混合搜索示例，给出产品的原始文本描述和图像嵌入。我们将演示如何存储多向量数据并使用 Rerankers 策略执行混合搜索。

## 创建具有多个向量场的 Collections

创建 Collections 的过程包括三个关键步骤：定义 Collections Schema、配置索引参数和创建 Collections。

### 定义 Schema

对于多向量混合搜索，我们应该在一个 Collection 模式中定义多个向量字段。有关集合中允许的向量字段数量限制的详细信息，请参阅[Zilliz Cloud Limits](https://zilliverse.feishu.cn/wiki/PuxkwMWvbiHxvTkHsVkcMZP9n5f#E5yxdHM16okh57xV3WKcTJsYn0f)。 不过，如有必要，您可以调整 [`proxy.maxVectorFieldNum`](https://milvus.io/docs/zh/configure_proxy.md#proxymaxVectorFieldNum)以根据需要在集合中最多包含 10 个向量字段。

此示例将以下字段纳入 Schema 模式：

- `id`:作为存储文本 ID 的主键。该字段的数据类型为`INT64` 。
- `text`:用于存储文本内容。该字段的数据类型为`VARCHAR` ，最大长度为 1000 字节。`enable_analyzer` 选项设置为`True` ，以便于全文检索。
- `text_dense`:用于存储文本的密集向量。该字段的数据类型为`FLOAT_VECTOR` ，向量维数为 768。
- `text_sparse`:用于存储文本的稀疏向量。该字段的数据类型为`SPARSE_FLOAT_VECTOR` 。
- `image_dense`:用于存储产品图像的密集向量。该字段的数据类型为`FLOAT_VETOR` ，向量维数为 512。

由于我们将使用内置的 BM25 算法对文本字段进行全文检索，因此有必要在 Schema 中添加 Milvus`Function` 。有关详细信息，请参阅[全文搜索](https://milvus.io/docs/zh/full-text-search.md)。

```python
from pymilvus import (
    MilvusClient, DataType, Function, FunctionType
)

client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

# Init schema with auto_id disabled
schema = client.create_schema(auto_id=False)

# Add fields to schema
schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, description="product id")
schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=1000, enable_analyzer=True, description="raw text of product description")
schema.add_field(field_name="text_dense", datatype=DataType.FLOAT_VECTOR, dim=768, description="text dense embedding")
schema.add_field(field_name="text_sparse", datatype=DataType.SPARSE_FLOAT_VECTOR, description="text sparse embedding auto-generated by the built-in BM25 function")
schema.add_field(field_name="image_dense", datatype=DataType.FLOAT_VECTOR, dim=512, description="image dense embedding")

# Add function to schema
bm25_function = Function(
    name="text_bm25_emb",
    input_field_names=["text"],
    output_field_names=["text_sparse"],
    function_type=FunctionType.BM25,
)
schema.add_function(bm25_function)




```

### 创建索引

定义完 Collections Schema 后，下一步就是配置向量索引并指定相似度指标。在给出的示例中

- `text_dense_index`：为文本密集向量字段创建了`AUTOINDEX` 类型的索引，其度量类型为`IP` 。
- `text_sparse_index`：为文本稀疏向量场创建了`SPARSE_INVERTED_INDEX`类型的索引，其度量类型为`BM25` 。
- `image_dense_index`：为图像密集向量场创建了`AUTOINDEX` 类型的索引，其公制类型为`IP` 。

您可以根据需要选择其他索引类型，以最适合您的需求和数据类型。有关支持的索引类型的详细信息，请参阅[可用索引类型](https://milvus.io/docs/zh/index-vector-fields.md)文档。

```python
# Prepare index parameters
index_params = client.prepare_index_params()

# Add indexes
index_params.add_index(
    field_name="text_dense",
    index_name="text_dense_index",
    index_type="AUTOINDEX",
    metric_type="IP"
)

index_params.add_index(
    field_name="text_sparse",
    index_name="text_sparse_index",
    index_type="SPARSE_INVERTED_INDEX",
    metric_type="BM25",
    params={"inverted_index_algo": "DAAT_MAXSCORE"}, # or "DAAT_WAND" or "TAAT_NAIVE"
)

index_params.add_index(
    field_name="image_dense",
    index_name="image_dense_index",
    index_type="AUTOINDEX",
    metric_type="IP"
)




```

### 创建 Collections

使用前两个步骤中配置的 Collection Schema 和索引创建名为`demo` 的 Collection。

```python
client.create_collection(
    collection_name="my_collection",
    schema=schema,
    index_params=index_params
)




```

## 插入数据

本节根据前面定义的 Schema 将数据插入`my_collection` Collection。在插入过程中，确保所有字段（有自动生成值的字段除外）的数据格式正确。在本例中

- `id`代表产品 ID 的整数
- `text`：包含产品描述的字符串
- `text_dense`一个包含 768 个浮点数值的列表，表示文本描述的密集 Embeddings
- `image_dense`代表产品图片密集嵌入的 512 个浮点数值的列表

您可以使用相同或不同的模型为每个字段生成密集嵌入。在本例中，两个高密度嵌入的维度不同，说明它们是由不同的模型生成的。以后定义每个查询时，请务必使用相应的模型生成相应的查询嵌入。

由于本示例使用内置的 BM25 函数从文本字段生成稀疏嵌入，因此无需手动提供稀疏向量。但是，如果您选择不使用 BM25，则必须自己预先计算并提供稀疏嵌入。

```python
import random

# Generate example vectors
def generate_dense_vector(dim):
    return [random.random() for _ in range(dim)]

data=[
    {
        "id": 0,
        "text": "Red cotton t-shirt with round neck",
        "text_dense": generate_dense_vector(768),
        "image_dense": generate_dense_vector(512)
    },
    {
        "id": 1,
        "text": "Wireless noise-cancelling over-ear headphones",
        "text_dense": generate_dense_vector(768),
        "image_dense": generate_dense_vector(512)
    },
    {
        "id": 2,
        "text": "Stainless steel water bottle, 500ml",
        "text_dense": generate_dense_vector(768),
        "image_dense": generate_dense_vector(512)
    }
]

res = client.insert(
    collection_name="my_collection",
    data=data
)




```

## 执行混合搜索

### 步骤 1：创建多个 AnnSearchRequest 实例

混合搜索是通过在`hybrid_search()` 函数中创建多个`AnnSearchRequest` 来实现的，其中每个`AnnSearchRequest` 代表一个特定向量场的基本 ANN 搜索请求。因此，在进行混合搜索之前，有必要为每个向量场创建一个`AnnSearchRequest` 。

此外，通过在`AnnSearchRequest` 中配置`expr` 参数，可以为混合搜索设置过滤条件。请参阅[过滤搜索](https://milvus.io/docs/zh/filtered-search.md)和[过滤说明](https://milvus.io/docs/zh/boolean.md)。

在混合搜索中，每个`AnnSearchRequest` 只支持一个查询数据。

为了演示各种搜索向量字段的功能，我们将使用一个示例查询构建三个`AnnSearchRequest` 搜索请求。在此过程中，我们还将使用其预先计算的密集向量。搜索请求将针对以下向量场：

- `text_dense` 语义文本搜索，允许基于意义而非直接关键词匹配进行上下文理解和检索。
- `text_sparse`全文搜索或关键词匹配，侧重于文本中精确匹配的单词或短语。
- `image_dense`多模态文本到图片搜索，根据查询的语义内容检索相关产品图片。

```python
from pymilvus import AnnSearchRequest

query_text = "white headphones, quiet and comfortable"
query_dense_vector = generate_dense_vector(768)
query_multimodal_vector = generate_dense_vector(512)

# text semantic search (dense)
search_param_1 = {
    "data": [query_dense_vector],
    "anns_field": "text_dense",
    "param": {"nprobe": 10},
    "limit": 2
}
request_1 = AnnSearchRequest(**search_param_1)

# full-text search (sparse)
search_param_2 = {
    "data": [query_text],
    "anns_field": "text_sparse",
    "limit": 2
}
request_2 = AnnSearchRequest(**search_param_2)

# text-to-image search (multimodal)
search_param_3 = {
    "data": [query_multimodal_vector],
    "anns_field": "image_dense",
    "param": {"nprobe": 10},
    "limit": 2
}
request_3 = AnnSearchRequest(**search_param_3)

reqs = [request_1, request_2, request_3]




```

参数`limit` 设置为 2 时，每个`AnnSearchRequest` 会返回 2 个搜索结果。在本示例中，创建了 3 个`AnnSearchRequest` 实例，总共产生了 6 个搜索结果。

### 步骤 2：配置 Rerankers 策略

要对 ANN 搜索结果集进行合并和重新排序，选择适当的重新排序策略至关重要。Milvus 提供多种重排策略。有关这些重排机制的更多详情，请参阅[加权排名器](https://milvus.io/docs/zh/weighted-ranker.md)或[RRF 排名器](https://milvus.io/docs/zh/rrf-ranker.md)。

在本例中，由于没有特别强调特定的搜索查询，我们将使用 RRFRanker 策略。

```python
ranker = Function(
    name="rrf",
    input_field_names=[], # Must be an empty list
    function_type=FunctionType.RERANK,
    params={
        "reranker": "rrf", 
        "k": 100  # Optional
    }
)




```

### 步骤 3：执行混合搜索

在启动混合搜索之前，请确保已加载 Collections。如果集合中的任何向量字段缺少索引或未加载到内存中，执行混合搜索方法时就会出错。

```python
res = client.hybrid_search(
    collection_name="my_collection",
    reqs=reqs,
    ranker=ranker,
    limit=2
)
for hits in res:
    print("TopK results:")
    for hit in hits:
        print(hit)




```

输出结果如下：

```python
["['id: 1, distance: 0.006047376897186041, entity: {}', 'id: 2, distance: 0.006422005593776703, entity: {}']"]
```

在为混合搜索指定`limit=2` 参数后，Milvus 将对三次搜索得到的六个结果进行 Rerankers 排序。最终，它们将只返回最相似的前两个结果。