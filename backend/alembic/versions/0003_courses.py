"""courses table

Per-owner academic course container. Phase 6A introduces the
foundation entity that documents and chat sessions will hang off
in later subphases — here it stands alone with name uniqueness
scoped to ``owner_id``.

Revision ID: 0003_courses
Revises: 0002_chat_message_sources
Create Date: 2026-08-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_courses"
down_revision: Union[str, None] = "0002_chat_message_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
            ["owner_id"],
            ["users.id"],
            name="fk_courses_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_courses"),
        sa.UniqueConstraint("owner_id", "name", name="uq_courses_owner_name"),
    )
    op.create_index("ix_courses_owner_id", "courses", ["owner_id"])
    op.create_index(
        "ix_courses_owner_updated", "courses", ["owner_id", "updated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_courses_owner_updated", table_name="courses")
    op.drop_index("ix_courses_owner_id", table_name="courses")
    op.drop_table("courses")
