"""服务层（Services）包。

企业级约定：
- API 层可以使用 `from app.services import UserService`。
- 采用懒加载，避免在 import app.services 时加载全部 service（降低启动开销与循环依赖风险）。
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "ChatSessionService",
    "ChatMessageService",
    "FileStorageService",
    "UserService",
    "VectorizationService",
    "RagService",
    "DocumentParser",
    "TextChunker",
    "MinioFileReader",
    "MilvusVectorStore",
]

_LAZY_IMPORTS: dict[str, str] = {
    "ChatSessionService": "app.services.chat_session_service:ChatSessionService",
    "ChatMessageService": "app.services.chat_message_service:ChatMessageService",
    "FileStorageService": "app.services.file_storage_service:FileStorageService",
    "UserService": "app.services.users_service:UserService",
    "VectorizationService": "app.services.vectorization_service:VectorizationService",
    "RagService": "app.services.rag.service:RagService",
    "DocumentParser": "app.services.vectorization.document_parser:DocumentParser",
    "TextChunker": "app.services.vectorization.text_chunker:TextChunker",
    "MinioFileReader": "app.services.vectorization.file_reader:MinioFileReader",
    "MilvusVectorStore": "app.services.vectorization.vector_store:MilvusVectorStore",
}


def __getattr__(name: str):
    target = _LAZY_IMPORTS.get(name)
    if not target:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = target.split(":", 1)
    module = import_module(module_path)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals().keys()) + list(__all__))


if TYPE_CHECKING:
    from app.services.chat_session_service import ChatSessionService
    from app.services.chat_message_service import ChatMessageService
    from app.services.file_storage_service import FileStorageService
    from app.services.users_service import UserService
    from app.services.vectorization_service import VectorizationService
    from app.services.rag.service import RagService
    from app.services.vectorization.document_parser import DocumentParser
    from app.services.vectorization.text_chunker import TextChunker
    from app.services.vectorization.file_reader import MinioFileReader
    from app.services.vectorization.vector_store import MilvusVectorStore
