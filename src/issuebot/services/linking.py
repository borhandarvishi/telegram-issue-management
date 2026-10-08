"""Link a project to the channel the owner just promoted the bot in."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from issuebot import runtime, texts
from issuebot.messaging import NO_PREVIEW, safe_error
from issuebot.services.members import ensure_member
from issuebot.services.projects import attach_channel, start_link

logger = logging.getLogger("issuebot")


def member_status(member) -> str:
    status = getattr(member, "status", "")
    return str(getattr(status, "value", status))


def is_joined(member) -> bool:
    status = member_status(member)
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return status in {"creator", "administrator", "member"}


def parse_channel_ref(text: str) -> str | None:
    """Return @username, the marker 'private' for an invite link, or None."""
    raw = text.strip()
    lowered = raw.lower()
    for prefix in ("https://", "http://"):
        if lowered.startswith(prefix):
            raw = raw[len(prefix) :]
            lowered = lowered[len(prefix) :]
            break
    if lowered.startswith("t.me/") or lowered.startswith("telegram.me/"):
        path = raw.split("/", 1)[1].strip("/")
        slug = path.split("/")[0].split("?")[0]
        if slug.startswith("+") or slug.lower() == "joinchat":
            return "private"
        return _username(slug)
    if raw.startswith("@"):
        return _username(raw[1:].split()[0])
    return None


def _username(slug: str) -> str | None:
    if slug.startswith("@"):
        slug = slug[1:]
    if len(slug) < 4 or not slug.replace("_", "").isalnum():
        return None
    return f"@{slug}"


def missing_admin_perms(member) -> list[str]:
    if member_status(member) != "administrator":
        return ["Be an admin"]
    missing = []
    checks = (
        ("can_invite_users", "Invite users"),
        ("can_post_messages", "Post messages"),
        ("can_delete_messages", "Delete messages"),
    )
    for attr, label in checks:
        if not getattr(member, attr, False):
            missing.append(label)
    return missing


async def user_in_channel(bot, channel_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    return is_joined(member)


async def sync_admins(bot, db, project) -> None:
    try:
        admins = await bot.get_chat_administrators(project.channel_id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("admin sync failed project=%s err=%s", project.id, safe_error(exc))
        return
    for admin in admins:
        if admin.user.is_bot:
            continue
        await ensure_member(db, project.id, admin.user, active=True)


async def complete_link(bot, db, project, channel_id: int, channel_title: str | None) -> str:
    invite = await bot.create_chat_invite_link(chat_id=channel_id, name=project.name[:32])
    attach_channel(
        project,
        channel_id=channel_id,
        channel_title=channel_title,
        invite_link=invite.invite_link,
    )
    await sync_admins(bot, db, project)
    if project.pinned_message_id or not runtime.bot_username:
        return invite.invite_link
    try:
        pinned = await bot.send_message(
            channel_id,
            texts.channel_pin(project.name, start_link(runtime.bot_username, project.public_id)),
            disable_notification=True,
            link_preview_options=NO_PREVIEW,
        )
        project.pinned_message_id = pinned.message_id
        await bot.pin_chat_message(channel_id, pinned.message_id, disable_notification=True)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("pin failed project=%s err=%s", project.id, safe_error(exc))
    return invite.invite_link
