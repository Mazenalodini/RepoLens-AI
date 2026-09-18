"""RepoLens AI — Database Configuration.

SQLAlchemy engine and session management for SQLite persistence.
"""

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "repolens.db"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


def get_database_url() -> str:
    """Resolve the database URL from environment or default.

    Uses REPOLENS_DB_URL if set, otherwise a local SQLite file.
    """
    url = os.environ.get("REPOLENS_DB_URL")
    if url:
        return url

    db_path = Path(os.environ.get("REPOLENS_DB_PATH", _DEFAULT_DB_PATH))
    return f"sqlite:///{db_path}"


def create_db_engine(url: str | None = None):
    """Create a SQLAlchemy engine.

    Args:
        url: Database URL. If None, resolved from environment/default.

    Returns:
        SQLAlchemy Engine instance.
    """
    db_url = url or get_database_url()
    logger.info("Initializing database: %s", db_url.split("///")[0] + "///***")
    return create_engine(db_url, echo=False)


def create_tables(engine) -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(engine)


def create_session_factory(engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""
    return sessionmaker(bind=engine)
