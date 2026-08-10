from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    billing = "billing"
    technical = "technical"
    complaint = "complaint"
    question = "question"
    abuse = "abuse"
    spam = "spam"
    other = "other"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Message(BaseModel):
    id: str
    text: str


class TriageResult(BaseModel):
    id: str
    category: Category
    priority: Priority
    summary: str = Field(max_length=400)
    suggested_action: str = Field(max_length=400)
    needs_human: bool
    confidence: float = Field(ge=0.0, le=1.0)

    # diagnostics, not part of the model's judgement but useful for the UI/eval
    flags: list[str] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    error: Optional[str] = None

    @field_validator("summary", "suggested_action")
    @classmethod
    def not_empty(cls, v: str) -> str:
        return v.strip() or "unknown"
