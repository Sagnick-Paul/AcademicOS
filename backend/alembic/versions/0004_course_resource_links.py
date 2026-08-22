"""link documents and chat_sessions to courses

Phase 6B — adds an OPTIONAL ``course_id`` foreign key on both
``documents`` and ``chat_sessions``. Existing rows keep ``NULL`` so
no data is lost; nothing about the previous behavior changes.

Revision ID: 0004_course_resource_links
Revises: 0003_courses
Create Date: 2026-08-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_course_resource_links"
down_revision: Union[str, None] = "0003_courses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- documents.course_id ---
    # Nullable FK. ``SET NULL`` on course delete: if a course is removed,
    # its documents and chat sessions simply revert to "uncoursed" —
    # they are not deleted (that would surprise the user).
    op.add_column(
        "documents",
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_course_id_courses",
        "documents",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_course_id", "documents", ["course_id"]
    )
    op.create_index(
        "ix_documents_course_created",
        "documents",
        ["course_id", "created_at"],
    )

    # --- chat_sessions.course_id ---
    op.add_column(
        "chat_sessions",
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_sessions_course_id_courses",
        "chat_sessions",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_chat_sessions_course_id", "chat_sessions", ["course_id"]
    )
    op.create_index(
        "ix_chat_sessions_course_updated",
        "chat_sessions",
        ["course_id", "updated_at"],
    )


def downgrade() -> None:
    # chat_sessions
    op.drop_index(
        "ix_chat_sessions_course_updated", table_name="chat_sessions"
    )
    op.drop_index(
        "ix_chat_sessions_course_id", table_name="chat_sessions"
    )
    op.drop_constraint(
        "fk_chat_sessions_course_id_courses",
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "course_id")

    # documents
    op.drop_index("ix_documents_course_created", table_name="documents")
    op.drop_index("ix_documents_course_id", table_name="documents")
    op.drop_constraint(
        "fk_documents_course_id_courses",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "course_id")
