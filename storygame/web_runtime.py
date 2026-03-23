from __future__ import annotations

import re
from random import Random
from typing import Any

from storygame.cli import run_turn
from storygame.cli import _room_lines, _transcript_command_echo, _with_paragraph_spacing
from storygame.engine.freeform import FreeformProposalAdapter
from storygame.engine.facts import active_story_goal, assistant_name as resolved_assistant_name
from storygame.engine.parser import parse_command
from storygame.engine.state import GameState
from storygame.llm.adapters import Narrator
from storygame.llm.context import build_narration_context
from storygame.llm.opening_coherence import (
    item_labels_for_opening,
    opening_coherence_issues,
    opening_fact_parity_issues,
)
from storygame.llm.output_editor import OutputEditor
from storygame.llm.story_director import StoryDirector
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase


class TurnExecution:
    def __init__(
        self,
        next_state: GameState,
        lines: list[str],
        action_raw: str,
        beat: str,
        continued: bool,
    ) -> None:
        self.next_state = next_state
        self.lines = lines
        self.action_raw = action_raw
        self.beat = beat
        self.continued = continued


class ScopedSaveStore:
    def __init__(self, store: SqliteSaveStore, scope: str) -> None:
        self._store = store
        self._scope = scope

    def _slot(self, slot: str) -> str:
        return f"{self._scope}:{slot}"

    def save_run(
        self,
        slot: str,
        state: GameState,
        rng: Random,
        raw_command: str = "save",
        action_kind: str = "save",
        beat_type: str | None = None,
        template_key: str | None = None,
        transcript: list[str] | None = None,
        judge_decision: dict[str, str] | None = None,
    ) -> None:
        self._store.save_run(
            self._slot(slot),
            state,
            rng,
            raw_command=raw_command,
            action_kind=action_kind,
            beat_type=beat_type,
            template_key=template_key,
            transcript=transcript,
            judge_decision=judge_decision,
        )

    def load_run(self, slot: str) -> tuple[GameState, Random]:
        return self._store.load_run(self._slot(slot))


def is_bootstrap_command(command: str) -> bool:
    return command.strip().lower() in {"", "look", "start"}


def build_state_snapshot_payload(
    state: GameState,
    scope_field: str,
    scope_id: str,
) -> dict[str, Any]:
    room = state.world.rooms[state.player.location]
    return {
        scope_field: scope_id,
        "location": state.player.location,
        "room_name": room.name,
        "inventory": list(state.player.inventory),
        "genre": state.story_genre,
        "tone": state.story_tone,
        "session_length": state.session_length,
        "plot_curve_id": state.plot_curve_id,
        "story_outline_id": state.story_outline_id,
        "objective": active_story_goal(state),
        "phase": str(get_phase(state.progress)),
        "progress": state.progress,
        "tension": state.tension,
        "turn_index": state.turn_index,
    }


