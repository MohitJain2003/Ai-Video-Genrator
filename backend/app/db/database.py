"""
Database engine and session management using SQLModel.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event, text

from app.config import get_settings


_settings = get_settings()

# ── Engine ───────────────────────────────────────────────────────

_db_url = _settings.database_url
if _db_url.startswith("sqlite"):
    # SQLite-specific: WAL mode for concurrent reads, foreign keys
    _connect_args = {"check_same_thread": False}
else:
    _connect_args = {}

engine = create_engine(
    _db_url,
    echo=_settings.debug,
    connect_args=_connect_args,
)

# Enable WAL mode for SQLite (better concurrency)
if _db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── Table Creation ───────────────────────────────────────────────

def create_db_and_tables() -> None:
    """Create all tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
    # Ensure llm_provider column exists in SQLite table
    with Session(engine) as session:
        try:
            session.execute(text("ALTER TABLE jobs ADD COLUMN llm_provider VARCHAR"))
            session.commit()
        except Exception:
            pass
        try:
            session.execute(text("ALTER TABLE jobs ADD COLUMN voice_id VARCHAR"))
            session.commit()
        except Exception:
            pass


# ── Session ──────────────────────────────────────────────────────

def get_session() -> Session:
    """Create a new database session."""
    return Session(engine)


def get_session_dep() -> Generator[Session, None, None]:
    """FastAPI dependency to get a database session and ensure it gets closed."""
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[Session, None]:
    """Async context manager for database sessions."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
