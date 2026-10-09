"""English copy. The bot speaks only through this module."""

from issuebot.formatting import h, link


def guide(name: str, project_count: int) -> str:
    if project_count:
        tail = f"Your projects: {project_count}"
    else:
        tail = "You have no projects yet. Start with the button below."
    return (
        f"Hello {h(name)} 👋\n\n"
        "<b>How it works</b>\n"
        "1. Create a project and connect a private channel.\n"
        "2. Share the invite. After joining, each person opens the bot.\n"
        "3. File a report and choose at least one assignee.\n"
        "4. The assignee marks it resolved. You confirm, or send it back.\n\n"
        "<b>Marks</b>\n"
        "🔴 Open\n"
        "🔴⚠️ Urgent\n"
        "🟡 Reopened\n"
        "🟤 Resolved, waiting for the reporter\n"
        "🟢 Confirmed\n"
        "👤 Reporter or assignee\n\n"
        "One number follows the issue everywhere: <b>ISSUE #12</b>\n\n"
        f"{tail}"
    )


def ask_project_name() -> str:
    return (
        "<b>New project</b>\n\nSend the project name.\nFor example: Shop, Mobile app, Company site"
    )


def await_channel(name: str, username: str, missing: list[str] | None = None) -> str:
    bot = f"@{username}" if username else "this bot"
    lines = [
        f"<b>{h(name)}</b>",
        "",
        "A bot cannot create a channel. You do that once.",
        "",
        "1. Create a <b>private channel</b> in Telegram.",
        "2. Tap <b>Choose channel</b> below and pick it.",
        f"3. Telegram asks to add {h(bot)} as an admin. Accept.",
        "That includes permission to ban users, so you can remove someone later.",
        "",
        "The channel is linked only to the project open on this screen.",
        "A public channel can also be sent as @name.",
        "A private invite link cannot be read, so use Choose channel.",
    ]
    if missing:
        lines += ["", "<b>These permissions are still off:</b>"]
        lines += [f"• {h(item)}" for item in missing]
        lines += ["", "Turn them on, then tap Check access."]
    return "\n".join(lines)


def channel_ready(name: str, invite: str, channel_title: str | None, start: str) -> str:
    where = f"\nChannel: {h(channel_title)}" if channel_title else ""
    return (
        f"<b>{h(name)}</b> is ready.{where}\n\n"
        "Send this channel invite to the team:\n"
        f"{link(invite)}\n\n"
        "After joining, each person opens the bot:\n"
        f"{link(start)}\n\n"
        "Join the channel yourself too, if you are not in it yet."
    )


def invite_screen(
    name: str,
    invite: str | None,
    channel_title: str | None,
    start: str,
    is_owner: bool,
) -> str:
    where = f"\nChannel: {h(channel_title)}" if channel_title else ""
    shown = link(invite) if invite else "No invite link yet."
    extra = "\n\nA new link revokes the current one." if is_owner else ""
    return (
        f"<b>Invite · {h(name)}</b>{where}\n\n"
        f"Join the channel:\n{shown}\n\n"
        f"Open the bot:\n{link(start)}"
        f"{extra}"
    )


def delete_confirm(name: str) -> str:
    return (
        f"<b>Delete {h(name)}?</b>\n\n"
        "This removes the project for every member.\n"
        "Issues in it are removed from the bot as well.\n"
        "The Telegram channel itself stays."
    )


def project_removed(name: str) -> str:
    return f"<b>{h(name)}</b> was deleted by its owner.\nIt is no longer in your projects."


def rotate_confirm(name: str) -> str:
    return (
        f"<b>{h(name)}</b>\n\n"
        "Revoke the current link and create a new one?\n"
        "Anyone holding the old link will not be able to join with it."
    )


def project_home(
    name: str,
    *,
    open_count: int,
    waiting_count: int,
    inbox_count: int,
    bot_admin: bool,
) -> str:
    lines = [
        f"<b>{h(name)}</b>",
        f"Open {open_count} · Awaiting confirmation {waiting_count}",
    ]
    if inbox_count:
        lines.append(f"{inbox_count} item(s) in My work are waiting for you.")
    if not bot_admin:
        lines += ["", "The bot no longer has access to the channel. Make it an admin again."]
    lines += ["", "Choose an action."]
    return "\n".join(lines)


def project_list(count: int) -> str:
    if not count:
        return "<b>Projects</b>\n\nYou have no projects yet."
    return f"<b>Projects</b>\n\n{count} project(s). Open one."


def members_screen(name: str, lines: list[str], *, can_remove: bool) -> str:
    if lines:
        body = "\n".join(lines)
    else:
        body = "Nobody else is in this project yet.\nSend the invite link."
    tail = (
        "Tap a person to remove them from the project and the channel."
        if can_remove
        else "Names look like @username (Name).\nAn account with no username is shown by name only."
    )
    return f"<b>Members · {h(name)}</b>\n\n{body}\n\n{tail}"


