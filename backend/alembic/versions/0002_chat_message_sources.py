"""chat_message_sources table

Persists per-citation metadata for each assistant message so
conversations can render sources without rerunning retrieval.

Revision ID: 0002_chat_message_sources
Revises: 0001_initial
Create Date: 2026-08-09 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_chat_message_sources"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_message_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("slide_number", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            name="fk_chat_message_sources_message_id_chat_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chat_message_sources_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_message_sources"),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_chat_message_sources_position_positive",
        ),
    )
    op.create_index(
        "ix_chat_message_sources_message_id",
        "chat_message_sources",
        ["message_id"],
    )
    op.create_index(
        "ix_chat_message_sources_document_id",
        "chat_message_sources",
        ["document_id"],
    )
    op.create_index(
        "ix_chat_message_sources_message_position",
        "chat_message_sources",
        ["message_id", "position"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_message_sources_message_position",
        table_name="chat_message_sources",
    )
    op.drop_index(
        "ix_chat_message_sources_document_id",
        table_name="chat_message_sources",
    )
    op.drop_index(
        "ix_chat_message_sources_message_id",
        table_name="chat_message_sources",
    )
    op.drop_table("chat_message_sources")
