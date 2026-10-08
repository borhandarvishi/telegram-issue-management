"""One database session per update, and one user at a time.

The lock is held until the session commits, so two taps from the same person
cannot overwrite each other's screen.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject

from issuebot.db.session import Database
from issuebot.services.accounts import get_or_create_dialog, upsert_user

_locks: dict[int, asyncio.Lock] = {}


def _subject(event: TelegramObject) -> TelegramObject:
    """The update middleware receives an Update; handlers receive the inner event."""
    inner = getattr(event, "event", None)
    if isinstance(inner, TelegramObject):
        return inner
    return event


def _user_id(event: TelegramObject) -> int | None:
    user = getattr(_subject(event), "from_user", None)
    if user is None:
        return None
    return user.id


class ContextMiddleware(BaseMiddleware):
    def __init__(self, database: Database) -> None:
        self.database = database

    async def __call__(self, handler, event: TelegramObject, data: dict):
        subject = _subject(event)
        user_id = _user_id(event)
        async with _user_lock(user_id):
            async with self.database.session() as db:
                data["db"] = db
                if (
                    isinstance(subject, Message)
                    and subject.chat.type == ChatType.PRIVATE
                    and subject.from_user
                ):
                    data["account"] = await upsert_user(db, subject.from_user, opened_bot=True)
                    data["dialog"] = await get_or_create_dialog(db, subject.from_user.id)
                try:
                    result = await handler(event, data)
                except Exception:
                    await db.rollback()
                    raise
                await db.commit()
                return result


@asynccontextmanager
async def _user_lock(user_id: int | None):
    if user_id is None:
        yield
        return
    lock = _locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        yield
