from __future__ import annotations

"""应用级 State（给 IDE/类型检查用）。

背景：
- FastAPI/Starlette 的 `app.state` 本质是一个动态对象（State），
  你可以在运行时随意挂载属性：`app.state.infra = ...`。
- 这对运行时完全没问题，但 PyCharm/静态类型检查往往会提示：
  “类 'FastAPI' 的未解析的特性引用 'state'”或“state 上的属性未解析”。

目标：
- 不改变 FastAPI 的运行机制；
- 通过一个显式的类型容器 + 统一访问函数，让 IDE 能正确推断 app.state 上有什么。

用法：
- 在 lifespan 启动时：
    from app.core.app_state import get_app_state
    state = get_app_state(app)
    state.infra = InfraProvider()

- 在 request/worker 中：
    state = get_app_state(request.app)
    infra = state.infra
"""

from dataclasses import dataclass
from typing import Any, Protocol, cast

from fastapi import FastAPI

from app.core.providers import InfraProvider


class _HasState(Protocol):
    """用于静态类型/IDE：声明对象具有 `.state` 属性。"""

    state: Any


@dataclass
class AppState:
    """应用状态容器（自定义、可扩展）。

    约定：
    - 所有需要跨请求复用的客户端/单例对象，都放在这里。
    - 避免在模块 import 阶段初始化这些对象。
    """

    infra: InfraProvider | None = None


def get_app_state(app: FastAPI) -> AppState:
    """获取（必要时创建）类型化的 AppState，并挂到 app.state 上。

    说明：
    - 仍然使用 FastAPI/Starlette 的 app.state 作为存储载体。
    - 但是我们把真实对象统一放到 `app.state._typed_state`，避免污染其它属性。
    """

    # PyCharm/部分类型检查工具对 FastAPI.state 的动态属性识别不佳。
    # 这里用 Protocol + Any 做一次“显式声明”，从根源消除未解析警告。
    app_with_state = cast(_HasState, cast(object, app))

    typed = getattr(app_with_state.state, "_typed_state", None)
    if typed is None:
        typed = AppState()
        setattr(app_with_state.state, "_typed_state", typed)
    return cast(AppState, typed)
