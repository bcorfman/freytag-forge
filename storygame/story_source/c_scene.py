"""Compile scene metadata, beats, pacing events, transitions, and endings."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from storygame.story_package.models import (
    CharacterPlacement,
    EndingVariant,
    EntryTextVariant,
    ItemPlacement,
    PacingEvent,
    PacingRealization,
    Scene,
    SceneBeat,
    SceneFrame,
    SceneMetadata,
    ScenePacing,
    StoryEnding,
    Transition,
)

from .c_passages import predicates


def apply_scene_order(
    records: Sequence[Any],
    scenes: Sequence[tuple[str, Mapping[str, Any]]],
    kind: str,
    scene_for: Callable[[Any], str | None],
    record_id: Callable[[Any], str],
) -> tuple[Any, ...]:
    """Reorder listed records within each natural scene block."""

    result = list(records)
    positions: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        scene_id = scene_for(record)
        if scene_id is not None:
            positions.setdefault(scene_id, []).append(index)

    for scene_id, scene in scenes:
        order = scene.get("order")
        if not isinstance(order, Mapping):
            continue
        requested = order.get(kind)
        if not isinstance(requested, list) or not requested:
            continue
        block_positions = positions.get(scene_id, [])
        by_id = {record_id(records[index]): records[index] for index in block_positions}
        selected = [by_id[item_id] for item_id in requested if item_id in by_id]
        selected.extend(records[index] for index in block_positions if record_id(records[index]) not in requested)
        for index, record in zip(block_positions, selected, strict=False):
            result[index] = record
    return tuple(result)


class CompiledScene(Scene):
    """Scene model with the convenient source-facing scene ID property."""

    @property
    def scene_id(self) -> str:
        """Return the scene ID held by metadata."""

        return self.metadata.scene_id


def build_scene(scene: Mapping[str, Any], entity_kinds: Mapping[str, str]) -> Scene:
    """Compile one source scene into its runtime scene model."""

    beats = _beats(scene)
    metadata = _metadata(scene, entity_kinds)
    prose = _render_prose(scene.get("brief", ""), beats)
    opening = next(beat for beat in beats.values() if beat.id == f"{scene['scene']}.1")
    return CompiledScene(metadata=metadata, prose=prose, beats=beats, opening_beat=opening)


def _beats(scene: Mapping[str, Any]) -> dict[str, SceneBeat]:
    """Convert outline beats to an anchor-keyed mapping."""

    result: dict[str, SceneBeat] = {}
    for record in scene.get("outline", ()):
        beat = SceneBeat(
            id=record["id"],
            anchor=record["anchor"],
            title=record["title"],
            details=tuple(record["details"]),
            prose=record["prose"],
        )
        result[beat.anchor] = beat
    return result


def _render_prose(brief: str, beats: Mapping[str, SceneBeat]) -> str:
    """Render reader-only scene prose deterministically from the authored blocks."""

    sections = [brief]
    sections.extend(
        f"### Scene {beat.id} — {beat.title}\n\n**Details:** {'; '.join(beat.details)}\n\n{beat.prose}"
        for beat in beats.values()
    )
    return "\n\n".join(section for section in sections if section)


def _metadata(scene: Mapping[str, Any], entity_kinds: Mapping[str, str]) -> SceneMetadata:
    """Build metadata, routing placements by catalog entity kind."""

    placements = scene.get("placements", {}) or {}
    item_placements: dict[str, object] = {}
    character_placements: dict[str, object] = {}
    for entity_id, placement in placements.items():
        if entity_kinds.get(entity_id) == "item":
            item_placements[entity_id] = _item_placement(placement)
        else:
            character_placements[entity_id] = _character_placement(placement)
    additions = tuple(
        EntryTextVariant(requires=tuple(predicate.fact_id for predicate in predicates(item["when"])), text=item["text"])
        for item in scene.get("entry_additions", ())
    )
    exits = scene.get("exit")
    transition_ids = (exits["id"],) if isinstance(exits, Mapping) else ()
    bridge_text = {exits["id"]: exits["bridge"]} if isinstance(exits, Mapping) else {}
    return SceneMetadata(
        scene_id=scene["scene"],
        location_id=scene["location"],
        objective=scene["objective"],
        freytag_phase=scene["freytag_phase"],
        participant_ids=tuple(scene.get("participants", ())),
        item_ids=tuple(scene.get("items", ())),
        entry_text=scene["entry"],
        entry_variants=additions,
        scripted_opening=scene.get("scripted_opening", False),
        transition_ids=transition_ids,
        bridge_text=bridge_text,
        item_placements=item_placements,
        companions=tuple(scene.get("companions", ())),
        character_placements=character_placements,
        setting_facts=tuple(scene.get("setting", ())),
        prop_pool=tuple(scene.get("prop_pool", ())),
    )


def _item_placement(value: object) -> object:
    """Convert the mapping placement form while preserving text and flags."""

    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        data = dict(value)
        extras = [
            key
            for key in data
            if key not in {"placement", "while_fact_false", "while_fact_true", "parent", "text", "under", "part_of"}
        ]
        if extras:
            suffix = ", ".join(str(key) for key in extras)
            data["text"] = f"{data.get('text', '')}, {suffix}".strip(", ")
            for key in extras:
                data.pop(key)
        return ItemPlacement.model_validate(data)
    return value


def _character_placement(value: object) -> object:
    """Convert a character placement and repair YAML's unquoted comma tail."""

    if isinstance(value, Mapping):
        data = dict(value)
        extras = [key for key in data if key not in {"parent", "text"}]
        if extras:
            suffix = ", ".join(str(key) for key in extras)
            data["text"] = f"{data.get('text', '')}, {suffix}".strip(", ")
            for key in extras:
                data.pop(key)
        return CharacterPlacement.model_validate(data)
    return value


