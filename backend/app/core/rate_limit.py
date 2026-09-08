"""Redis-backed fixed-window rate limiting."""

import asyncio
import hashlib
import hmac
import time
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, status

from app.core.auth import CurrentUser
from app.core.config import settings

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return current
""".strip()


async def enforce_ai_rate_limit(current_user: CurrentUser) -> None:
    if settings.ai_requests_per_minute < 1:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI rate limiting is not configured",
        )
    window = int(time.time()) // 60
    key = f"rate:ai:{_fingerprint(current_user.user_id)}:{window}"
    try:
        count = await _redis_eval(key, 60)
    except (OSError, EOFError, TimeoutError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI rate limiter is unavailable",
        ) from exc
    if count > settings.ai_requests_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI request limit exceeded",
            headers={"Retry-After": "60"},
        )


AiRateLimit = Annotated[None, Depends(enforce_ai_rate_limit)]


def _fingerprint(user_id: str) -> str:
    secret = settings.app_encryption_key.get_secret_value().encode()
    if not secret:
        raise ValueError("Rate-limit fingerprint secret is not configured")
    return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()


async def _redis_eval(key: str, ttl_seconds: int) -> int:
    parsed = urlparse(settings.redis_url)
    if parsed.scheme != "redis" or not parsed.hostname:
        raise ValueError("Unsupported Redis URL")
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(parsed.hostname, parsed.port or 6379),
        timeout=2,
    )
    try:
        if parsed.password:
            await _send_command(writer, "AUTH", parsed.password)
            await _read_response(reader)
        database = parsed.path.lstrip("/")
        if database and database != "0":
            await _send_command(writer, "SELECT", database)
            await _read_response(reader)
        await _send_command(
            writer,
            "EVAL",
            RATE_LIMIT_SCRIPT,
            "1",
            key,
            str(ttl_seconds),
        )
        result = await asyncio.wait_for(_read_response(reader), timeout=2)
        if not isinstance(result, int):
            raise ValueError("Unexpected Redis response")
        return result
    finally:
        writer.close()
        await writer.wait_closed()


async def redis_ping() -> bool:
    parsed = urlparse(settings.redis_url)
    if parsed.scheme != "redis" or not parsed.hostname:
        return False
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(parsed.hostname, parsed.port or 6379),
            timeout=2,
        )
        try:
            if parsed.password:
                await _send_command(writer, "AUTH", parsed.password)
                await asyncio.wait_for(_read_response(reader), timeout=2)
            await _send_command(writer, "PING")
            return (
                await asyncio.wait_for(_read_response(reader), timeout=2)
                == "PONG"
            )
        finally:
            writer.close()
            await writer.wait_closed()
    except (OSError, EOFError, TimeoutError, ValueError):
        return False


async def _send_command(
    writer: asyncio.StreamWriter,
    *parts: str,
) -> None:
    encoded = [part.encode() for part in parts]
    payload = [f"*{len(encoded)}\r\n".encode()]
    for part in encoded:
        payload.extend((f"${len(part)}\r\n".encode(), part, b"\r\n"))
    writer.writelines(payload)
    await writer.drain()


async def _read_response(
    reader: asyncio.StreamReader,
) -> str | int | None:
    prefix = await reader.readexactly(1)
    line = (await reader.readline()).removesuffix(b"\r\n")
    if prefix == b"+":
        return line.decode()
    if prefix == b":":
        return int(line)
    if prefix == b"$":
        length = int(line)
        if length == -1:
            return None
        value = await reader.readexactly(length)
        await reader.readexactly(2)
        return value.decode()
    if prefix == b"-":
        raise ValueError(f"Redis error: {line.decode()}")
    raise ValueError("Unsupported Redis response")
