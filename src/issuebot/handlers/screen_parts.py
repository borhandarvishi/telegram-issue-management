"""Shared pieces used while drawing a screen."""

from __future__ import annotations

from issuebot.constants import PAGE_SIZE, Screen
from issuebot.formatting import (
    format_person,
    h,
    issue_button,
    issue_token,
    person_button,
    status_emoji,
    unique_labels,
)
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import goto, present
from issuebot.keyboards import back_row, pager_row
from issuebot.services.accounts import update_payload
from issuebot.services.members import roster
from issuebot.services.projects import get_project


async def linked_project(ctx: Ctx):
    project = await get_project(ctx.db, ctx.dialog.project_id)
    if project is None:
        await goto(ctx, Screen.HOME)
        return None
    if not project.channel_id:
        ctx.dialog.state = Screen.AWAIT_CHANNEL.value
        from issuebot.handlers import screens

        await screens.render_await(ctx)
        return None
    return project


async def people_picker(ctx: Ctx, project_id: int, selected: set[int]):
    pairs = []
    chosen: list[str] = []
    pending: list[str] = []
    for row in await roster(ctx.db, project_id):
        person = format_person(row.user.username, row.user.first_name, row.user.last_name)
        picked = row.user_id in selected
        pairs.append((person_button(person, selected=picked), row.user_id))
        if picked:
            chosen.append(person)
            if not row.user.opened_bot:
                pending.append(format_person(None, row.user.first_name, row.user.last_name))
    labels = unique_labels(pairs)
    rows = [[label] for label in labels]
    stored = {key: int(value) for key, value in labels.items()}
    return {"selected": chosen, "pending": pending}, rows, stored


async def issue_buttons(
    ctx: Ctx,
    text: str,
    issues,
    *,
    page: int,
    pages: int,
    with_project: bool,
    placeholder: str,
) -> None:
    pairs = []
    extra: list[str] = []
    for issue in issues:
        project_name = issue.project.name if with_project else None
        pairs.append((issue_button(issue.number, issue.title, project_name), issue.id))
        if with_project:
            extra.append(
                f"{status_emoji(issue.status)} {h(issue_token(issue.number))}"
                f" · {h(issue.project.name)}\n"
                f"{h(issue.title)}"
            )
    labels = unique_labels(pairs)
    update_payload(ctx.dialog, labels={key: int(value) for key, value in labels.items()})
    body = text if not extra else text + "\n\n" + "\n\n".join(extra)
    rows = [[label] for label in labels]
    pager = pager_row(has_prev=page > 0, has_next=page + 1 < pages)
    if pager:
        rows.append(pager)
    rows.append(back_row())
    await present(ctx, body, rows, placeholder)


async def confirm_screen(ctx: Ctx, builder, buttons: list[str]) -> None:
    from issuebot.services.issues import get_issue

    issue = await get_issue(ctx.db, ctx.dialog.issue_id)
    if issue is None:
        await goto(ctx, Screen.PROJECT)
        return
    await present(ctx, builder(issue.number, issue.title), [buttons, back_row()], "Confirm")


def page_slice(items: list, page: int) -> tuple[list, int, int]:
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 0), pages - 1)
    start = page * PAGE_SIZE
    return items[start : start + PAGE_SIZE], pages, page
