from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserCRUD:
    """用户相关的纯数据库操作（Repository/DAO 层）。

    约定：
    - 这里只做 SQLAlchemy 查询/写入，不处理 FastAPI 的 Depends/HTTPException。
    - 不做复杂业务编排，业务由 Service 层负责。
    """

    @staticmethod
    def list_users(db: Session) -> Sequence[User]:
        return db.scalars(select(User).order_by(User.id)).all()

