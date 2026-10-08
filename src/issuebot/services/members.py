"""Who belongs to a project."""

from __future__ import annotations

from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from issuebot.constants import Role
from issuebot.db.models import Membership, utcnow
from issuebot.formatting import format_person
from issuebot.services.accounts import upsert_user


async def get_membership(db: AsyncSession, project_id: int, user_id: int) -> Membership | None:
    return await db.get(Membership, (project_id, user_id))


async def ensure_member(
    db: AsyncSession,
    project_id: int,
    tg: TgUser,
    *,
    active: bool = True,
    opened_bot: bool = False,
) -> Membership:
    user = await upsert_user(db, tg, opened_bot=opened_bot)
    row = await get_membership(db, project_id, user.id)
    if row is None:
        row = Membership(
            project_id=project_id,
            user_id=user.id,
            role=Role.MEMBER,
            active=active,
            joined_at=utcnow(),
        )
        db.add(row)
    else:
        row.active = active or row.role == Role.OWNER
    await db.flush()
    return row


async def activate_user(
    db: AsyncSession, project_id: int, user_id: int, *, active: bool = True
) -> Membership:
    row = await get_membership(db, project_id, user_id)
    if row is None:
        row = Membership(
            project_id=project_id,
            user_id=user_id,
            role=Role.MEMBER,
            active=active,
            joined_at=utcnow(),
        )
        db.add(row)
    elif active:
        row.active = True
    await db.flush()
    return row


async def set_active(db: AsyncSession, project_id: int, user_id: int, active: bool) -> None:
    row = await get_membership(db, project_id, user_id)
    if row is None or row.role == Role.OWNER:
        return
    row.active = active


async def roster(db: AsyncSession, project_id: int) -> list[Membership]:
    stmt = (
        select(Membership)
        .where(Membership.project_id == project_id)
        .where((Membership.active.is_(True)) | (Membership.role == Role.OWNER))
        .options(selectinload(Membership.user))
        .order_by(Membership.joined_at)
    )
    rows = list(await db.scalars(stmt))
    def _sort_key(row: Membership) -> tuple[bool, str]:
        person = format_person(row.user.username, row.user.first_name, row.user.last_name)
        return (row.role != Role.OWNER, person)

    rows.sort(key=_sort_key)
    return rows


async def member_ids(db: AsyncSession, project_id: int) -> set[int]:
    rows = await roster(db, project_id)
    return {row.user_id for row in rows}
