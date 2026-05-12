from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    id: str
    firebase_uid: str
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = None


class ConversationCreate(BaseModel):
    participant_id: str


class MessageCreate(BaseModel):
    content: str = Field(default="", max_length=5000)
    image_url: str | None = None
    client_id: str | None = None


class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    sender_id: str
    content: str
    image_url: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    sender: UserRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    participants: list[UserRead]
    last_message: MessageRead | None = None


class UploadResponse(BaseModel):
    url: str
    path: str


class WebSocketMessagePayload(BaseModel):
    type: str
    content: str | None = None
    image_url: str | None = None
    is_typing: bool | None = None
    client_id: str | None = None
