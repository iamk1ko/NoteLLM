from __future__ import annotations

from typing import List, Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(tags=["users"])


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)) -> Sequence[User]:
    """获取所有用户列表。

    RESTFul 风格：GET /users
    """

    return UserService(db).list_users()
