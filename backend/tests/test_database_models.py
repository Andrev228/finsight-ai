"""Tests for the initial database metadata."""

from app.db.base import Base
from app.db.models import Account, PlaidItem, Transaction


def test_initial_banking_tables_are_registered():
    assert {PlaidItem.__tablename__, Account.__tablename__, Transaction.__tablename__} <= {
        table.name for table in Base.metadata.sorted_tables
    }


def test_money_uses_fixed_precision_numeric():
    amount = Transaction.__table__.c.amount.type
    assert amount.precision == 19
    assert amount.scale == 4