def remove_member_confirm(project: str, person: str) -> str:
    return (
        f"<b>Remove {h(person)}?</b>\n"
        f"{h(project)}\n\n"
        "They leave the project and the channel.\n"
        "A new invite can let them back in later."
    )


def removed_from_project(project: str) -> str:
    return (
        f"You were removed from <b>{h(project)}</b>.\n"
        "It is no longer in your projects, and you were removed from the channel."
    )


CANNOT_REMOVE_FROM_CHANNEL = (
    "The bot could not remove that person from the channel.\n"
    "In the channel, edit the bot's admin rights and turn on Ban users. Then try again."
)


def member_line(person: str, *, is_owner: bool, opened_bot: bool) -> str:
    bits = [person]
    if is_owner:
        bits.append("owner")
    if not opened_bot:
        bits.append("has not opened the bot")
    return " · ".join(bits)


def inbox_screen(count: int) -> str:
    if not count:
        return (
            "<b>My work</b>\n\n"
            "Nothing is waiting for you.\n"
            "Open issues assigned to you, and reports waiting for your confirmation, show up here."
        )
    return (
        f"<b>My work</b>\n\n"
        f"{count} item(s). Pick the same ISSUE number you saw in the notification."
    )


def join_screen(name: str, invite: str | None) -> str:
    shown = f"\n{link(invite)}" if invite else ""
    return (
        f"<b>{h(name)}</b>\n\n"
        "Join the project channel with the link below."
        f"{shown}\n\n"
        "Then tap I joined the channel."
    )


def report_title(project: str) -> str:
    return f"<b>New issue · {h(project)}</b>\n\nSend a title for this issue."


def report_body(project: str, title: str) -> str:
    return (
        f"<b>New issue · {h(project)}</b>\n\n{h(title)}\n\nWrite a good description.\nOr tap Skip."
    )


def report_media(project: str, photo_count: int) -> str:
    photos = f"{photo_count} photo(s) added." if photo_count else "No photo yet."
    return (
        f"<b>New issue · {h(project)}</b>\n\n"
        f"{photos}\n\n"
        "Send a photo or a link if you have one.\n"
        "Then tap Skip."
    )


def report_assign(
    project: str,
    *,
    title: str,
    description: str,
    photo_count: int,
    selected: list[str],
    pending_names: list[str],
    urgent: bool,
) -> str:
    if selected:
        chosen = "\n".join(f"👤 {h(item)}" for item in selected)
    else:
        chosen = "Nobody yet. At least one person is required."
    warn = ""
    if pending_names:
        names = ", ".join(h(name) for name in pending_names)
        warn = f"\n\n⚠️ {names} has not opened the bot, so they will not get a notification."
    snippet = description if len(description) <= 280 else description[:279] + "…"
    written = h(snippet) if snippet else "No description."
    return (
        f"<b>New issue · {h(project)}</b>\n\n"
        f"<b>{h(title)}</b>\n"
        f"{written}\n"
        f"Photos: {photo_count}\n"
        f"Priority: {'Urgent' if urgent else 'Normal'}\n\n"
        "Select the assignees. Tap a name again to remove them.\n"
        "Then tap Submit issue under this message.\n\n"
        f"<b>Assignees</b>\n{chosen}{warn}"
    )


def filters_screen(project: str, counts: dict[str, int]) -> str:
    return (
        f"<b>Issues · {h(project)}</b>\n\n"
        f"🔴 Open · {counts.get('open', 0)}\n"
        f"🟤 Awaiting confirmation · {counts.get('waiting', 0)}\n"
        f"🟢 Confirmed · {counts.get('done', 0)}\n\n"
        "Which list do you want?"
    )


def issue_list_screen(title: str, lines: list[str], page: int, pages: int) -> str:
    body = "\n".join(lines) if lines else "Nothing in this list."
    pager = f"\n\nPage {page} of {pages}" if pages > 1 else ""
    return f"<b>{h(title)}</b>\n\n{body}{pager}"


def ask_note(number: int) -> str:
    return (
        f"<b>ISSUE #{number}</b>\n\n"
        "Send the note.\n"
        "It is saved for the assignee, the reporter, and the project channel."
    )


def resolve_confirm(number: int, title: str) -> str:
    return (
        f"<b>ISSUE #{number}</b>\n"
        f"{h(title)}\n\n"
        "Mark this as resolved?\n"
        "The reporter will be asked to confirm."
    )


def confirm_confirm(number: int, title: str) -> str:
    return f"<b>ISSUE #{number}</b>\n{h(title)}\n\nConfirm that this issue is fixed?"


def reopen_confirm(number: int, title: str) -> str:
    return (
        f"<b>ISSUE #{number}</b>\n{h(title)}\n\nReopen this issue?\nThe assignee will be notified."
    )


