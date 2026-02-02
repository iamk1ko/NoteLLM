from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.db import Base, engine
from app import models  # noqa: F401
from app.core.logging import get_logger, setup_logging
from app.core.settings import get_settings
from app.core.middleware import TraceIdMiddleware
from app.core.redis_client import get_redis_client
from app.core.rabbitmq_client import get_rabbitmq_connection
from app.core.minio_client import get_minio_client
from app.core.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.schemas.response import ApiResponse

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
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
    print("\n" + "=" * 60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

    yield
    logger.info("应用关闭，释放数据库连接")
    engine.dispose()


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
