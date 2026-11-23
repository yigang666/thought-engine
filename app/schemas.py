"""Typed contracts for conversations and Thought Maps.

Field meanings follow PROJECT_REQUIREMENTS v1.1. Article and publishing
records are intentionally absent in this phase.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"
PROMPT_VERSION = "phase0-extract-1"


class Speaker(str, Enum):
    user = "user"
    assistant = "assistant"
    unknown = "unknown"


class Origin(str, Enum):
    user_original = "user_original"
    ai_suggestion = "ai_suggestion"
    user_adopted = "user_adopted"
    jointly_developed = "jointly_developed"
    inferred = "inferred"
    uncertain = "uncertain"


class ThoughtType(str, Enum):
    thesis = "thesis"
    argument = "argument"
    reasoning = "reasoning"
    example = "example"
    assumption = "assumption"
    conclusion = "conclusion"
    question = "question"
    counterargument = "counterargument"


class ReviewStatus(str, Enum):
    pending = "pending"
    in_review = "in_review"
    confirmed = "confirmed"


ORIGIN_LABELS = {
    Origin.user_original: "User original",
    Origin.ai_suggestion: "AI suggestion",
    Origin.user_adopted: "User adopted",
    Origin.jointly_developed: "Jointly developed",
    Origin.inferred: "Inferred",
    Origin.uncertain: "Uncertain",
}

TYPE_LABELS = {
    ThoughtType.thesis: "Thesis",
    ThoughtType.argument: "Argument",
    ThoughtType.reasoning: "Reasoning",
    ThoughtType.example: "Example",
    ThoughtType.assumption: "Assumption",
    ThoughtType.conclusion: "Conclusion",
    ThoughtType.question: "Open question",
    ThoughtType.counterargument: "Counterargument",
}

TYPE_ORDER = list(TYPE_LABELS)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str
    sequence: int = Field(ge=1)
    speaker: Speaker
    speaker_label: str
    content: str = Field(min_length=1)
    timestamp: Optional[str] = None
    speaker_confidence: float = Field(ge=0, le=1)
    speaker_uncertain: bool = False


class Conversation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    title: str = Field(min_length=1, max_length=200)
    source_type: Literal["paste", "markdown"]
    created_at: datetime
    original_text: str
    messages: list[Message]
    parse_warnings: list[str] = Field(default_factory=list)


class ThoughtItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    type: ThoughtType
    content: str = Field(min_length=1, max_length=20000)
    origin: Origin
    source_message_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    user_confirmed: bool = False
    notes: str = ""
    origin_set_by: Literal["extraction", "user"] = "extraction"
    model_origin: Optional[Origin] = None


class ReasoningStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1)
    description: str = Field(min_length=1)
    depends_on: list[int] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)


class ThoughtMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thought_map_id: str
    conversation_id: str
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    central_question: str = Field(default="", max_length=4000)
    main_thesis: str = Field(default="", max_length=8000)
    thought_items: list[ThoughtItem] = Field(default_factory=list)
    reasoning_chain: list[ReasoningStep] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.pending
    created_at: datetime
    updated_at: datetime
    system_adjustments: list[str] = Field(default_factory=list)
    prompt_version: str = ""
    provider: str = ""
    model: str = ""
