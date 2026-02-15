from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class TextChunk:
    chunk_index: int
    chunk_text: str
    chunk_tokens: int
    page_no: int | None = None
    section: str | None = None


class TextChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = min(overlap, max(0, chunk_size - 1))

    def chunk_elements(self, elements: Iterable[object]) -> Iterable[TextChunk]:
        index = 0
        for element in elements:
            text = getattr(element, "text", "") or ""
            page_no = getattr(element, "page_no", None)
            section = getattr(element, "section", None)
            for chunk in self._chunk_text(text, index, page_no, section):
                yield chunk
                index += 1

    def _chunk_text(
        self,
        text: str,
        start_index: int,
        page_no: int | None,
        section: str | None,
    ) -> Iterable[TextChunk]:
        words = text.split()
        if not words:
            return

        index = start_index
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            yield TextChunk(
                chunk_index=index,
                chunk_text=chunk_text,
                chunk_tokens=len(chunk_words),
                page_no=page_no,
                section=section,
            )
            index += 1
            if end == len(words):
                break
            start = max(0, end - self.overlap)
