import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

from database import Base  # noqa: E402
import models  # noqa: F401,E402  (import to register tables on Base.metadata)

config = context.config

# Allow the DB URL to be overridden by the DATABASE_URL env var so the same
# migrations can be applied to local SQLite and to a managed Postgres in prod.
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    if _env_url.startswith("postgres://"):
        _env_url = "postgresql://" + _env_url[len("postgres://") :]
    config.set_main_option("sqlalchemy.url", _env_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL statements without connecting to a DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the DB and apply migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
