"""Turn a private message into one screen change."""

from __future__ import annotations

from issuebot import texts
from issuebot.constants import FILTER_BY_BUTTON, Btn, Screen
from issuebot.handlers.actions import (
    add_photo,
    begin_reassign,
    change_page,
    confirm_joined,
    create_named_project,
    delete_owned_project,
    do_confirm,
    do_reopen,
    do_resolve,
    link_from_text,
    open_filter,
    open_labeled_issue,
    open_labeled_project,
    recheck_channel,
    retry_publish,
    rotate_link,
    save_assignees,
    save_body,
    save_note,
    save_title,
    start_report,
    submit_report,
    toggle_person,
)
from issuebot.handlers.types import Ctx
from issuebot.handlers.ui import go_back, goto, remember
from issuebot.services.accounts import update_payload

_LABEL_SCREENS = {
    Screen.PROJECT_LIST.value,
    Screen.ISSUE_LIST.value,
    Screen.INBOX.value,
    Screen.REPORT_ASSIGN.value,
    Screen.REASSIGN.value,
}
_TEXT_SCREENS = {
    Screen.NEW_PROJECT.value,
    Screen.REPORT_TITLE.value,
    Screen.REPORT_BODY.value,
    Screen.NOTE.value,
}


async def handle_text(ctx: Ctx) -> None:
    text = ctx.text
    if text == Btn.BACK:
        await go_back(ctx)
        return

    state = ctx.dialog.state
    labels = {str(key): int(value) for key, value in (ctx.payload.get("labels") or {}).items()}
    if state in _LABEL_SCREENS and text in labels:
        await _open_label(ctx, labels[text])
        return

    if text in FILTER_BY_BUTTON and state == Screen.FILTERS:
        await open_filter(ctx, FILTER_BY_BUTTON[text])
        return
    if text == Btn.NEXT and state in {Screen.ISSUE_LIST.value, Screen.INBOX.value}:
        await change_page(ctx, 1)
        return
    if text == Btn.PREV and state in {Screen.ISSUE_LIST.value, Screen.INBOX.value}:
        await change_page(ctx, -1)
        return

    action = _ACTIONS.get(state, {}).get(text)
    if action is not None:
        await action(ctx)
        return
    if state in _TEXT_SCREENS:
        await _save_text(ctx)
        return
    if state == Screen.AWAIT_CHANNEL:
        await link_from_text(ctx)
        return
    await remember(ctx, texts.USE_BUTTONS)


async def handle_photo(ctx: Ctx) -> None:
    if ctx.dialog.state != Screen.REPORT_MEDIA:
        await remember(ctx, texts.PHOTO_AS_IMAGE if ctx.file_id else texts.USE_BUTTONS)
        return
    if not ctx.file_id:
        await remember(ctx, texts.PHOTO_AS_IMAGE)
        return
    await add_photo(ctx)


async def _open_label(ctx: Ctx, value: int) -> None:
    state = ctx.dialog.state
    if state == Screen.PROJECT_LIST:
        await open_labeled_project(ctx, value)
        return
    if state in {Screen.ISSUE_LIST.value, Screen.INBOX.value}:
        await open_labeled_issue(ctx, value)
        return
    await toggle_person(ctx, value)


async def _save_text(ctx: Ctx) -> None:
    state = ctx.dialog.state
    if state == Screen.NEW_PROJECT:
        await create_named_project(ctx)
    elif state == Screen.REPORT_TITLE:
        await save_title(ctx)
    elif state == Screen.REPORT_BODY:
        await save_body(ctx)
    elif state == Screen.NOTE:
        await save_note(ctx)


async def _inbox(ctx: Ctx) -> None:
    update_payload(ctx.dialog, page=0)
    await goto(ctx, Screen.INBOX)


async def _resolve_screen(ctx: Ctx) -> None:
    await goto(ctx, Screen.RESOLVE_CONFIRM)


async def _confirm_screen(ctx: Ctx) -> None:
    await goto(ctx, Screen.CONFIRM_CONFIRM)


async def _reopen_screen(ctx: Ctx) -> None:
    await goto(ctx, Screen.REOPEN_CONFIRM)


async def _note_screen(ctx: Ctx) -> None:
    await goto(ctx, Screen.NOTE)


_ACTIONS = {
    Screen.HOME.value: {
        Btn.NEW: lambda ctx: goto(ctx, Screen.NEW_PROJECT),
        Btn.PROJECTS: lambda ctx: goto(ctx, Screen.PROJECT_LIST),
        Btn.HELP: lambda ctx: goto(ctx, Screen.HELP),
    },
    Screen.HELP.value: {},
    Screen.AWAIT_CHANNEL.value: {
        Btn.RECHECK: recheck_channel,
        Btn.DELETE: lambda ctx: goto(ctx, Screen.DELETE_CONFIRM),
    },
    Screen.PROJECT_LIST.value: {Btn.NEW: lambda ctx: goto(ctx, Screen.NEW_PROJECT)},
    Screen.PROJECT.value: {
        Btn.REPORT: start_report,
        Btn.ISSUES: lambda ctx: goto(ctx, Screen.FILTERS),
        Btn.MEMBERS: lambda ctx: goto(ctx, Screen.MEMBERS),
        Btn.INVITE: lambda ctx: goto(ctx, Screen.INVITE),
        Btn.INBOX: _inbox,
        Btn.PROJECTS: lambda ctx: goto(ctx, Screen.PROJECT_LIST),
        Btn.HELP: lambda ctx: goto(ctx, Screen.HELP),
        Btn.DELETE: lambda ctx: goto(ctx, Screen.DELETE_CONFIRM),
    },
    Screen.INVITE.value: {Btn.ROTATE: lambda ctx: goto(ctx, Screen.INVITE_CONFIRM)},
    Screen.INVITE_CONFIRM.value: {Btn.ROTATE_YES: rotate_link},
    Screen.DELETE_CONFIRM.value: {Btn.DELETE_YES: delete_owned_project},
    Screen.JOIN.value: {Btn.JOINED: confirm_joined},
    Screen.REPORT_MEDIA.value: {Btn.PHOTOS_DONE: lambda ctx: goto(ctx, Screen.REPORT_ASSIGN)},
    Screen.REPORT_ASSIGN.value: {Btn.SAVE_ISSUE: submit_report},
    Screen.ISSUE.value: {
        Btn.RESOLVED: _resolve_screen,
        Btn.CONFIRM: _confirm_screen,
        Btn.REOPEN: _reopen_screen,
        Btn.REOPEN_CLOSED: _reopen_screen,
        Btn.NOTE: _note_screen,
        Btn.ASSIGNEES: begin_reassign,
        Btn.PUBLISH: retry_publish,
    },
    Screen.RESOLVE_CONFIRM.value: {Btn.RESOLVED_YES: do_resolve},
    Screen.CONFIRM_CONFIRM.value: {Btn.CONFIRM_YES: do_confirm},
    Screen.REOPEN_CONFIRM.value: {Btn.REOPEN_YES: do_reopen},
    Screen.REASSIGN.value: {Btn.SAVE_ASSIGNEES: save_assignees},
}
