"""Process entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BotCommand, ErrorEvent

from issuebot import runtime, texts
from issuebot.config import Settings, load_settings
from issuebot.db.session import Database
from issuebot.handlers.channel import router as channel_router
from issuebot.handlers.private import router as private_router
from issuebot.messaging import safe_error
from issuebot.middlewares import ContextMiddleware

logger = logging.getLogger("issuebot")


async def run(settings: Settings) -> None:
    database = Database(settings.database_url)
    await database.create_tables()
    bot = Bot(
        settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    runtime.bot_username = me.username or ""
    runtime.bot_id = me.id
    dispatcher = Dispatcher()
    dispatcher.update.middleware(ContextMiddleware(database))
    dispatcher.include_router(private_router)
    dispatcher.include_router(channel_router)
    dispatcher.errors.register(on_error)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start"),
            BotCommand(command="help", description="Help"),
            BotCommand(command="cancel", description="Back"),
        ]
    )
    allowed = dispatcher.resolve_used_update_types()
    logger.info("started as @%s updates=%s", runtime.bot_username, ",".join(allowed))
    await dispatcher.start_polling(bot, allowed_updates=allowed)


async def on_error(event: ErrorEvent, bot: Bot) -> None:
    logger.exception("update failed: %s", safe_error(event.exception))
    message = event.update.message if event.update else None
    if message is None or message.chat.type != ChatType.PRIVATE:
        return
    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await bot.send_message(message.chat.id, texts.GENERIC_ERROR)


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run(settings))
