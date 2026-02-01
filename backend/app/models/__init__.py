"""数据库模型包。

说明：
- 导出所有数据模型，便于在其他模块中引用
- 所有模型继承自 app.core.db.Base，支持 SQLAlchemy ORM 操作

使用示例：
    ```python
    from app.models import User, ChatSession, FileStorage, ChatSessionFile

    # 查询用户
    user = db.query(User).filter(User.id == 1).first()

    # 创建会话
    session = ChatSession(user_id=1, biz_type="ai_chat", title="新对话")
    db.add(session)
    db.commit()

    # 关联文件到会话
    session_file = ChatSessionFile(chat_session_id=1, file_id=10)
    db.add(session_file)
    db.commit()
    ```

注意：
- 所有表名遵循 snake_case 命名规范
- 模型类名遵循 PascalCase 命名规范
- 不建立复杂外键约束，保持学习项目灵活性
"""

from app.models.users import User
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.chat_context import ChatContext
from app.models.file_storage import FileStorage
from app.models.file_chunks import FileChunks
from app.models.chat_session_files import ChatSessionFile

__all__ = [
    "User",
    "ChatSession",
    "ChatMessage",
    "ChatContext",
    "FileStorage",
    "FileChunks",
    "ChatSessionFile",
]
