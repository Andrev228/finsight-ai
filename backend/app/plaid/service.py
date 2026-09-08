"""Plaid application workflows."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import AppCipher
from app.db.models import Account, PlaidItem, Transaction
from app.plaid.client import PlaidClient
from app.plaid.exceptions import (
    PlaidItemAlreadyExistsError,
    PlaidItemNotFoundError,
)
from app.plaid.schemas import (
    AccountsSyncResult,
    ConnectedItem,
    PlaidAccount,
    PlaidTransaction,
    SyncedAccount,
    TransactionsSyncResult,
)


class PlaidService:
    def __init__(
        self,
        client: PlaidClient,
        session: AsyncSession,
        token_cipher: AppCipher,
    ) -> None:
        self._client = client
        self._session = session
        self._token_cipher = token_cipher

    async def connect_item(
        self,
        public_token: str,
        user_id: str,
    ) -> ConnectedItem:
        exchange = await self._client.exchange_public_token(public_token)
        item = PlaidItem(
            user_id=user_id,
            plaid_item_id=exchange.item_id,
            access_token_encrypted=self._token_cipher.encrypt(
                exchange.access_token.get_secret_value(),
            ),
        )
        self._session.add(item)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise PlaidItemAlreadyExistsError(exchange.item_id) from exc

        return ConnectedItem(id=item.id, plaid_item_id=item.plaid_item_id)

    async def sync_accounts(
        self,
        item_id: UUID,
        user_id: str,
    ) -> AccountsSyncResult:
        item = await self._get_item(item_id, user_id)
        response = await self._client.get_accounts(
            self._token_cipher.decrypt(item.access_token_encrypted),
        )
        synced_accounts = await self._upsert_accounts(item.id, response.accounts)
        await self._session.commit()
        return AccountsSyncResult(
            accounts=[
                SyncedAccount(
                    id=account.id,
                    plaid_account_id=account.plaid_account_id,
                    name=account.name,
                    mask=account.mask,
                    account_type=account.account_type,
                    account_subtype=account.account_subtype,
                    current_balance=account.current_balance,
                    available_balance=account.available_balance,
                    iso_currency_code=account.iso_currency_code,
                )
                for account in synced_accounts
            ],
        )

    async def sync_transactions(
        self,
        item_id: UUID,
        user_id: str,
    ) -> TransactionsSyncResult:
        item = await self._get_item(item_id, user_id)
        access_token = self._token_cipher.decrypt(item.access_token_encrypted)
        cursor = item.sync_cursor
        added: dict[str, PlaidTransaction] = {}
        modified: dict[str, PlaidTransaction] = {}
        removed: set[str] = set()

        while True:
            response = await self._client.sync_transactions(access_token, cursor)
            await self._upsert_accounts(item.id, response.accounts)
            added.update(
                {transaction.transaction_id: transaction for transaction in response.added},
            )
            modified.update(
                {
                    transaction.transaction_id: transaction
                    for transaction in response.modified
                },
            )
            removed.update(transaction.transaction_id for transaction in response.removed)
            cursor = response.next_cursor
            if not response.has_more:
                break

        changed = {**added, **modified}
        await self._upsert_transactions(changed.values())

        if removed:
            removed_transactions = (
                await self._session.scalars(
                    select(Transaction).where(
                        Transaction.plaid_transaction_id.in_(removed),
                    ),
                )
            ).all()
            for transaction in removed_transactions:
                transaction.is_removed = True

        item.sync_cursor = cursor
        await self._session.commit()
        return TransactionsSyncResult(
            added=len(added),
            modified=len(modified),
            removed=len(removed),
        )

    async def _get_item(self, item_id: UUID, user_id: str) -> PlaidItem:
        item = await self._session.scalar(
            select(PlaidItem).where(
                PlaidItem.id == item_id,
                PlaidItem.user_id == user_id,
            ),
        )
        if item is None:
            raise PlaidItemNotFoundError(str(item_id))
        return item

    async def _upsert_accounts(
        self,
        item_id: UUID,
        plaid_accounts: list[PlaidAccount],
    ) -> list[Account]:
        plaid_account_ids = [account.account_id for account in plaid_accounts]
        existing_accounts = (
            await self._session.scalars(
                select(Account).where(
                    Account.plaid_account_id.in_(plaid_account_ids),
                ),
            )
        ).all()
        accounts_by_plaid_id = {
            account.plaid_account_id: account for account in existing_accounts
        }

        synced_accounts: list[Account] = []
        for plaid_account in plaid_accounts:
            account = accounts_by_plaid_id.get(plaid_account.account_id)
            if account is None:
                account = Account(
                    plaid_item_id=item_id,
                    plaid_account_id=plaid_account.account_id,
                )
                self._session.add(account)

            account.name = plaid_account.name
            account.official_name = plaid_account.official_name
            account.mask = plaid_account.mask
            account.account_type = plaid_account.type
            account.account_subtype = plaid_account.subtype
            account.iso_currency_code = plaid_account.balances.iso_currency_code
            account.current_balance = plaid_account.balances.current
            account.available_balance = plaid_account.balances.available
            synced_accounts.append(account)

        await self._session.flush()
        return synced_accounts

    async def _upsert_transactions(
        self,
        plaid_transactions: Iterable[PlaidTransaction],
    ) -> None:
        transactions = list(plaid_transactions)
        if not transactions:
            return

        account_ids = {transaction.account_id for transaction in transactions}
        accounts = (
            await self._session.scalars(
                select(Account).where(Account.plaid_account_id.in_(account_ids)),
            )
        ).all()
        accounts_by_plaid_id = {
            account.plaid_account_id: account for account in accounts
        }
        transaction_ids = {
            transaction.transaction_id for transaction in transactions
        }
        existing_transactions = (
            await self._session.scalars(
                select(Transaction).where(
                    Transaction.plaid_transaction_id.in_(transaction_ids),
                ),
            )
        ).all()
        transactions_by_plaid_id = {
            transaction.plaid_transaction_id: transaction
            for transaction in existing_transactions
        }

        for plaid_transaction in transactions:
            account = accounts_by_plaid_id[plaid_transaction.account_id]
            transaction = transactions_by_plaid_id.get(
                plaid_transaction.transaction_id,
            )
            if transaction is None:
                transaction = Transaction(
                    account_id=account.id,
                    plaid_transaction_id=plaid_transaction.transaction_id,
                )
                self._session.add(transaction)

            category = plaid_transaction.personal_finance_category
            transaction.amount = plaid_transaction.amount
            transaction.iso_currency_code = plaid_transaction.iso_currency_code
            transaction.transaction_date = plaid_transaction.date
            transaction.authorized_date = plaid_transaction.authorized_date
            transaction.name = plaid_transaction.name
            transaction.merchant_name = plaid_transaction.merchant_name
            transaction.pending = plaid_transaction.pending
            transaction.category_primary = category.primary if category else None
            transaction.category_detailed = category.detailed if category else None
            transaction.is_removed = False
