from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.user_crud import UserCRUD
from app.models.users import User

logger = get_logger(__name__)


class UserService:
    """用户业务服务层。

    Controller(API) 应尽量只做：参数校验、依赖注入、HTTP 错误映射。
    Service 负责：业务编排、日志、（可选）事务边界。

    这里先按当前项目的同步 SQLAlchemy Session 实现；将来迁移 AsyncSession 时，
    可以：
    - 新增 AsyncUserCRUD / AsyncUserService 或把方法改成 async def
    - 在 db 依赖里提供 get_async_db
    """

    def __init__(self, db: Session):
        self.db = db

    def list_users(self) -> Sequence[User]:
        logger.info("开始查询所有用户")
        users = UserCRUD.list_users(self.db)
        logger.info("查询完成，返回 {} 条用户记录", len(users))
        return users

    def list_users_page(
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
        items, total = UserCRUD.list_users_page(self.db, page, size, keyword)
        logger.info("分页查询完成，返回 {} 条记录，总数 {}", len(items), total)
        return items, total

    def get_user(self, user_id: int) -> User | None:
        """获取用户详情。"""

        logger.info("查询用户详情：user_id={}", user_id)
        return UserCRUD.get_user_by_id(self.db, user_id)

    def create_user(self, payload) -> User:
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
        return UserCRUD.create_user(self.db, user)

    def update_user(self, user_id: int, payload) -> User | None:
        """更新用户。

        说明：
        - payload 为 UserUpdate
        - 只更新有传入的字段
        """

        user = UserCRUD.get_user_by_id(self.db, user_id)
        if not user:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        return UserCRUD.update_user(self.db, user)

    def delete_user(self, user_id: int) -> bool:
        """删除用户。"""

        user = UserCRUD.get_user_by_id(self.db, user_id)
        if not user:
            return False
        UserCRUD.delete_user(self.db, user)
        return True
