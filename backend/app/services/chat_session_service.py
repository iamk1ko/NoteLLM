from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.chat_session_crud import ChatSessionCRUD
from app.crud.file_storage_crud import FileStorageCRUD
from app.models import ChatSession, ChatSessionFile, FileStorage, User
from app.schemas.chat_session import ChatSessionCreate, ChatSessionUpdate

logger = get_logger(__name__)


class ChatSessionService:
    """聊天会话业务服务层。

    说明：
    - 处理会话的创建、查询、删除、文件关联等业务逻辑
    - 权限控制：普通用户只能操作自己的会话
    - 管理员可以访问所有用户的会话
    """

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user: User, payload: ChatSessionCreate) -> ChatSession:
        """创建聊天会话。

        参数说明：
        - user: 当前登录用户
        - payload: 会话创建参数

        返回值：
        - ChatSession: 创建成功的会话对象
        """

        logger.info("创建聊天会话：user_id={}, title={}", user.id, payload.title)
        return ChatSessionCRUD.create_session(
            db=self.db,
            user_id=user.id,
            title=payload.title,
            biz_type=payload.biz_type,
            context_id=payload.context_id,
        )

    def list_sessions(
        self,
        user: User,
        page: int = 1,
        size: int = 10,
        biz_type: str | None = None,
        query_user_id: int | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询会话列表（分页）。

        说明：
        - 普通用户只能看到自己的会话
        - 管理员可以查看所有会话，也可按 user_id 过滤
        """

        if user.role == "admin" and query_user_id is None:
            # 管理员查看全部会话
            return ChatSessionCRUD.get_all_sessions(
                db=self.db, page=page, size=size, biz_type=biz_type
            )

        target_user_id = query_user_id if user.role == "admin" else user.id
        return ChatSessionCRUD.get_user_sessions(
            db=self.db,
            user_id=target_user_id,
            page=page,
            size=size,
            biz_type=biz_type,
        )

    def get_session_detail(self, user: User, session_id: int) -> ChatSession | None:
        """获取会话详情。

        说明：
        - 普通用户只能访问自己的会话
        - 管理员可以访问任意会话
        """

        if user.role == "admin":
            return ChatSessionCRUD.get_session_by_id(self.db, session_id)
        return ChatSessionCRUD.get_user_session(self.db, session_id, user.id)

    def update_session(
        self, user: User, session_id: int, payload: ChatSessionUpdate
    ) -> ChatSession | None:
        """更新会话信息。

        说明：
        - 普通用户只能更新自己的会话
        - 管理员可以更新任意会话
        """

        session = self.get_session_detail(user, session_id)
        if not session:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        return ChatSessionCRUD.update_session(self.db, session_id, update_data)

    def delete_session(self, user: User, session_id: int) -> bool:
        """删除会话。

        说明：
        - 普通用户只能删除自己的会话
        - 管理员可以删除任意会话
        """

        session = self.get_session_detail(user, session_id)
        if not session:
            return False

        return ChatSessionCRUD.delete_session(self.db, session_id)

    def attach_files(self, user: User, session_id: int, file_ids: list[int]) -> int:
        """关联文件到会话。

        说明：
        - 普通用户只能关联自己或公共文件
        - 管理员可以关联任意文件
        - 会话必须归属当前用户（管理员除外）
        """

        session = self.get_session_detail(user, session_id)
        if not session:
            return 0

        # 权限校验：普通用户只能关联自己的或公共文件
        if user.role != "admin":
            valid_file_ids: list[int] = []
            for file_id in file_ids:
                file_obj = FileStorageCRUD.get_file_by_id(self.db, file_id)
                if not file_obj:
                    continue
                if file_obj.is_public or file_obj.user_id == user.id:
                    valid_file_ids.append(file_id)
            file_ids = valid_file_ids

        if not file_ids:
            return 0

        return ChatSessionCRUD.link_files_to_session(
            db=self.db, session_id=session_id, file_ids=file_ids
        )

    def detach_files(self, user: User, session_id: int, file_ids: list[int]) -> int:
        """取消文件与会话关联。

        说明：
        - 普通用户只能操作自己的会话
        - 管理员可以操作任意会话
        """

        session = self.get_session_detail(user, session_id)
        if not session:
            return 0

        return ChatSessionCRUD.unlink_files_from_session(
            db=self.db, session_id=session_id, file_ids=file_ids
        )
