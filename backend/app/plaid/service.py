"""Plaid application workflows."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import TokenCipher
from app.db.models import PlaidItem
from app.plaid.client import PlaidClient
from app.plaid.exceptions import PlaidItemAlreadyExistsError
from app.plaid.schemas import ConnectedItem


class PlaidService:
    def __init__(
        self,
        client: PlaidClient,
        session: AsyncSession,
        token_cipher: TokenCipher,
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
