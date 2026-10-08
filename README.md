# Telegram Issue Bot

A small Telegram bot for teams that want to report a problem, hand it to someone, and follow it until the reporter confirms it is fixed.

Each project is one private channel. The bot posts a single card per issue. When the status changes, that card is deleted and a new one is sent. Inside the private chat, buttons stay under the keyboard, and the bot keeps one screen: it sends the next message, then deletes the previous one.

The interface is English.

## What a team can do

- Create a project and connect it to a private channel.
- Delete a project you created. It disappears from every member's list.
- Remove a member from a project you created. They are also removed from the channel.
- Share one invite link. Regenerating the link revokes the previous one.
- Report an issue with a title, a description (links included), and up to 10 photos.
- See who is in the project and assign one or more people.
- Read the issue as `ISSUE #12` in the bot, in the channel, and in notifications.
- Mark it resolved, confirm the fix, or reopen it.
- Add notes. Notes are kept on the issue and copied onto the channel card.
- Open **My work** and see what is waiting: issues assigned to you, and reports that need your confirmation.

People are shown as `@username (Name)`. An account without a public username is shown by name only.

## Status

```
open  →  resolved  →  confirmed
           ↑            │
           └────────────┘
              reopen
```

- An assignee, or the project owner, marks an open issue resolved.
- The reporter confirms it, or sends it back.
- The reporter or the owner can reopen a confirmed issue.

## Run it

Telegram does not let a bot create a channel, and it cannot read a private invite link. The owner creates a private channel, then taps **Choose channel** while that project is open. Telegram lists the owner's channels and adds the bot as admin on the spot. The channel is linked only to the project on screen.

1. Talk to [@BotFather](https://t.me/BotFather), create a bot, and copy the token.
2. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

3. Put the token in `.env`:

```
TELEGRAM_BOT_TOKEN=123456:your-token
DATABASE_URL=sqlite+aiosqlite:///./data/issuebot.db
```

4. Start one instance:

```bash
python -m issuebot
```

Docker:

```bash
docker compose up --build
```

Run a single process. Two pollers on the same token will fight over updates.

## Using it

1. `/start`, then **New project**. Send the project name.
2. Create a **private** channel. Add this bot as an admin with permission to invite people, post, and delete messages. Use the same Telegram account that created the project.
3. The bot replies with the channel invite and a link that opens the bot.
4. Send the channel invite to the team. After they join, they open the bot from the pinned channel message (or from the bot link).
5. **Report issue** walks through title, description, photos, and assignees.
6. The assignee gets `ISSUE #12` in the bot. They open **My work**, then **Resolved**.
7. The reporter gets a notification, opens the same issue, and confirms or reopens it.

**New link** revokes the current invite and creates another one. Older links stop working only when the channel is private.

## Layout

| Path | What lives there |
| --- | --- |
| `src/issuebot/texts.py` | Every sentence the bot sends |
| `src/issuebot/constants.py` | Button labels, screens, limits |
| `src/issuebot/services/rules.py` | Who can change an issue, and who is notified |
| `src/issuebot/services/issues.py` | Issue records and status changes |
| `src/issuebot/services/publish.py` | Delete-and-send for the channel card |
| `src/issuebot/handlers/` | Screens and button routing |
| `src/issuebot/messaging.py` | The single private-chat screen |

Change the copy in `texts.py`. Change permissions in `rules.py`. The handlers should stay thin.

## Tests

```bash
pytest
```

## Limits worth knowing

- A bot cannot create a channel. Connecting one is a one-time step.
- The bot learns who is in the channel from joins after it is an admin, from channel admins, and from people who open the bot. It cannot list every existing subscriber.
- The bot can message a person only after that person has started it. Until then, their name is marked and assignment does not reach them.
- The bot can delete its own messages in a private chat. It cannot delete the texts a person sends, so those stay in the history.
- One photo with a short card is a single channel message. A long report, or several photos, is the card plus the photos beside it. Status changes always replace that card. Nothing is edited.

## License

MIT. See [LICENSE](LICENSE).
