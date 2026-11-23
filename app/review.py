"""Edit and confirm a Thought Map without writing an article."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import ValidationError

from app.attribution import validate_user_item
from app.schemas import (
    Message,
    Origin,
    ReasoningStep,
    ReviewStatus,
    ThoughtItem,
    ThoughtMap,
    ThoughtType,
)


def apply_edits(
    current: ThoughtMap,
    messages: list[Message],
    *,
    central_question: str,
    main_thesis: str,
    open_questions: str,
    contradictions: str,
    item_ids: list[str],
    contents: list[str],
    item_types: list[str],
    origins: list[str],
    notes: list[str],
    sources_by_item: dict[str, list[str]],
    remove_ids: list[str],
    reasoning_steps: list[str],
    reasoning_descriptions: list[str],
    new_reasoning: str,
) -> ThoughtMap:
    if not (
        len(item_ids)
        == len(contents)
        == len(item_types)
        == len(origins)
        == len(notes)
    ):
        raise ValueError("The edit form was incomplete. Reload the page and try again.")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("The edit form repeated a thought. Reload the page and try again.")
    existing = {item.item_id: item for item in current.thought_items}
    if set(item_ids) != set(existing):
        raise ValueError("The Thought Map changed. Reload the page and edit again.")
    unknown_removals = [item_id for item_id in remove_ids if item_id not in existing]
    if unknown_removals:
        raise ValueError("A thought marked for removal is not on this map.")

    removing = set(remove_ids)
    updated_items: list[ThoughtItem] = []
    for index, item_id in enumerate(item_ids):
        if item_id in removing:
            continue
        previous = existing[item_id]
        content = contents[index].strip()
        if not content:
            raise ValueError("Thought text cannot be empty. Mark the thought for removal instead.")
        try:
            origin = Origin(origins[index])
            item_type = ThoughtType(item_types[index])
        except ValueError as exc:
            raise ValueError("A thought has an unknown type or attribution.") from exc
        item = previous.model_copy(
            update={
                "content": content,
                "type": item_type,
                "origin": origin,
                "notes": notes[index].strip(),
                "source_message_ids": _dedupe(sources_by_item.get(item_id, [])),
                "origin_set_by": "user" if origin != previous.origin else previous.origin_set_by,
                "user_confirmed": False,
            }
        )
        errors = validate_user_item(item, messages)
        if errors:
            raise ValueError(" ".join(errors))
        updated_items.append(item)

    reasoning = _reasoning(
        current.reasoning_chain,
        reasoning_steps,
        reasoning_descriptions,
        new_reasoning,
    )
    candidate = _replace(
        current,
        central_question=central_question.strip(),
        main_thesis=main_thesis.strip(),
        open_questions=_lines(open_questions),
        contradictions=_lines(contradictions),
        thought_items=updated_items,
        reasoning_chain=reasoning,
        review_status=current.review_status,
    )
    if _signature(candidate) == _signature(current):
        return current
    cleared = [item.model_copy(update={"user_confirmed": False}) for item in candidate.thought_items]
    return _replace(
        candidate,
        thought_items=cleared,
        review_status=ReviewStatus.in_review,
    )


def add_item(
    current: ThoughtMap,
    messages: list[Message],
    *,
    content: str,
    item_type: str,
    origin: str,
    notes: str,
    source_message_ids: list[str],
) -> ThoughtMap:
    text = content.strip()
    if not text:
        raise ValueError("Write the thought before adding it.")
    try:
        parsed_origin = Origin(origin)
        parsed_type = ThoughtType(item_type)
    except ValueError as exc:
        raise ValueError("Choose a type and an attribution for the new thought.") from exc
    item = ThoughtItem(
        item_id=str(uuid.uuid4()),
        type=parsed_type,
        content=text,
        origin=parsed_origin,
        source_message_ids=_dedupe(source_message_ids),
        confidence=1.0,
        notes=notes.strip(),
        origin_set_by="user",
        model_origin=None,
        user_confirmed=False,
    )
    errors = validate_user_item(item, messages)
    if errors:
        raise ValueError(" ".join(errors))
    cleared = [existing.model_copy(update={"user_confirmed": False}) for existing in current.thought_items]
    return _replace(
        current,
        thought_items=[*cleared, item],
        review_status=ReviewStatus.in_review,
    )


def confirm_map(current: ThoughtMap, messages: list[Message]) -> ThoughtMap:
    if (
        not current.central_question.strip()
        and not current.main_thesis.strip()
        and not current.thought_items
    ):
        raise ValueError("Add a central question, a thesis, or at least one thought before confirming.")
    errors: list[str] = []
    for item in current.thought_items:
        errors.extend(validate_user_item(item, messages))
    if errors:
        raise ValueError(" ".join(errors))
    confirmed = [item.model_copy(update={"user_confirmed": True}) for item in current.thought_items]
    return _replace(
        current,
        thought_items=confirmed,
        review_status=ReviewStatus.confirmed,
    )


def reopen_map(current: ThoughtMap) -> ThoughtMap:
    cleared = [item.model_copy(update={"user_confirmed": False}) for item in current.thought_items]
    return _replace(
        current,
        thought_items=cleared,
        review_status=ReviewStatus.in_review,
    )


def _reasoning(
    existing_steps: list[ReasoningStep],
    step_numbers: list[str],
    descriptions: list[str],
    new_reasoning: str,
) -> list[ReasoningStep]:
    if len(step_numbers) != len(descriptions):
        raise ValueError("The reasoning form was incomplete. Reload the page and try again.")
    existing = {step.step: step for step in existing_steps}
    kept: list[tuple[int, str]] = []
    for raw_step, raw_description in zip(step_numbers, descriptions):
        description = raw_description.strip()
        if not description:
            continue
        try:
            number = int(raw_step)
        except ValueError as exc:
            raise ValueError("A reasoning step has an invalid number.") from exc
        if number < 1:
            raise ValueError("A reasoning step has an invalid number.")
        kept.append((number, description))
    kept_numbers = {number for number, _ in kept}
    steps: list[ReasoningStep] = []
    for number, description in kept:
        previous = existing.get(number)
        depends = [step for step in (previous.depends_on if previous else []) if step in kept_numbers]
        sources = list(previous.source_message_ids) if previous else []
        steps.append(
            ReasoningStep(
                step=number,
                description=description,
                depends_on=depends,
                source_message_ids=sources,
            )
        )
    extra = new_reasoning.strip()
    if extra:
        next_number = max((step.step for step in steps), default=0) + 1
        steps.append(ReasoningStep(step=next_number, description=extra))
    return steps


def _replace(current: ThoughtMap, **changes) -> ThoughtMap:
    changes.setdefault("updated_at", datetime.now(timezone.utc))
    try:
        return current.model_copy(update=changes)
    except ValidationError as exc:
        raise ValueError("The Thought Map is not valid. Shorten a field and try again.") from exc


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()][:50]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _signature(thought_map: ThoughtMap) -> tuple:
    return (
        thought_map.central_question,
        thought_map.main_thesis,
        tuple(thought_map.open_questions),
        tuple(thought_map.contradictions),
        tuple(
            (
                item.item_id,
                item.type,
                item.content,
                item.origin,
                tuple(item.source_message_ids),
                item.notes,
            )
            for item in thought_map.thought_items
        ),
        tuple((step.step, step.description) for step in thought_map.reasoning_chain),
    )
