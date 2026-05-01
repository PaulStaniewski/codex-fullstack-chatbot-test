from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic import field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must include at least one letter and one number.")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationModeUpdate(BaseModel):
    mode: str


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    mode: str
    is_pinned: bool
    user_id: int
    created_at: datetime


class MessageCreate(BaseModel):
    conversation_id: int
    content: str = Field(min_length=1)
    role: str = Field(default="user", max_length=50)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    created_at: datetime


class AchievementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    icon: str
    condition_type: str
    condition_value: int
    earned_at: datetime | None = None


class BadgeRead(BaseModel):
    id: int
    key: str
    title: str
    description: str
    icon: str
    condition_type: str
    condition_value: int
    earned: bool
    earned_at: datetime | None = None


class UserProgressStats(BaseModel):
    sessions_count: int
    messages_count: int
    lessons_completed: int
    correct_answers: int
    incorrect_answers: int
    time_spent_seconds: int
    xp_points: int
    level: int
    total_xp: int
    xp_into_level: int
    xp_required_for_next_level: int
    progress_percent: float
    current_streak_days: int
    last_streak_date: date | None
    last_activity_at: datetime | None


class UserProgressRead(UserProgressStats):
    achievements: list[AchievementRead]


class ProgressResponse(BaseModel):
    progress: UserProgressStats
    achievements: list[AchievementRead]
    badges: list[BadgeRead]
    new_achievements: list[AchievementRead]


class ProgressActivityRequest(BaseModel):
    active_seconds: int = Field(ge=1, le=300)


class LessonStepRead(BaseModel):
    type: str
    title: str
    content: str
    difficulty: str | None = None
    completed: bool = False
    completed_at: datetime | None = None
    xp_awarded: int = 0


class LessonProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson_id: str
    course_id: str
    current_step_index: int
    completed: bool
    completed_at: datetime | None = None


class LessonRead(LessonProgressRead):
    title: str
    difficulty: str | None = None
    steps: list[LessonStepRead]


class PracticeSubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: str
    step_index: int
    attempt_number: int
    answer: str
    feedback: str
    score: int | None = None
    strengths: list[str] | None = None
    improvements: list[str] | None = None
    created_at: datetime
