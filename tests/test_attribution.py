import pytest

from app.attribution import adjust_extracted_items, validate_user_item
from app.schemas import Message, Origin, ThoughtItem

SHAPES = {
    "none": [],
    "user": ["user"],
    "assistant": ["assistant"],
    "both": ["user", "assistant"],
    "unknown": ["unknown"],
}


def message(message_id, speaker, uncertain=False):
    return Message(
        message_id=message_id,
        sequence=1,
        speaker=speaker,
        speaker_label=speaker,
        content=f"{speaker} message",
        speaker_confidence=0.2 if uncertain or speaker == "unknown" else 0.96,
        speaker_uncertain=uncertain or speaker == "unknown",
    )


def item(origin, source_ids, confidence=0.9, content="A claim"):
    return ThoughtItem(
        item_id="i1",
        type="argument",
        content=content,
        origin=origin,
        source_message_ids=source_ids,
        confidence=confidence,
    )


def messages_for(shape):
    return [message(f"m{index}", speaker) for index, speaker in enumerate(SHAPES[shape], start=1)]


@pytest.mark.parametrize("origin", [origin.value for origin in Origin])
@pytest.mark.parametrize("shape", list(SHAPES))
def test_extraction_never_promotes_a_thought_to_user_original(origin, shape):
    linked = messages_for(shape)
    original = item(origin, [entry.message_id for entry in linked])
    adjusted, _notes = adjust_extracted_items([original], linked)
    if origin != Origin.user_original.value:
        assert adjusted[0].origin != Origin.user_original
    assert adjusted[0].model_origin == Origin(origin)
    assert original.origin == Origin(origin)


def test_assistant_only_user_original_is_downgraded_to_ai_suggestion():
    linked = [message("a1", "assistant")]
    original = item("user_original", ["a1"], content="Generate the article immediately.")
    adjusted, notes = adjust_extracted_items([original], linked)
    assert adjusted[0].origin == Origin.ai_suggestion
    assert adjusted[0].model_origin == Origin.user_original
    assert adjusted[0].confidence == 0.4
    assert any("assistant" in note for note in notes)
    assert original.origin == Origin.user_original


def test_uncertain_speaker_cannot_support_user_original():
    unknown = [message("u1", "unknown")]
    adjusted, _notes = adjust_extracted_items([item("user_original", ["u1"])], unknown)
    assert adjusted[0].origin == Origin.uncertain

    hesitant = [message("u2", "user", uncertain=True)]
    adjusted, _notes = adjust_extracted_items([item("user_original", ["u2"])], hesitant)
    assert adjusted[0].origin == Origin.uncertain


def test_confident_user_source_keeps_user_original():
    linked = [message("u1", "user")]
    adjusted, notes = adjust_extracted_items(
        [item("user_original", ["u1"], content="Confirmation comes first.")],
        linked,
    )
    assert adjusted[0].origin == Origin.user_original
    assert notes == []
    assert adjusted[0].confidence == 0.9


def test_mixed_sources_keep_user_original_with_a_review_note():
    linked = [message("u1", "user"), message("a1", "assistant")]
    adjusted, notes = adjust_extracted_items([item("user_original", ["u1", "a1"])], linked)
    assert adjusted[0].origin == Origin.user_original
    assert any("confirm this is the user's idea" in note for note in notes)


def test_ai_suggestion_is_not_promoted_when_a_user_message_is_also_linked():
    linked = [message("u1", "user"), message("a1", "assistant")]
    adjusted, _notes = adjust_extracted_items([item("ai_suggestion", ["u1", "a1"])], linked)
    assert adjusted[0].origin == Origin.ai_suggestion


def test_ai_suggestion_without_an_assistant_source_becomes_uncertain():
    linked = [message("u1", "user")]
    adjusted, _notes = adjust_extracted_items([item("ai_suggestion", ["u1"])], linked)
    assert adjusted[0].origin == Origin.uncertain


def test_inferred_stays_inferred():
    linked = [message("u1", "user")]
    adjusted, notes = adjust_extracted_items(
        [item("inferred", ["u1"], content="The user dislikes publishing.")],
        linked,
    )
    assert adjusted[0].origin == Origin.inferred
    assert notes == []


def test_adoption_and_joint_ideas_need_both_speakers():
    both = [message("u1", "user"), message("a1", "assistant")]
    adopted, _notes = adjust_extracted_items([item("user_adopted", ["u1", "a1"])], both)
    assert adopted[0].origin == Origin.user_adopted
    joint, _notes = adjust_extracted_items([item("jointly_developed", ["u1", "a1"])], both)
    assert joint[0].origin == Origin.jointly_developed

    user_only = [message("u1", "user")]
    adopted, _notes = adjust_extracted_items([item("user_adopted", ["u1"])], user_only)
    assert adopted[0].origin == Origin.uncertain
    joint, _notes = adjust_extracted_items([item("jointly_developed", ["u1"])], user_only)
    assert joint[0].origin == Origin.uncertain
    assert joint[0].origin != Origin.user_original


def test_missing_source_ids_are_dropped():
    linked = [message("u1", "user")]
    adjusted, notes = adjust_extracted_items([item("user_original", ["u1", "missing"])], linked)
    assert adjusted[0].source_message_ids == ["u1"]
    assert adjusted[0].origin == Origin.user_original
    assert any("missing" in note for note in notes)


def test_user_cannot_mark_assistant_only_text_as_user_original():
    linked = [message("a1", "assistant")]
    edited = item("user_original", ["a1"])
    errors = validate_user_item(edited, linked)
    assert errors
    assert "assistant" in errors[0]


def test_user_can_correct_an_ai_suggestion_when_a_user_message_is_linked():
    linked = [message("u1", "user"), message("a1", "assistant")]
    edited = item("ai_suggestion", ["u1"]).model_copy(
        update={"origin": Origin.user_original, "origin_set_by": "user", "model_origin": Origin.ai_suggestion}
    )
    assert validate_user_item(edited, linked) == []
    assert edited.model_origin == Origin.ai_suggestion


def test_user_can_add_a_thought_without_a_source_message():
    edited = item("user_original", [])
    assert validate_user_item(edited, [message("a1", "assistant")]) == []
