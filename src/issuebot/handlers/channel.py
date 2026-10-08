"""Channel membership: linking a project, and people joining or leaving."""

from __future__ import annotations

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import ChatMemberUpdated

from issuebot import texts
from issuebot.constants import Screen
from issuebot.db.models import User
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import goto
from issuebot.messaging import push_notice
from issuebot.services.accounts import get_dialog
from issuebot.services.linking import is_joined, member_status, missing_admin_perms
from issuebot.services.members import ensure_member, set_active
from issuebot.services.projects import by_channel

router = Router(name="channel")


@router.my_chat_member()
async def on_bot_membership(event: ChatMemberUpdated, bot, db) -> None:
    if event.chat.type != ChatType.CHANNEL:
        await _tell(bot, db, event.from_user.id, texts.NOT_CHANNEL)
        return
    new_status = member_status(event.new_chat_member)
    if new_status in {"left", "kicked"}:
        await _bot_removed(event, bot, db)
        return
    if new_status != "administrator":
        return
    missing = missing_admin_perms(event.new_chat_member)
    if missing:
        await _missing_rights(event, bot, db, missing)
        return
    existing = await by_channel(db, event.chat.id)
    if existing is not None:
        if not existing.bot_admin:
            existing.bot_admin = True
            await _tell(bot, db, existing.owner_id, f"<b>{existing.name}</b>\n{texts.RESTORED}")
        return
    await _tell(bot, db, event.from_user.id, texts.bot_added(event.chat.title or "the channel"))


@router.chat_member()
async def on_channel_member(event: ChatMemberUpdated, bot, db) -> None:
    if event.chat.type != ChatType.CHANNEL:
        return
    project = await by_channel(db, event.chat.id)
    if project is None or event.new_chat_member.user.is_bot:
        return
    joined_now = is_joined(event.new_chat_member) and not is_joined(event.old_chat_member)
    left_now = is_joined(event.old_chat_member) and not is_joined(event.new_chat_member)
    if joined_now:
        await ensure_member(db, project.id, event.new_chat_member.user, active=True)
        await _welcome(event, bot, db, project)
    elif left_now:
        await set_active(db, project.id, event.new_chat_member.user.id, False)


async def _bot_removed(event: ChatMemberUpdated, bot, db) -> None:
    project = await by_channel(db, event.chat.id)
    if project is None:
        return
    project.bot_admin = False
    await _tell(bot, db, project.owner_id, f"<b>{project.name}</b>\n{texts.REMOVED}")


async def _missing_rights(event: ChatMemberUpdated, bot, db, missing: list[str]) -> None:
    title = event.chat.title or "the channel"
    existing = await by_channel(db, event.chat.id)
    if existing is not None:
        existing.bot_admin = False
        await _tell(bot, db, existing.owner_id, texts.bot_needs_rights(title, missing))
        return
    await _tell(bot, db, event.from_user.id, texts.bot_needs_rights(title, missing))


async def _welcome(event: ChatMemberUpdated, bot, db, project) -> None:
    account = await db.get(User, event.new_chat_member.user.id)
    if account is None or not account.opened_bot:
        return
    dialog = await get_dialog(db, account.id)
    if dialog is None:
        await push_notice(bot, db, account.id, texts.notify_joined(project.name))
        return
    waiting = dialog.state == Screen.JOIN and dialog.project_id == project.id
    idle = dialog.state == Screen.HOME
    if waiting or idle:
        dialog.project_id = project.id
        ctx = await _ctx(bot, db, account, dialog)
        if ctx is not None:
            await goto(ctx, Screen.PROJECT)
        return
    await push_notice(bot, db, account.id, texts.notify_joined(project.name))


async def _ctx(bot, db, account: User, dialog) -> Ctx | None:
    if dialog is None:
        return None
    return Ctx(bot=bot, db=db, chat_id=account.id, account=account, dialog=dialog)


async def _tell(bot, db, user_id: int, text: str) -> None:
    await push_notice(bot, db, user_id, text)
