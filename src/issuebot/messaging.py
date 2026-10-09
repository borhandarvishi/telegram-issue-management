"""Sending and replacing bot messages. The bot never edits a message."""

from __future__ import annotations

import logging
import re

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import LinkPreviewOptions
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.db.models import Dialog, User, utcnow

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
    """Send the new screen, then delete only the previous screen. Notices stay."""
    del db
    previous = dialog.message_id
    sent = await bot.send_message(
        dialog.user_id,
        text,
        reply_markup=markup,
        link_preview_options=NO_PREVIEW,
        disable_notification=True,
    )
    dialog.message_id = sent.message_id
    dialog.updated_at = utcnow()
    if previous and previous != sent.message_id:
        await safe_delete(bot, dialog.user_id, previous)


async def push_notice(
    bot, db: AsyncSession, user_id: int, text: str, markup=None, *, silent: bool = False
) -> None:
    """A notification the person keeps. Later screens do not delete it.

    Sound only when that person has something to do. Status chatter stays quiet.
    """
    user = await db.get(User, user_id)
    if user is None or not user.opened_bot:
        return
    try:
        await bot.send_message(
            user_id,
            text,
            reply_markup=markup,
            link_preview_options=NO_PREVIEW,
            disable_notification=silent,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("notice failed user=%s err=%s", user_id, safe_error(exc))
