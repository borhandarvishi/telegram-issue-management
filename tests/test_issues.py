from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from issuebot.constants import Status
from issuebot.db.models import User
from issuebot.db.session import Database
from issuebot.services.issues import (
    BadTransition,
    NotAllowed,
    add_note,
    confirm,
    create_issue,
    get_issue,
    mark_resolved,
    reopen,
    to_card,
)
from issuebot.services.projects import create_project


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


async def _user(db: AsyncSession, user_id: int, username: str, first: str) -> User:
    user = User(id=user_id, username=username, first_name=first, opened_bot=True)
    db.add(user)
    await db.flush()
    return user


async def test_issue_numbers_and_status_flow(db: AsyncSession):
    owner = await _user(db, 1, "owner", "Owner")
    reporter = await _user(db, 2, "sara", "Sara")
    assignee = await _user(db, 3, "ali", "Ali")
    project = await create_project(db, owner, "Shop")
    from issuebot.services.members import activate_user

    await activate_user(db, project.id, reporter.id)
    await activate_user(db, project.id, assignee.id)

    first = await create_issue(
        db,
        project=project,
        reporter=reporter,
        title="Login fails",
        description="Blank page",
        photos=["file-a"],
        assignee_ids=[assignee.id],
    )
    second = await create_issue(
        db,
        project=project,
        reporter=reporter,
        title="Checkout",
        description="Payment failed",
        photos=[],
        assignee_ids=[],
    )
    assert first.number == 1
    assert second.number == 2

    with pytest.raises(NotAllowed):
        await mark_resolved(db, first.id, reporter)

    resolved = await mark_resolved(db, first.id, assignee)
    assert resolved.notify_ids == [reporter.id]
    with pytest.raises(BadTransition):
        await mark_resolved(db, first.id, assignee)

    with pytest.raises(NotAllowed):
        await confirm(db, first.id, assignee)

    confirmed = await confirm(db, first.id, reporter)
    assert assignee.id in confirmed.notify_ids
    fresh = await get_issue(db, first.id)
    assert fresh is not None
    assert fresh.status == Status.CONFIRMED
    card = to_card(fresh)
    assert card.solver == "@ali (Ali)"
    assert card.confirmer == "@sara (Sara)"
    assert card.timeline[-1].startswith("Confirmed by")

    reopened = await reopen(db, first.id, reporter)
    assert assignee.id in reopened.notify_ids
    again = await get_issue(db, first.id)
    assert again is not None
    assert again.status == Status.OPEN
    assert again.resolved_by_id is None

    note = await add_note(db, first.id, assignee, "Checked again")
    assert reporter.id in note.notify_ids
    noted = await get_issue(db, first.id)
    assert noted is not None
    assert noted.notes[-1].body == "Checked again"


async def test_republish_sends_then_deletes_and_never_edits():
    from issuebot.services.publish import republish

    class FakeBot:
        def __init__(self):
            self.sent = []
            self.deleted = []
            self.edited = []
            self._next = 10

        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append(("message", text, kwargs))
            self._next += 1
            return SimpleNamespace(message_id=self._next)

        async def send_photo(self, chat_id, photo, **kwargs):
            self.sent.append(("photo", photo, kwargs.get("caption")))
            self._next += 1
            return SimpleNamespace(message_id=self._next)

        async def send_media_group(self, chat_id, media, **kwargs):
            messages = []
            for item in media:
                self._next += 1
                messages.append(SimpleNamespace(message_id=self._next))
            self.sent.append(("album", [item.caption for item in media]))
            return messages

        async def delete_message(self, chat_id, message_id):
            self.deleted.append(message_id)

        async def edit_message_text(self, *args, **kwargs):
            self.edited.append(args)

    bot = FakeBot()
    ids = await republish(
        bot,
        -100,
        old_ids=[1, 2],
        text="ISSUE #4\n\n#4",
        photo_ids=[],
        silent=False,
    )
    assert ids
    assert bot.deleted == [1, 2]
    assert bot.edited == []
    assert bot.sent[0][0] == "message"

    photo_bot = FakeBot()
    await republish(
        photo_bot,
        -100,
        old_ids=[],
        text="short",
        photo_ids=["abc"],
        silent=False,
    )
    assert photo_bot.sent[0][0] == "photo"
    assert photo_bot.sent[0][2] == "short"
    assert photo_bot.edited == []

    album_bot = FakeBot()
    ids = await republish(
        album_bot,
        -100,
        old_ids=[4],
        text="ISSUE #5",
        photo_ids=["one", "two"],
        silent=True,
    )
    assert album_bot.sent[0][0] == "album"
    assert album_bot.sent[0][1] == ["ISSUE #5", None]
    assert len(ids) == 2
    assert album_bot.deleted == [4]
    assert all(item[0] != "message" for item in album_bot.sent)
