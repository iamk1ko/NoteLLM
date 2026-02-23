from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import UserCRUD
from app.models import User

logger = get_logger(__name__)


class UserService:
    """用户业务服务层。

    Controller(API) 应尽量只做：参数校验、依赖注入、HTTP 错误映射。
    Service 负责：业务编排、日志、（可选）事务边界。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self) -> Sequence[User]:
        logger.info("开始查询所有用户")
        users = await UserCRUD.list_users_async(self.db)
        logger.info("查询完成，返回 {} 条用户记录", len(users))
        return users

    async def list_users_page(
        self,
        page: int,
        size: int,
        keyword: str | None = None,
    ) -> tuple[Sequence[User], int]:
        """分页查询用户。

        说明：
        - page 从 1 开始
        - size 为每页数量
        - keyword 为可选搜索关键词
        """

        logger.info("分页查询用户：page={}, size={}, keyword={}", page, size, keyword)
        items, total = await UserCRUD.list_users_page_async(
            self.db, page, size, keyword
        )
        logger.info("分页查询完成，返回 {} 条记录，总数 {}", len(items), total)
        return items, total

    async def get_user(self, user_id: int) -> User | None:
        """获取用户详情。"""

        logger.info("查询用户详情：user_id={}", user_id)
        return await UserCRUD.get_user_by_id_async(self.db, user_id)

    async def create_user(self, payload) -> User:
        """创建用户。

        说明：
        - payload 为 UserCreate
        """

        logger.info("创建用户：username={}", payload.username)
        user = User(
            username=payload.username,
            password=payload.password,
            name=payload.name,
            gender=payload.gender,
            phone=payload.phone,
            email=payload.email,
            avatar_file_id=payload.avatar_file_id,
            bio=payload.bio,
        )
        return await UserCRUD.create_user_async(self.db, user)

    async def update_user(self, user_id: int, payload) -> User | None:
        """更新用户。

        说明：
        - payload 为 UserUpdate
        - 只更新有传入的字段
        """

        user = await UserCRUD.get_user_by_id_async(self.db, user_id)
        if not user:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        return await UserCRUD.update_user_async(self.db, user)

    async def delete_user(self, user_id: int) -> bool:
        """删除用户。"""

        user = await UserCRUD.get_user_by_id_async(self.db, user_id)
        if not user:
            return False
        await UserCRUD.delete_user_async(self.db, user)
        return True
