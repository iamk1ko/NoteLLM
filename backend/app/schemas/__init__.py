"""接口数据模型包。

说明：
- 导出所有 API 接口使用的 Pydantic 模型
- 包含请求模型、响应模型、基础模型等

使用示例：
    ```python
    from app.schemas import (
        ApiResponse,
        ChatSessionCreate,
        ChatMessageCreate,
        FileStorageOut
    )

    # 创建会话
    session_data = ChatSessionCreate(title="新对话")
    # ... 业务逻辑 ...

    # 返回响应
    return ApiResponse.ok(data=ChatSessionOut(...))
    ```
"""

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
]
