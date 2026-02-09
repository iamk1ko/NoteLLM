from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

import pytest

loader = TextLoader("backend/app/tests/data/C2/txt/蜂医.txt")
docs = loader.load()


@pytest.mark.integration
def test_text_chunking():
    text_splitter = CharacterTextSplitter(
        chunk_size=200,  # 每个块的目标大小为100个字符
        chunk_overlap=10  # 每个块之间重叠10个字符，以缓解语义割裂
    )

    chunks = text_splitter.split_documents(docs)

    print(f"\n文本被切分为 {len(chunks)} 个块。\n")
    print("--- 前5个块内容示例 ---")
    for i, chunk in enumerate(chunks[:5]):
        print("=" * 60)
        # chunk 是一个 Document 对象，需要访问它的 .page_content 属性来获取文本
        print(f'块 {i + 1} (长度: {len(chunk.page_content)}): "{chunk.page_content}"')


@pytest.mark.integration
def test_text_chunking_with_recursive():
    text_splitter = RecursiveCharacterTextSplitter(
        # 针对中英文混合文本，定义一个更全面的分隔符列表
        separators=["\n\n", "\n", "。", "，", " ", ""],  # 按顺序尝试分割
        chunk_size=200,
        chunk_overlap=10
    )

    chunks = text_splitter.split_documents(docs)

    print(f"文本被切分为 {len(chunks)} 个块。\n")
    print("--- 前5个块内容示例 ---")
    for i, chunk in enumerate(chunks[:5]):
        print("=" * 60)
        print(f'块 {i + 1} (长度: {len(chunk.page_content)}): "{chunk.page_content}"')
