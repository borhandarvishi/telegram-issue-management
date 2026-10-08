"""Issue lists, the open issue, and choosing a person."""

from __future__ import annotations

from issuebot import texts
from issuebot.constants import Btn, IssueFilter, Screen, Status
from issuebot.formatting import detail_card, h, issue_token, status_emoji
from issuebot.handlers.screen_parts import (
    confirm_screen,
    issue_buttons,
    linked_project,
    page_slice,
    people_picker,
)
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import goto, present
from issuebot.keyboards import back_row, filter_rows
from issuebot.services.accounts import update_payload
from issuebot.services.issues import counts, get_issue, inbox, list_issues, to_card
from issuebot.services.members import get_membership
from issuebot.services.projects import get_project
from issuebot.services.rules import capabilities

_FILTER_TITLES = {
    IssueFilter.OPEN: "Open",
    IssueFilter.WAITING: "Awaiting confirmation",
    IssueFilter.DONE: "Confirmed",
    IssueFilter.REPORTED: "Reported by me",
    IssueFilter.ASSIGNED: "Assigned to me",
}


async def render_report_assign(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    selected = {int(item) for item in ctx.payload.get("selected") or []}
    body, rows, labels = await people_picker(ctx, project.id, selected)
    update_payload(ctx.dialog, labels=labels)
    await present(
        ctx,
        texts.report_assign(
            project.name,
            title=str(ctx.payload.get("title") or ""),
            description=str(ctx.payload.get("description") or ""),
            photo_count=len(ctx.payload.get("photos") or []),
            selected=body["selected"],
            pending_names=body["pending"],
        ),
        rows + [[Btn.SAVE_ISSUE], back_row()],
        "Choose an assignee",
    )


async def render_inbox(ctx: Ctx) -> None:
    found = await inbox(ctx.db, ctx.account.id)
    page = int(ctx.payload.get("page") or 0)
    chunk, pages, page = page_slice(found, page)
    update_payload(ctx.dialog, page=page, list_from="inbox")
    await issue_buttons(
        ctx,
        texts.inbox_screen(len(found)),
        chunk,
        page=page,
        pages=pages,
        with_project=True,
        placeholder="Choose an issue",
    )


async def render_filters(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    await present(
        ctx,
        texts.filters_screen(project.name, await counts(ctx.db, project.id)),
        filter_rows(),
        "Choose a list",
    )


async def render_issue_list(ctx: Ctx) -> None:
    project = await linked_project(ctx)
    if project is None:
        return
    filt = str(ctx.payload.get("filter") or IssueFilter.OPEN)
    page = int(ctx.payload.get("page") or 0)
    chunk, pages, page = await list_issues(ctx.db, project.id, ctx.account.id, filt, page)
    update_payload(ctx.dialog, page=page, filter=filt, list_from="issues")
    try:
        title = f"{_FILTER_TITLES[IssueFilter(filt)]} · {project.name}"
    except ValueError:
        title = f"Issues · {project.name}"
    lines = [
        f"{status_emoji(issue.status)} {h(issue_token(issue.number))}  {h(issue.title)}"
        for issue in chunk
    ]
    await issue_buttons(
        ctx,
        texts.issue_list_screen(title, lines, page + 1, pages),
        chunk,
        page=page,
        pages=pages,
        with_project=False,
        placeholder="Choose an issue",
    )


async def render_issue(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if issue is None or project is None or issue.project_id != project.id:
        await goto(ctx, Screen.FILTERS)
        return
    membership = await get_membership(ctx.db, project.id, ctx.account.id)
    if membership is None:
        await goto(ctx, Screen.PROJECT_LIST)
        return
    caps = capabilities(
        status=issue.status,
        is_owner=project.owner_id == ctx.account.id,
        is_reporter=issue.reporter_id == ctx.account.id,
        is_assignee=any(item.user_id == ctx.account.id for item in issue.assignments),
        is_member=True,
        has_post=bool(issue.channel_message_ids),
    )
    rows: list[list[str]] = []
    if caps.resolve:
        rows.append([Btn.RESOLVED])
    if caps.confirm:
        rows.append([Btn.CONFIRM])
    if caps.reopen:
        rows.append([Btn.REOPEN if issue.status == Status.RESOLVED else Btn.REOPEN_CLOSED])
    tools = []
    if caps.note:
        tools.append(Btn.NOTE)
    if caps.reassign:
        tools.append(Btn.ASSIGNEES)
    if tools:
        rows.append(tools)
    if caps.publish:
        rows.append([Btn.PUBLISH])
    rows.append(back_row())
    await present(ctx, detail_card(to_card(issue)), rows, issue_token(issue.number))


async def render_resolve_confirm(ctx: Ctx) -> None:
    await confirm_screen(ctx, texts.resolve_confirm, [Btn.RESOLVED_YES])


async def render_confirm_confirm(ctx: Ctx) -> None:
    await confirm_screen(ctx, texts.confirm_confirm, [Btn.CONFIRM_YES])


async def render_reopen_confirm(ctx: Ctx) -> None:
    await confirm_screen(ctx, texts.reopen_confirm, [Btn.REOPEN_YES])


async def render_note(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    if issue is None:
        await goto(ctx, Screen.PROJECT)
        return
    await present(ctx, texts.ask_note(issue.number), [back_row()], "Write a note")


async def render_reassign(ctx: Ctx) -> None:
    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if issue is None or project is None:
        await goto(ctx, Screen.PROJECT)
        return
    if "selected" not in ctx.payload:
        selected = {item.user_id for item in issue.assignments}
        update_payload(ctx.dialog, selected=sorted(selected))
    else:
        selected = {int(item) for item in ctx.payload.get("selected") or []}
    _body, rows, labels = await people_picker(ctx, project.id, selected)
    update_payload(ctx.dialog, labels=labels)
    text = (
        f"<b>{issue_token(issue.number)}</b>\n"
        f"{h(issue.title)}\n\n"
        "Choose assignees, then save."
    )
    await present(ctx, text, rows + [[Btn.SAVE_ASSIGNEES], back_row()], "Choose assignees")
