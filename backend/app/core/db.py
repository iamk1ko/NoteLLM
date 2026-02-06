from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.settings import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""


# ------------------------------
# 企业级约定：延迟初始化（Lazy init）
# ------------------------------
# 以前的写法：engine = _create_engine() 会在 import app.core.db 时立刻尝试连接数据库。
# 这会带来三个常见问题：
# 1) 启动慢：只要导入到 models/crud，就会触发 DB 初始化。
# 2) 更容易循环依赖：某些模块 import 链很长，import 阶段就做 I/O 容易爆炸。
# 3) 测试/脚本不友好：导入模块就要求数据库可用。
#
# 改造后：
# - get_engine() 首次被调用时才创建引擎。
# - get_db()（FastAPI Depends）在第一次请求用到时自动初始化。
# - 可在 FastAPI lifespan 中显式调用 init_db() 做“启动时建表”等操作。

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _create_engine() -> Engine:
    """创建数据库引擎（内部函数）。

    说明：
    - 统一使用 SQLAlchemy 的同步引擎，适合学习项目与简单业务
    - 生产可按需切换异步引擎或引入连接池监控
    """

    settings = get_settings()
    database_url = settings.database_url()
    safe_url = make_url(database_url).render_as_string(hide_password=True)

    # 注意：这里用的是 loguru 风格的 {} 占位符（你的 logging.py 已适配）。
    logger.info("初始化数据库引擎：{}", safe_url)

    return create_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


def init_db() -> None:
    """显式初始化 DB 引擎与 SessionFactory。

    建议：
    - 在 FastAPI lifespan.startup 中调用一次，确保多 worker/多处引用时只初始化一次。
    """

    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return

    _engine = _create_engine()
    _SessionLocal = sessionmaker(
        bind=_engine, class_=Session, autocommit=False, autoflush=False
    )


def get_engine() -> Engine:
    """获取（并在必要时创建）Engine。"""

    if _engine is None:
        init_db()
    # 经过 init_db 后一定不为 None
    assert _engine is not None
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """获取（并在必要时创建）SessionLocal。"""

    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    return _SessionLocal


def close_db() -> None:
    """应用关闭时释放连接池资源。"""

    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


# ------------------------------
# FastAPI Depends
# ------------------------------

def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话。

    使用方法：
    - 在 API 路由中通过 Depends(get_db) 获取 Session

    说明：
    - 这里会在第一次调用时自动 init_db()，避免 import 阶段就连库。
    """

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------
# 兼容旧代码的导出（逐步迁移用）
# ------------------------------
# 你项目里某些地方（如消费者脚本）直接 import SessionLocal。
# 为避免一次性大改，这里保留同名符号，但它会在首次使用时才真正初始化。
class _LazySessionLocalProxy:
    def __call__(self) -> Session:
        return get_sessionmaker()()


SessionLocal = _LazySessionLocalProxy()  # type: ignore

