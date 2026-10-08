"""Publish an issue card into the project channel.

A new card is sent first. The previous card is deleted only after that succeeds,
so a failed update never leaves the channel without the issue.
"""

from __future__ import annotations

import logging

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InputMediaPhoto

from issuebot.formatting import channel_delivery
from issuebot.messaging import NO_PREVIEW, safe_delete, safe_error

logger = logging.getLogger("issuebot")


class PublishFailed(Exception):
    pass


async def republish(
    bot,
    chat_id: int,
    *,
    old_ids: list[int],
    text: str,
    photo_ids: list[str],
    silent: bool,
) -> list[int]:
    new_ids: list[int] = []
    try:
        plan = channel_delivery(text, len(photo_ids))
        if plan == "text":
            message = await bot.send_message(
                chat_id,
                text,
                disable_notification=silent,
                link_preview_options=NO_PREVIEW,
            )
            new_ids.append(message.message_id)
        elif plan == "photo":
            message = await bot.send_photo(
                chat_id,
                photo_ids[0],
                caption=text,
                disable_notification=silent,
            )
            new_ids.append(message.message_id)
        else:
            new_ids.extend(await _send_album(bot, chat_id, text, photo_ids, silent=silent))
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("publish failed chat=%s err=%s", chat_id, safe_error(exc))
        for message_id in new_ids:
            await safe_delete(bot, chat_id, message_id)
        raise PublishFailed from exc
    for message_id in old_ids:
        if message_id not in new_ids:
            await safe_delete(bot, chat_id, message_id)
    return new_ids


async def _send_album(
    bot,
    chat_id: int,
    text: str,
    photo_ids: list[str],
    *,
    silent: bool,
) -> list[int]:
    media = [
        InputMediaPhoto(media=photo_ids[0], caption=text, parse_mode=ParseMode.HTML),
        *[InputMediaPhoto(media=file_id) for file_id in photo_ids[1:10]],
    ]
    messages = await bot.send_media_group(chat_id, media=media, disable_notification=silent)
    return [message.message_id for message in messages]
