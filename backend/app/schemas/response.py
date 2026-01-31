from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型。

    说明：
    - code: 业务状态码，0 表示成功，其它表示失败
    - message: 友好的提示信息
    - data: 实际返回的数据，成功时携带
    - timestamp: 响应时间，便于排查与审计
    """

    code: int = Field(0, description="业务状态码，0 表示成功")
    message: str = Field("OK", description="提示信息")
    data: T | None = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")

    @classmethod
    def ok(cls, data: T | None = None, message: str = "OK") -> "ApiResponse[T]":
        """快速构造成功响应。"""

        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str) -> "ApiResponse[None]":
        """快速构造失败响应。"""

        return cls(code=code, message=message, data=None)
