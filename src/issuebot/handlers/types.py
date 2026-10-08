"""The person, their screen, and the update being handled."""

from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.db.models import Dialog, User


@dataclass
class Ctx:
    bot: Bot
    db: AsyncSession
    chat_id: int
    account: User
    dialog: Dialog
    text: str = ""
    file_id: str | None = None

    @property
    def payload(self) -> dict:
        return self.dialog.payload or {}
