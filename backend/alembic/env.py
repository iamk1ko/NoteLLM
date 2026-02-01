from __future__ import annotations

import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 添加当前目录到 sys.path，确保能找到 app 模块
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from app.core.settings import get_settings
from app.core.logging import get_logger
from app.core.db import Base
import app.models  # noqa: F401  # 触发模型加载，保证 metadata 完整

logger = get_logger(__name__)

# Alembic Config 对象，提供访问 alembic.ini 中的配置
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据，用于 autogenerate
target_metadata = Base.metadata


def _get_database_url() -> str:
    """从项目配置中获取数据库 URL。"""

    settings = get_settings()
    return settings.database_url()


def run_migrations_offline() -> None:
    """离线模式运行迁移。

    离线模式下不创建引擎，仅生成 SQL 脚本。
    """

    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移。

    在线模式会创建引擎并直接执行迁移。
    """

    config.set_main_option("sqlalchemy.url", _get_database_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
