"""Projects and the channel each one publishes into."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.constants import Role, Screen
from issuebot.db.models import Dialog, Membership, Project, User, utcnow


async def create_project(db: AsyncSession, owner: User, name: str) -> Project:
    project = Project(
        public_id=secrets.token_hex(6),
        name=name,
        owner_id=owner.id,
        next_issue_number=0,
        bot_admin=False,
    )
    db.add(project)
    await db.flush()
    db.add(
        Membership(
            project_id=project.id,
            user_id=owner.id,
            role=Role.OWNER,
            active=True,
            joined_at=utcnow(),
        )
    )
    await db.flush()
    return project


async def get_project(db: AsyncSession, project_id: int | None) -> Project | None:
    if not project_id:
        return None
    return await db.get(Project, project_id)


async def by_public_id(db: AsyncSession, public_id: str) -> Project | None:
    stmt = select(Project).where(Project.public_id == public_id)
    return await db.scalar(stmt)


async def by_channel(db: AsyncSession, channel_id: int) -> Project | None:
    stmt = select(Project).where(Project.channel_id == channel_id)
    return await db.scalar(stmt)


def attach_channel(
    project: Project,
    *,
    channel_id: int,
    channel_title: str | None,
    invite_link: str,
) -> None:
    project.channel_id = channel_id
    project.channel_title = channel_title
    project.invite_link = invite_link
    project.bot_admin = True


class NotOwner(Exception):
    pass


@dataclass(frozen=True)
class RemovedProject:
    name: str
    member_ids: tuple[int, ...]
    channel_id: int | None
    invite_link: str | None


async def remove_project(db: AsyncSession, project_id: int, actor_id: int) -> RemovedProject:
    """Delete a project for every member. Only the person who created it may do this."""
    project = await get_project(db, project_id)
    if project is None or project.owner_id != actor_id:
        raise NotOwner
    member_ids = tuple(
        await db.scalars(select(Membership.user_id).where(Membership.project_id == project.id))
    )
    dialogs = list(await db.scalars(select(Dialog).where(Dialog.project_id == project.id)))
    for dialog in dialogs:
        dialog.state = Screen.HOME
        dialog.project_id = None
        dialog.issue_id = None
        dialog.payload = {}
    removed = RemovedProject(
        name=project.name,
        member_ids=member_ids,
        channel_id=project.channel_id,
        invite_link=project.invite_link,
    )
    await db.delete(project)
    await db.flush()
    return removed


def start_link(username: str, public_id: str) -> str:
    return f"https://t.me/{username}?start=p{public_id}"
