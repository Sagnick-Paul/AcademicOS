from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.pool import StaticPool

from app.core.config import settings
settings.ENVIRONMENT = "test"


from app.api.deps import _db_session_dep  # noqa: PLC2701 – intentional override target
from app.db import models  # noqa: F401 – registers ORM models on Base.metadata
from app.db.base import Base
from app.main import app



@pytest_asyncio.fixture(scope="function")
async def engine():
    """Fresh in-memory SQLite engine per test, schema bootstrapped."""
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def sessionmaker_(engine) -> async_sessionmaker[AsyncSession]:
    """Sessionmaker bound to the test engine."""
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture(scope="function")
async def db_session(sessionmaker_: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """Raw async session for direct repo manipulation in tests."""
    async with sessionmaker_() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(sessionmaker_: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the ASGI app with the test DB."""

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        async with sessionmaker_() as session:
            yield session

    # Override the callable that every FastAPI dep actually Depends() on.
    # deps.py wraps get_db inside _db_session_dep; all Depends() point there.
    app.dependency_overrides[_db_session_dep] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------- Storage isolation ----------


@pytest.fixture(autouse=True)
def _isolated_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the global storage singleton with a tmpdir-backed instance.

    Every test gets an isolated upload directory so:
    * No test touches the real ``backend/app/uploads/`` folder.
    * ``tmp_path`` is fresh per test — concurrent / sequential tests
      cannot interfere with each other's files.

    The singleton is swapped via ``monkeypatch`` so it is automatically
    restored after each test (even if the test fails or raises).
    """
    from app.storage import local as _local_mod

    new_storage = _local_mod.LocalStorage(tmp_path)
    monkeypatch.setattr(_local_mod, "_storage_singleton", new_storage, raising=False)


@pytest.fixture()
def upload_tmp_path(tmp_path: Path) -> Path:
    """Expose the per-test tmpdir root so tests can assert on file presence."""
    return tmp_path
