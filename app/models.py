from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class CardStatus(str, Enum):
    SPEC = "spec"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class CardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: CardStatus | None = None


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: CardStatus


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
