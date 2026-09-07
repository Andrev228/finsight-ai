"""Generate a short-lived HS256 token for an operator-controlled demo."""

import argparse
import base64
import hashlib
import hmac
import json
import time

from app.core.config import settings


def encode(value: object) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(value, separators=(",", ":")).encode(),
    ).rstrip(b"=").decode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id")
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    args = parser.parse_args()
    if not 60 <= args.ttl_seconds <= 86400:
        parser.error("ttl-seconds must be between 60 and 86400")
    secret = settings.auth_jwt_secret.get_secret_value()
    if len(secret) < 32:
        parser.error("AUTH_JWT_SECRET must contain at least 32 characters")
    header = encode({"alg": "HS256", "typ": "JWT"})
    payload = encode(
        {
            "sub": args.user_id,
            "iss": settings.auth_jwt_issuer,
            "aud": settings.auth_jwt_audience,
            "iat": int(time.time()),
            "exp": int(time.time()) + args.ttl_seconds,
        },
    )
    signature = base64.urlsafe_b64encode(
        hmac.new(
            secret.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest(),
    ).rstrip(b"=").decode()
    print(f"{header}.{payload}.{signature}")


if __name__ == "__main__":
    main()
