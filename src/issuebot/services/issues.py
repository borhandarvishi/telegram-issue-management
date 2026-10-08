"""Issue records, notes, and status changes."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from issuebot.constants import PAGE_SIZE, IssueFilter, Role, Status
from issuebot.db.models import (
    Assignment,
    Event,
    Issue,
    Membership,
    Note,
    Photo,
    Project,
    User,
    utcnow,
)
from issuebot.formatting import IssueCard, NoteLine, format_person
from issuebot.services.rules import note_recipients


class NotAllowed(Exception):
    pass


class BadTransition(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    issue_id: int
    notify_ids: list[int]
    kind: str


def person_label(user: User) -> str:
    return format_person(user.username, user.first_name, user.last_name)


def _event(issue: Issue, actor: User | None, kind: str, line: str) -> Event:
    return Event(
        issue_id=issue.id,
        actor_id=actor.id if actor else None,
        type=kind,
        payload={"line": line},
        created_at=utcnow(),
    )


_ISSUE_OPTIONS = (
    selectinload(Issue.project),
    selectinload(Issue.reporter),
    selectinload(Issue.resolved_by),
    selectinload(Issue.confirmed_by),
    selectinload(Issue.assignments).selectinload(Assignment.user),
    selectinload(Issue.notes).selectinload(Note.author),
    selectinload(Issue.events),
    selectinload(Issue.photos),
)


async def get_issue(db: AsyncSession, issue_id: int | None) -> Issue | None:
    if not issue_id:
        return None
    stmt = (
        select(Issue)
        .where(Issue.id == issue_id)
        .options(*_ISSUE_OPTIONS)
        .execution_options(populate_existing=True)
    )
    return await db.scalar(stmt)


def to_card(issue: Issue) -> IssueCard:
    assignees = tuple(person_label(item.user) for item in issue.assignments)
    notes = tuple(NoteLine(person_label(note.author), note.body) for note in issue.notes)
    timeline = tuple(event.payload.get("line", "") for event in issue.events if event.payload)
    return IssueCard(
        number=issue.number,
        project=issue.project.name,
        title=issue.title,
        description=issue.description,
        status=issue.status,
        reporter=person_label(issue.reporter),
        assignees=assignees,
        notes=notes,
        timeline=tuple(line for line in timeline if line),
        created_at=issue.created_at,
        solver=person_label(issue.resolved_by) if issue.resolved_by else None,
        confirmer=person_label(issue.confirmed_by) if issue.confirmed_by else None,
        photo_count=len(issue.photos),
    )


def photo_ids(issue: Issue) -> list[str]:
    return [photo.file_id for photo in issue.photos]


async def counts(db: AsyncSession, project_id: int) -> dict[str, int]:
    stmt = (
        select(Issue.status, func.count())
        .where(Issue.project_id == project_id)
        .group_by(Issue.status)
    )
    found = {status: count for status, count in (await db.execute(stmt)).all()}
    return {
        "open": found.get(Status.OPEN, 0),
        "waiting": found.get(Status.RESOLVED, 0),
        "done": found.get(Status.CONFIRMED, 0),
    }


def inbox_stmt(user_id: int):
    assigned_to_user = exists().where(
        Assignment.issue_id == Issue.id,
        Assignment.user_id == user_id,
    )
    member = exists().where(
        Membership.project_id == Issue.project_id,
        Membership.user_id == user_id,
    )
    return (
        select(Issue)
        .where(member)
        .where(
            or_(
                and_(assigned_to_user, Issue.status == Status.OPEN),
                and_(Issue.reporter_id == user_id, Issue.status == Status.RESOLVED),
            )
        )
        .order_by(Issue.updated_at.desc())
        .options(selectinload(Issue.project))
    )


async def inbox(db: AsyncSession, user_id: int) -> list[Issue]:
    return list(await db.scalars(inbox_stmt(user_id)))


async def inbox_count(db: AsyncSession, user_id: int) -> int:
    return len(await inbox(db, user_id))


def _filtered(project_id: int, user_id: int, filt: str):
    stmt = select(Issue).where(Issue.project_id == project_id)
    if filt == IssueFilter.OPEN:
        stmt = stmt.where(Issue.status == Status.OPEN)
    elif filt == IssueFilter.WAITING:
        stmt = stmt.where(Issue.status == Status.RESOLVED)
    elif filt == IssueFilter.DONE:
        stmt = stmt.where(Issue.status == Status.CONFIRMED)
    elif filt == IssueFilter.REPORTED:
        stmt = stmt.where(Issue.reporter_id == user_id)
    elif filt == IssueFilter.ASSIGNED:
        stmt = stmt.where(
            exists().where(Assignment.issue_id == Issue.id, Assignment.user_id == user_id)
        )
    return stmt.order_by(Issue.number.desc())


async def list_issues(
    db: AsyncSession, project_id: int, user_id: int, filt: str, page: int
) -> tuple[list[Issue], int, int]:
    stmt = _filtered(project_id, user_id, filt)
    rows = list(await db.scalars(stmt))
    pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(page, 0), pages - 1)
    start = page * PAGE_SIZE
    return rows[start : start + PAGE_SIZE], pages, page


async def create_issue(
    db: AsyncSession,
    *,
    project: Project,
    reporter: User,
    title: str,
    description: str,
    photos: list[str],
    assignee_ids: list[int],
) -> Issue:
    project.next_issue_number += 1
    issue = Issue(
        project_id=project.id,
        number=project.next_issue_number,
        title=title,
        description=description,
        status=Status.OPEN,
        reporter_id=reporter.id,
        channel_message_ids=[],
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(issue)
    await db.flush()
    for position, file_id in enumerate(photos):
        db.add(Photo(issue_id=issue.id, file_id=file_id, position=position))
    labels: list[str] = []
    for user_id in assignee_ids:
        user = await db.get(User, user_id)
        if user is None:
            continue
        db.add(
            Assignment(
                issue_id=issue.id,
                user_id=user_id,
                assigned_by_id=reporter.id,
                assigned_at=utcnow(),
            )
        )
        labels.append(person_label(user))
    db.add(_event(issue, reporter, "created", f"Filed by {person_label(reporter)}"))
    if labels:
        db.add(_event(issue, reporter, "assigned", "Assignees: " + ", ".join(labels)))
    await db.flush()
    return issue


async def _require(db: AsyncSession, issue_id: int, actor_id: int) -> tuple[Issue, Membership]:
    issue = await get_issue(db, issue_id)
    if issue is None:
        raise BadTransition
    membership = await db.get(Membership, (issue.project_id, actor_id))
    if membership is None:
        raise NotAllowed
    return issue, membership


def _flags(issue: Issue, actor_id: int, membership: Membership) -> dict:
    return {
        "is_owner": membership.role == Role.OWNER or issue.project.owner_id == actor_id,
        "is_reporter": issue.reporter_id == actor_id,
        "is_assignee": any(item.user_id == actor_id for item in issue.assignments),
        "is_member": True,
    }


async def mark_resolved(db: AsyncSession, issue_id: int, actor: User) -> Outcome:
    issue, membership = await _require(db, issue_id, actor.id)
    flags = _flags(issue, actor.id, membership)
    if issue.status != Status.OPEN or not (flags["is_assignee"] or flags["is_owner"]):
        if issue.status != Status.OPEN:
            raise BadTransition
        raise NotAllowed
    issue.status = Status.RESOLVED
    issue.resolved_by_id = actor.id
    issue.resolved_at = utcnow()
    issue.updated_at = utcnow()
    db.add(_event(issue, actor, "resolved", f"Resolved by {person_label(actor)}"))
    notify = [] if issue.reporter_id == actor.id else [issue.reporter_id]
    await db.flush()
    return Outcome(issue.id, notify, "resolved")


async def confirm(db: AsyncSession, issue_id: int, actor: User) -> Outcome:
    issue, _membership = await _require(db, issue_id, actor.id)
    if issue.status != Status.RESOLVED:
        raise BadTransition
    if issue.reporter_id != actor.id:
        raise NotAllowed
    issue.status = Status.CONFIRMED
    issue.confirmed_by_id = actor.id
    issue.confirmed_at = utcnow()
    issue.updated_at = utcnow()
    db.add(_event(issue, actor, "confirmed", f"Confirmed by {person_label(actor)}"))
    notify = [item.user_id for item in issue.assignments if item.user_id != actor.id]
    await db.flush()
    return Outcome(issue.id, notify, "confirmed")


async def reopen(db: AsyncSession, issue_id: int, actor: User) -> Outcome:
    issue, membership = await _require(db, issue_id, actor.id)
    flags = _flags(issue, actor.id, membership)
    if issue.status not in {Status.RESOLVED, Status.CONFIRMED}:
        raise BadTransition
    if not (flags["is_reporter"] or flags["is_owner"]):
        raise NotAllowed
    issue.status = Status.OPEN
    issue.resolved_by_id = None
    issue.resolved_at = None
    issue.confirmed_by_id = None
    issue.confirmed_at = None
    issue.updated_at = utcnow()
    db.add(_event(issue, actor, "reopened", f"Reopened by {person_label(actor)}"))
    notify = [item.user_id for item in issue.assignments if item.user_id != actor.id]
    await db.flush()
    return Outcome(issue.id, notify, "reopened")


async def add_note(db: AsyncSession, issue_id: int, actor: User, body: str) -> Outcome:
    issue, _membership = await _require(db, issue_id, actor.id)
    note = Note(issue_id=issue.id, author_id=actor.id, body=body, created_at=utcnow())
    db.add(note)
    issue.updated_at = utcnow()
    label = person_label(actor)
    db.add(_event(issue, actor, "note", f"Note by {label}"))
    notify = note_recipients(
        reporter_id=issue.reporter_id,
        assignee_ids=[item.user_id for item in issue.assignments],
        actor_id=actor.id,
    )
    await db.flush()
    return Outcome(issue.id, notify, "note")


async def set_assignees(
    db: AsyncSession, issue_id: int, actor: User, user_ids: list[int]
) -> Outcome:
    issue, membership = await _require(db, issue_id, actor.id)
    flags = _flags(issue, actor.id, membership)
    if issue.status == Status.CONFIRMED or not (
        flags["is_owner"] or flags["is_reporter"] or flags["is_assignee"]
    ):
        if issue.status == Status.CONFIRMED:
            raise BadTransition
        raise NotAllowed
    previous = {item.user_id for item in issue.assignments}
    issue.assignments.clear()
    await db.flush()
    labels: list[str] = []
    kept: list[int] = []
    for user_id in dict.fromkeys(user_ids):
        user = await db.get(User, user_id)
        if user is None:
            continue
        member = await db.get(Membership, (issue.project_id, user_id))
        if member is None:
            continue
        db.add(
            Assignment(
                issue_id=issue.id,
                user_id=user_id,
                assigned_by_id=actor.id,
                assigned_at=utcnow(),
            )
        )
        labels.append(person_label(user))
        kept.append(user_id)
    issue.updated_at = utcnow()
    pretty = ", ".join(labels) if labels else "nobody"
    db.add(_event(issue, actor, "assigned", f"Assignees: {pretty}"))
    await db.flush()
    fresh = [user_id for user_id in kept if user_id not in previous and user_id != actor.id]
    return Outcome(issue.id, fresh, "assigned")
