"""Reply keyboards. Every action in the bot is one of these buttons."""

from aiogram.types import (
    ChatAdministratorRights,
    KeyboardButton,
    KeyboardButtonRequestChat,
    ReplyKeyboardMarkup,
)

from issuebot.constants import BUTTON_LIMIT, CHANNEL_REQUEST_ID, Btn


def keyboard(rows: list[list[str | KeyboardButton]], placeholder: str) -> ReplyKeyboardMarkup:
    built: list[list[KeyboardButton]] = []
    for row in rows:
        if not row:
            continue
        built.append(
            [
                cell if isinstance(cell, KeyboardButton) else KeyboardButton(text=cell)
                for cell in row
            ]
        )
    return ReplyKeyboardMarkup(
        keyboard=built,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholder[:BUTTON_LIMIT],
    )


def channel_button() -> KeyboardButton:
    """Let the owner pick a channel; Telegram adds the bot as admin if it is not there yet."""
    rights = ChatAdministratorRights(
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_send_welcome_messages=False,
        can_post_messages=True,
        can_pin_messages=True,
    )
    return KeyboardButton(
        text=Btn.CHOOSE_CHANNEL,
        request_chat=KeyboardButtonRequestChat(
            request_id=CHANNEL_REQUEST_ID,
            chat_is_channel=True,
            request_title=True,
            user_administrator_rights=rights,
            bot_administrator_rights=rights,
        ),
    )


def home_rows(*, has_projects: bool) -> list[list[str]]:
    rows: list[list[str]] = [[Btn.NEW]]
    if has_projects:
        rows.append([Btn.PROJECTS])
    rows.append([Btn.HELP])
    return rows


def project_rows() -> list[list[str]]:
    return [
        [Btn.REPORT, Btn.ISSUES],
        [Btn.MEMBERS, Btn.INVITE],
        [Btn.INBOX, Btn.PROJECTS],
        [Btn.HELP],
    ]


def back_row() -> list[str]:
    return [Btn.BACK]


def filter_rows() -> list[list[str]]:
    return [
        [Btn.OPEN, Btn.WAITING],
        [Btn.DONE],
        [Btn.REPORTED, Btn.ASSIGNED],
        [Btn.BACK],
    ]


def pager_row(*, has_prev: bool, has_next: bool) -> list[str]:
    row: list[str] = []
    if has_prev:
        row.append(Btn.PREV)
    if has_next:
        row.append(Btn.NEXT)
    return row
