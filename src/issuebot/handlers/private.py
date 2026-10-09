"""Private chat: commands, buttons, and typed text."""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from issuebot import texts
from issuebot.constants import Screen
from issuebot.handlers.actions import handle_callback, link_shared_channel, open_deep_link
from issuebot.handlers.flow import handle_photo, handle_text
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import go_back, goto, remember

router = Router(name="private")
router.message.filter(F.chat.type == ChatType.PRIVATE)


def _ctx(message: Message, bot, db, account, dialog) -> Ctx:
    file_id = message.photo[-1].file_id if message.photo else None
    return Ctx(
        bot=bot,
        db=db,
        chat_id=message.chat.id,
        account=account,
        dialog=dialog,
        text=(message.text or "").strip(),
        file_id=file_id,
    )


@router.message(CommandStart())
async def on_start(message: Message, command: CommandObject, bot, db, account, dialog) -> None:
    ctx = _ctx(message, bot, db, account, dialog)
    args = (command.args or "").strip()
    if args.startswith("p") and len(args) > 1:
        await open_deep_link(ctx, args[1:])
        return
    await goto(ctx, Screen.HOME)


@router.message(Command("help"))
async def on_help(message: Message, bot, db, account, dialog) -> None:
    await goto(_ctx(message, bot, db, account, dialog), Screen.HELP)


@router.message(Command("cancel"))
async def on_cancel(message: Message, bot, db, account, dialog) -> None:
    await go_back(_ctx(message, bot, db, account, dialog))


@router.message(F.photo)
async def on_photo(message: Message, bot, db, account, dialog) -> None:
    await handle_photo(_ctx(message, bot, db, account, dialog))


@router.message(F.document)
async def on_document(message: Message, bot, db, account, dialog) -> None:
    await remember(_ctx(message, bot, db, account, dialog), texts.PHOTO_AS_IMAGE)


@router.message(F.chat_shared)
async def on_chat_shared(message: Message, bot, db, account, dialog) -> None:
    shared = message.chat_shared
    if shared is None:
        return
    await link_shared_channel(_ctx(message, bot, db, account, dialog), shared)


@router.message(F.text)
async def on_text(message: Message, bot, db, account, dialog) -> None:
    await handle_text(_ctx(message, bot, db, account, dialog))


@router.callback_query()
async def on_callback(query: CallbackQuery, bot, db, account, dialog) -> None:
    message = query.message
    if message is None or message.chat.type != ChatType.PRIVATE:
        await query.answer()
        return
    await query.answer()
    ctx = Ctx(
        bot=bot,
        db=db,
        chat_id=message.chat.id,
        account=account,
        dialog=dialog,
    )
    await handle_callback(ctx, query.data or "")


@router.message()
async def on_other(message: Message, bot, db, account, dialog) -> None:
    await remember(_ctx(message, bot, db, account, dialog), texts.USE_BUTTONS)
