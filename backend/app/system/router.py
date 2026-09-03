"""System health endpoints."""

from fastapi import APIRouter

from app import __version__
from app.core.config import settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env, "version": __version__}


@router.get("/api/health")
async def api_health() -> dict[str, str]:
    """Alias used by the frontend."""
    return {"status": "ok", "version": __version__}
