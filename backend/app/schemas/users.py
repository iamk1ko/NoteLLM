from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UsersOut(BaseModel):
    """用户输出模型。

    用于响应 /users 列表接口。
    """

    id: int
    username: str
    email: str | None
    create_time: datetime | None

    model_config = {"from_attributes": True}
