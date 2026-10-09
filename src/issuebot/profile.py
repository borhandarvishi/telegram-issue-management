"""Default Telegram profile photo.

The picture at ``assets/default_bot_profile.jpg`` is the source. Every start
sets the bot profile from that file when it exists. Replace the file to change
the photo.
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, InputProfilePhotoStatic

logger = logging.getLogger("issuebot")

PHOTO_NAME = "default_bot_profile.jpg"


def profile_photo_path() -> Path | None:
    """Find the picture next to the process, then next to the source tree."""
    candidates = (
        Path.cwd() / "assets" / PHOTO_NAME,
        Path(__file__).resolve().parents[2] / "assets" / PHOTO_NAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


async def apply_default_profile(bot: Bot) -> None:
    photo = profile_photo_path()
    if photo is None:
        logger.info("no default profile photo; add assets/%s to set one", PHOTO_NAME)
        return
    try:
        await bot.set_my_profile_photo(
            InputProfilePhotoStatic(photo=FSInputFile(photo, filename=PHOTO_NAME))
        )
    except TelegramAPIError:
        logger.warning("could not set the default profile photo", exc_info=True)
        return
    logger.info("set profile photo from %s", photo)
