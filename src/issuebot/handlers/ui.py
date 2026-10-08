"""Navigation between screens. One place decides where Back goes."""

from __future__ import annotations

from issuebot.constants import Screen
from issuebot.db.models import utcnow
from issuebot.handlers.types import Ctx
from issuebot.keyboards import keyboard
from issuebot.messaging import show_screen
from issuebot.services.accounts import projects_for, update_payload
from issuebot.services.projects import get_project

_REPORT = {
    Screen.REPORT_TITLE.value,
    Screen.REPORT_BODY.value,
    Screen.REPORT_MEDIA.value,
    Screen.REPORT_ASSIGN.value,
}
_ISSUE_STEPS = {
    Screen.RESOLVE_CONFIRM.value,
    Screen.CONFIRM_CONFIRM.value,
    Screen.REOPEN_CONFIRM.value,
    Screen.NOTE.value,
    Screen.REASSIGN.value,
}


async def present(ctx: Ctx, text: str, rows: list, placeholder: str) -> None:
    flash = ctx.payload.get("flash")
    if flash:
        text = f"{flash}\n\n{text}"
        update_payload(ctx.dialog, flash=None)
    await show_screen(ctx.bot, ctx.db, ctx.dialog, text, keyboard(rows, placeholder))


async def goto(ctx: Ctx, state: Screen, **payload: object) -> None:
    ctx.dialog.state = state.value
    ctx.dialog.updated_at = utcnow()
    if payload:
        update_payload(ctx.dialog, **payload)
    await render(ctx)


async def remember(ctx: Ctx, message: str) -> None:
    update_payload(ctx.dialog, flash=message)
    await render(ctx)


async def render(ctx: Ctx) -> None:
    from issuebot.handlers import screens

    try:
        state = Screen(ctx.dialog.state)
    except ValueError:
        state = Screen.HOME
        ctx.dialog.state = state.value
    await screens.RENDER[state](ctx)


async def land(ctx: Ctx) -> None:
    found = await projects_for(ctx.db, ctx.account.id)
    current = await get_project(ctx.db, ctx.dialog.project_id)
    if current and current.channel_id and any(item.id == current.id for item in found):
        await goto(ctx, Screen.PROJECT)
        return
    linked = [item for item in found if item.channel_id]
    if len(found) == 1 and linked:
        ctx.dialog.project_id = linked[0].id
        await goto(ctx, Screen.PROJECT)
        return
    if found:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    await goto(ctx, Screen.HOME)


async def go_back(ctx: Ctx) -> None:
    state = ctx.dialog.state
    if state in _REPORT:
        update_payload(
            ctx.dialog,
            title=None,
            description=None,
            photos=None,
            selected=None,
            labels=None,
        )
        await _back_to_project(ctx)
        return
    if state in _ISSUE_STEPS:
        await goto(ctx, Screen.ISSUE)
        return
    if state == Screen.ISSUE:
        target = Screen.INBOX if ctx.payload.get("list_from") == "inbox" else Screen.ISSUE_LIST
        await goto(ctx, target)
        return
    if state == Screen.ISSUE_LIST:
        await goto(ctx, Screen.FILTERS)
        return
    if state in {Screen.FILTERS, Screen.INVITE, Screen.MEMBERS, Screen.INBOX}:
        await _back_to_project(ctx)
        return
    if state == Screen.INVITE_CONFIRM:
        await goto(ctx, Screen.INVITE)
        return
    if state == Screen.REMOVE_MEMBER:
        await goto(ctx, Screen.MEMBERS)
        return
    if state == Screen.DELETE_CONFIRM:
        await goto(ctx, Screen.PROJECT)
        return
    if state == Screen.PROJECT:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    if state == Screen.AWAIT_CHANNEL:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    if state == Screen.PROJECT_LIST:
        project = await get_project(ctx.db, ctx.dialog.project_id)
        if project and project.channel_id:
            await goto(ctx, Screen.PROJECT)
            return
        await goto(ctx, Screen.HOME)
        return
    if state == Screen.HELP:
        await land(ctx)
        return
    await goto(ctx, Screen.HOME)


async def _back_to_project(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project and project.channel_id:
        await goto(ctx, Screen.PROJECT)
        return
    if project:
        await goto(ctx, Screen.AWAIT_CHANNEL)
        return
    await goto(ctx, Screen.HOME)
