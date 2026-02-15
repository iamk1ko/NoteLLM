from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.md import partition_md

from app.services.vectorization.doc_converter import DocConverter


@dataclass
class ParsedElement:
    text: str
    page_no: int | None = None
    section: str | None = None


class DocumentParser:
    def parse(self, file_path: str, content_type: str) -> Iterable[ParsedElement]:
        if content_type == "application/pdf" or file_path.lower().endswith(".pdf"):
            elements = partition_pdf(filename=file_path)
        elif content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            docx_path = file_path
            if content_type == "application/msword" or file_path.lower().endswith(
                ".doc"
            ):
                docx_path = DocConverter.to_docx(file_path)
            elements = partition_docx(filename=docx_path)
        elif content_type == "text/markdown" or file_path.lower().endswith(".md"):
            elements = partition_md(filename=file_path)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        for element in elements:
            text = getattr(element, "text", "") or ""
            if not text.strip():
                continue
            metadata = getattr(element, "metadata", None)
            page_no = getattr(metadata, "page_number", None) if metadata else None
            section = getattr(metadata, "section", None) if metadata else None
            yield ParsedElement(text=text, page_no=page_no, section=section)
