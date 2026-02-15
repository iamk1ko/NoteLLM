import pytest
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, Element, CompositeElement, ElementType, Text
from unstructured.partition.auto import partition
from unstructured.partition.html import partition_html
from unstructured.partition.md import partition_md
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.constants import PartitionStrategy
from unstructured.staging.base import elements_to_json


@pytest.mark.integration
def test_unstructured_auto():
    # PDF文件路径
    pdf_path = "backend/app/tests/data/C2/pdf/rag.pdf"

    # 使用Unstructured加载并解析PDF文档
    elements = partition(
        filename=pdf_path,
        content_type="application/pdf",
        strategy=PartitionStrategy.AUTO,
    )

    # 打印解析结果
    print(f"解析完成: {len(elements)} 个元素, {sum(len(str(e)) for e in elements)} 字符")

    # 统计元素类型
    from collections import Counter
    types = Counter(e.category for e in elements)
    print(f"元素类型: {dict(types)}")

    # 显示所有元素
    print("\n所有元素:")
    for i, element in enumerate(elements, 1):
        print(f"Element {i} ({element.category}):")
        print(element)
        print("=" * 60)


@pytest.mark.integration
def test_unstructured_partition_md():
    md_path = "backend/app/tests/data/C2/md/派聪明RAG文件上传解析面试题预测.md"

    elements = partition_md(
        filename=md_path,
        strategy=PartitionStrategy.AUTO,
    )

    # elements = partition_pdf(
    #     filename=md_path,
    #     strategy=PartitionStrategy.HI_RES,
    # )

    # chunks = chunk_elements(elements, max_characters=1000, overlap=200)

    # -- OR --
    chunks: list[Element] = chunk_by_title(elements, max_characters=1000, overlap=200)

    for chunk in chunks:
        orig_elements: list[Text] = chunk.metadata.orig_elements
        for orig in orig_elements:
            print(orig.metadata)
        # 查看构成 CompositeElement 的所有原始元素列表
        print(f"构成组合分片的子分片的元素列表: {orig_elements}, 一共包含 {len(orig_elements)} 个子分片")
        print(f"组合分片的ID: {chunk.id}")
        print(f"组合分片的类型: {chunk.category}")  # CompositeElement
        print(f"组合分片的页码（目前是None）: {chunk.metadata.page_number}")
        print(f"组合分片的文件类型: {chunk.metadata.filetype}")
        [print(f"当前组合分片的标题: {orig_element}") for orig_element in orig_elements if
         orig_element.category == ElementType.TITLE]
        print(f"0 号子分片元素的页码: {orig_elements[0].metadata.page_number}")
        print(f"0 号子分片元素的id: {orig_elements[0].id}")
        print(f"1 号子元素的父元素id: {orig_elements[1].metadata.parent_id}")
        [print(f"组合分片中包含的图片URL: {orig_element.metadata.image_url}") for orig_element in orig_elements if
         orig_element.category == ElementType.IMAGE]
        print(f"组合分片的文本内容：{chunk.text}")
        print("\n\n" + "-" * 80)

    print(f"解析完成: {len(elements)} 个元素, {sum(len(str(e)) for e in elements)} 字符")

    # elements_to_json(elements=elements, filename="./md_elements.json", encoding="utf-8")
    #
    # for element in elements:
    #     element: Element = element
    #     metadata: ElementMetadata = element.metadata
    #
    #     text = element.text
    #     if not text.strip():
    #         continue
    #
    #     print("=" * 60)
    #     print(f"元信息: {metadata}")
    #     print(f"元素ID: {element.id}")
    #     print(f"元素类型: {element.category}")
    #     print(f"文本: {text[:200]}..." if len(text) > 200 else f"文本: {text}")
    #     print(f"页码: {metadata.page_number}")
    #     print(f"父元素id: {metadata.parent_id}")
    #     print(f"元素文件类型: {metadata.filetype}")
    #     print(f"图片URL: {metadata.image_url}")


@pytest.mark.integration
def test_unstructured_chunking():
    url = "https://www.runoob.com/linux/linux-tutorial.html"
    elements = partition_html(url=url)
    chunks = chunk_elements(elements)

    # -- OR --
    chunks = chunk_by_title(elements)

    for chunk in chunks:
        print(chunk)
        print("\n\n" + "-" * 80)
        input()
