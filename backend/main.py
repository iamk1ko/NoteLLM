from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.db import Base, init_db, get_engine, close_db
from app.core.logging import get_logger, setup_logging
from app.core.settings import get_settings
from app.core.middleware import TraceIdMiddleware
from app.core.providers import InfraProvider
from app.core.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.schemas.response import ApiResponse
from app.consumers.file_merge_listener import start_file_merge_listener
from app.core.app_state import get_app_state

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期事件。

    - 启动时创建数据库表
    - 关闭时释放数据库连接
    """

    logger.info("应用启动，开始初始化数据库表")
    # 显式初始化 DB（只做一次），避免模块 import 阶段就连库。
    init_db()
    engine = get_engine()

    # 建表：学习/演示项目可用。生产环境建议使用 Alembic 做迁移。
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")

    # 初始化外部服务客户端（类似 Spring Bean）
    logger.info("开始初始化外部服务")
    state = get_app_state(app)
    state.infra = InfraProvider()
    await state.infra.init()
    health = await state.infra.self_check()
    logger.info("外部服务初始化完成：{}", health)

    # 启动后台消费者（类似 Spring 的 @RabbitListener）
    # 注意：如果你使用多 worker（例如 gunicorn/uvicorn --workers>1），每个 worker 都会启动一个监听器。
    # 生产环境通常将 worker 与 web 服务解耦：单独起一个 consumer 进程更稳。
    file_merge_task = start_file_merge_listener(app)

    print("\n" + "=" * 60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

    yield

    # 优雅停止后台监听器
    file_merge_task.cancel()
    try:
        await file_merge_task
    except asyncio.CancelledError:
        # 正常：我们主动 cancel 了任务，属于预期行为
        pass
    except Exception:
        # 非预期异常：不要影响整体关停，但建议记录
        logger.exception("后台监听器退出时发生异常")

    # 优先按统一入口释放 DB 资源
    close_db()

    # 关闭外部服务连接
    try:
        if state.infra is not None:
            await state.infra.close()
        logger.info("外部服务连接已关闭")
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="A simple FastAPI application",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# TraceId 中间件
app.add_middleware(TraceIdMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """根路径示例。"""

    return ApiResponse.ok({"message": "Hello World"})


@app.get("/hello/{name}")
async def say_hello(name: str):
    """简单问候示例。"""

    return ApiResponse.ok({"message": f"Hello {name}"})


# 异常处理器（统一响应格式）
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
