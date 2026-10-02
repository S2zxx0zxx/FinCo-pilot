import asyncio
from logging.config import fileConfig

from sqlalchemy import text
from sqlalchemy.engine import Connection

from alembic import context

from app.core.config import get_settings
from app.core.database import Base
from app.core.database_runtime import create_database_engine
from app.models import *  # noqa: F401,F403
# Agents module models (always loaded so migrations stay in sync; the
# feature itself is gated at runtime by AGENTS_ENABLED).
from app.agents.models import *  # noqa: F401,F403

config = context.config
settings = get_settings()

config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


_MIGRATION_ADVISORY_LOCK = 46069839201401


def do_run_migrations(connection: Connection) -> None:
    # Session-level advisory lock serializes deploys that accidentally start
    # Alembic concurrently. Commit the lock-acquisition transaction first; the
    # session lock remains held until the explicit unlock below.
    connection.execute(
        text("SELECT pg_advisory_lock(:lock_id)"),
        {"lock_id": _MIGRATION_ADVISORY_LOCK},
    )
    connection.commit()
    try:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": _MIGRATION_ADVISORY_LOCK},
        )
        connection.commit()


async def run_async_migrations() -> None:
    connectable = create_database_engine(settings, short_lived=True)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
