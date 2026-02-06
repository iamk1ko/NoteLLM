"""依赖注入模块

"""

from app.dependencies.auth import get_current_user_optional, get_current_user, require_admin, require_ownership
from app.dependencies.infra import get_redis, get_minio, get_rabbitmq_connection, get_rabbitmq_channel

__all__ = [
    "require_admin",
    "require_ownership",
    "get_current_user",
    "get_current_user_optional",
    "get_redis",
    "get_minio",
    "get_rabbitmq_connection",
    "get_rabbitmq_channel",
]
