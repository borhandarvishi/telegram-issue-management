"""Sending and replacing bot messages. The bot never edits a message."""

from __future__ import annotations

import logging
import re

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import LinkPreviewOptions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.db.models import Dialog, Notice, User, utcnow

logger = logging.getLogger("issuebot")
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
_TOKEN = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")


def safe_error(exc: BaseException) -> str:
    return _TOKEN.sub("[token]", str(exc))[:400]


async def safe_delete(bot, chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return


async def show_screen(bot, db: AsyncSession, dialog: Dialog, text: str, markup) -> None:
    """Send the new screen, then delete the previous one and any push notices."""
    notices = list(await db.scalars(select(Notice).where(Notice.user_id == dialog.user_id)))
    previous = dialog.message_id
    sent = await bot.send_message(
        dialog.user_id,
        text,
        reply_markup=markup,
        link_preview_options=NO_PREVIEW,
    )
    dialog.message_id = sent.message_id
    dialog.updated_at = utcnow()
    for notice in notices:
        await safe_delete(bot, dialog.user_id, notice.message_id)
        await db.delete(notice)
    if previous and previous != sent.message_id:
        await safe_delete(bot, dialog.user_id, previous)


async def push_notice(bot, db: AsyncSession, user_id: int, text: str) -> None:
    user = await db.get(User, user_id)
    if user is None or not user.opened_bot:
        return
    existing = list(
        await db.scalars(select(Notice).where(Notice.user_id == user_id).order_by(Notice.id))
    )
    overflow = existing[:-7] if len(existing) >= 8 else []
    for old in overflow:
        await safe_delete(bot, user_id, old.message_id)
        await db.delete(old)
    try:
        sent = await bot.send_message(user_id, text, link_preview_options=NO_PREVIEW)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("notice failed user=%s err=%s", user_id, safe_error(exc))
        return
    db.add(Notice(user_id=user_id, message_id=sent.message_id, created_at=utcnow()))