def build_frame(scene: Mapping[str, Any]) -> SceneFrame:
    """Create the safe scene frame used by knowledge projection."""

    return SceneFrame(scene_id=scene["scene"], situation=scene.get("situation", ""), pressure=scene["pressure"])


def build_pacing_scene(scene: Mapping[str, Any]) -> ScenePacing:
    """Create the scene's pacing window."""

    turns = scene["turns"]
    return ScenePacing(
        scene_id=scene["scene"],
        min_turns=turns["min"],
        nudge_after_turns=turns["nudge"],
        handoff_after_turns=turns["handoff"],
    )


def build_events(scene: Mapping[str, Any]) -> tuple[PacingEvent, ...]:
    """Compile ordered pacing records and their first-match realizations."""

    events: list[PacingEvent] = []
    for record in scene.get("beats", ()):
        realizations = tuple(
            _realization(item, record.get("verbatim", False)) for item in _say_entries(record.get("say"))
        )
        events.append(
            PacingEvent(
                id=record["id"],
                scene_id=scene["scene"],
                at_turn=record["at_turn"],
                when=predicates(record.get("when")),
                effects=predicates(record["sets"]),
                transition_id=record.get("exit"),
                realizations=realizations,
                trailing=record.get("trailing", False),
            )
        )
    return apply_scene_order(
        events,
        ((scene["scene"], scene),),
        "pacing_events",
        lambda item: item.scene_id,
        lambda item: item.id,
    )


def _say_entries(value: object) -> list[Mapping[str, Any]]:
    """Normalize a scalar say passage to one realization record."""

    if isinstance(value, str):
        return [{"text": value}]
    return list(value) if isinstance(value, list) else []


def _realization(record: Mapping[str, Any], default_verbatim: bool) -> PacingRealization:
    """Compile one pacing passage."""

    return PacingRealization(
        when=predicates(record.get("when")),
        text=record["text"],
        verbatim=record.get("verbatim", default_verbatim),
    )


def build_transition(scene: Mapping[str, Any]) -> Transition | None:
    """Compile a scene exit, if present."""

    record = scene.get("exit")
    if not isinstance(record, Mapping):
        return None
    needs = tuple(
        item["item"]
        for item in record.get("needs", ())
        if item.get("relation") in {"exists", "held"} and not item.get("not", False)
    )
    return Transition(
        id=record["id"],
        source_scene_id=scene["scene"],
        target_scene_id=record["to"],
        priority=record["priority"],
        triggers=tuple(predicates(record["when_all"])),
        required_dependencies=needs,
    )


def build_ending(scene: Mapping[str, Any]) -> StoryEnding | None:
    """Compile the optional ending stored beside the final scene."""

    record = scene.get("ending")
    if not isinstance(record, Mapping):
        return None
    variants = tuple(
        EndingVariant(
            requires=tuple(predicate.fact_id for predicate in predicates(item["when"])),
            text=item["text"],
        )
        for item in record.get("additions", ())
    )
    return StoryEnding(
        scene_id=scene["scene"],
        when=predicates(record["when"]),
        text=record["text"],
        marker=record["marker"],
        variants=variants,
    )
