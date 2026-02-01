"""添加用户角色、文件可见性、会话-文件关联表

Revision ID: 20260131_000002
Revises: 20260131_000001
Create Date: 2026-01-31

说明：
1. 在 users 表中添加 role 字段，区分普通用户和管理员
2. 在 file_storage 表中添加 is_public 字段，标记公共文件
3. 创建 chat_session_files 表，实现会话与文件的多对多关系

使用说明：
    运行迁移：
    ```bash
    cd backend
    alembic upgrade head
    ```

    回滚迁移：
    ```bash
    alembic downgrade -1
    ```

注意事项：
    - role 字段默认为 'user'，现有用户默认为普通用户
    - is_public 字段默认为 False，现有文件默认为私有文件
    - chat_session_files 表不建外键，保持学习项目灵活性
"""

from alembic import op
import sqlalchemy as sa


revision = "20260131_000002"
down_revision = "20260131_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级操作：添加新字段和新表"""

    # 1. 在 users 表中添加 role 字段
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="user",
            comment="用户角色：user-普通用户，admin-管理员",
        ),
    )

    # 2. 在 file_storage 表中添加 is_public 字段
    op.add_column(
        "file_storage",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="是否为公共文件：True-公共，False-私有",
        ),
    )

    # 3. 创建 chat_session_files 表（会话-文件关联表）
    op.create_table(
        "chat_session_files",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "chat_session_id",
            sa.BigInteger(),
            nullable=False,
            comment="会话ID，关联chat_session.id",
        ),
        sa.Column(
            "file_id",
            sa.BigInteger(),
            nullable=False,
            comment="文件ID，关联file_storage.id",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="关联时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_session_id", "file_id", name="uk_session_file"),
        comment="会话-文件关联表，实现多对多关系",
    )

    # 4. 为 chat_session_files 表添加索引（提升查询性能）
    op.create_index(
        "ix_chat_session_files_chat_session_id",
        "chat_session_files",
        ["chat_session_id"],
        unique=False,
    )

    op.create_index(
        "ix_chat_session_files_file_id", "chat_session_files", ["file_id"], unique=False
    )


def downgrade() -> None:
    """降级操作：回滚所有更改"""

    # 1. 删除 chat_session_files 表
    op.drop_index("ix_chat_session_files_file_id", table_name="chat_session_files")
    op.drop_index(
        "ix_chat_session_files_chat_session_id", table_name="chat_session_files"
    )
    op.drop_table("chat_session_files")

    # 2. 删除 file_storage 表中的 is_public 字段
    op.drop_column("file_storage", "is_public")

    # 3. 删除 users 表中的 role 字段
    op.drop_column("users", "role")


if __name__ == '__main__':
    upgrade()
    # downgrade()