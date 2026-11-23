"""Turn a parsed conversation into a Thought Map with one LLM call."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.attribution import adjust_extracted_items
from app.llm import LLMAdapter
from app.schemas import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    Conversation,
    Origin,
    ReasoningStep,
    ThoughtItem,
    ThoughtMap,
    ThoughtType,
)

class SchemaError(ValueError):
    """The model JSON does not satisfy the Thought Map contract."""


ORIGIN_ALIASES = {
    "user_original": Origin.user_original,
    "ai_suggestion": Origin.ai_suggestion,
    "ai_suggested": Origin.ai_suggestion,
    "assistant_suggestion": Origin.ai_suggestion,
    "suggestion": Origin.ai_suggestion,
    "ai": Origin.ai_suggestion,
    "user_adopted": Origin.user_adopted,
    "adopted": Origin.user_adopted,
    "jointly_developed": Origin.jointly_developed,
    "joint": Origin.jointly_developed,
    "jointly": Origin.jointly_developed,
    "inferred": Origin.inferred,
    "inference": Origin.inferred,
    "uncertain": Origin.uncertain,
    "unknown": Origin.uncertain,
    "ambiguous": Origin.uncertain,
}

TYPE_ALIASES = {
    "thesis": ThoughtType.thesis,
    "argument": ThoughtType.argument,
    "reasoning": ThoughtType.reasoning,
    "reason": ThoughtType.reasoning,
    "example": ThoughtType.example,
    "assumption": ThoughtType.assumption,
    "conclusion": ThoughtType.conclusion,
    "question": ThoughtType.question,
    "open_question": ThoughtType.question,
    "counterargument": ThoughtType.counterargument,
    "counter_argument": ThoughtType.counterargument,
    "objection": ThoughtType.counterargument,
}

SYSTEM_PROMPT = """You extract a Thought Map from a conversation between a user and an assistant.

Return one JSON object and nothing else. Do not invent positions, facts, or certainty.

Attribution:
- user_original: the user explicitly expressed this idea.
- ai_suggestion: the assistant introduced this idea and the user has not clearly adopted it.
- user_adopted: the user explicitly agreed with, adopted, or meaningfully developed an assistant suggestion.
- jointly_developed: the idea emerged through back-and-forth and cannot be attributed to only one speaker.
- inferred: you inferred this. The user did not say it. Do not present it as their belief.
- uncertain: the speaker or the meaning is ambiguous.

