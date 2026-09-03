"""Create initial banking schema.

Revision ID: 20260903_01
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "plaid_items",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("plaid_item_id", sa.String(length=255), nullable=False),
        sa.Column("access_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("institution_id", sa.String(length=255), nullable=True),
        sa.Column("sync_cursor", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plaid_item_id"),
    )
    op.create_index("ix_plaid_items_user_id", "plaid_items", ["user_id"])

    op.create_table(
        "accounts",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("plaid_item_id", sa.Uuid(), nullable=False),
        sa.Column("plaid_account_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("official_name", sa.String(length=255), nullable=True),
        sa.Column("mask", sa.String(length=16), nullable=True),
        sa.Column("account_type", sa.String(length=64), nullable=False),
        sa.Column("account_subtype", sa.String(length=64), nullable=True),
        sa.Column("iso_currency_code", sa.String(length=3), nullable=True),
        sa.Column("current_balance", sa.Numeric(19, 4), nullable=True),
        sa.Column("available_balance", sa.Numeric(19, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plaid_item_id"],
            ["plaid_items.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plaid_account_id"),
    )
    op.create_index("ix_accounts_plaid_item_id", "accounts", ["plaid_item_id"])

    op.create_table(
        "transactions",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("plaid_transaction_id", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("iso_currency_code", sa.String(length=3), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("authorized_date", sa.Date(), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("merchant_name", sa.String(length=512), nullable=True),
        sa.Column("pending", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("category_primary", sa.String(length=128), nullable=True),
        sa.Column("category_detailed", sa.String(length=128), nullable=True),
        sa.Column(
            "is_removed",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plaid_transaction_id"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index(
        "ix_transactions_account_date",
        "transactions",
        ["account_id", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_account_date", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_accounts_plaid_item_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_index("ix_plaid_items_user_id", table_name="plaid_items")
    op.drop_table("plaid_items")
