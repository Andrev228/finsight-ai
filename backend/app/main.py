"""finsight-ai FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app import __version__
from app.analytics.router import router as analytics_router
from app.ai.router import router as ai_router
from app.billing.router import router as billing_router
from app.core.config import settings
from app.plaid.router import router as plaid_router
from app.system.router import router as system_router


async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def create_app() -> FastAPI:
    application = FastAPI(
        title="finsight-ai",
        version=__version__,
        description="AI-powered personal finance insights (budgeting, not advice).",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)
    application.include_router(analytics_router)
    application.include_router(ai_router)
    application.include_router(billing_router)
    application.include_router(system_router)
    application.include_router(plaid_router)
    return application


app = create_app()
