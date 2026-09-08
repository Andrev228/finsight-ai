"""Authenticated user and administrative boundaries."""

import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.jwt import InvalidTokenError, decode_hs256


@dataclass(frozen=True)
class UserPrincipal:
    user_id: str


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UserPrincipal:
    if settings.app_env == "local" and settings.allow_insecure_local_auth:
        return UserPrincipal(user_id=settings.plaid_client_user_id)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return UserPrincipal(user_id=_verify_token(credentials.credentials))


CurrentUser = Annotated[UserPrincipal, Depends(get_current_user)]


def require_admin(
    x_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    configured_key = settings.admin_api_key.get_secret_value()
    if settings.app_env == "local" and settings.allow_insecure_local_admin:
        return
    if not configured_key or not x_admin_key or not secrets.compare_digest(
        configured_key,
        x_admin_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required",
        )


AdminAccess = Annotated[None, Depends(require_admin)]


def _verify_token(token: str) -> str:
    try:
        return decode_hs256(
            token,
            secret=settings.auth_jwt_secret.get_secret_value(),
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
        )
    except InvalidTokenError:
        raise _unauthorized() from None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
