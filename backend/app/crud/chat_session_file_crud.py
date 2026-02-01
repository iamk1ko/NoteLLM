from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import ChatSessionFile

logger = get_logger(__name__)


class ChatSessionFileCRUD:
    """会话-文件关联相关的数据库操作（Repository/DAO 层）。

    说明：
    - 负责 chat_session_files 表的 CRUD 操作
    - 管理会话与文件的多对多关系
    - 支持批量操作和查询

    使用示例：
        ```python
        # 为会话添加文件
        ChatSessionFileCRUD.add_files_to_session(
            db=session,
            session_id=1,
            file_ids=[10, 20, 30]
        )

        # 从会话中移除文件
        ChatSessionFileCRUD.remove_files_from_session(
            db=session,
            session_id=1,
            file_ids=[10, 20]
        )

        # 查询会话关联的所有文件 ID
        file_ids = ChatSessionFileCRUD.get_session_file_ids(
            db=session,
            session_id=1
        )

        # 查询文件被哪些会话使用
        session_ids = ChatSessionFileCRUD.get_file_session_ids(
            db=session,
            file_id=10
        )

        # 检查文件是否在会话中
        exists = ChatSessionFileCRUD.check_file_in_session(
            db=session,
            session_id=1,
            file_id=10
        )
        ```
    """

    @staticmethod
    def add_file_to_session(
        db: Session, session_id: int, file_id: int
    ) -> ChatSessionFile | None:
        """为会话添加文件。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_id: 文件 ID

        返回值：
        - ChatSessionFile | None: 关联记录对象或 None（失败）

        注意事项：
        - 通过复合唯一索引避免重复关联
        - 不检查文件或会话是否存在（由调用方确保）
        - 不检查权限（由调用方确保）
        - 失败原因可能是数据库约束或其他异常
        """

        try:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)
            db.commit()
            db.refresh(session_file)

            logger.info(
                "为会话添加文件：session_id={}, file_id={}, relation_id={}",
                session_id,
                file_id,
                session_file.id,
            )

            return session_file

        except Exception as e:
            db.rollback()
            logger.error(
                "为会话添加文件失败：session_id={}, file_id={}, error={}",
                session_id,
                file_id,
                e,
            )
            return None

    @staticmethod
    def add_files_to_session(
        db: Session, session_id: int, file_ids: Sequence[int]
    ) -> int:
        """为会话批量添加文件。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_ids: 文件 ID 列表

        返回值：
        - int: 成功添加的文件数量

        注意事项：
        - 批量操作，提高效率
        - 忽略已存在的关联（通过唯一索引）
        - 不检查文件或会话是否存在（由调用方确保）
        - 不检查权限（由调用方确保）
        - 失败的关联会被跳过，不影响其他关联
        """

        success_count = 0

        for file_id in file_ids:
            session_file = ChatSessionFile(chat_session_id=session_id, file_id=file_id)
            db.add(session_file)

        try:
            db.commit()

            # 统计成功添加的数量
            success_count = (
                db.scalar(
                    select(func.count(ChatSessionFile.id)).where(
                        ChatSessionFile.chat_session_id == session_id
                    )
                )
                or 0
            )

            logger.info(
                "为会话批量添加文件：session_id={}, success_count={}",
                session_id,
                success_count,
            )

        except Exception as e:
            db.rollback()
            logger.error(
                "为会话批量添加文件失败：session_id={}, file_ids={}, error={}",
                session_id,
                file_ids,
                e,
            )

        return success_count

    @staticmethod
    def remove_file_from_session(db: Session, session_id: int, file_id: int) -> bool:
        """从会话中移除文件。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_id: 文件 ID

        返回值：
        - bool: True 表示移除成功，False 表示关联不存在

        注意事项：
        - 只删除关联记录，不删除文件本身
        - 不检查权限（由调用方确保）
        - 不删除文件的其他关联记录
        """

        session_file = db.scalar(
            select(ChatSessionFile).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id == file_id,
                )
            )
        )

        if not session_file:
            return False

        db.delete(session_file)
        db.commit()

        logger.info(
            "从会话中移除文件：session_id={}, file_id={}",
            session_id,
            file_id,
        )

        return True

    @staticmethod
    def remove_files_from_session(
        db: Session, session_id: int, file_ids: Sequence[int]
    ) -> int:
        """从会话中批量移除文件。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_ids: 文件 ID 列表

        返回值：
        - int: 成功移除的文件数量

        注意事项：
        - 批量操作，提高效率
        - 不删除文件本身，只删除关联记录
        - 不检查权限（由调用方确保）
        - 不存在的关联会被忽略
        """

        # 查询要删除的关联记录数量
        count = (
            db.scalar(
                select(func.count(ChatSessionFile.id)).where(
                    and_(
                        ChatSessionFile.chat_session_id == session_id,
                        ChatSessionFile.file_id.in_(file_ids),
                    )
                )
            )
            or 0
        )

        if count == 0:
            return 0

        # 批量删除
        db.query(ChatSessionFile).filter(
            and_(
                ChatSessionFile.chat_session_id == session_id,
                ChatSessionFile.file_id.in_(file_ids),
            )
        ).delete()

        db.commit()

        logger.info(
            "从会话中批量移除文件：session_id={}, count={}",
            session_id,
            count,
        )

        return count

    @staticmethod
    def get_session_file_ids(db: Session, session_id: int) -> Sequence[int]:
        """获取会话关联的所有文件 ID。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - Sequence[int]: 文件 ID 列表

        注意事项：
        - 返回所有关联文件的 ID
        - 不检查文件是否存在或权限（由调用方确保）
        - 用于查询会话使用的知识库文件
        """

        file_ids = db.scalars(
            select(ChatSessionFile.file_id).where(
                ChatSessionFile.chat_session_id == session_id
            )
        ).all()

        logger.debug(
            "查询会话关联文件 ID：session_id={}, count={}",
            session_id,
            len(file_ids),
        )

        return file_ids

    @staticmethod
    def get_file_session_ids(db: Session, file_id: int) -> Sequence[int]:
        """获取文件被哪些会话使用。

        参数说明：
        - db: 数据库会话
        - file_id: 文件 ID

        返回值：
        - Sequence[int]: 会话 ID 列表

        注意事项：
        - 返回所有使用该文件的会话 ID
        - 不检查会话是否存在或权限（由调用方确保）
        - 用于分析文件使用情况和影响范围
        """

        session_ids = db.scalars(
            select(ChatSessionFile.chat_session_id).where(
                ChatSessionFile.file_id == file_id
            )
        ).all()

        logger.debug(
            "查询文件使用的会话 ID：file_id={}, count={}",
            file_id,
            len(session_ids),
        )

        return session_ids

    @staticmethod
    def check_file_in_session(db: Session, session_id: int, file_id: int) -> bool:
        """检查文件是否在会话中。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID
        - file_id: 文件 ID

        返回值：
        - bool: True 表示文件在会话中，False 表示不在

        注意事项：
        - 用于重复添加检查
        - 不检查权限（由调用方确保）
        - 性能高效（只查一条记录）
        """

        exists = db.scalar(
            select(func.count(ChatSessionFile.id)).where(
                and_(
                    ChatSessionFile.chat_session_id == session_id,
                    ChatSessionFile.file_id == file_id,
                )
            )
        )

        return (exists or 0) > 0

    @staticmethod
    def remove_all_files_from_session(db: Session, session_id: int) -> int:
        """移除会话的所有文件关联。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - int: 移除的关联记录数量

        注意事项：
        - 只删除关联记录，不删除文件本身
        - 不检查权限（由调用方确保）
        - 通常在删除会话时调用
        """

        # 查询要删除的关联记录数量
        count = (
            db.scalar(
                select(func.count(ChatSessionFile.id)).where(
                    ChatSessionFile.chat_session_id == session_id
                )
            )
            or 0
        )

        if count == 0:
            return 0

        # 批量删除
        db.query(ChatSessionFile).filter(
            ChatSessionFile.chat_session_id == session_id
        ).delete()

        db.commit()

        logger.info(
            "移除会话的所有文件关联：session_id={}, count={}",
            session_id,
            count,
        )

        return count

    @staticmethod
    def remove_session_from_all_files(db: Session, session_id: int) -> int:
        """移除会话与所有文件的关联（同上，语义更清晰）。

        参数说明：
        - db: 数据库会话
        - session_id: 会话 ID

        返回值：
        - int: 移除的关联记录数量

        注意事项：
        - 与 remove_all_files_from_session 功能相同
        - 语义更清晰，表示从所有文件的角度操作
        - 推荐使用此方法
        """

        return ChatSessionFileCRUD.remove_all_files_from_session(db, session_id)
