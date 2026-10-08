"""Telegram users and the screen they currently have open."""

from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.constants import Screen
from issuebot.db.models import Dialog, Membership, Project, User, utcnow


async def upsert_user(db: AsyncSession, tg: TgUser, *, opened_bot: bool = False) -> User:
    user = await db.get(User, tg.id)
    if user is None:
        user = User(id=tg.id, opened_bot=opened_bot)
        db.add(user)
    user.username = tg.username
    user.first_name = tg.first_name or ""
    user.last_name = tg.last_name
    user.updated_at = utcnow()
    if opened_bot:
        user.opened_bot = True
    await db.flush()
    return user


async def touch_opened(db: AsyncSession, user: User) -> None:
    if not user.opened_bot:
        user.opened_bot = True
        user.updated_at = utcnow()


async def get_dialog(db: AsyncSession, user_id: int) -> Dialog | None:
    return await db.get(Dialog, user_id)


async def get_or_create_dialog(db: AsyncSession, user_id: int) -> Dialog:
    dialog = await db.get(Dialog, user_id)
    if dialog is None:
        dialog = Dialog(user_id=user_id, state=Screen.HOME, payload={})
        db.add(dialog)
        await db.flush()
    if dialog.payload is None:
        dialog.payload = {}
    return dialog


def update_payload(dialog: Dialog, **kwargs: object) -> None:
    data = dict(dialog.payload or {})
    for key, value in kwargs.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    dialog.payload = data


async def projects_for(db: AsyncSession, user_id: int) -> list[Project]:
    stmt = (
        select(Project)
        .join(Membership, Membership.project_id == Project.id)
        .where(Membership.user_id == user_id)
        .order_by(Project.created_at.desc())
    )
    return list(await db.scalars(stmt))
