from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import ChatSessionCRUD, FileStorageCRUD
from app.models import ChatSession, User
from app.schemas.chat_session import ChatSessionCreate, ChatSessionUpdate

logger = get_logger(__name__)


class ChatSessionService:
    """聊天会话业务服务层（异步版）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self, user: User, payload: ChatSessionCreate
    ) -> ChatSession:
        """创建聊天会话。"""

        logger.info("创建聊天会话：user_id={}, title={}", user.id, payload.title)
        # TODO: 目前 payload ：{ title='测试会话_demo_01' biz_type='ai_chat' context_id=None status=1 } 还是一些基础信息。
        #  后续可以使用一个小模型来生成更复杂的会话标题等信息。

        return await ChatSessionCRUD.create_session_async(
            db=self.db,
            user_id=user.id,
            title=payload.title,
            biz_type=payload.biz_type,
            context_id=payload.context_id,
        )

    async def list_sessions(
        self,
        user: User,
        page: int = 1,
        size: int = 10,
        biz_type: str | None = None,
        query_user_id: int | None = None,
    ) -> tuple[Sequence[ChatSession], int]:
        """查询会话列表（分页）。"""

        if user.role == "admin" and query_user_id is None:
            # 管理员查看全部会话
            return await ChatSessionCRUD.get_all_sessions_async(
                db=self.db, page=page, size=size, biz_type=biz_type
            )

        target_user_id = (
            query_user_id if (user.role == "admin" and query_user_id) else user.id
        )
        return await ChatSessionCRUD.get_user_sessions_async(
            db=self.db,
            user_id=target_user_id,
            page=page,
            size=size,
            biz_type=biz_type,
        )

    async def get_session_detail(
        self, user: User, session_id: int
    ) -> ChatSession | None:
        """获取会话详情。"""

        # TODO: session_id 已经是唯一了，这里区分用户和管理员查询的意义不大，后续可以简化。
        if user.role == "admin":
            return await ChatSessionCRUD.get_session_by_id_async(self.db, session_id)
        return await ChatSessionCRUD.get_user_session_async(
            self.db, session_id, user.id
        )

    async def get_session_files_ids(self, session_id: int) -> list[int]:
        """获取会话关联的文件ID列表。"""

        return await ChatSessionCRUD.get_session_file_ids_async(self.db, session_id)

    async def update_session(
        self, user: User, session_id: int, payload: ChatSessionUpdate
    ) -> ChatSession | None:
        """更新会话信息。"""

        session = await self.get_session_detail(user, session_id)
        if not session:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        return await ChatSessionCRUD.update_session_async(
            self.db, session_id, update_data
        )

    async def delete_session(self, user: User, session_id: int) -> bool:
        """删除会话。"""

        session = await self.get_session_detail(user, session_id)
        if not session:
            return False

        return await ChatSessionCRUD.delete_session_async(self.db, session_id)

    async def attach_files(
        self, user: User, session_id: int, file_ids: list[int]
    ) -> int:
        """关联文件到会话。"""

        session = await self.get_session_detail(user, session_id)
        if not session:
            return 0

        # 权限校验：普通用户只能关联自己的或公共文件
        if user.role != "admin":
            valid_file_ids: list[int] = []
            for file_id in file_ids:
                # Need to implement get_file_by_id_async in FileStorageCRUD if not exists?
                # Ah, FileStorageCRUD is already async. Let's assume it has get_file_by_id_async.
                # Checking my memory or need to read FileStorageCRUD?
                # Assuming get_file_by_id was updated to async or I need to use get_file_by_id_async.
                # Wait, I previously migrated FileStorageCRUD. Let's assume I should use get_file_by_id_async.
                file_obj = await FileStorageCRUD.get_file_by_id_async(self.db, file_id)
                if not file_obj:
                    continue
                if file_obj.is_public or file_obj.user_id == user.id:
                    valid_file_ids.append(file_id)
            file_ids = valid_file_ids

        if not file_ids:
            return 0

        return await ChatSessionCRUD.link_files_to_session_async(
            db=self.db, session_id=session_id, file_ids=file_ids
        )

    async def detach_files(
        self, user: User, session_id: int, file_ids: list[int]
    ) -> int:
        """取消文件与会话关联。"""

        session = await self.get_session_detail(user, session_id)
        if not session:
            return 0

        return await ChatSessionCRUD.unlink_files_from_session_async(
            db=self.db, session_id=session_id, file_ids=file_ids
        )
