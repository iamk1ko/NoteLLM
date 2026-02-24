from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


class UserCRUD:
    """用户相关的纯数据库操作（Repository/DAO 层）。

    约定：
    - 这里只做 SQLAlchemy 查询/写入，不处理 FastAPI 的 Depends/HTTPException。
    - 不做复杂业务编排，业务由 Service 层负责。
    """

    @staticmethod
    def list_users(db: Session) -> Sequence[User]:
        """查询所有用户（不分页，适合小数据量）。"""

        return db.scalars(select(User).order_by(User.id)).all()

    @staticmethod
    async def list_users_async(db: AsyncSession) -> Sequence[User]:
        """异步查询所有用户（不分页）。"""
        result = await db.scalars(select(User).order_by(User.id))
        return result.all()

    @staticmethod
    def list_users_page(
        db: Session,
        page: int,
        size: int,
        keyword: str | None = None,
    ) -> tuple[Sequence[User], int]:
        """分页查询用户，并返回总数量。

        说明：
        - keyword 为空则查询全部
        - keyword 模糊匹配 username/name/phone/email
        """

        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if keyword:
            like = f"%{keyword}%"
            condition = or_(
                User.username.like(like),
                User.name.like(like),
                User.phone.like(like),
                User.email.like(like),
            )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        total = db.scalar(count_stmt) or 0
        items = db.scalars(
            stmt.order_by(User.id).offset((page - 1) * size).limit(size)
        ).all()
        return items, total

    @staticmethod
    async def list_users_page_async(
        db: AsyncSession,
        page: int,
        size: int,
        keyword: str | None = None,
    ) -> tuple[Sequence[User], int]:
        """异步分页查询用户，并返回总数量。"""

        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if keyword:
            like = f"%{keyword}%"
            condition = or_(
                User.username.like(like),
                User.name.like(like),
                User.phone.like(like),
                User.email.like(like),
            )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        total = (await db.scalar(count_stmt)) or 0

        stmt = stmt.order_by(User.id).offset((page - 1) * size).limit(size)
        result = await db.scalars(stmt)
        items = result.all()

        return items, total

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        """根据 ID 获取用户。"""

        return db.get(User, user_id)

    @staticmethod
    async def get_user_by_id_async(db: AsyncSession, user_id: int) -> User | None:
        """异步根据 ID 获取用户。"""
        return await db.get(User, user_id)

    @staticmethod
    async def get_user_by_username_async(
        db: AsyncSession, username: str
    ) -> User | None:
        """根据用户名获取用户。"""

        return await db.scalar(select(User).where(User.username == username))

    @staticmethod
    async def get_user_by_email_async(db: AsyncSession, email: str) -> User | None:
        """根据邮箱获取用户。"""

        return await db.scalar(select(User).where(User.email == email))

    @staticmethod
    def create_user(db: Session, user: User) -> User:
        """创建用户。"""

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    async def create_user_async(db: AsyncSession, user: User) -> User:
        """异步创建用户。"""
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user: User) -> User:
        """更新用户。"""

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    async def update_user_async(db: AsyncSession, user: User) -> User:
        """异步更新用户。"""
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        """删除用户。"""

        db.delete(user)
        db.commit()

    @staticmethod
    async def delete_user_async(db: AsyncSession, user: User) -> None:
        """异步删除用户。"""
        await db.delete(user)
        await db.commit()
