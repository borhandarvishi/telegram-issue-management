"""Home, projects, invite, members, and the report wizard up to photos."""

from __future__ import annotations

from issuebot import runtime, texts
from issuebot.constants import Btn, Screen
from issuebot.formatting import format_person, h, project_button, unique_labels
from issuebot.handlers.screen_parts import linked_project
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import goto, present
from issuebot.keyboards import back_row, channel_button, home_rows, project_rows
from issuebot.services.accounts import projects_for, update_payload
from issuebot.services.issues import counts, inbox_count
from issuebot.services.members import roster
from issuebot.services.projects import get_project, start_link


async def render_home(ctx: Ctx) -> None:
    found = await projects_for(ctx.db, ctx.account.id)
    name = ctx.account.first_name or "there"
    await present(
        ctx,
        texts.home(name, len(found)),
        home_rows(has_projects=bool(found)),
        "Choose an action",
    )


async def render_help(ctx: Ctx) -> None:
    await present(ctx, texts.HELP, [back_row()], "Back")


async def render_new_project(ctx: Ctx) -> None:
    await present(ctx, texts.ask_project_name(), [back_row()], "Project name")


async def render_await(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.HOME)
        return
    if project.channel_id:
        await goto(ctx, Screen.INVITE)
        return
    missing = ctx.payload.get("missing") or None
    rows: list = [[channel_button()]]
    if ctx.payload.get("pending_channel_id"):
        rows.append([Btn.RECHECK])
    if project.owner_id == ctx.account.id:
        rows.append([Btn.DELETE])
    rows.append(back_row())
    await present(
        ctx,
        texts.await_channel(project.name, runtime.bot_username, missing),
        rows,
        "Waiting for the channel",
    )


async def render_project_list(ctx: Ctx) -> None:
    found = await projects_for(ctx.db, ctx.account.id)
    pairs = [(project_button(item.name, pending=not item.channel_id), item.id) for item in found]
    labels = unique_labels(pairs)
    update_payload(ctx.dialog, labels={key: int(value) for key, value in labels.items()})
    rows = [[label] for label in labels]
    rows.append([Btn.NEW])
    if found:
        rows.append(back_row())
    await present(ctx, texts.project_list(len(found)), rows, "Choose a project")


async def render_project(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    if not project.channel_id:
        ctx.dialog.state = Screen.AWAIT_CHANNEL.value
        await render_await(ctx)
        return
    summary = await counts(ctx.db, project.id)
    mine = await inbox_count(ctx.db, ctx.account.id)
    rows = project_rows()
    if project.owner_id == ctx.account.id:
        rows.append([Btn.DELETE])
    await present(
        ctx,
        texts.project_home(
            project.name,
            open_count=summary["open"],
            waiting_count=summary["waiting"],
            inbox_count=mine,
            bot_admin=project.bot_admin,
        ),
        rows,
        "Choose an action",
    )


async def render_invite(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    start = start_link(runtime.bot_username, project.public_id) if runtime.bot_username else ""
    rows = []
    if project.owner_id == ctx.account.id:
        rows.append([Btn.ROTATE])
    rows.append(back_row())
    await present(
        ctx,
        texts.invite_screen(
            project.name,
            project.invite_link,
            project.channel_title,
            start,
            project.owner_id == ctx.account.id,
        ),
        rows,
        "Copy the link",
    )


async def render_delete_confirm(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    if project.owner_id != ctx.account.id:
        update_payload(ctx.dialog, flash=texts.NOT_ALLOWED)
        await goto(ctx, Screen.PROJECT)
        return
    await present(
        ctx,
        texts.delete_confirm(project.name),
        [[Btn.DELETE_YES], back_row()],
        "Confirm delete",
    )


async def render_invite_confirm(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    await present(
        ctx,
        texts.rotate_confirm(project.name),
        [[Btn.ROTATE_YES], back_row()],
        "Confirm the new link",
    )


async def render_members(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    owner = project.owner_id == ctx.account.id
    lines = []
    pairs = []
    for row in await roster(ctx.db, project.id):
        person = format_person(row.user.username, row.user.first_name, row.user.last_name)
        lines.append(
            h(
                texts.member_line(
                    person,
                    is_owner=row.user_id == project.owner_id,
                    opened_bot=row.user.opened_bot,
                )
            )
        )
        if owner and row.user_id != project.owner_id:
            pairs.append((person, row.user_id))
    labels = unique_labels(pairs)
    update_payload(ctx.dialog, labels={key: int(value) for key, value in labels.items()})
    rows = [[label] for label in labels]
    rows.append(back_row())
    await present(
        ctx,
        texts.members_screen(project.name, lines, can_remove=bool(pairs)),
        rows,
        "Members",
    )


async def render_remove_member(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    if project.owner_id != ctx.account.id:
        update_payload(ctx.dialog, flash=texts.NOT_ALLOWED)
        await goto(ctx, Screen.MEMBERS)
        return
    user_id = ctx.payload.get("remove_user_id")
    row = None
    for item in await roster(ctx.db, project.id):
        if item.user_id == user_id:
            row = item
            break
    if row is None:
        await goto(ctx, Screen.MEMBERS)
        return
    person = format_person(row.user.username, row.user.first_name, row.user.last_name)
    await present(
        ctx,
        texts.remove_member_confirm(project.name, person),
        [[Btn.REMOVE_YES], back_row()],
        "Confirm remove",
    )


async def render_join(ctx: Ctx) -> None:
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.HOME)
        return
    await present(
        ctx,
        texts.join_screen(project.name, project.invite_link),
        [[Btn.JOINED], back_row()],
        "Tap after you join",
    )


async def render_report_title(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    await present(ctx, texts.report_title(project.name), [back_row()], "Issue title")


async def render_report_body(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    await present(
        ctx,
        texts.report_body(project.name, str(ctx.payload.get("title") or "")),
        [back_row()],
        "Describe the issue",
    )


async def render_report_media(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    photos = list(ctx.payload.get("photos") or [])
    await present(
        ctx,
        texts.report_media(project.name, len(photos)),
        [[Btn.PHOTOS_DONE], back_row()],
        "Send photos or continue",
    )
