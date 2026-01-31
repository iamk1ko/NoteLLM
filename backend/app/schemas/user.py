from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    """用户输出模型。

    用于响应 /users 列表接口。
    """

    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
