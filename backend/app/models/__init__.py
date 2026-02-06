"""数据库模型包。

企业级约定：
- 这里提供“聚合导出”，让上层可以 `from app.models import User`。
- 为了避免导入时就加载所有 ORM 模型（启动慢/更容易循环依赖），这里采用“懒加载”。

说明：
- 运行时：只有真正访问到某个模型名时，才会 import 对应模块。
- 类型检查/IDE：在 TYPE_CHECKING 下仍能解析到真实类型。

使用示例：
    from app.models import User, ChatSession
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

# 公共 API：只暴露这些名字（也用于 `from app.models import *`）。
__all__ = [
    "User",
    "ChatSession",
    "ChatMessage",
    "ChatContext",
    "FileStorage",
    "FileChunks",
    "ChatSessionFile",
    "FileStorageStatus",
    "FileChunksStatus",
]

# 懒加载映射：name -> "module_path:attr_name"
# 注意：这里只写字符串，不会在 import app.models 时产生任何 ORM 导入副作用。
_LAZY_IMPORTS: dict[str, str] = {
    "User": "app.models.users:User",
    "ChatSession": "app.models.chat_session:ChatSession",
    "ChatMessage": "app.models.chat_message:ChatMessage",
    "ChatContext": "app.models.chat_context:ChatContext",
    "FileStorage": "app.models.file_storage:FileStorage",
    "FileStorageStatus": "app.models.file_storage:FileStorageStatus",
    "FileChunks": "app.models.file_chunks:FileChunks",
    "FileChunksStatus": "app.models.file_chunks:FileChunksStatus",
    "ChatSessionFile": "app.models.chat_session_files:ChatSessionFile",
}


def __getattr__(name: str):
    """PEP-562：在属性不存在时触发，用于按需导入。"""

    target = _LAZY_IMPORTS.get(name)
    if not target:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = target.split(":", 1)
    module = import_module(module_path)
    value = getattr(module, attr_name)

    # 缓存到模块全局命名空间：下一次访问不再触发 __getattr__。
    globals()[name] = value
    return value


def __dir__():
    """让 dir(app.models) 也能看到这些导出。"""

    return sorted(list(globals().keys()) + list(__all__))


if TYPE_CHECKING:
    # 仅用于类型检查：不在运行时执行，避免副作用。
    from app.models.users import User
    from app.models.chat_session import ChatSession
    from app.models.chat_message import ChatMessage
    from app.models.chat_context import ChatContext
    from app.models.file_storage import FileStorage, FileStorageStatus
    from app.models.file_chunks import FileChunks, FileChunksStatus
    from app.models.chat_session_files import ChatSessionFile

