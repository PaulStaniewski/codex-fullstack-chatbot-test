from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    progress: Mapped["UserProgress"] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    lesson_progress: Mapped[list["LessonProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    practice_submissions: Mapped[list["PracticeSubmission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation", nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="chat", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    user: Mapped[User] = relationship(back_populates="messages")


class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    sessions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_streak_date: Mapped[date | None] = mapped_column(Date)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="progress")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_value: Mapped[int] = mapped_column(Integer, nullable=False)

    users: Mapped[list["UserAchievement"]] = relationship(
        back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="achievements")
    achievement: Mapped[Achievement] = relationship(back_populates="users")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String(120), nullable=False)
    course_id: Mapped[str] = mapped_column(String(120), nullable=False)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="lesson_progress")


class PracticeSubmission(Base):
    __tablename__ = "practice_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="practice_submissions")
