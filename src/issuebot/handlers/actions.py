"""What happens when a button is pressed or a text is sent."""

from __future__ import annotations

import logging
from contextlib import suppress

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatShared

from issuebot import runtime, texts
from issuebot.constants import (
    CAPTION_LIMIT,
    CHANNEL_REQUEST_ID,
    MAX_DESCRIPTION,
    MAX_NOTE,
    MAX_PHOTOS,
    MAX_PROJECT_NAME,
    MAX_TITLE,
    MESSAGE_LIMIT,
    IssueFilter,
    Screen,
)
from issuebot.formatting import channel_card, format_person
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import goto, remember, render
from issuebot.messaging import push_notice, safe_error
from issuebot.services.accounts import update_payload
from issuebot.services.issues import (
    BadTransition,
    NotAllowed,
    add_note,
    confirm,
    create_issue,
    get_issue,
    mark_resolved,
    photo_ids,
    reopen,
    set_assignees,
    to_card,
)
from issuebot.services.linking import (
    complete_link,
    missing_admin_perms,
    parse_channel_ref,
    user_in_channel,
)
from issuebot.services.members import activate_user, member_ids
from issuebot.services.projects import by_channel, by_public_id, create_project, get_project
from issuebot.services.publish import PublishFailed, republish

logger = logging.getLogger("issuebot")


async def create_named_project(ctx: Ctx) -> None:
    name = " ".join(ctx.text.split())
    if len(name) < 2:
        await remember(ctx, texts.NAME_TOO_SHORT)
        return
    if len(name) > MAX_PROJECT_NAME:
        await remember(ctx, texts.NAME_TOO_LONG)
        return
    project = await create_project(ctx.db, ctx.account, name)
    ctx.dialog.project_id = project.id
    update_payload(ctx.dialog, missing=None, pending_channel_id=None, pending_channel_title=None)
    await goto(ctx, Screen.AWAIT_CHANNEL)


async def link_shared_channel(ctx: Ctx, shared: ChatShared) -> None:
    if shared.request_id != CHANNEL_REQUEST_ID:
        await remember(ctx, texts.USE_BUTTONS)
        return
    await attach_chosen_channel(ctx, shared.chat_id, shared.title)


async def link_from_text(ctx: Ctx) -> None:
    ref = parse_channel_ref(ctx.text)
    if ref is None:
        await remember(ctx, texts.USE_BUTTONS)
        return
    if ref == "private":
        await remember(ctx, texts.PRIVATE_LINK)
        return
    try:
        chat = await ctx.bot.get_chat(ref)
    except (TelegramBadRequest, TelegramForbiddenError):
        await remember(ctx, texts.CHANNEL_NOT_FOUND)
        return
    if chat.type != ChatType.CHANNEL:
        await remember(ctx, texts.NOT_CHANNEL)
        return
    await attach_chosen_channel(ctx, chat.id, chat.title)


