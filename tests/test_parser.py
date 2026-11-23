from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.parser import parse_conversation
from app.schemas import Speaker

FIXTURE = Path(__file__).parent / "fixtures" / "sample_conversation.md"


def parse(text, **kwargs):
    return parse_conversation(
        text,
        title=kwargs.pop("title", "Notes"),
        source_type=kwargs.pop("source_type", "paste"),
        **kwargs,
    )


def test_user_and_assistant_turns_keep_order_and_original_text():
    raw = "User: Hello there.\r\n\r\nAssistant: Hi.\r\n"
    parsed = parse(raw)
    assert parsed.original_text == raw
    assert [message.speaker for message in parsed.messages] == [Speaker.user, Speaker.assistant]
    assert [message.content for message in parsed.messages] == ["Hello there.", "Hi."]
    assert [message.sequence for message in parsed.messages] == [1, 2]
    assert len({message.message_id for message in parsed.messages}) == 2
    assert parsed.messages[0].speaker_uncertain is False
    assert parsed.messages[0].speaker_confidence == 0.96


def test_markdown_bold_and_heading_labels():
    bold = parse("**User:** Keep it private.\n\n**Assistant:** Publish it.")
    assert [message.speaker for message in bold.messages] == [Speaker.user, Speaker.assistant]
    headings = parse("### User\nKeep it private.\n\n### Assistant\nPublish it.\n")
    assert [message.content for message in headings.messages] == ["Keep it private.", "Publish it."]
    assert headings.messages[1].speaker == Speaker.assistant


def test_chinese_labels():
    parsed = parse("用户：我想保留推理。\n\n助手：可以先写成文章。")
    assert [message.speaker for message in parsed.messages] == [Speaker.user, Speaker.assistant]
    assert parsed.messages[0].content == "我想保留推理。"


def test_missing_labels_are_one_uncertain_message():
    parsed = parse("I think the map should stay private.\nThere is no speaker label.")
    assert len(parsed.messages) == 1
    assert parsed.messages[0].speaker == Speaker.unknown
    assert parsed.messages[0].speaker_uncertain is True
    assert parsed.messages[0].speaker_confidence == 0.0
    assert "No speaker labels found" in parsed.parse_warnings[0]


def test_unknown_names_are_not_assigned_to_the_user():
    single = parse("Alice: I think this should stay private.")
    assert len(single.messages) == 1
    assert single.messages[0].speaker == Speaker.unknown
    dialogue = parse(
        "Alice: I think the map should stay private.\n"
        "Bob: Agreed, but maybe publish the summary.\n"
        "Alice: Only after I confirm it.\n"
    )
    assert [message.speaker for message in dialogue.messages] == [Speaker.unknown] * 3
    assert [message.speaker_label for message in dialogue.messages] == ["Alice", "Bob", "Alice"]
    assert all(message.speaker_uncertain for message in dialogue.messages)
    assert any("not user or assistant" in warning for warning in dialogue.parse_warnings)


def test_preamble_is_uncertain_and_title_heading_is_not_a_turn():
    parsed = parse("# Private notes\n\nThis was said before any label.\n\nUser: The map comes first.\n")
    assert parsed.messages[0].speaker == Speaker.unknown
    assert parsed.messages[0].speaker_uncertain is True
    assert "before any label" in parsed.messages[0].content
    assert "# Private notes" not in parsed.messages[0].content
    assert parsed.messages[1].speaker == Speaker.user


def test_you_is_confident_only_beside_an_assistant_label():
    paired = parse("You: I want a private map.\n\nChatGPT: Noted.")
    assert paired.messages[0].speaker == Speaker.user
    assert paired.messages[0].speaker_uncertain is False
    assert paired.messages[1].speaker == Speaker.assistant
    alone = parse("You: I want a private map.")
    assert alone.messages[0].speaker_uncertain is True
    assert any("uncertain" in warning for warning in alone.parse_warnings)


def test_system_lines_are_uncertain():
    parsed = parse("System: You are a helper.\n\nUser: I want a private map.\n\nAssistant: Ok.")
    assert parsed.messages[0].speaker == Speaker.unknown
    assert parsed.messages[0].speaker_uncertain is True
    assert parsed.messages[1].speaker == Speaker.user
    assert parsed.messages[1].speaker_uncertain is False


def test_note_inside_a_turn_does_not_start_a_new_speaker():
    parsed = parse("User: Note: keep this private.\nIt stays one turn.\n\nAssistant: OK.")
    assert len(parsed.messages) == 2
    assert "Note: keep this private." in parsed.messages[0].content
    assert "It stays one turn." in parsed.messages[0].content


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        parse("  \n\t")


def test_sample_fixture_parses_user_and_assistant_turns():
    parsed = parse(FIXTURE.read_text(encoding="utf-8"), title="Confirmation", source_type="markdown")
    assert [message.speaker for message in parsed.messages] == [
        Speaker.user,
        Speaker.assistant,
        Speaker.user,
        Speaker.assistant,
        Speaker.user,
        Speaker.user,
    ]
    assert parsed.messages[2].content.startswith("No. I do not want article writing")
    assert parsed.source_type == "markdown"
    assert parsed.created_at.tzinfo is timezone.utc or parsed.created_at.tzinfo == timezone.utc


def test_explicit_timestamp_is_kept():
    created = datetime(2026, 11, 23, 7, 0, tzinfo=timezone.utc)
    parsed = parse("User: Hello.", created_at=created, conversation_id="fixed")
    assert parsed.created_at == created
    assert parsed.conversation_id == "fixed"
