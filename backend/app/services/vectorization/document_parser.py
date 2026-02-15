from __future__ import annotations

from unstructured.documents.elements import Element
from unstructured.partition.docx import partition_docx
from unstructured.partition.md import partition_md
from unstructured.partition.pdf import partition_pdf

from app.services.vectorization.doc_converter import DocConverter


class DocumentParser:
    @staticmethod
    def parse(file_path: str, content_type: str) -> list[Element]:
        if content_type == "application/pdf" or file_path.lower().endswith(".pdf"):
            elements: list[Element] = partition_pdf(filename=file_path)
        elif content_type in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
        ):
            docx_path = file_path
            if content_type == "application/msword" or file_path.lower().endswith(
                    ".doc"
            ):
                docx_path = DocConverter.to_docx(file_path)
            elements: list[Element] = partition_docx(filename=docx_path)
        elif content_type == "text/markdown" or file_path.lower().endswith(".md"):
            elements: list[Element] = partition_md(filename=file_path)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        return elements
