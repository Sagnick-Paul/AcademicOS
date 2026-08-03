"""FastAPI application entry point.

Boilerplate for the AcademicOS backend. Wires the FastAPI app, registers
middleware, mounts API routers, and exposes a health endpoint. Business
logic, authentication, and database integration will be added later.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging


def create_application() -> FastAPI:
    """Application factory for the FastAPI app."""
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="AcademicOS backend API.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — permissive defaults; tighten in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight liveness probe."""
        return {"status": "ok"}

    # Routers will be registered here as they are implemented.
    # app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
