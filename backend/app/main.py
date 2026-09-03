"""finsight-ai FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.plaid.router import router as plaid_router
from app.system.router import router as system_router


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
    application.include_router(system_router)
    application.include_router(plaid_router)
    return application


app = create_app()
