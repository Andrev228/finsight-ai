"""User-scoped SQL financial analytics."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, and_, case, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.schemas import (
    AnalyticsPeriod,
    CategorySpending,
    FinancialOverview,
    MonthlyCashFlow,
)
from app.db.models import Account, PlaidItem, Transaction

ZERO = Decimal("0")
UNCATEGORIZED = "UNCATEGORIZED"
NON_CASH_FLOW_CATEGORIES = (
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "LOAN_PAYMENTS",
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_overview(
        self,
        user_id: str,
        start: date,
        end_exclusive: date,
        currency: str,
        category_limit: int,
    ) -> FinancialOverview:
        await self._session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"),
        )
        filters = self._transaction_filters(
            user_id,
            start,
            end_exclusive,
            currency,
        )
        category = func.coalesce(Transaction.category_primary, UNCATEGORIZED)
        excluded_movement = category.in_(NON_CASH_FLOW_CATEGORIES)
        income_transaction = category == "INCOME"
        spending_transaction = and_(
            ~excluded_movement,
            ~income_transaction,
        )
        spending_expression = case(
            (spending_transaction, Transaction.amount),
            else_=ZERO,
        )
        income_expression = case(
            (income_transaction, -Transaction.amount),
            else_=ZERO,
        )
        counted_transaction = case(
            (or_(spending_transaction, income_transaction), Transaction.id),
        )

        totals = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(spending_expression), ZERO),
                    func.coalesce(func.sum(income_expression), ZERO),
                    func.count(counted_transaction),
                )
                .select_from(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .join(PlaidItem, Account.plaid_item_id == PlaidItem.id)
                .where(*filters),
            )
        ).one()
        total_spending = Decimal(totals[0])
        total_income = Decimal(totals[1])

        category_rows = (
            await self._session.execute(
                select(
                    category.label("category"),
                    func.sum(Transaction.amount).label("amount"),
                    func.count(Transaction.id).label("transaction_count"),
                )
                .select_from(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .join(PlaidItem, Account.plaid_item_id == PlaidItem.id)
                .where(*filters, spending_transaction)
                .group_by("category")
                .order_by(
                    func.sum(Transaction.amount).desc(),
                    category.asc(),
                )
                .limit(category_limit),
            )
        ).all()

        month = cast(func.date_trunc("month", Transaction.transaction_date), Date)
        monthly_rows = (
            await self._session.execute(
                select(
                    month.label("month"),
                    func.coalesce(func.sum(spending_expression), ZERO),
                    func.coalesce(func.sum(income_expression), ZERO),
                )
                .select_from(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .join(PlaidItem, Account.plaid_item_id == PlaidItem.id)
                .where(*filters)
                .group_by(month)
                .order_by(month),
            )
        ).all()

        warnings: list[str] = []
        if not totals[2]:
            warnings.append("No settled transactions found for this period.")

        return FinancialOverview(
            period=AnalyticsPeriod(start=start, end_exclusive=end_exclusive),
            currency=currency,
            total_spending=total_spending,
            total_income=total_income,
            net_cash_flow=total_income - total_spending,
            transaction_count=int(totals[2]),
            top_categories=[
                CategorySpending(
                    category=row.category,
                    amount=Decimal(row.amount),
                    transaction_count=int(row.transaction_count),
                )
                for row in category_rows
            ],
            monthly_cash_flow=[
                MonthlyCashFlow(
                    month=row[0],
                    spending=Decimal(row[1]),
                    income=Decimal(row[2]),
                    net_cash_flow=Decimal(row[2]) - Decimal(row[1]),
                )
                for row in monthly_rows
            ],
            generated_at=datetime.now(UTC),
            warnings=warnings,
        )

    @staticmethod
    def _transaction_filters(
        user_id: str,
        start: date,
        end_exclusive: date,
        currency: str,
    ) -> tuple[object, ...]:
        return (
            PlaidItem.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end_exclusive,
            func.coalesce(
                Transaction.iso_currency_code,
                Account.iso_currency_code,
            )
            == currency,
            Transaction.pending.is_(False),
            Transaction.is_removed.is_(False),
            and_(
                Transaction.amount.is_not(None),
                Transaction.amount != ZERO,
            ),
        )
