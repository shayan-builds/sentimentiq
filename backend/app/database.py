"""Database engine and session dependency for the FastAPI application."""

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

# Resolve the repository root from this file so loading works from any CWD.
ROOT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ROOT_ENV_PATH)


def _required_environment_variable(name: str) -> str:
    """Read a required setting without including its value in errors."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set.")
    return value


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=_required_environment_variable("POSTGRES_USER"),
    password=_required_environment_variable("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(_required_environment_variable("POSTGRES_PORT")),
    database=_required_environment_variable("POSTGRES_DB"),
)

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one database session and always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
