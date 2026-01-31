from __future__ import annotations

import uuid

from fastapi import Request


TRACE_HEADER = "X-Trace-Id"


def get_trace_id(request: Request) -> str:
    """获取当前请求的 trace_id。

    说明：
    - 优先使用上游传入的 X-Trace-Id
    - 若不存在则生成新的 UUID
    """

    header_value = request.headers.get(TRACE_HEADER)
    if header_value:
        return header_value
    return uuid.uuid4().hex
