"""FastAPI application entry point.

Wires the FastAPI app, registers middleware, mounts API routers, and
exposes a health endpoint. Business logic lives in services; the
HTTP layer here is glue.
"""
from __future__ import annotations

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

# pyrefly: ignore [missing-import]
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

    # Mount the v1 API. Importing the endpoint modules here (rather than
    # inside ``app.api.v1``) keeps that package import-side-effect-free
    # so a test can import the router without triggering route
    # registration.
    from app.api.v1 import api_router
    from app.api.v1.endpoints import auth as _auth  # noqa: F401
    from app.api.v1.endpoints import courses as _courses  # noqa: F401
    from app.api.v1.endpoints import documents as _documents  # noqa: F401
    from app.api.v1.endpoints import search as _search  # noqa: F401
    from app.api.v1.endpoints import chat as _chat  # noqa: F401

    api_router.include_router(_auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(_courses.router, prefix="/courses", tags=["courses"])
    api_router.include_router(_documents.router, prefix="/documents", tags=["documents"])
    api_router.include_router(_search.router, prefix="/search", tags=["search"])
    api_router.include_router(_chat.router, prefix="/chat", tags=["chat"])
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
