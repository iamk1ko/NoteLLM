"""依赖注入（FastAPI Depends）包。

企业级约定：
- 上层通过 `from app.dependencies import get_current_user, get_redis` 使用依赖。
- 采用懒加载：避免 import app.dependencies 时就导入 infra/auth 相关模块，减少副作用与循环依赖风险。

提示：
- 请确保 infra/auth 模块本身也不要在 import 阶段创建网络连接（应在函数内部或 lifespan 初始化）。
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "require_admin",
    "require_ownership",
    "get_current_user",
    "get_current_user_optional",
    "get_redis",
    "get_minio",
    "get_rabbitmq_connection",
    "get_rabbitmq_channel",
    "get_milvus",
]

_LAZY_IMPORTS: dict[str, str] = {
    # auth
    "get_current_user_optional": "app.dependencies.auth:get_current_user_optional",
    "get_current_user": "app.dependencies.auth:get_current_user",
    "require_admin": "app.dependencies.auth:require_admin",
    "require_ownership": "app.dependencies.auth:require_ownership",
    # infra
    "get_redis": "app.dependencies.infra:get_redis",
    "get_minio": "app.dependencies.infra:get_minio",
    "get_rabbitmq_connection": "app.dependencies.infra:get_rabbitmq_connection",
    "get_rabbitmq_channel": "app.dependencies.infra:get_rabbitmq_channel",
    "get_milvus": "app.dependencies.infra:get_milvus",
}


def __getattr__(name: str):
    target = _LAZY_IMPORTS.get(name)
    if not target:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = target.split(":", 1)
    module = import_module(module_path)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(list(globals().keys()) + list(__all__))


if TYPE_CHECKING:
    from app.dependencies.auth import (
        get_current_user_optional,
        get_current_user,
        require_admin,
        require_ownership,
    )
    from app.dependencies.infra import (
        get_redis,
        get_minio,
        get_rabbitmq_connection,
        get_rabbitmq_channel,
        get_milvus,
    )
