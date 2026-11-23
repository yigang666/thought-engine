from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.extraction import SchemaError, extract_thought_map, parse_llm_payload
from app.schemas import Conversation, Message, Origin, ThoughtItem, ThoughtMap, ThoughtType

NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


def message(message_id="m1", speaker="user", content="Hello", uncertain=False):
    return Message(
        message_id=message_id,
        sequence=1,
        speaker=speaker,
        speaker_label=speaker,
        content=content,
        speaker_confidence=0.2 if uncertain or speaker == "unknown" else 0.96,
        speaker_uncertain=uncertain,
    )


def conversation(messages=None):
    return Conversation(
        conversation_id="c1",
        title="Notes",
        source_type="paste",
        created_at=NOW,
        original_text="User: Hello",
        messages=messages or [message()],
    )


def thought_item(**overrides):
    data = {
        "item_id": "i1",
        "type": "argument",
        "content": "A thought",
        "origin": "user_original",
        "source_message_ids": ["m1"],
        "confidence": 0.8,
    }
    data.update(overrides)
    return ThoughtItem(**data)


def thought_map(**overrides):
    data = {
        "thought_map_id": "t1",
        "conversation_id": "c1",
        "central_question": "What should wait?",
        "main_thesis": "Confirmation comes first.",
        "thought_items": [thought_item()],
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return ThoughtMap(**data)


def test_valid_thought_map_round_trip():
    original = thought_map(
        reasoning_chain=[{"step": 1, "description": "The user stated the limit."}],
        open_questions=["How strict is confirmation?"],
    )
    restored = ThoughtMap.model_validate(original.model_dump(mode="json"))
    assert restored.schema_version == "1.0"
    assert restored.thought_items[0].origin == Origin.user_original
    assert restored.thought_items[0].type == ThoughtType.argument
    assert restored.open_questions == ["How strict is confirmation?"]


def test_schema_rejects_unknown_origin_speaker_and_extra_article_fields():
    with pytest.raises(ValidationError):
        thought_item(origin="assistant")
    with pytest.raises(ValidationError):
        message(speaker="narrator")
    with pytest.raises(ValidationError):
        thought_item(confidence=1.2)
    with pytest.raises(ValidationError):
        thought_item(content="")
    payload = thought_map().model_dump()
    payload["content_markdown"] = "An article does not belong on a Thought Map."
    with pytest.raises(ValidationError):
        ThoughtMap.model_validate(payload)
    payload = thought_map().model_dump()
    payload["schema_version"] = "9.0"
    with pytest.raises(ValidationError):
        ThoughtMap.model_validate(payload)


def test_missing_origin_is_not_defaulted_to_user_original():
    with pytest.raises(SchemaError, match="not treated as user original"):
        parse_llm_payload(
            {"thought_items": [{"type": "thesis", "content": "Ship it."}]},
            conversation(),
            provider="fake",
            model="fake-1",
        )


def test_bare_user_label_is_not_user_original():
    with pytest.raises(SchemaError, match="not treated as user_original"):
        parse_llm_payload(
            {
                "thought_items": [
                    {
                        "type": "thesis",
                        "content": "Ship it.",
                        "origin": "user",
                        "source_message_ids": ["m1"],
                    }
                ]
            },
            conversation(),
            provider="fake",
            model="fake-1",
        )


def test_schema_failure_retries_once_then_accepts_valid_json():
    class Flaky:
        name = "fake"
        model = "fake-1"

        def __init__(self):
            self.prompts = []

        def complete_json(self, *, system, user):
            self.prompts.append(user)
            if len(self.prompts) == 1:
                return {"thought_items": [{"content": "Missing origin"}]}
            return {
                "central_question": "What comes first?",
                "main_thesis": "The user did not state a thesis.",
                "thought_items": [],
            }

    adapter = Flaky()
    result = extract_thought_map(conversation(), adapter)
    assert adapter.prompts[1] != adapter.prompts[0]
    assert "origin" in adapter.prompts[1]
    assert result.central_question == "What comes first?"
    assert result.review_status.value == "pending"
    assert result.prompt_version == "phase0-extract-1"


def test_two_schema_failures_raise():
    class AlwaysBad:
        name = "fake"
        model = "fake-1"

        def complete_json(self, *, system, user):
            return {"thought_items": [{"content": "No origin"}]}

    with pytest.raises(SchemaError):
        extract_thought_map(conversation(), AlwaysBad())
