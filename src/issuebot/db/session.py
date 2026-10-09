"""Async engine and sessions."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from issuebot.db.models import Base


class Database:
    def __init__(self, url: str, *, memory: bool = False) -> None:
        self.url = url
        self.engine = _engine(url, memory=memory)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        _enable_sqlite_fk(self.engine)

    async def create_tables(self) -> None:
        _ensure_sqlite_directory(self.url)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_issue_columns)

    def session(self) -> AsyncSession:
        return self.sessions()


def _engine(url: str, *, memory: bool) -> AsyncEngine:
    if memory:
        return create_async_engine(
            "sqlite+aiosqlite://",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(url)


def _ensure_sqlite_directory(url: str) -> None:
    parsed = make_url(url)
    if not parsed.drivername.startswith("sqlite"):
        return
    database = parsed.database
    if not database or database == ":memory:":
        return
    Path(database).parent.mkdir(parents=True, exist_ok=True)


def _ensure_issue_columns(connection) -> None:
    rows = connection.execute(text("PRAGMA table_info(issues)")).fetchall()
    names = {row[1] for row in rows}
    if "urgent" not in names:
        connection.execute(text("ALTER TABLE issues ADD COLUMN urgent BOOLEAN NOT NULL DEFAULT 0"))
    if "reopened" not in names:
        connection.execute(
            text("ALTER TABLE issues ADD COLUMN reopened BOOLEAN NOT NULL DEFAULT 0")
        )


def _enable_sqlite_fk(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
