"""应用顶层包。

说明：
- 本项目是“服务端应用”而不是可发布的 SDK，因此顶层包尽量保持轻量。
- 不要在这里做任何 I/O、副作用初始化（数据库/Redis/MinIO/RabbitMQ/日志等）。

企业级常见写法：
- 仅提供极少量元信息（如版本号）与清晰的包边界说明。
"""

from __future__ import annotations

# 对外不聚合导出任何内容；具体请从 app.models/app.schemas/app.services 等子包导入。
__all__: list[str] = []

# 可选：如果你希望在运行时能拿到版本号，可以手动维护或从 pyproject 读取。
# __version__ = "0.1.0"

