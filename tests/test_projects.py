import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.constants import Screen
from issuebot.db.models import Assignment, Dialog, Membership, User
from issuebot.db.session import Database
from issuebot.services.accounts import projects_for
from issuebot.services.issues import create_issue, get_issue
from issuebot.services.members import CannotRemove, drop_member, get_membership
from issuebot.services.projects import NotOwner, create_project, get_project, remove_project


@pytest.fixture
async def db() -> AsyncSession:
    database = Database("sqlite+aiosqlite://", memory=True)
    await database.create_tables()
    try:
        async with database.session() as session:
            yield session
            await session.commit()
    finally:
        await database.engine.dispose()


async def _user(db: AsyncSession, user_id: int, username: str) -> User:
    user = User(id=user_id, username=username, first_name=username, opened_bot=True)
    db.add(user)
    await db.flush()
    return user


async def test_only_the_creator_can_delete_and_it_leaves_every_list(db: AsyncSession):
    owner = await _user(db, 1, "owner")
    member = await _user(db, 2, "member")
    project = await create_project(db, owner, "Shop")
    db.add(
        Membership(
            project_id=project.id,
            user_id=member.id,
            role="member",
            active=True,
        )
    )
    db.add(
        Dialog(
            user_id=member.id,
            state=Screen.PROJECT,
            project_id=project.id,
            issue_id=None,
            payload={"labels": {}},
        )
    )
    issue = await create_issue(
        db,
        project=project,
        reporter=member,
        title="Login fails",
        description="Blank page",
        photos=[],
        assignee_ids=[],
    )
    await db.flush()

    with pytest.raises(NotOwner):
        await remove_project(db, project.id, member.id)

    removed = await remove_project(db, project.id, owner.id)
    assert removed.name == "Shop"
    assert set(removed.member_ids) == {owner.id, member.id}
    assert await get_project(db, project.id) is None
    assert await get_issue(db, issue.id) is None
    assert await projects_for(db, owner.id) == []
    assert await projects_for(db, member.id) == []
    dialog = await db.get(Dialog, member.id)
    assert dialog is not None
    assert dialog.project_id is None
    assert dialog.state == Screen.HOME


async def test_owner_can_remove_a_member_but_not_themselves(db: AsyncSession):
    owner = await _user(db, 1, "owner")
    member = await _user(db, 2, "member")
    project = await create_project(db, owner, "Shop")
    db.add(Membership(project_id=project.id, user_id=member.id, role="member", active=True))
    db.add(
        Dialog(
            user_id=member.id,
            state=Screen.PROJECT,
            project_id=project.id,
            payload={},
        )
    )
    issue = await create_issue(
        db,
        project=project,
        reporter=owner,
        title="Login fails",
        description="Blank page",
        photos=[],
        assignee_ids=[member.id],
    )
    await db.flush()

    with pytest.raises(CannotRemove):
        await drop_member(db, project.id, member.id, owner.id)
    with pytest.raises(CannotRemove):
        await drop_member(db, project.id, owner.id, owner.id)

    await drop_member(db, project.id, owner.id, member.id)
    assert await get_membership(db, project.id, member.id) is None
    assert await projects_for(db, member.id) == []
    assert await db.get(Assignment, (issue.id, member.id)) is None
    dialog = await db.get(Dialog, member.id)
    assert dialog is not None
    assert dialog.project_id is None