Never label an assistant idea as user_original.
Never label a user idea as ai_suggestion.
If speaker_uncertain is true, do not use user_original for that message.
Use only message ids from the conversation.
Prefer empty arrays over filler.
If the user never stated a thesis, say so in main_thesis and do not invent one.
Include assumptions, reasoning steps, conclusions, and open questions when the conversation contains them.
Every thought item needs type, content, origin, and source_message_ids.
"""


def build_user_prompt(conversation: Conversation) -> str:
    lines = [f"Title: {conversation.title}", "", "Messages:"]
    for message in conversation.messages:
        lines.append(
            f"- id={message.message_id} speaker={message.speaker.value} "
            f"speaker_uncertain={str(message.speaker_uncertain).lower()} "
            f"label={message.speaker_label}"
        )
        lines.append(message.content)
        lines.append("")
    lines.append(
        "JSON shape: {"
        '"central_question": string, '
        '"main_thesis": string, '
        '"thought_items": [{"type": "thesis|argument|reasoning|example|assumption|conclusion|question|counterargument", '
        '"content": string, '
        '"origin": "user_original|ai_suggestion|user_adopted|jointly_developed|inferred|uncertain", '
        '"source_message_ids": [string], "confidence": number from 0 to 1, "notes": string}], '
        '"reasoning_chain": [{"step": number, "description": string, "depends_on": [number], "source_message_ids": [string]}], '
        '"open_questions": [string], '
        '"contradictions": [string]'
        "}"
    )
    return "\n".join(lines)


def extract_thought_map(conversation: Conversation, adapter: LLMAdapter) -> ThoughtMap:
    user_prompt = build_user_prompt(conversation)
    last_error = "The model returned an unusable Thought Map."
    for attempt in range(2):
        prompt = user_prompt
        if attempt:
            prompt += (
                "\n\nThe previous JSON failed validation:\n"
                + last_error
                + "\nReturn corrected JSON only."
            )
        payload = adapter.complete_json(system=SYSTEM_PROMPT, user=prompt)
        try:
            return parse_llm_payload(
                payload,
                conversation,
                provider=adapter.name,
                model=adapter.model,
            )
        except SchemaError as exc:
            last_error = str(exc)
    raise SchemaError(last_error)


def parse_llm_payload(
    payload: object,
    conversation: Conversation,
    *,
    provider: str,
    model: str,
) -> ThoughtMap:
    if not isinstance(payload, dict):
        raise SchemaError("The model did not return a JSON object.")
    raw_items = payload.get("thought_items", [])
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        raise SchemaError("thought_items must be a list.")
    if len(raw_items) > 100:
        raise SchemaError("thought_items has more than 100 entries.")

    items: list[ThoughtItem] = []
    for raw in raw_items:
        items.append(_item_from_payload(raw))
    adjusted, notes = adjust_extracted_items(items, conversation.messages)
    now = datetime.now(timezone.utc)
    try:
        thought_map = ThoughtMap(
            thought_map_id=str(uuid.uuid4()),
            conversation_id=conversation.conversation_id,
            schema_version=SCHEMA_VERSION,
            central_question=_optional_text(payload.get("central_question")),
            main_thesis=_optional_text(payload.get("main_thesis")),
            thought_items=adjusted,
            reasoning_chain=_reasoning(payload.get("reasoning_chain")),
            open_questions=_string_list(payload.get("open_questions"), "open_questions"),
            contradictions=_string_list(payload.get("contradictions"), "contradictions"),
            review_status="pending",
            created_at=now,
            updated_at=now,
            system_adjustments=notes,
            prompt_version=PROMPT_VERSION,
            provider=provider,
            model=model,
        )
    except ValidationError as exc:
        raise SchemaError(f"Thought Map schema validation failed: {exc}") from exc
    if not thought_map.thought_items and not thought_map.central_question and not thought_map.main_thesis:
        thought_map.system_adjustments.append(
            "Extraction returned no thought items, thesis, or central question."
        )
    return thought_map


def _item_from_payload(raw: object) -> ThoughtItem:
    if not isinstance(raw, dict):
        raise SchemaError("Each thought item must be an object.")
    if raw.get("origin") in (None, ""):
        raise SchemaError(
            "Every thought item needs an origin. Missing origins are not treated as user original."
        )
    if raw.get("type") in (None, ""):
        raise SchemaError("Every thought item needs a type.")
    content = str(raw.get("content", "")).strip()
    if not content:
        raise SchemaError("A thought item has empty content.")
    confidence = raw.get("confidence", 0.5)
    if confidence is None or confidence == "":
        confidence = 0.5
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise SchemaError("confidence must be a number from 0 to 1.") from exc
    if confidence_value < 0 or confidence_value > 1:
        raise SchemaError("confidence must be a number from 0 to 1.")
    sources = raw.get("source_message_ids") or []
    if not isinstance(sources, list) or not all(isinstance(source, str) for source in sources):
        raise SchemaError("source_message_ids must be a list of message ids.")
    try:
        return ThoughtItem(
            item_id=str(uuid.uuid4()),
            type=_thought_type(raw.get("type")),
            content=content,
            origin=_origin(raw.get("origin")),
            source_message_ids=list(sources),
            confidence=confidence_value,
            notes=str(raw.get("notes") or "").strip(),
            origin_set_by="extraction",
        )
    except ValidationError as exc:
        raise SchemaError(f"Thought item schema validation failed: {exc}") from exc


def _origin(value: object) -> Origin:
    key = _alias_key(value)
    if key not in ORIGIN_ALIASES:
        raise SchemaError(
            f"Origin {value!r} is not allowed. Use user_original, ai_suggestion, "
            "user_adopted, jointly_developed, inferred, or uncertain. "
            "The word user is not treated as user_original."
        )
    return ORIGIN_ALIASES[key]


def _thought_type(value: object) -> ThoughtType:
    key = _alias_key(value)
    if key not in TYPE_ALIASES:
        raise SchemaError(f"Thought type {value!r} is not allowed.")
    return TYPE_ALIASES[key]


def _alias_key(value: object) -> str:
    return str(value).strip().lower().replace("-", " ").replace(" ", "_")


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _string_list(value: object, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SchemaError(f"{field_name} must be a list of strings.")
    result = [str(item).strip() for item in value if str(item).strip()]
    return result[:50]


def _reasoning(value: object) -> list[ReasoningStep]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SchemaError("reasoning_chain must be a list.")
    steps: list[ReasoningStep] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise SchemaError("Each reasoning step must be an object.")
        description = str(raw.get("description") or "").strip()
        if not description:
            continue
        depends = raw.get("depends_on") or []
        if not isinstance(depends, list) or not all(isinstance(step, int) for step in depends):
            raise SchemaError("depends_on must be a list of step numbers.")
        sources = raw.get("source_message_ids") or []
        if not isinstance(sources, list) or not all(isinstance(source, str) for source in sources):
            raise SchemaError("reasoning source_message_ids must be a list of message ids.")
        step_number = raw.get("step", index)
        if not isinstance(step_number, int) or step_number < 1:
            step_number = index
        try:
            steps.append(
                ReasoningStep(
                    step=step_number,
                    description=description,
                    depends_on=list(depends),
                    source_message_ids=list(sources),
                )
            )
        except ValidationError as exc:
            raise SchemaError(f"Reasoning step schema validation failed: {exc}") from exc
    return steps
