"""Readable review copies of a Thought Map. These are not articles."""

from __future__ import annotations

from app.schemas import ORIGIN_LABELS, TYPE_LABELS, Conversation, ThoughtMap


def to_markdown(conversation: Conversation, thought_map: ThoughtMap) -> str:
    by_id = {message.message_id: message for message in conversation.messages}
    lines = [
        f"# Thought Map: {conversation.title}",
        "",
        "Review copy for checking attribution. Not an article. Nothing here is published.",
        "",
        f"Review status: {thought_map.review_status.value}",
        f"Schema: {thought_map.schema_version}",
        "",
        "## Central question",
        "",
        thought_map.central_question or "_None_",
        "",
        "## Main thesis",
        "",
        thought_map.main_thesis or "_None_",
        "",
        "## Thoughts",
        "",
    ]
    if not thought_map.thought_items:
        lines.extend(["_No thought items._", ""])
    for index, item in enumerate(thought_map.thought_items, start=1):
        lines.extend(
            [
                f"### {index}. {TYPE_LABELS[item.type]} · {ORIGIN_LABELS[item.origin]}",
                "",
                item.content,
                "",
                f"Set by: {item.origin_set_by}",
                f"Confidence: {item.confidence:.2f}",
            ]
        )
        if item.model_origin and item.model_origin != item.origin:
            lines.append(f"Extracted as: {ORIGIN_LABELS[item.model_origin]}")
        if item.notes:
            lines.append(f"Notes: {item.notes}")
        if item.source_message_ids:
            lines.append("Sources:")
            for message_id in item.source_message_ids:
                message = by_id.get(message_id)
                if message is None:
                    lines.append(f"- {message_id} (missing)")
                    continue
                excerpt = " ".join(message.content.split())
                if len(excerpt) > 140:
                    excerpt = excerpt[:140].rstrip() + "…"
                uncertain = ", speaker uncertain" if message.speaker_uncertain else ""
                lines.append(
                    f"- #{message.sequence} {message.speaker.value}{uncertain}: {excerpt}"
                )
        else:
            lines.append("Sources: none linked")
        lines.append("")

    lines.extend(["## Reasoning", ""])
    if not thought_map.reasoning_chain:
        lines.extend(["_None_", ""])
    for step in thought_map.reasoning_chain:
        depends = f" (depends on {', '.join(str(item) for item in step.depends_on)})" if step.depends_on else ""
        lines.append(f"{step.step}. {step.description}{depends}")
    lines.append("")

    lines.extend(["## Open questions", ""])
    lines.extend(_bullets(thought_map.open_questions))
    lines.extend(["## Contradictions", ""])
    lines.extend(_bullets(thought_map.contradictions))
    lines.extend(["## Extraction notes", ""])
    lines.extend(_bullets(thought_map.system_adjustments))
    return "\n".join(lines).rstrip() + "\n"


def _bullets(values: list[str]) -> list[str]:
    if not values:
        return ["_None_", ""]
    return [f"- {value}" for value in values] + [""]
