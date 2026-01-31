from __future__ import annotations

from typing import List, Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.users_service import UserService
from app.models.users import Users
from app.schemas.users import UsersOut

router = APIRouter(tags=["users"])


@router.get("/users", response_model=List[UsersOut])
def list_users(db: Session = Depends(get_db)) -> Sequence[Users]:
    """获取所有用户列表。

    RESTFul 风格：GET /users
    """

    return UserService(db).list_users()
