"""finsight-ai FastAPI application entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.config import settings

app = FastAPI(
    title="finsight-ai",
    version=__version__,
    description="AI-powered personal finance insights (budgeting, not advice).",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env, "version": __version__}


@app.get("/api/health", tags=["system"])
async def api_health() -> dict[str, str]:
    """Alias used by the frontend."""
    return {"status": "ok", "version": __version__}
