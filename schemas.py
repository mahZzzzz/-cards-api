
from pydantic import BaseModel, Field


class CardDraft(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    prd_section: str = Field(min_length=1)
    possible_duplicate: bool = False


class Breakdown(BaseModel):
    cards: list[CardDraft] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
