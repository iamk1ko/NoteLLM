from __future__ import annotations

from typing import Iterable

from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element, ElementType

from app.schemas import TextChunk, TextChunkMetadata


class TextChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size if chunk_size > 0 else 1000
        self.overlap = min(max(0, overlap), max(0, self.chunk_size - 1))

    def chunk_elements(self, elements: Iterable[Element]) -> Iterable[TextChunk]:
        chunks: list[Element] = chunk_by_title(
            elements=elements, max_characters=self.chunk_size, overlap=self.overlap
        )
        for index, chunk in enumerate(chunks):
            orig_elements: list[Element] = (
                list(chunk.metadata.orig_elements)
                if chunk.metadata and chunk.metadata.orig_elements
                else []
            )  # 构成 CompositeElement 的所有原始元素列表
            chunk_id = chunk.id
            chunk_index = index
            text = chunk.text.strip()

            page_titles: list[str] = []
            image_urls: list[str] = []
            for orig in orig_elements:
                if orig.category == ElementType.TITLE:
                    page_titles.append(orig.text.strip())
                elif orig.category == ElementType.IMAGE and orig.metadata.image_url:
                    image_urls.append(orig.metadata.image_url)

            metadata: TextChunkMetadata | None = (
                TextChunkMetadata(
                    file_directory=chunk.metadata.file_directory,
                    filename=chunk.metadata.filename,
                    filetype=chunk.metadata.filetype,
                    page_number=chunk.metadata.page_number,
                    page_title=page_titles[0] if page_titles else None,
                    image_urls=image_urls if image_urls else None,
                    last_modified=chunk.metadata.last_modified,
                )
                if chunk.metadata
                else None
            )

            yield TextChunk(
                chunk_id=chunk_id,
                chunk_index=chunk_index,
                chunk_text=text,
                chunk_size=len(text.split()),
                metadata=metadata,
            )
