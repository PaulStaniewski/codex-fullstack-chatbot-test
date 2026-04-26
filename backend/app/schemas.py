from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


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
