"""Bootstrap script for the AcademicOS Postgres database.

Run once after cloning the repo (or any time you want to recreate the
local DB from scratch). Creates the ``academicos`` role and database
that the backend expects, then applies all Alembic migrations.

Why this script exists
----------------------
``backend/.env.example`` ships with::

    DATABASE_URL=postgresql+asyncpg://academicos:academicos@localhost:5432/academicos

That URL only works once a matching ``academicos`` role and database
exist in Postgres. The default Postgres install creates a ``postgres``
superuser and no other roles, so a fresh checkout boots the backend,
hits ``InvalidPasswordError`` on the first request, and 500s.

This script bridges that gap by:

1. Asking you (once) for the ``postgres`` superuser password.
2. Creating the ``academicos`` role with password ``academicos`` if
   it doesn't already exist.
3. Creating the ``academicos`` database owned by that role if it
   doesn't already exist.
4. Running ``alembic upgrade head`` against the new database.

After it finishes, you should be able to start the backend with no
other changes.

Usage
-----
From the ``backend/`` directory, with the project's virtualenv
activated (so ``asyncpg`` and ``alembic`` are importable)::

    python -m scripts.bootstrap_db

It is intentionally idempotent — re-running it after the role and
database already exist is safe; both ``CREATE ROLE`` and
``CREATE DATABASE`` use ``IF NOT EXISTS`` equivalents.
"""
from __future__ import annotations

import asyncio
import getpass
import os
import sys
from pathlib import Path

import asyncpg


# Defaults that match ``backend/.env.example``. Override via env vars if
# your local Postgres install uses different names.
PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_SUPERUSER = os.environ.get("PG_SUPERUSER", "postgres")
APP_DB_USER = os.environ.get("APP_DB_USER", "academicos")
APP_DB_PASSWORD = os.environ.get("APP_DB_PASSWORD", "academicos")
APP_DB_NAME = os.environ.get("APP_DB_NAME", "academicos")


def prompt_password(prompt: str) -> str:
    """Read a password from stdin without echoing it."""
    return getpass.getpass(prompt)


async def role_exists(conn: asyncpg.Connection, role: str) -> bool:
    row = await conn.fetchrow("SELECT 1 FROM pg_roles WHERE rolname = $1", role)
    return row is not None


async def database_exists(conn: asyncpg.Connection, db: str) -> bool:
    row = await conn.fetchrow("SELECT 1 FROM pg_database WHERE datname = $1", db)
    return row is not None


async def bootstrap(superuser_password: str) -> None:
    """Create the academicos role and DB if missing."""
    print(f"Connecting to Postgres at {PG_HOST}:{PG_PORT} as {PG_SUPERUSER!r}...")
    conn = await asyncpg.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_SUPERUSER,
        password=superuser_password,
        database="postgres",  # the always-present default DB
    )
    try:
        if not await role_exists(conn, APP_DB_USER):
            # Quote the role name and password so special characters are safe.
            # Note: PostgreSQL's CREATE ROLE / ALTER ROLE PASSWORD clauses
            # do not accept $1 bind parameters in this form — the password
            # must be interpolated into the SQL string. APP_DB_PASSWORD
            # comes from the env / a hard-coded default, so injection is
            # not a concern here.
            await conn.execute(
                f'CREATE ROLE "{APP_DB_USER}" WITH LOGIN PASSWORD \'{APP_DB_PASSWORD}\''
            )
            print(f"  + created role {APP_DB_USER!r}")
        else:
            # Reset password to match the one in .env.example so a stale
            # password doesn't break things later. Idempotent.
            await conn.execute(
                f'ALTER ROLE "{APP_DB_USER}" WITH LOGIN PASSWORD \'{APP_DB_PASSWORD}\''
            )
            print(f"  = role {APP_DB_USER!r} already exists (password reset)")

        if not await database_exists(conn, APP_DB_NAME):
            await conn.execute(
                f'CREATE DATABASE "{APP_DB_NAME}" OWNER "{APP_DB_USER}"'
            )
            print(f"  + created database {APP_DB_NAME!r} (owner={APP_DB_USER!r})")
        else:
            print(f"  = database {APP_DB_NAME!r} already exists")
    finally:
        await conn.close()


def run_alembic_upgrade() -> None:
    """Apply all migrations against the freshly-bootstrapped database."""
    import subprocess

    backend_dir = Path(__file__).resolve().parent.parent
    print(f"Running 'alembic upgrade head' in {backend_dir}...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
    )
    if result.returncode != 0:
        print(
            "  ! alembic exited non-zero. Check the traceback above.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


async def main() -> None:
    password = os.environ.get("POSTGRES_SUPERUSER_PASSWORD")
    if not password:
        password = prompt_password(
            f"Postgres superuser password for {PG_SUPERUSER}@{PG_HOST}:{PG_PORT}: "
        )

    await bootstrap(password)
    run_alembic_upgrade()
    print()
    print("Done. You can now start the backend:")
    print("    uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    asyncio.run(main())