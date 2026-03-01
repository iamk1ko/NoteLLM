import os

import openai
import pytest
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from openai.types import CreateEmbeddingResponse
from pydantic import SecretStr

load_dotenv()


@pytest.mark.integration
def test_glm3_embedding_model_by_openai():
    client = openai.OpenAI(
        api_key=os.environ["BLSC_API_KEY"],
        base_url=os.environ["BLSC_BASE_URL"].rstrip("/") + "/v1/",
    )

    response: CreateEmbeddingResponse = client.embeddings.create(
        model="GLM-Embedding-3",
        input=["需要转embedding的内容"],
        dimensions=1024,
    )

    # response.data[0].embedding: List[float]，长度为1024
    print(response.data[0].embedding[0:10], len(response.data[0].embedding))


@pytest.mark.integration
async def test_glm3_embedding_model_by_langchain_openai():
    embedding_model = OpenAIEmbeddings(model="GLM-Embedding-3",
                                       dimensions=1024,
                                       base_url=os.environ["BLSC_BASE_URL"],
                                       api_key=SecretStr(os.environ["BLSC_API_KEY"]))

    # 同步调用
    # query_vector: list[float] = embedding_model.embed_query(text="需要转embedding的内容")
    # documents_vector: list[list[float]] = embedding_model.embed_documents(
    #     texts=["需要转embedding的内容", "需要转embedding的内容2"])

    # 异步调用
    query_vector: list[float] = await embedding_model.aembed_query(text="需要转embedding的内容")
    documents_vector: list[list[float]] = await embedding_model.aembed_documents(
        texts=["需要转embedding的内容", "需要转embedding的内容2"])
    print(query_vector[0:10], len(query_vector))
    print(documents_vector[0][0:10], len(documents_vector[0]))
