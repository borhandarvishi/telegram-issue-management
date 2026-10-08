"""Who may move an issue, and who should hear about it.

open -> resolved -> confirmed
resolved or confirmed -> open
"""

from __future__ import annotations

from dataclasses import dataclass

from issuebot.constants import Status


@dataclass(frozen=True)
class Caps:
    view: bool = False
    resolve: bool = False
    confirm: bool = False
    reopen: bool = False
    reassign: bool = False
    note: bool = False
    publish: bool = False


def capabilities(
    *,
    status: str,
    is_owner: bool,
    is_reporter: bool,
    is_assignee: bool,
    is_member: bool,
    has_post: bool,
) -> Caps:
    if not is_member:
        return Caps()
    return Caps(
        view=True,
        resolve=status == Status.OPEN and (is_assignee or is_owner),
        confirm=status == Status.RESOLVED and is_reporter,
        reopen=status in {Status.RESOLVED, Status.CONFIRMED} and (is_reporter or is_owner),
        reassign=status != Status.CONFIRMED and (is_owner or is_reporter or is_assignee),
        note=True,
        publish=not has_post and (is_owner or is_reporter),
    )


def except_actor(user_ids: list[int], actor_id: int) -> list[int]:
    return [user_id for user_id in dict.fromkeys(user_ids) if user_id != actor_id]


def note_recipients(*, reporter_id: int, assignee_ids: list[int], actor_id: int) -> list[int]:
    people = [reporter_id, *assignee_ids]
    return except_actor(people, actor_id)