async def attach_chosen_channel(ctx: Ctx, channel_id: int, title: str | None) -> None:
    if ctx.dialog.state != Screen.AWAIT_CHANNEL:
        await remember(ctx, texts.PICK_ON_PROJECT)
        return
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.HOME)
        return
    if project.owner_id != ctx.account.id:
        await remember(ctx, texts.NOT_ALLOWED)
        return
    if project.channel_id:
        await goto(ctx, Screen.INVITE)
        return
    existing = await by_channel(ctx.db, channel_id)
    if existing is not None and existing.id != project.id:
        await remember(ctx, texts.ALREADY_LINKED)
        return
    try:
        member = await ctx.bot.get_chat_member(channel_id, runtime.bot_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        await remember(ctx, texts.CHANNEL_NOT_FOUND)
        return
    missing = missing_admin_perms(member)
    if missing:
        update_payload(
            ctx.dialog,
            pending_channel_id=channel_id,
            pending_channel_title=title,
            missing=missing,
        )
        await remember(ctx, texts.PERMS_STILL_MISSING)
        return
    await _finish_link(ctx, project, channel_id, title)


async def recheck_channel(ctx: Ctx) -> None:
    channel_id = ctx.payload.get("pending_channel_id")
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if not channel_id or project is None:
        await remember(ctx, "Make the bot an admin of the channel first.")
        return
    try:
        member = await ctx.bot.get_chat_member(int(channel_id), runtime.bot_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        await remember(ctx, texts.PERMS_STILL_MISSING)
        return
    missing = missing_admin_perms(member)
    if missing:
        update_payload(ctx.dialog, missing=missing)
        await remember(ctx, texts.PERMS_STILL_MISSING)
        return
    await _finish_link(
        ctx,
        project,
        int(channel_id),
        ctx.payload.get("pending_channel_title"),
    )


async def rotate_link(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None or not project.channel_id:
        await remember(ctx, texts.NO_CHANNEL)
        return
    if project.owner_id != ctx.account.id:
        await remember(ctx, texts.NOT_ALLOWED)
        return
    if project.invite_link:
        with suppress(TelegramBadRequest, TelegramForbiddenError):
            await ctx.bot.revoke_chat_invite_link(project.channel_id, project.invite_link)
    try:
        created = await ctx.bot.create_chat_invite_link(
            chat_id=project.channel_id,
            name=project.name[:32],
        )
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("rotate failed project=%s err=%s", project.id, safe_error(exc))
        await remember(ctx, texts.PUBLISH_FAILED)
        return
    project.invite_link = created.invite_link
    update_payload(ctx.dialog, flash="The new link is ready. The previous one no longer works.")
    await goto(ctx, Screen.INVITE)


async def open_labeled_project(ctx: Ctx, project_id: int) -> None:
    ctx.dialog.project_id = project_id
    await goto(ctx, Screen.PROJECT)


async def open_labeled_issue(ctx: Ctx, issue_id: int) -> None:
    issue = await get_issue(ctx.db, issue_id)
    if issue is None:
        await remember(ctx, texts.STALE)
        return
    ctx.dialog.project_id = issue.project_id
    ctx.dialog.issue_id = issue.id
    await goto(ctx, Screen.ISSUE)


async def toggle_person(ctx: Ctx, user_id: int) -> None:
    selected = {int(item) for item in ctx.payload.get("selected") or []}
    if user_id in selected:
        selected.remove(user_id)
    else:
        selected.add(user_id)
    update_payload(ctx.dialog, selected=sorted(selected))
    await render(ctx)


async def start_report(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None or not project.channel_id:
        await remember(ctx, texts.NO_CHANNEL)
        return
    if not project.bot_admin:
        await remember(ctx, "The bot has no access to the channel. Make it an admin again.")
        return
    update_payload(
        ctx.dialog,
        title=None,
        description=None,
        photos=[],
        selected=[],
        labels=None,
    )
    await goto(ctx, Screen.REPORT_TITLE)


async def save_title(ctx: Ctx) -> None:
    title = " ".join(ctx.text.split())
    if len(title) < 3:
        await remember(ctx, texts.TITLE_TOO_SHORT)
        return
    if len(title) > MAX_TITLE:
        await remember(ctx, texts.TITLE_TOO_LONG)
        return
    update_payload(ctx.dialog, title=title)
    await goto(ctx, Screen.REPORT_BODY)


async def save_body(ctx: Ctx) -> None:
    body = ctx.text.strip()
    if not body:
        await remember(ctx, texts.BODY_TOO_SHORT)
        return
    update_payload(ctx.dialog, description=body[:MAX_DESCRIPTION])
    await goto(ctx, Screen.REPORT_MEDIA)


async def add_photo(ctx: Ctx) -> None:
    if ctx.dialog.state != Screen.REPORT_MEDIA:
        await remember(ctx, texts.USE_BUTTONS)
        return
    if not ctx.file_id:
        await remember(ctx, texts.PHOTO_AS_IMAGE)
        return
    photos = list(ctx.payload.get("photos") or [])
    if ctx.file_id not in photos:
        photos.append(ctx.file_id)
    if len(photos) > MAX_PHOTOS:
        photos = photos[:MAX_PHOTOS]
        update_payload(ctx.dialog, photos=photos, flash=f"Up to {MAX_PHOTOS} photos.")
    else:
        update_payload(ctx.dialog, photos=photos)
    await render(ctx)


async def submit_report(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    title = str(ctx.payload.get("title") or "").strip()
    description = str(ctx.payload.get("description") or "").strip()
    if project is None or not title or not description:
        await remember(ctx, texts.STALE)
        return
    allowed = await member_ids(ctx.db, project.id)
    chosen = [int(item) for item in ctx.payload.get("selected") or [] if int(item) in allowed]
    photos = list(ctx.payload.get("photos") or [])[:MAX_PHOTOS]
    issue = await create_issue(
        ctx.db,
        project=project,
        reporter=ctx.account,
        title=title,
        description=description,
        photos=photos,
        assignee_ids=chosen,
    )
    fresh = await get_issue(ctx.db, issue.id)
    published = False
    if fresh is not None:
        published = await sync_channel(ctx, fresh, silent=False)
        await _notify_assigned(ctx, fresh, chosen)
    ctx.dialog.issue_id = issue.id
    update_payload(
        ctx.dialog,
        title=None,
        description=None,
        photos=None,
        selected=None,
        labels=None,
        list_from="issues",
        flash=texts.registered(issue.number, published),
    )
    await goto(ctx, Screen.ISSUE)


async def open_filter(ctx: Ctx, filt: IssueFilter) -> None:
    update_payload(ctx.dialog, filter=filt.value, page=0)
    await goto(ctx, Screen.ISSUE_LIST)


async def change_page(ctx: Ctx, delta: int) -> None:
    page = int(ctx.payload.get("page") or 0) + delta
    update_payload(ctx.dialog, page=max(page, 0))
    await render(ctx)


async def save_note(ctx: Ctx) -> None:
    body = ctx.text.strip()
    if not body:
        await remember(ctx, texts.NOTE_TOO_SHORT)
        return
    await _transition(
        ctx,
        lambda: add_note(ctx.db, ctx.dialog.issue_id, ctx.account, body[:MAX_NOTE]),
        silent=True,
    )


async def do_resolve(ctx: Ctx) -> None:
    await _transition(
        ctx,
        lambda: mark_resolved(ctx.db, ctx.dialog.issue_id, ctx.account),
        silent=False,
    )


async def do_confirm(ctx: Ctx) -> None:
    await _transition(ctx, lambda: confirm(ctx.db, ctx.dialog.issue_id, ctx.account), silent=False)


async def do_reopen(ctx: Ctx) -> None:
    await _transition(ctx, lambda: reopen(ctx.db, ctx.dialog.issue_id, ctx.account), silent=False)


async def begin_reassign(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    if issue is None:
        await remember(ctx, texts.STALE)
        return
    update_payload(ctx.dialog, selected=[item.user_id for item in issue.assignments])
    await goto(ctx, Screen.REASSIGN)


async def save_assignees(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    if issue is None:
        await remember(ctx, texts.STALE)
        return
    allowed = await member_ids(ctx.db, issue.project_id)
    chosen = [int(item) for item in ctx.payload.get("selected") or [] if int(item) in allowed]
    try:
        outcome = await set_assignees(ctx.db, issue.id, ctx.account, chosen)
    except NotAllowed:
        await remember(ctx, texts.NOT_ALLOWED)
        return
    except BadTransition:
        await remember(ctx, texts.STALE)
        return
    fresh = await get_issue(ctx.db, outcome.issue_id)
    if fresh is not None:
        await sync_channel(ctx, fresh, silent=True)
        await _notify_assigned(ctx, fresh, outcome.notify_ids)
    update_payload(ctx.dialog, selected=None, labels=None, flash="Assignees saved.")
    await goto(ctx, Screen.ISSUE)


async def retry_publish(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    if issue is None:
        await remember(ctx, texts.STALE)
        return
    published = await sync_channel(ctx, issue, silent=False)
    await remember(ctx, "Posted to the channel." if published else texts.PUBLISH_FAILED)


async def open_deep_link(ctx: Ctx, public_id: str) -> None:
    project = await by_public_id(ctx.db, public_id)
    if project is None:
        update_payload(ctx.dialog, flash=texts.INVALID_LINK)
        await goto(ctx, Screen.HOME)
        return
    ctx.dialog.project_id = project.id
    if not project.channel_id:
        if project.owner_id == ctx.account.id:
            await goto(ctx, Screen.AWAIT_CHANNEL)
        else:
            update_payload(ctx.dialog, flash=texts.NO_CHANNEL)
            await goto(ctx, Screen.HOME)
        return
    joined = await user_in_channel(ctx.bot, project.channel_id, ctx.account.id)
    if not joined:
        await goto(ctx, Screen.JOIN)
        return
    await activate_user(ctx.db, project.id, ctx.account.id, active=True)
    await goto(ctx, Screen.PROJECT)


async def confirm_joined(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None or not project.channel_id:
        await remember(ctx, texts.NO_CHANNEL)
        return
    if not await user_in_channel(ctx.bot, project.channel_id, ctx.account.id):
        await remember(ctx, texts.NOT_A_MEMBER)
        return
    await activate_user(ctx.db, project.id, ctx.account.id, active=True)
    await goto(ctx, Screen.PROJECT)


async def sync_channel(ctx: Ctx, issue, *, silent: bool) -> bool:
    project = issue.project
    if not project.channel_id or not project.bot_admin:
        return False
    try:
        photos = photo_ids(issue)
        new_ids = await republish(
            ctx.bot,
            project.channel_id,
            old_ids=[int(item) for item in (issue.channel_message_ids or [])],
            text=channel_card(to_card(issue), limit=CAPTION_LIMIT if photos else MESSAGE_LIMIT),
            photo_ids=photos,
            silent=silent,
        )
    except PublishFailed:
        return False
    issue.channel_message_ids = list(new_ids)
    await ctx.db.flush()
    return True


async def _finish_link(ctx: Ctx, project, channel_id: int, title: str | None) -> None:
    try:
        await complete_link(ctx.bot, ctx.db, project, channel_id, title)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("link failed project=%s err=%s", project.id, safe_error(exc))
        await remember(ctx, texts.PUBLISH_FAILED)
        return
    update_payload(
        ctx.dialog,
        missing=None,
        pending_channel_id=None,
        pending_channel_title=None,
        flash=texts.LINKED,
    )
    await goto(ctx, Screen.INVITE)


async def _transition(ctx: Ctx, factory, *, silent: bool) -> None:
    try:
        outcome = await factory()
    except NotAllowed:
        await remember(ctx, texts.NOT_ALLOWED)
        return
    except BadTransition:
        await remember(ctx, texts.STALE)
        return
    fresh = await get_issue(ctx.db, outcome.issue_id)
    if fresh is None:
        await remember(ctx, texts.STALE)
        return
    published = await sync_channel(ctx, fresh, silent=silent)
    await _notify_outcome(ctx, fresh, outcome.notify_ids, outcome.kind)
    actor = format_person(ctx.account.username, ctx.account.first_name, ctx.account.last_name)
    extra = "" if published else f"\n{texts.PUBLISH_FAILED}"
    flash = texts.status_changed(fresh.number, _kind_text(outcome.kind, actor)) + extra
    update_payload(ctx.dialog, flash=flash)
    await goto(ctx, Screen.ISSUE)


def _kind_text(kind: str, actor: str) -> str:
    if kind == "resolved":
        return f"Resolved by {actor}"
    if kind == "confirmed":
        return f"Confirmed by {actor}"
    if kind == "reopened":
        return f"Reopened by {actor}"
    if kind == "note":
        return "Note saved"
    return "Updated"


async def _notify_outcome(ctx: Ctx, issue, user_ids: list[int], kind: str) -> None:
    if kind == "assigned":
        await _notify_assigned(ctx, issue, user_ids)
        return
    card = to_card(issue)
    actor = format_person(ctx.account.username, ctx.account.first_name, ctx.account.last_name)
    for user_id in user_ids:
        if kind == "resolved":
            text = texts.notify_resolved(card.number, card.project, card.title, actor)
        elif kind == "confirmed":
            text = texts.notify_confirmed(card.number, card.project, card.title, actor)
        elif kind == "reopened":
            text = texts.notify_reopened(card.number, card.project, card.title, actor)
        elif kind == "note" and issue.notes:
            note = issue.notes[-1]
            author = format_person(
                note.author.username, note.author.first_name, note.author.last_name
            )
            excerpt = note.body if len(note.body) <= 140 else note.body[:139] + "…"
            text = texts.notify_note(card.number, card.project, card.title, author, excerpt)
        else:
            continue
        await push_notice(ctx.bot, ctx.db, user_id, text)


async def _notify_assigned(ctx: Ctx, issue, user_ids: list[int]) -> None:
    card = to_card(issue)
    text = texts.notify_assigned(card.number, card.project, card.title, card.reporter)
    for user_id in user_ids:
        if user_id == ctx.account.id:
            continue
        await push_notice(ctx.bot, ctx.db, user_id, text)
