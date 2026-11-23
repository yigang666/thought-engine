"""Deterministic attribution rules.

Extraction may downgrade an over-claimed origin. It never promotes any
other origin to user_original, including ai_suggestion and inferred.
A person can correct an origin during review when the linked messages
support the correction. That edit does not rewrite the stored extraction.
"""

from __future__ import annotations

from app.schemas import Message, Origin, Speaker, ThoughtItem

BLOCKED_PROMOTIONS = {Origin.ai_suggestion, Origin.inferred}


def adjust_origin(origin: Origin, linked: list[Message]) -> tuple[Origin, str | None]:
    """Return the origin to keep, plus a note when reviewers should look."""
    uncertain = any(message.speaker == Speaker.unknown or message.speaker_uncertain for message in linked)
    has_user = any(
        message.speaker == Speaker.user and not message.speaker_uncertain for message in linked
    )
    has_assistant = any(
        message.speaker == Speaker.assistant and not message.speaker_uncertain for message in linked
    )

    if origin == Origin.user_original:
        if linked and not uncertain and has_assistant and not has_user:
            return (
                Origin.ai_suggestion,
                "Downgraded from user original: every source message is from the assistant.",
            )
        if not linked or uncertain or not has_user:
            return (
                Origin.uncertain,
                "Downgraded from user original: there is no confident user message, or a source speaker is uncertain.",
            )
        if has_assistant:
            return (
                origin,
                "Kept as user original because a confident user message is linked. An assistant message is linked too, so confirm this is the user's idea.",
            )
        return origin, None

    if origin == Origin.ai_suggestion:
        if not has_assistant or uncertain:
            return (
                Origin.uncertain,
                "Downgraded from AI suggestion: there is no confident assistant message, or a source speaker is uncertain.",
            )
        return origin, None

    if origin == Origin.user_adopted:
        if uncertain or not (has_user and has_assistant):
            return (
                Origin.uncertain,
                "Downgraded from user adopted: adoption needs a confident user message and a confident assistant message, with no uncertain speakers.",
            )
        return origin, None

    if origin == Origin.jointly_developed:
        if uncertain or not (has_user and has_assistant):
            return (
                Origin.uncertain,
                "Downgraded from jointly developed: joint attribution needs confident messages from both the user and the assistant.",
            )
        return origin, None

    if origin in (Origin.inferred, Origin.uncertain):
        return origin, None

    return Origin.uncertain, "Downgraded an unknown origin to uncertain."


def adjust_extracted_items(
    items: list[ThoughtItem],
    messages: list[Message],
) -> tuple[list[ThoughtItem], list[str]]:
    by_id = {message.message_id: message for message in messages}
    adjusted: list[ThoughtItem] = []
    notes: list[str] = []
    for item in items:
        found, missing = _resolve(item.source_message_ids, by_id)
        model_origin = item.origin
        origin, note = adjust_origin(model_origin, found)
        if model_origin in BLOCKED_PROMOTIONS and origin == Origin.user_original:
            origin = Origin.uncertain
            note = "Blocked a promotion from an AI suggestion or an inference to user original."
        if model_origin != Origin.user_original and origin == Origin.user_original:
            origin = Origin.uncertain
            note = "Blocked a promotion to user original. The model did not classify this as the user's own idea."
        snippet = _snippet(item.content)
        if missing:
            notes.append(
                f"“{snippet}”: ignored source ids that are not in this conversation ({', '.join(missing)})."
            )
        if note:
            notes.append(f"“{snippet}”: {note}")
        confidence = min(item.confidence, 0.4) if origin != model_origin else item.confidence
        adjusted.append(
            item.model_copy(
                update={
                    "origin": origin,
                    "model_origin": model_origin,
                    "source_message_ids": [message.message_id for message in found],
                    "confidence": confidence,
                    "origin_set_by": "extraction",
                    "user_confirmed": False,
                }
            )
        )
    return adjusted, notes


def validate_user_item(item: ThoughtItem, messages: list[Message]) -> list[str]:
    """Reject a review edit that contradicts the messages it cites.

    An empty source list is allowed so a person can add a missing thought.
    """
    by_id = {message.message_id: message for message in messages}
    missing = [message_id for message_id in item.source_message_ids if message_id not in by_id]
    if missing:
        return [f"Unknown source message: {', '.join(missing)}."]
    linked = [by_id[message_id] for message_id in item.source_message_ids]
    if not linked:
        return []
    revised, note = adjust_origin(item.origin, linked)
    if revised != item.origin:
        return [note or "That attribution does not match the linked messages."]
    return []


def _resolve(
    message_ids: list[str], by_id: dict[str, Message]
) -> tuple[list[Message], list[str]]:
    found: list[Message] = []
    missing: list[str] = []
    seen: set[str] = set()
    for message_id in message_ids:
        if message_id in seen:
            continue
        seen.add(message_id)
        message = by_id.get(message_id)
        if message is None:
            missing.append(message_id)
        else:
            found.append(message)
    return found, missing


def _snippet(content: str) -> str:
    text = " ".join(content.split())
    if len(text) > 80:
        return text[:80].rstrip() + "…"
    return text
