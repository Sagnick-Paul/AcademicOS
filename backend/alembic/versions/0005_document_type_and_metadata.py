"""add document_type and document_metadata to documents

Phase 6C — gives :class:`Document` an authoritative academic
classification (``document_type``) and structured academic
metadata (``document_metadata``). Existing rows are preserved
verbatim: ``document_type`` defaults to ``NULL`` (uncategorised)
rather than a guessed value so we do not silently misclassify
files that pre-date this phase.

Revision ID: 0005_document_type_and_metadata
Revises: 0004_course_resource_links
Create Date: 2026-08-18 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_document_type_and_metadata"
down_revision: Union[str, None] = "0004_course_resource_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Phase 6C mirrors the canonical enum values from
# ``app.db.models.enums.DocumentType``. Stored here as a literal list
# so the migration is self-contained — reordering/removing values
# would not be silent even if someone edits the Python enum.
_DOCUMENT_TYPE_VALUES = (
    "lecture_notes",
    "textbook",
    "presentation",
    "assignment",
    "previous_year_question",
    "reference",
    "other",
)


def upgrade() -> None:
    # --- document_type ---
    # VARCHAR(32) — same shape as DocumentUploadStatus so the column
    # behaves consistently with the rest of the table. Nullable on
    # the column; rows inserted after the migration are filled by the
    # ORM default (``DocumentType.OTHER``).
    op.add_column(
        "documents",
        sa.Column(
            "document_type",
            sa.String(length=32),
            nullable=True,
        ),
    )
    # Surface unknown enum values rather than silently downcasting
    # them at read time — keeps the contract honest.
    document_type_enum = postgresql.ENUM(
        *_DOCUMENT_TYPE_VALUES,
        name="document_type_enum",
        create_type=False,
    )
    document_type_enum.create(op.get_bind(), checkfirst=True)
    # Best-effort CHECK constraint. Defensive against legacy data with
    # unexpected values; not enforced on SQLite (where CHECK would
    # fire on every insert under the in-memory test harness).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_check_constraint(
            "ck_documents_document_type",
            "documents",
            # ``document_type IS NULL`` covers the legacy rows.
            sa.text(
                "document_type IS NULL OR "
                "document_type IN ("
                + ", ".join(f"'{v}'" for v in _DOCUMENT_TYPE_VALUES)
                + ")"
            ),
        )
    op.create_index(
        "ix_documents_document_type",
        "documents",
        ["document_type"],
    )

    # --- document_metadata ---
    # JSONB on PostgreSQL for indexability / binary representation;
    # JSON on SQLite (not used by Alembic migrations, but documents
    # the intent). nullable=True so legacy rows keep NULL.
    op.add_column(
        "documents",
        sa.Column(
            "document_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "document_metadata")

    op.drop_index("ix_documents_document_type", table_name="documents")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint(
            "ck_documents_document_type",
            "documents",
            type_="check",
        )
    op.drop_column("documents", "document_type")

    postgresql.ENUM(
        *_DOCUMENT_TYPE_VALUES,
        name="document_type_enum",
    ).drop(op.get_bind(), checkfirst=True)
