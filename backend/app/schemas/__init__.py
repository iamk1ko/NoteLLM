"""接口数据模型（Pydantic Schemas）包。

企业级约定：
- 上层可以 `from app.schemas import ApiResponse, UserOut ...`。
- 采用“懒加载聚合导出”，避免 import app.schemas 就把所有 schema 全部导入。

说明：
- Pydantic 模型通常导入成本不高，但在业务变复杂/相互引用增多时，懒加载能显著降低循环依赖概率。
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    # 通用响应
    "ApiResponse",
    # 会话相关
    "ChatSessionCreate",
    "ChatSessionUpdate",
    "ChatSessionOut",
    "ChatSessionListResponse",
    "ChatSessionWithFiles",
    # 消息相关
    "ChatMessageCreate",
    "ChatMessageOut",
    "ChatMessageListResponse",
    "ChatMessageIn",
    # 文件相关
    "FileChunkUploadIn",
    "FileUploadCompleteIn",
    "FileStorageOut",
    "FileListResponse",
    "FileSessionRelation",
    "FileInfoWithSessions",
    # 用户相关
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "UserListResponse",
    "SimpleResponse",
    # 向量化相关
    "TextChunkMetadata",
    "TextChunk",
    "ChunkRecord",
]

_LAZY_IMPORTS: dict[str, str] = {
    # response
    "ApiResponse": "app.schemas.response:ApiResponse",
    # chat_session
    "ChatSessionCreate": "app.schemas.chat_session:ChatSessionCreate",
    "ChatSessionUpdate": "app.schemas.chat_session:ChatSessionUpdate",
    "ChatSessionOut": "app.schemas.chat_session:ChatSessionOut",
    "ChatSessionListResponse": "app.schemas.chat_session:ChatSessionListResponse",
    "ChatSessionWithFiles": "app.schemas.chat_session:ChatSessionWithFiles",
    # chat_message
    "ChatMessageCreate": "app.schemas.chat_message:ChatMessageCreate",
    "ChatMessageOut": "app.schemas.chat_message:ChatMessageOut",
    "ChatMessageListResponse": "app.schemas.chat_message:ChatMessageListResponse",
    "ChatMessageIn": "app.schemas.chat_message:ChatMessageIn",
    # file_storage
    "FileChunkUploadIn": "app.schemas.file_storage:FileChunkUploadIn",
    "FileUploadCompleteIn": "app.schemas.file_storage:FileUploadCompleteIn",
    "FileStorageOut": "app.schemas.file_storage:FileStorageOut",
    "FileListResponse": "app.schemas.file_storage:FileListResponse",
    "FileSessionRelation": "app.schemas.file_storage:FileSessionRelation",
    "FileInfoWithSessions": "app.schemas.file_storage:FileInfoWithSessions",
    # users
    "UserCreate": "app.schemas.users:UserCreate",
    "UserUpdate": "app.schemas.users:UserUpdate",
    "UserOut": "app.schemas.users:UserOut",
    "UserListResponse": "app.schemas.users:UserListResponse",
    "SimpleResponse": "app.schemas.users:SimpleResponse",
    # vectorization
    "TextChunkMetadata": "app.schemas.vectorization:TextChunkMetadata",
    "TextChunk": "app.schemas.vectorization:TextChunk",
    "ChunkRecord": "app.schemas.vectorization:ChunkRecord",
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
    from app.schemas.response import ApiResponse

    from app.schemas.chat_session import (
        ChatSessionCreate,
        ChatSessionUpdate,
        ChatSessionOut,
        ChatSessionListResponse,
        ChatSessionWithFiles,
    )
    from app.schemas.chat_message import (
        ChatMessageCreate,
        ChatMessageOut,
        ChatMessageListResponse,
        ChatMessageIn,
    )
    from app.schemas.file_storage import (
        FileChunkUploadIn,
        FileUploadCompleteIn,
        FileStorageOut,
        FileListResponse,
        FileSessionRelation,
        FileInfoWithSessions,
    )
    from app.schemas.users import (
        UserCreate,
        UserUpdate,
        UserOut,
        UserListResponse,
        SimpleResponse,
    )
    from app.schemas.vectorization import (
        TextChunkMetadata,
        TextChunk,
        ChunkRecord,
    )
