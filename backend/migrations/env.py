"""Alembic environment for the backend schema."""
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic may be launched from the repository root, where ``app`` is not on
# sys.path. Resolve the backend package from this file instead of the caller's
# working directory.
BACKEND_PATH = str(Path(__file__).resolve().parents[1])
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

from app.database import DATABASE_URL
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the application's URL assembly without writing credentials to config files.
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.render_as_string(hide_password=False).replace("%", "%%"),
)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Render migration SQL without connecting to PostgreSQL."""
    context.configure(
        url=DATABASE_URL.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a short-lived engine connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
