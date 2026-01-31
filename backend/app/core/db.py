from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.settings import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""


def _create_engine():
    """创建数据库引擎。

    说明：
    - 统一使用 SQLAlchemy 的同步引擎，适合学习项目与简单业务
    - 实际生产可按需切换异步引擎或引入连接池监控
    """

    settings = get_settings()
    database_url = settings.database_url()
    safe_url = make_url(database_url).render_as_string(hide_password=True)
    logger.info("初始化数据库引擎：{}", safe_url)

    return create_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
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