def _sanitize_assistant_targeting(text: str, assistant_name: str) -> str:
    normalized = " ".join(text.split())
    if not normalized or not assistant_name:
        return normalized
    assistant_references = [assistant_name]
    assistant_parts = assistant_name.split()
    if assistant_parts:
        assistant_references.append(assistant_parts[0])
    for assistant_reference in tuple(dict.fromkeys(reference for reference in assistant_references if reference)):
        assistant_pattern = re.escape(assistant_reference)
        normalized = re.sub(
            rf"\b(question|interrogate|interview|press|confront|accuse|ask)\s+{assistant_pattern}\b",
            f"consult {assistant_reference}",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\b{assistant_pattern}'s involvement\b",
            "the suspect's involvement",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\binvolvement of {assistant_pattern}\b",
            "involvement of the suspect",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\babout {assistant_pattern} involvement\b",
            "about the suspect's involvement",
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def build_bootstrap_response_payload(
    state: GameState,
    command: str,
    scope_field: str,
    scope_id: str,
    story_director: StoryDirector,
    narrator: Narrator,
    output_editor: OutputEditor,
    use_fast_story_director_opening: bool = False,
) -> dict[str, Any]:
    opening_lines = _llm_bootstrap_opening_lines(
        state,
        story_director,
        narrator,
        output_editor,
        use_fast_story_director_opening=use_fast_story_director_opening,
    )
    return build_bootstrap_response_payload_from_lines(
        state,
        command,
        scope_field,
        scope_id,
        opening_lines,
    )


def bootstrap_failure_debug_payload(
    state: GameState,
    command: str,
    scope_field: str,
    scope_id: str,
) -> dict[str, Any]:
    room = state.world.rooms[state.player.location]
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    opening_paragraphs = [
        str(line).strip()
        for line in bundle.get("opening_paragraphs", ())
        if str(line).strip()
    ]
    assistant = str(bundle.get("assistant_name", "")).strip() or resolved_assistant_name(state).strip()
    return {
        scope_field: scope_id,
        "command": command,
        "turn_index": state.turn_index,
        "location": state.player.location,
        "room_name": room.name,
        "active_goal": active_story_goal(state),
        "assistant_name": assistant,
        "bundle_actionable_objective": str(bundle.get("actionable_objective", "")).strip(),
        "bundle_opening_paragraphs": opening_paragraphs[:4],
    }


def _llm_bootstrap_opening_lines(
    state: GameState,
    story_director: StoryDirector,
    narrator: Narrator,
    output_editor: OutputEditor,
    use_fast_story_director_opening: bool = False,
) -> list[str]:
    story_director_error = ""
    try:
        if use_fast_story_director_opening:
            opening_lines = story_director.compose_opening_fast(state)
        else:
            opening_lines = story_director.compose_opening(state)
        bundle = dict(state.world_package.get("llm_story_bundle", {}))
        bundle_lines = [str(line).strip() for line in bundle.get("opening_paragraphs", ()) if str(line).strip()]
        if bundle_lines:
            return opening_lines
    except RuntimeError as exc:
        story_director_error = str(exc).strip()
        opening_lines = []

    try:
        narrator_lines = _bootstrap_opening_from_narrator(state, narrator, output_editor)
        if narrator_lines:
            return narrator_lines
    except RuntimeError as exc:
        narrator_error = str(exc).strip()
        if story_director_error:
            raise RuntimeError(
                "Bootstrap opening failed after story-director fallback: "
                f"story_director={story_director_error}; narrator={narrator_error}"
            ) from exc
        raise

    if story_director_error:
        raise RuntimeError(
            "Web bootstrap requires an LLM-authored opening. "
            f"story_director={story_director_error}; narrator=empty"
        )
    raise RuntimeError("Web bootstrap requires an LLM-authored opening. narrator=empty")


def _bootstrap_opening_from_narrator(
    state: GameState,
    narrator: Narrator,
    output_editor: OutputEditor,
) -> list[str]:
    context = build_narration_context(state, parse_command("look"), "setup_scene")
    try:
        raw = str(narrator.generate(context)).strip()
    except RuntimeError:
        return []
    if not raw:
        return []
    paragraphs = [part.strip() for part in raw.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [raw]
    opening_lines = [_sanitize_assistant_targeting(paragraph, context.assistant_name) for paragraph in paragraphs[:4]]
    item_labels = item_labels_for_opening(tuple(state.world.items.keys()))
    assistant_npc_id = next(
        (
            npc_id
            for npc_id, npc in state.world.npcs.items()
            if npc.name.strip().lower() == context.assistant_name.strip().lower()
        ),
        "",
    )
    issues = opening_coherence_issues(
        opening_lines,
        context.assistant_name,
        active_story_goal(state),
        item_labels,
        tuple(npc.name for npc in state.world.npcs.values() if npc.name.strip()),
    )
    issues.extend(
        opening_fact_parity_issues(
            opening_lines,
            context.assistant_name,
            "assistant" if context.assistant_name else "",
            bool(assistant_npc_id) and state.world_facts.holds("npc_at", assistant_npc_id, state.player.location),
            item_labels,
            item_labels_for_opening(
                tuple(fact[2] for fact in state.world_facts.query("holding", assistant_npc_id, None) if len(fact) > 2)
            ),
        )
    )
    if issues:
        raise RuntimeError("Opening validation failed: " + "; ".join(dict.fromkeys(issues)))
    return output_editor.review_opening(opening_lines, active_story_goal(state))


def build_bootstrap_response_payload_from_lines(
    state: GameState,
    command: str,
    scope_field: str,
    scope_id: str,
    opening_lines: list[str],
) -> dict[str, Any]:
    room = state.world.rooms[state.player.location]
    cache = state.world_package.get("room_presentation_cache", {})
    room_cache = cache.get(room.id, {})
    banned_lines = {
        room.name.strip().lower(),
        room.description.strip().lower(),
        str(room_cache.get("long", "")).strip().lower(),
        str(room_cache.get("short", "")).strip().lower(),
    }
    filtered_opening = [
        line for line in opening_lines if line.strip() and line.strip().lower() not in banned_lines
    ]
    return {
        scope_field: scope_id,
        "command": command,
        "action_raw": command,
        "beat": "setup_scene",
        "continued": True,
        "lines": [
            *_with_paragraph_spacing(filtered_opening),
            "",
            _room_lines(state, long_form=False),
        ],
        "state": build_state_snapshot_payload(state, scope_field, scope_id),
    }


def build_turn_response_payload(
    state: GameState,
    command: str,
    action_raw: str,
    beat: str,
    continued: bool,
    lines: list[str],
    scope_field: str,
    scope_id: str,
) -> dict[str, Any]:
    return {
        scope_field: scope_id,
        "command": command,
        "action_raw": action_raw,
        "beat": beat,
        "continued": continued,
        "lines": [_transcript_command_echo(command), *list(lines)],
        "state": build_state_snapshot_payload(state, scope_field, scope_id),
    }


def execute_turn(
    state: GameState,
    command: str,
    rng: Random,
    narrator: Narrator,
    freeform_adapter: FreeformProposalAdapter,
    narrator_mode: str,
    debug: bool,
    save_store: ScopedSaveStore,
    memory_slot: str,
    output_editor: OutputEditor,
    story_director: StoryDirector,
) -> TurnExecution:
    next_state, lines, action_raw, beat, continued = run_turn(
        state,
        command,
        rng,
        narrator,
        freeform_adapter=freeform_adapter,
        narrator_mode=narrator_mode,
        debug=debug,
        save_store=save_store,
        memory_slot=memory_slot,
        output_editor=output_editor,
        story_director=story_director,
    )
    return TurnExecution(
        next_state=next_state,
        lines=list(lines),
        action_raw=action_raw,
        beat=beat,
        continued=continued,
    )
