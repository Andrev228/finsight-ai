"""System health endpoints."""

from fastapi import APIRouter
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.core.config import settings
from app.core.rate_limit import redis_ping
from app.db.session import async_session

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env, "version": __version__}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    """Alias used by the frontend."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        redis_ready = await redis_ping()
    except (OSError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    if not redis_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        )
    return {"status": "ready"}
