"""Harden AI run telemetry.

Revision ID: 20260905_05
Revises: 20260905_04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_05"
down_revision: str | None = "20260905_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_ai_runs_user_id", table_name="ai_runs")
    op.alter_column("ai_runs", "user_id", new_column_name="user_fingerprint")
    op.alter_column(
        "ai_runs",
        "user_fingerprint",
        type_=sa.String(length=64),
        existing_type=sa.String(length=255),
    )
    op.add_column(
        "ai_runs",
        sa.Column(
            "unsupported",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ai_runs_user_fingerprint",
        "ai_runs",
        ["user_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_runs_user_fingerprint", table_name="ai_runs")
    op.drop_column("ai_runs", "unsupported")
    op.alter_column(
        "ai_runs",
        "user_fingerprint",
        type_=sa.String(length=255),
        existing_type=sa.String(length=64),
    )
    op.alter_column(
        "ai_runs",
        "user_fingerprint",
        new_column_name="user_id",
    )
    op.create_index("ix_ai_runs_user_id", "ai_runs", ["user_id"])
