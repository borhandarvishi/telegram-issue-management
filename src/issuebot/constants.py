"""Stable names for screens, statuses, and reply-keyboard buttons.

Button labels are the whole interface. They must stay short (Telegram allows
64 characters) and must match exactly, so they live in one place.
"""

from enum import StrEnum


class Screen(StrEnum):
    HOME = "home"
    HELP = "help"
    NEW_PROJECT = "new_project"
    AWAIT_CHANNEL = "await_channel"
    PROJECT_LIST = "project_list"
    PROJECT = "project"
    INVITE = "invite"
    INVITE_CONFIRM = "invite_confirm"
    MEMBERS = "members"
    INBOX = "inbox"
    JOIN = "join"
    REPORT_TITLE = "report_title"
    REPORT_BODY = "report_body"
    REPORT_MEDIA = "report_media"
    REPORT_ASSIGN = "report_assign"
    FILTERS = "filters"
    ISSUE_LIST = "issue_list"
    ISSUE = "issue"
    RESOLVE_CONFIRM = "resolve_confirm"
    CONFIRM_CONFIRM = "confirm_confirm"
    REOPEN_CONFIRM = "reopen_confirm"
    NOTE = "note"
    REASSIGN = "reassign"
    DELETE_CONFIRM = "delete_confirm"


class Status(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CONFIRMED = "confirmed"


class IssueFilter(StrEnum):
    OPEN = "open"
    WAITING = "waiting"
    DONE = "done"
    REPORTED = "reported"
    ASSIGNED = "assigned"


class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class Btn:
    NEW = "➕ New project"
    PROJECTS = "📂 Projects"
    HELP = "❓ Help"
    INBOX = "📥 My work"
    REPORT = "📝 Report issue"
    ISSUES = "📋 Issues"
    MEMBERS = "👥 Members"
    INVITE = "🔗 Invite"
    BACK = "↩️ Back"
    ROTATE = "🔄 New link"
    ROTATE_YES = "✅ Create new link"
    RECHECK = "🔄 Check access"
    CHOOSE_CHANNEL = "📡 Choose channel"
    JOINED = "✅ I joined the channel"
    SAVE_ISSUE = "✅ Submit issue"
    PHOTOS_DONE = "✅ Continue"
    RESOLVED = "🟢 Resolved"
    RESOLVED_YES = "✅ Yes, resolved"
    CONFIRM = "✅ Confirm fix"
    CONFIRM_YES = "✅ Yes, I confirm"
    REOPEN = "🔄 Not fixed yet"
    REOPEN_CLOSED = "🔄 Reopen"
    REOPEN_YES = "🔄 Yes, reopen"
    NOTE = "📝 Note"
    ASSIGNEES = "👤 Assignees"
    SAVE_ASSIGNEES = "✅ Save assignees"
    PUBLISH = "📣 Post to channel"
    OPEN = "🔴 Open"
    WAITING = "🟢 Awaiting confirm"
    DONE = "✅ Confirmed"
    REPORTED = "📝 Reported by me"
    ASSIGNED = "🎯 Assigned to me"
    NEXT = "▶️ Next"
    PREV = "◀️ Previous"
    DELETE = "🗑 Delete project"
    DELETE_YES = "✅ Delete this project"


FILTER_BY_BUTTON = {
    Btn.OPEN: IssueFilter.OPEN,
    Btn.WAITING: IssueFilter.WAITING,
    Btn.DONE: IssueFilter.DONE,
    Btn.REPORTED: IssueFilter.REPORTED,
    Btn.ASSIGNED: IssueFilter.ASSIGNED,
}

PAGE_SIZE = 6
MAX_PHOTOS = 10
MAX_TITLE = 120
MAX_PROJECT_NAME = 80
MAX_DESCRIPTION = 3500
MAX_NOTE = 1000
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4000
BUTTON_LIMIT = 64
CHANNEL_REQUEST_ID = 1
