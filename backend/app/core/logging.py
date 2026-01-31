from __future__ import annotations

import sys

from loguru import logger


def setup_logging(level: str = "INFO") -> None:
    """配置 Loguru 日志输出。

    说明：
    - Loguru 默认自带彩色输出
    - 通过统一格式让终端更清晰
    """

    logger.remove()
    logger.add(
        sys.stdout,
        level=level.upper(),
        colorize=True,
        backtrace=False,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "{process.name} | "  # Process name
            "{thread.name} | "  # Thread name
            "<cyan>{module}</cyan>.<cyan>{function}</cyan>"
            ":<cyan>{line}</cyan> | "  # Module, function, line number
            "<level>{level}</level>: "  # Log level
            "<level>{message}</level> "  # Log message
        ),
    )


def get_logger(name: str | None = None):
    """获取统一配置的 logger。

    Loguru 默认根据模块名输出 {module}，这里保持接口一致。
    """

    return logger
