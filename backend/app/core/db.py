from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from app.core.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""


# ------------------------------
# 企业级约定：延迟初始化（Lazy init）
# ------------------------------
# 说明：仅保留异步引擎，避免同步/异步双引擎重复连接。
# - get_async_engine() 首次被调用时才创建引擎。
# - get_async_db()（FastAPI Depends）在第一次请求用到时自动初始化。
# - 可在 FastAPI lifespan 中显式调用 init_async_db() 做“启动时建表”等操作。

_async_engine: AsyncEngine | None = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _create_async_engine() -> AsyncEngine:
    """创建异步数据库引擎（内部函数）。"""
    settings = get_settings()
    async_database_url = settings.async_database_url
    safe_url = make_url(async_database_url).render_as_string(hide_password=True)

    logger.info("初始化异步数据库引擎：{}", safe_url)

    return create_async_engine(
        async_database_url,
        echo=settings.DB_ECHO,
        future=True,
        pool_pre_ping=True,
    )


def init_async_db() -> None:
    """显式初始化异步 DB 引擎与 SessionFactory。"""
    global _async_engine, _AsyncSessionLocal
    if _async_engine is not None and _AsyncSessionLocal is not None:
        return

    _async_engine = _create_async_engine()
    _AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_async_engine() -> AsyncEngine:
    """获取（并在必要时创建）AsyncEngine。"""
    if _async_engine is None:
        init_async_db()
    assert _async_engine is not None
    return _async_engine


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """获取（并在必要时创建）AsyncSessionLocal。"""
    if _AsyncSessionLocal is None:
        init_async_db()
    assert _AsyncSessionLocal is not None
    return _AsyncSessionLocal


async def close_async_db() -> None:
    """应用关闭时释放异步连接池资源。"""
    global _async_engine, _AsyncSessionLocal
    if _async_engine is not None:
        await _async_engine.dispose()
    _async_engine = None
    _AsyncSessionLocal = None


# ------------------------------
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取异步数据库会话。"""
    AsyncSessionLocal = get_async_sessionmaker()
    async with AsyncSessionLocal() as session:
        yield session
