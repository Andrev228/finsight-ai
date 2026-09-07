"""Add knowledge ingestion metadata.

Revision ID: 20260903_03
Revises: 20260903_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_03"
down_revision: str | None = "20260903_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "knowledge_chunks",
        sa.Column("document_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column("chunk_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column("heading", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_knowledge_chunks_document_chunk",
        "knowledge_chunks",
        ["source", "document_hash", "chunk_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_knowledge_chunks_document_chunk",
        table_name="knowledge_chunks",
    )
    op.drop_column("knowledge_chunks", "fetched_at")
    op.drop_column("knowledge_chunks", "heading")
    op.drop_column("knowledge_chunks", "chunk_index")
    op.drop_column("knowledge_chunks", "document_hash")
