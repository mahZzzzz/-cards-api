from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class CardStatus(str, Enum):
    SPEC = "spec"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


# Shared by the card update endpoint and the assistant's move proposals.
ALLOWED_TRANSITIONS = {
    CardStatus.SPEC: {CardStatus.READY},
    CardStatus.READY: {CardStatus.IN_PROGRESS},
    CardStatus.IN_PROGRESS: {CardStatus.REVIEW},
    CardStatus.REVIEW: {CardStatus.DONE},
    CardStatus.DONE: set(),
}


def _validate_assignee(value):
    if value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("Assignee must be a string or null")
    if value.strip() == "":
        raise ValueError("Assignee cannot be empty or whitespace-only")
    return value


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    assignee: str | None = None

    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, value):
        return _validate_assignee(value)


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: CardStatus | None = None
    assignee: str | None = None

    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, value):
        return _validate_assignee(value)


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: CardStatus
    assignee: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class Comment(BaseModel):
    author: str = Field(min_length=1)
    text: str = Field(min_length=1)


class CommentCreate(Comment):
    pass


class CommentRead(Comment):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int


# Backwards/alternative aliases used by callers and tests
CommentIn = CommentCreate
CommentOut = CommentRead
CommentModel = Comment
