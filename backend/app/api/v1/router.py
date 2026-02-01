from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.chat_sessions import router as chat_sessions_router
from app.api.v1.endpoints.chat_messages import router as chat_messages_router
from app.api.v1.endpoints.files import router as files_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(chat_sessions_router)
api_router.include_router(chat_messages_router)
api_router.include_router(files_router)
