from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.response import ApiResponse


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理参数校验错误。

    说明：
    - code 统一为 1001
    - message 展示首个错误信息，便于学习和排查
    """

    message = (
        exc.errors()[0].get("msg", "参数校验失败") if exc.errors() else "参数校验失败"
    )
    payload = ApiResponse.fail(code=1001, message=message)
    return JSONResponse(status_code=422, content=payload.model_dump())


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    """处理 HTTPException。

    说明：
    - code 使用 HTTP 状态码
    - message 使用异常 detail
    """

    payload = ApiResponse.fail(code=exc.status_code, message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获异常。

    说明：
    - code 统一为 1000
    - message 不暴露内部错误细节
    """

    payload = ApiResponse.fail(code=1000, message="服务器内部错误")
    return JSONResponse(status_code=500, content=payload.model_dump())
