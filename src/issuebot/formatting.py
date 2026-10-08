"""Pure presentation helpers. No database and no Telegram calls."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape

from issuebot.constants import BUTTON_LIMIT, MESSAGE_LIMIT, Status

_URL = re.compile(r"https?://[^\s<]+")


def h(text: str) -> str:
    return escape(text or "", quote=False)


def link(url: str, label: str | None = None) -> str:
    """A clickable link. Anything that is not an http(s) URL is shown as plain text."""
    target = (url or "").strip()
    if not target.lower().startswith(("http://", "https://")) or any(c in target for c in ' "<>'):
        return h(label or target)
    shown = h(label) if label else h(target)
    return f'<a href="{escape(target, quote=True)}">{shown}</a>'


def linkify(text: str) -> str:
    """Escape text and turn URLs in it into clickable links."""
    parts: list[str] = []
    last = 0
    for match in _URL.finditer(text or ""):
        parts.append(h(text[last : match.start()]))
        raw = match.group(0)
        url = raw.rstrip(".,);]")
        parts.append(link(url))
        parts.append(h(raw[len(url) :]))
        last = match.end()
    parts.append(h((text or "")[last:]))
    return "".join(parts)


def clip(text: str, limit: int) -> str:
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    if limit <= 1:
        return collapsed[:limit]
    return collapsed[: limit - 1] + "…"


def format_person(username: str | None, first_name: str, last_name: str | None = None) -> str:
    """@username (Name), or just Name when the account has no public username."""
    name = " ".join(part for part in (first_name, last_name) if part).strip() or "Unnamed"
    if username:
        handle = username[1:] if username.startswith("@") else username
        return f"@{handle} ({name})"
    return name


def format_when(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%d %b %Y, %H:%M UTC")


def status_emoji(status: str) -> str:
    return {
        Status.OPEN: "🔴",
        Status.RESOLVED: "🟢",
        Status.CONFIRMED: "✅",
    }.get(status, "🔴")


def status_phrase(
    status: str,
    *,
    solver: str | None = None,
    confirmer: str | None = None,
) -> str:
    if status == Status.RESOLVED and solver:
        return f"Resolved by {solver}"
    if status == Status.CONFIRMED and confirmer:
        return f"Confirmed by {confirmer}"
    if status == Status.RESOLVED:
        return "Resolved"
    if status == Status.CONFIRMED:
        return "Confirmed"
    return "Open"


@dataclass(frozen=True)
class NoteLine:
    author: str
    body: str


@dataclass(frozen=True)
class IssueCard:
    number: int
    project: str
    title: str
    description: str
    status: str
    reporter: str
    assignees: tuple[str, ...]
    notes: tuple[NoteLine, ...]
    timeline: tuple[str, ...]
    created_at: datetime
    solver: str | None = None
    confirmer: str | None = None
    photo_count: int = 0


def issue_token(number: int) -> str:
    return f"ISSUE #{number}"


def channel_delivery(_text: str, photo_count: int) -> str:
    """One channel post. Photos carry the card as their caption, never as a second message."""
    if photo_count <= 0:
        return "text"
    if photo_count == 1:
        return "photo"
    return "album"


def _people(assignees: tuple[str, ...]) -> str:
    if not assignees:
        return "Unassigned"
    return "، ".join(assignees)


def _notes_block(notes: tuple[NoteLine, ...], *, limit: int) -> list[str]:
    if not notes:
        return []
    body = ["", "<b>Notes</b>"]
    for note in notes[-limit:]:
        text = note.body if len(note.body) <= 220 else note.body[:219] + "…"
        body.append(f"• {h(note.author)}: {linkify(text)}")
    return body


def channel_card(card: IssueCard, *, limit: int = MESSAGE_LIMIT) -> str:
    return _shrink(card, _channel_lines, limit)


def detail_card(card: IssueCard) -> str:
    return _shrink(card, _detail_lines, MESSAGE_LIMIT)


def _channel_lines(card: IssueCard) -> str:
    phrase = status_phrase(card.status, solver=card.solver, confirmer=card.confirmer)
    lines = [
        f"{status_emoji(card.status)} <b>{issue_token(card.number)}</b>",
        f"Status: {h(phrase)}",
        f"Project: {h(card.project)}",
        "",
        f"<b>{h(card.title)}</b>",
        "",
        linkify(card.description),
        "",
        f"Reporter: {h(card.reporter)}",
        f"Assignees: {h(_people(card.assignees))}",
    ]
    lines += _notes_block(card.notes, limit=5)
    lines += ["", f"Reported {format_when(card.created_at)}", "", f"#{card.number}"]
    return "\n".join(lines)


def _detail_lines(card: IssueCard) -> str:
    phrase = status_phrase(card.status, solver=card.solver, confirmer=card.confirmer)
    lines = [
        f"{status_emoji(card.status)} <b>{issue_token(card.number)}</b>",
        h(card.project),
        f"Status: {h(phrase)}",
        "",
        f"<b>{h(card.title)}</b>",
        linkify(card.description),
        "",
        f"Reporter: {h(card.reporter)}",
        f"Assignees: {h(_people(card.assignees))}",
        f"Photos: {card.photo_count}",
    ]
    lines += _notes_block(card.notes, limit=10)
    if card.timeline:
        lines += ["", "<b>History</b>"]
        lines += [f"• {h(item)}" for item in card.timeline[-8:]]
    lines += ["", f"Reported {format_when(card.created_at)}"]
    return "\n".join(lines)


def _shrink(card: IssueCard, render, limit: int) -> str:
    text = render(card)
    description = card.description
    notes = card.notes
    while len(text) > limit and (description or len(notes) > 1):
        if description:
            description = description[: max(0, len(description) - 240)]
        else:
            notes = notes[-max(1, len(notes) // 2) :]
        card = IssueCard(
            number=card.number,
            project=card.project,
            title=card.title,
            description=(description + "…") if description else "…",
            status=card.status,
            reporter=card.reporter,
            assignees=card.assignees,
            notes=notes,
            timeline=card.timeline[-4:],
            created_at=card.created_at,
            solver=card.solver,
            confirmer=card.confirmer,
            photo_count=card.photo_count,
        )
        text = render(card)
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def issue_button(number: int, title: str, project: str | None = None) -> str:
    head = issue_token(number)
    if project:
        head = f"{head} · {clip(project, 18)}"
    room = BUTTON_LIMIT - len(head) - 1
    if room >= 8:
        return clip(f"{head} {clip(title, room)}", BUTTON_LIMIT)
    return clip(head, BUTTON_LIMIT)


def project_button(name: str, *, pending: bool) -> str:
    suffix = " · no channel" if pending else ""
    return clip(f"📁 {name}{suffix}", BUTTON_LIMIT)


def person_button(person: str, *, selected: bool) -> str:
    mark = "✅" if selected else "▫️"
    return clip(f"{mark} {person}", BUTTON_LIMIT)


def unique_labels(pairs: list[tuple[str, int]]) -> dict[str, int]:
    """Button text -> id, with suffixes when two labels would collide."""
    seen: dict[str, int] = {}
    for label, value in pairs:
        candidate = clip(label, BUTTON_LIMIT) or "—"
        extra = 2
        while candidate in seen and seen[candidate] != value:
            suffix = f" {extra}"
            candidate = clip(label, BUTTON_LIMIT - len(suffix)) + suffix
            extra += 1
        seen[candidate] = value
    return seen
