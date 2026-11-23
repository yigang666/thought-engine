"""Parse pasted text or Markdown into ordered messages.

Known speaker labels become user or assistant turns. Unrecognized names
and text without labels stay unknown, with speaker attribution marked
uncertain. The original string is stored unchanged.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.schemas import Conversation, Message, Speaker

ROLE_KEYS = {
    "user": "user",
    "human": "user",
    "me": "user",
    "用户": "user",
    "我": "user",
    "you": "you",
    "你": "you",
    "assistant": "assistant",
    "ai": "assistant",
    "chatgpt": "assistant",
    "claude": "assistant",
    "gpt": "assistant",
    "助手": "assistant",
    "人工智能": "assistant",
    "system": "system",
}

LABEL_RE = re.compile(
    r"^(?:\*\*|__)?\s*"
    r"([^\n:：*]{1,60}?)"
    r"\s*(?:\*\*|__)?\s*[:：]\s*(.*)$"
)

UNKNOWN_LABEL_RE = re.compile(
    r"^([A-Z][A-Za-z0-9_.'’-]{0,30}|[\u4e00-\u9fff]{1,12})\s*[:：]\s*(.*)$"
)

UNKNOWN_STOP = {
    "note",
    "notes",
    "warning",
    "example",
    "examples",
    "conclusion",
    "step",
    "update",
    "title",
    "date",
    "time",
    "subject",
    "from",
    "to",
    "summary",
    "question",
    "questions",
    "answer",
    "answers",
    "assumption",
    "assumptions",
    "hypothesis",
    "context",
    "background",
    "goal",
    "result",
    "results",
    "todo",
    "fixme",
    "ps",
    "re",
    "fw",
    "abstract",
    "overview",
    "introduction",
    "agenda",
}

MAX_MESSAGES = 2000
_QUALIFIERS = {"assistant", "bot", "model", "ai"}
_LEADING = {"the", "ai"}


def parse_conversation(
    original_text: str,
    *,
    title: str,
    source_type: str,
    conversation_id: str | None = None,
    created_at: datetime | None = None,
) -> Conversation:
    if source_type not in ("paste", "markdown"):
        raise ValueError("Source type must be paste or markdown.")
    if original_text is None or not original_text.strip():
        raise ValueError("The conversation is empty.")

    working = original_text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = working.split("\n")
    if _has_known_labels(lines):
        raw_messages, warnings = _parse_known(lines)
    else:
        raw_messages, warnings = _parse_unlabeled(lines, working)

    messages: list[Message] = []
    for raw in raw_messages:
        content = raw["content"].strip()
        if not content:
            continue
        messages.append(
            Message(
                message_id=str(uuid.uuid4()),
                sequence=len(messages) + 1,
                speaker=Speaker(raw["speaker"]),
                speaker_label=raw["label"][:80],
                content=content,
                speaker_confidence=raw["confidence"],
                speaker_uncertain=raw["uncertain"],
            )
        )
    if not messages:
        raise ValueError("No conversation text found.")
    if len(messages) > MAX_MESSAGES:
        raise ValueError(
            "This conversation has more than 2000 messages. Split it and import the part you want to review."
        )

    clean_title = " ".join((title or "").split()).strip() or "Untitled conversation"
    if len(clean_title) > 200:
        clean_title = clean_title[:200].rstrip()

    return Conversation(
        conversation_id=conversation_id or str(uuid.uuid4()),
        title=clean_title,
        source_type=source_type,  # type: ignore[arg-type]
        created_at=created_at or datetime.now(timezone.utc),
        original_text=original_text,
        messages=messages,
        parse_warnings=warnings,
    )


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().strip(".").split())


def resolve_role(label: str) -> str | None:
    """Map a speaker label to a role key. None means the label is not a known role."""
    key = _normalize_label(label)
    if not key:
        return None
    if key in ROLE_KEYS:
        return ROLE_KEYS[key]
    parts = key.split(" ")
    if len(parts) == 2 and parts[0] in ROLE_KEYS and parts[1] in _QUALIFIERS:
        return ROLE_KEYS[parts[0]]
    if len(parts) == 2 and parts[1] in ROLE_KEYS and parts[0] in _LEADING:
        return ROLE_KEYS[parts[1]]
    return None


def classify_line(line: str) -> tuple[str, str, str] | None:
    """Return (role_key, display_label, inline_text) when a line opens a known turn."""
    stripped = line.strip()
    if not stripped:
        return None
    without_heading = re.sub(r"^#{1,6}\s+", "", stripped).strip()
    match = LABEL_RE.match(without_heading)
    if match:
        role = resolve_role(match.group(1))
        if role:
            return role, match.group(1).strip(), match.group(2).strip()
    bare = _strip_emphasis(without_heading)
    exact = ROLE_KEYS.get(_normalize_label(bare))
    if exact and ":" not in bare and "：" not in bare:
        return exact, bare.strip(), ""
    return None


def _strip_emphasis(text: str) -> str:
    if (text.startswith("**") and text.endswith("**") and len(text) >= 4) or (
        text.startswith("__") and text.endswith("__") and len(text) >= 4
    ):
        return text[2:-2].strip()
    return text


def _has_known_labels(lines: list[str]) -> bool:
    return any(classify_line(line) is not None for line in lines)


def _assign_speaker(
    role: str,
    *,
    assistant_present: bool,
    warnings: list[str],
    flags: dict[str, bool],
) -> tuple[str, float, bool]:
    if role == "you":
        if assistant_present:
            return "user", 0.93, False
        if not flags["you"]:
            warnings.append(
                "A You/你 label appeared without an assistant label, so that speaker is marked uncertain."
            )
            flags["you"] = True
        return "user", 0.5, True
    if role == "system":
        if not flags["system"]:
            warnings.append(
                "System lines are not treated as the user or the assistant. Their speaker is uncertain."
            )
            flags["system"] = True
        return "unknown", 0.4, True
    if role == "user":
        return "user", 0.96, False
    if role == "assistant":
        return "assistant", 0.96, False
    return "unknown", 0.0, True


def _preamble_text(lines: list[str]) -> str:
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^#{1,6}\s+\S", stripped) and classify_line(line) is None:
            continue
        body.append(line)
    return "\n".join(body).strip()


def _parse_known(lines: list[str]) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    flags = {"you": False, "system": False}
    classified = [classify_line(line) for line in lines]
    assistant_present = any(item is not None and item[0] == "assistant" for item in classified)
    messages: list[dict] = []
    current: dict | None = None
    preamble: list[str] = []
    started = False

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        content = "\n".join(current["lines"]).strip()
        if content:
            current["content"] = content
            messages.append(current)
        else:
            warnings.append(f"Dropped an empty turn labeled {current['label']}.")
        current = None

    for line, role in zip(lines, classified):
        if role is not None:
            if not started:
                body = _preamble_text(preamble)
                if body:
                    messages.append(
                        {
                            "speaker": "unknown",
                            "label": "unknown",
                            "content": body,
                            "confidence": 0.2,
                            "uncertain": True,
                            "lines": [],
                        }
                    )
                    warnings.append("Text before the first speaker label has an uncertain speaker.")
                started = True
            flush()
            speaker, confidence, uncertain = _assign_speaker(
                role[0],
                assistant_present=assistant_present,
                warnings=warnings,
                flags=flags,
            )
            current = {
                "speaker": speaker,
                "label": role[1],
                "confidence": confidence,
                "uncertain": uncertain,
                "lines": [role[2]] if role[2] else [],
                "content": "",
            }
        elif not started:
            preamble.append(line)
        elif current is not None:
            current["lines"].append(line)
    flush()
    return messages, warnings


def _parse_unlabeled(lines: list[str], working: str) -> tuple[list[dict], list[str]]:
    labels: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = UNKNOWN_LABEL_RE.match(line.strip())
        if not match:
            continue
        name = match.group(1).strip()
        if name.lower() in UNKNOWN_STOP:
            continue
        labels.append((index, name, match.group(2).strip()))
    if len(labels) >= 2:
        return _split_unknown(lines, labels)
    return (
        [
            {
                "speaker": "unknown",
                "label": "unknown",
                "content": working.strip(),
                "confidence": 0.0,
                "uncertain": True,
                "lines": [],
            }
        ],
        ["No speaker labels found. The import is one message with uncertain attribution."],
    )


def _split_unknown(
    lines: list[str], labels: list[tuple[int, str, str]]
) -> tuple[list[dict], list[str]]:
    warnings = [
        "Speaker names are not user or assistant labels, so every speaker is marked uncertain."
    ]
    messages: list[dict] = []
    preamble = "\n".join(lines[: labels[0][0]]).strip()
    if preamble:
        messages.append(
            {
                "speaker": "unknown",
                "label": "unknown",
                "content": preamble,
                "confidence": 0.2,
                "uncertain": True,
                "lines": [],
            }
        )
        warnings.append("Text before the first speaker label has an uncertain speaker.")
    for index, (line_index, name, inline) in enumerate(labels):
        end = labels[index + 1][0] if index + 1 < len(labels) else len(lines)
        parts = ([inline] if inline else []) + lines[line_index + 1 : end]
        content = "\n".join(parts).strip()
        if not content:
            warnings.append(f"Dropped an empty turn labeled {name}.")
            continue
        messages.append(
            {
                "speaker": "unknown",
                "label": name,
                "content": content,
                "confidence": 0.35,
                "uncertain": True,
                "lines": [],
            }
        )
    return messages, warnings
