from sqlalchemy import (
    String,
    Text,
    Integer,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    terms_accepted_at: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))
    bio: Mapped[str] = mapped_column(Text, default="")
    institute: Mapped[str] = mapped_column(String(100), default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    role: Mapped[str] = mapped_column(String(20), default="student")
    is_blocked: Mapped[bool] = mapped_column(default=False)
    block_reason: Mapped[str] = mapped_column(Text, default="")


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[int] = mapped_column(Integer)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60))
    format: Mapped[str] = mapped_column(String(20))
    skills: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    moderation_note: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(default=False)
    recruitment_open: Mapped[bool] = mapped_column(default=True)
    team_contact: Mapped[str] = mapped_column(String(500), default="")


class Vacancy(Base):
    __tablename__ = "vacancies"
    __table_args__ = (CheckConstraint("capacity > 0 AND capacity <= 30"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(100))
    requirements: Mapped[str] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "vacancy_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[int] = mapped_column(Integer)
    resolved_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ModerationEvent(Base):
    __tablename__ = "moderation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    moderator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("reports.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(Integer)
