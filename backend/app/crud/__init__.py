"""CRUD 包。

企业级约定：
- 上层可以 `from app.crud import UserCRUD`。
- 采用懒加载，避免 import app.crud 时加载所有 CRUD 模块。

注意：CRUD 往往会依赖 models；懒加载可以降低循环依赖概率。
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "ChatMessageCRUD",
    "ChatSessionCRUD",
    "ChatSessionFileCRUD",
    "FileChunksCRUD",
    "UserCRUD",
    "FileStorageCRUD",
]

_LAZY_IMPORTS: dict[str, str] = {
    "ChatMessageCRUD": "app.crud.chat_message_crud:ChatMessageCRUD",
    "ChatSessionCRUD": "app.crud.chat_session_crud:ChatSessionCRUD",
    "ChatSessionFileCRUD": "app.crud.chat_session_file_crud:ChatSessionFileCRUD",
    "FileChunksCRUD": "app.crud.file_chunks_crud:FileChunksCRUD",
    "UserCRUD": "app.crud.user_crud:UserCRUD",
    "FileStorageCRUD": "app.crud.file_storage_crud:FileStorageCRUD",
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
    from app.crud.chat_message_crud import ChatMessageCRUD
    from app.crud.chat_session_crud import ChatSessionCRUD
    from app.crud.chat_session_file_crud import ChatSessionFileCRUD
    from app.crud.file_chunks_crud import FileChunksCRUD
    from app.crud.user_crud import UserCRUD
    from app.crud.file_storage_crud import FileStorageCRUD
