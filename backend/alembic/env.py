"""Alembic environment configuration.

Loads the SQLAlchemy `MetaData` from `app.db.base` and the database URL
from `app.core.config`. Run as:

    alembic revision --autogenerate -m "..."
    alembic upgrade head
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Importing the models package registers every model on `Base.metadata`
# so Alembic autogenerate sees all tables. Add new models there.
# `_models` is referenced below purely to keep static analyzers (Pyrefly)
# from flagging the import as unused; the side effect on `Base.metadata`
# is what we actually need.
import app.db.models as _models  # type: ignore[unused-ignore]  # noqa: F401
_ = _models  # explicit reference to silence "unused import"

config = context.config


def _alembic_database_url() -> str:
    """Return a *synchronous* DB URL for Alembic.

    The app uses an async driver (`postgresql+asyncpg`) at runtime, but
    Alembic runs migrations synchronously. Reusing the async URL here
    triggers `sqlalchemy.exc.MissingGreenlet` because the sync engine
    tries to await an asyncpg connect. We rewrite `+asyncpg` to
    `+psycopg2` (which is in `requirements.txt`) so migrations work
    against the same database without changing app behaviour.
    """
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + url[len("postgresql+asyncpg://"):]
    return url


# Inject the *sync* database URL.
config.set_main_option("sqlalchemy.url", _alembic_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
