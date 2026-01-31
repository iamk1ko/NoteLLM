"""init schema

Revision ID: 20260131_000001
Revises:
Create Date: 2026-01-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260131_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=10), nullable=False),
        sa.Column("gender", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("phone", sa.String(length=11), nullable=True),
        sa.Column("email", sa.String(length=50), nullable=True),
        sa.Column("avatar_file_id", sa.Integer(), nullable=True),
        sa.Column(
            "bio",
            sa.String(length=255),
            nullable=True,
            server_default="这个人很懒,什么都没写...",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("phone"),
    )

    op.create_table(
        "chat_session",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("biz_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("context_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True, server_default="1"),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_biz", "chat_session", ["user_id", "biz_type"], unique=False
    )
    op.create_index(
        "idx_user_created", "chat_session", ["user_id", "create_time"], unique=False
    )

    op.create_table(
        "chat_message",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="chat_role"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_session", "chat_message", ["session_id"], unique=False)
    op.create_index(
        "idx_session_time", "chat_message", ["session_id", "create_time"], unique=False
    )
    op.create_index("idx_user", "chat_message", ["user_id"], unique=False)

    op.create_table(
        "chat_context",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("reference_text", sa.Text(), nullable=True),
        sa.Column("similarity", sa.DECIMAL(precision=6, scale=4), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_session", "chat_context", ["session_id"], unique=False)
    op.create_index(
        "idx_session_time", "chat_context", ["session_id", "create_time"], unique=False
    )

    op.create_table(
        "file_storage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("bucket_name", sa.String(length=100), nullable=False),
        sa.Column("object_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("etag", sa.String(length=100), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("chat_session_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "upload_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_id", "file_storage", ["user_id"], unique=False)
    op.create_index(
        "idx_bucket_object",
        "file_storage",
        ["bucket_name", "object_name"],
        unique=False,
    )
    op.create_index(
        "idx_chat_session_id", "file_storage", ["chat_session_id"], unique=False
    )

    op.create_table(
        "file_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(length=128), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_file_chunk", "file_chunks", ["file_id", "chunk_index"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_file_chunk", table_name="file_chunks")
    op.drop_table("file_chunks")

    op.drop_index("idx_chat_session_id", table_name="file_storage")
    op.drop_index("idx_bucket_object", table_name="file_storage")
    op.drop_index("idx_user_id", table_name="file_storage")
    op.drop_table("file_storage")

    op.drop_index("idx_session_time", table_name="chat_context")
    op.drop_index("idx_session", table_name="chat_context")
    op.drop_table("chat_context")

    op.drop_index("idx_user", table_name="chat_message")
    op.drop_index("idx_session_time", table_name="chat_message")
    op.drop_index("idx_session", table_name="chat_message")
    op.drop_table("chat_message")

    op.drop_index("idx_user_created", table_name="chat_session")
    op.drop_index("idx_user_biz", table_name="chat_session")
    op.drop_table("chat_session")

    op.drop_table("users")
