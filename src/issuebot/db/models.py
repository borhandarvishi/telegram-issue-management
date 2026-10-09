"""Database tables."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[str | None] = mapped_column(String(128))
    opened_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    channel_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    channel_title: Mapped[str | None] = mapped_column(String(255))
    invite_link: Mapped[str | None] = mapped_column(String(255))
    pinned_message_id: Mapped[int | None] = mapped_column(BigInteger)
    bot_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    next_issue_number: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    owner: Mapped[User] = relationship()
    issues: Mapped[list[Issue]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Membership(Base):
    __tablename__ = "memberships"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), default="member")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped[User] = relationship()
    project: Mapped[Project] = relationship(back_populates="memberships")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (UniqueConstraint("project_id", "number", name="uq_issue_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column()
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True)
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    reopened: Mapped[bool] = mapped_column(Boolean, default=False)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    confirmed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column()
    confirmed_at: Mapped[datetime | None] = mapped_column()
    channel_message_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)

    project: Mapped[Project] = relationship(back_populates="issues")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id])
    confirmed_by: Mapped[User | None] = relationship(foreign_keys=[confirmed_by_id])
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="Note.created_at",
    )
    events: Mapped[list[Event]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="Event.created_at",
    )
    photos: Mapped[list[Photo]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="Photo.position",
    )


class Assignment(Base):
    __tablename__ = "assignments"

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)

    issue: Mapped[Issue] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    issue: Mapped[Issue] = relationship(back_populates="notes")
    author: Mapped[User] = relationship()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    issue: Mapped[Issue] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship()


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(256))
    position: Mapped[int] = mapped_column(default=0)

    issue: Mapped[Issue] = relationship(back_populates="photos")


class Dialog(Base):
    """Where this person is in the bot. One row per Telegram user."""

    __tablename__ = "dialogs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), default="home")
    project_id: Mapped[int | None] = mapped_column()
    issue_id: Mapped[int | None] = mapped_column()
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class Notice(Base):
    """A push message. Kept separate so it never overwrites someone's open screen."""

    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
