from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.trace_id import TRACE_HEADER, get_trace_id


class TraceIdMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 trace_id。

    说明：
    - 将 trace_id 保存到 request.state
    - 同时写回到响应头，方便前端/调用方排查
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = get_trace_id(request)
        request.state.trace_id = trace_id

        response: Response = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        return response
