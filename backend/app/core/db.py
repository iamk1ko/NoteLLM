from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.settings import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""


def _create_engine():
    """创建数据库引擎。

    SQLite 说明：
    - check_same_thread=False 允许在不同线程复用连接（FastAPI 常见配置）
    """

    settings = get_settings()
    database_url = settings.DATABASE_URL
    logger.info("初始化数据库引擎：{}", database_url)

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(
        database_url, echo=False, future=True, connect_args=connect_args
    )


engine = _create_engine()

# SessionLocal 用于请求级别会话
SessionLocal = sessionmaker(
    bind=engine, class_=Session, autocommit=False, autoflush=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话。

    使用方法：
    - 在 API 路由中通过 Depends(get_db) 获取 Session
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
