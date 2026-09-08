"""finsight-ai FastAPI application factory."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from app import __version__
from app.ai.agent import InvalidAnalyticsPeriodError
from app.ai.exceptions import LLMConfigurationError, LLMProviderError
from app.ai.history import ConversationNotFoundError
from app.analytics.router import router as analytics_router
from app.ai.router import router as ai_router
from app.billing.router import router as billing_router
from app.core.config import settings
from app.plaid.router import router as plaid_router
from app.system.router import router as system_router


async def add_security_headers(request: StarletteRequest, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(ConversationNotFoundError)
    async def _handle_conversation_not_found(
        _request: Request,
        _exc: ConversationNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Conversation was not found"},
        )

    @application.exception_handler(InvalidAnalyticsPeriodError)
    async def _handle_invalid_period(
        _request: Request,
        exc: InvalidAnalyticsPeriodError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @application.exception_handler(LLMConfigurationError)
    async def _handle_llm_configuration(
        _request: Request,
        _exc: LLMConfigurationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Gemini is not configured"},
        )

    @application.exception_handler(LLMProviderError)
    async def _handle_llm_provider(
        _request: Request,
        exc: LLMProviderError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "detail": {
                    "message": "Gemini request failed",
                    "error_code": exc.error_code,
                    "request_id": exc.request_id,
                },
            },
        )


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
    _register_exception_handlers(application)
    application.include_router(analytics_router)
    application.include_router(ai_router)
    application.include_router(billing_router)
    application.include_router(system_router)
    application.include_router(plaid_router)
    return application


app = create_app()
