"""Add vector-backed knowledge chunks.

Revision ID: 20260903_02
Revises: 20260903_01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260903_02"
down_revision: str | None = "20260903_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE knowledge_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(512) NOT NULL,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_chunks_embedding_hnsw
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        """,
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
