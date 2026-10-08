from datetime import UTC, datetime

from aiogram.enums import ChatType
from aiogram.types import Chat, Message, Update, User

from issuebot.db.session import Database
from issuebot.middlewares import ContextMiddleware


async def test_update_middleware_injects_private_chat_session():
    database = Database("sqlite+aiosqlite://", memory=True)
    await database.create_tables()
    seen: dict = {}

    async def handler(_event, data):
        seen.update(data)

    user = User(id=42, is_bot=False, first_name="Ada", username="ada")
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=42, type=ChatType.PRIVATE),
        from_user=user,
        text="/start",
    )
    update = Update(update_id=1, message=message)
    try:
        await ContextMiddleware(database)(handler, update, {})
    finally:
        await database.engine.dispose()

    assert seen["account"].id == 42
    assert seen["account"].username == "ada"
    assert seen["dialog"].user_id == 42
