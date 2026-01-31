from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crud.user_crud import UserCRUD
from app.models.user import User

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
