from dataclasses import dataclass
from typing import Optional


@dataclass
class TextChunkMetadata:
    file_directory: Optional[str] = None
    filename: Optional[str] = None
    filetype: Optional[str] = None
    page_number: Optional[int] = None
    page_title: Optional[str] = None
    image_urls: Optional[list[str]] = None
    last_modified: Optional[str] = None


@dataclass
class TextChunk:
    chunk_index: int
    chunk_text: str
    chunk_size: int
    chunk_id: Optional[str] = None
    metadata: Optional[TextChunkMetadata] = None


@dataclass
class ChunkRecord:
    file_id: int
    file_md5: str
    chunk_index: int
    chunk_size: int
    page_no: Optional[int]
    section: Optional[str]
    content: Optional[str]
    metadata: Optional[TextChunkMetadata] = None