def registered(number: int, published: bool) -> str:
    where = (
        "It was also posted to the project channel."
        if published
        else "It was not posted to the channel. Post it again from this screen."
    )
    return f"<b>ISSUE #{number}</b> filed.\n{where}"


def status_changed(number: int, label: str) -> str:
    return f"<b>ISSUE #{number}</b>\n{h(label)}"


INVALID_LINK = "This link is not valid."
NOT_A_MEMBER = "You are not in the channel yet."
NOT_ALLOWED = "You cannot do that."
STALE = "This issue changed. Look at the screen again."
USE_BUTTONS = "Use the buttons below."
SEND_TEXT = "Send text here."
PHOTO_AS_IMAGE = "Send it as a photo, not as a file. You can put a link in the description."
TITLE_TOO_SHORT = "Make the title a little clearer. At least 3 characters."
TITLE_TOO_LONG = "That title is too long. One short sentence is enough."
BODY_TOO_SHORT = "Describe the issue. Links go here too."
NOTE_TOO_SHORT = "The note is empty."
NEED_ASSIGNEE = "Choose at least one person. Tap a name again to remove them."
NAME_TOO_SHORT = "That project name is too short."
NAME_TOO_LONG = "That project name is too long."
GENERIC_ERROR = "Something went wrong. Tap the same button again."
NO_CHANNEL = "This project has no channel yet."
PUBLISH_FAILED = (
    "Could not post to the channel. Check that the bot is still an admin "
    "and can post and delete messages."
)
RESTORED = "The channel connection is back."
REMOVED = "The bot was removed from the project channel. Make it an admin again to continue."
LINKED = "Channel connected. The invite link is ready."
PERMS_STILL_MISSING = "The permissions are still incomplete."
NOT_CHANNEL = "Add the bot to a channel, not a group."
NO_PENDING = (
    "The bot was made an admin, but no project was waiting for a channel.\n"
    "Create a project in the bot first, then make the bot an admin again."
)
ALREADY_LINKED = "This channel is already connected to another project."
PRIVATE_LINK = "A private invite link cannot be read. Tap Choose channel and pick the channel."
CHANNEL_NOT_FOUND = "That channel was not found. Make the bot an admin, then tap Choose channel."
PICK_ON_PROJECT = "Open the project first, then tap Choose channel."


def bot_added(title: str) -> str:
    return (
        f"The bot is an admin of <b>{h(title)}</b>.\n"
        "Open the project and tap Choose channel. That project gets this channel."
    )


def bot_needs_rights(title: str, missing: list[str]) -> str:
    lines = [
        f"The bot is in <b>{h(title)}</b>, but these permissions are still off:",
        *[f"• {h(item)}" for item in missing],
        "",
        "Turn them on, open the project, and tap Choose channel.",
    ]
    return "\n".join(lines)


def you_removed(person: str, project: str) -> str:
    return f"You removed 👤 {h(person)} from <b>{h(project)}</b>."


def notify_assigned(number: int, project: str, title: str, reporter: str, mark: str) -> str:
    return (
        f"{mark} <b>ISSUE #{number}</b>\n"
        f"{h(project)}\n\n"
        "Assigned to you.\n"
        f"{h(title)}\n"
        f"Reporter: {h(reporter)}\n\n"
        "Use the button below, or open it from My work."
    )


def notify_resolved(number: int, project: str, title: str, solver: str) -> str:
    return (
        f"🟤 <b>ISSUE #{number}</b>\n"
        f"{h(project)}\n\n"
        f"👤 {h(solver)} marked it resolved.\n"
        f"{h(title)}\n\n"
        "Confirm the fix, or send it back."
    )


def notify_confirmed(number: int, project: str, title: str, reporter: str) -> str:
    return (
        f"🟢 <b>ISSUE #{number}</b>\n"
        f"{h(project)}\n\n"
        f"👤 {h(reporter)} confirmed the fix.\n"
        f"{h(title)}"
    )


def notify_reopened(number: int, project: str, title: str, actor: str) -> str:
    return (
        f"🟡 <b>ISSUE #{number}</b>\n"
        f"{h(project)}\n\n"
        f"👤 {h(actor)} says it is not fixed yet.\n"
        f"{h(title)}"
    )


def notify_note(number: int, project: str, title: str, author: str, excerpt: str) -> str:
    return (
        f"📝 <b>ISSUE #{number}</b>\n"
        f"{h(project)}\n\n"
        f"New note from {h(author)}:\n"
        f"{h(excerpt)}\n\n"
        f"{h(title)}"
    )


def notify_joined(project: str) -> str:
    return f"You were added to <b>{h(project)}</b>.\nOpen it from Projects."


def channel_pin(project: str, start_link: str) -> str:
    return (
        f"<b>{h(project)}</b>\n\n"
        "Issues are filed only through the bot.\n"
        "Open the bot:\n"
        f"{link(start_link)}"
    )
