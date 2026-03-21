from __future__ import annotations

from random import Random
from typing import Any

from storygame.cli import run_turn
from storygame.cli import _room_lines, _transcript_command_echo, _with_paragraph_spacing
from storygame.engine.freeform import FreeformProposalAdapter
from storygame.engine.facts import active_story_goal
from storygame.engine.parser import parse_command
from storygame.engine.state import GameState
from storygame.llm.adapters import Narrator
from storygame.llm.context import build_narration_context
from storygame.llm.opening_coherence import cohere_opening_lines, item_labels_for_opening
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


def build_bootstrap_response_payload(
    state: GameState,
    command: str,
    scope_field: str,
    scope_id: str,
    story_director: StoryDirector,
    narrator: Narrator,
    output_editor: OutputEditor,
) -> dict[str, Any]:
    opening_lines = _llm_bootstrap_opening_lines(state, story_director, narrator, output_editor)
    return build_bootstrap_response_payload_from_lines(
        state,
        command,
        scope_field,
        scope_id,
        opening_lines,
    )


def _llm_bootstrap_opening_lines(
    state: GameState,
    story_director: StoryDirector,
    narrator: Narrator,
    output_editor: OutputEditor,
) -> list[str]:
    try:
        opening_lines = story_director.compose_opening(state)
        bundle = dict(state.world_package.get("llm_story_bundle", {}))
        bundle_lines = [str(line).strip() for line in bundle.get("opening_paragraphs", ()) if str(line).strip()]
        if bundle_lines:
            return opening_lines
    except RuntimeError:
        opening_lines = []

    narrator_lines = _bootstrap_opening_from_narrator(state, narrator, output_editor)
    if narrator_lines:
        return narrator_lines

    raise RuntimeError("Web bootstrap requires an LLM-authored opening.")


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
    coherent_paragraphs = cohere_opening_lines(
        paragraphs[:4],
        state.story_genre,
        context.protagonist_name,
        context.assistant_name,
        active_story_goal(state),
        item_labels_for_opening(tuple(state.world.items.keys())),
        tuple(npc.name for npc in state.world.npcs.values() if npc.name.strip()),
    )
    return output_editor.review_opening(coherent_paragraphs, active_story_goal(state))


def build_bootstrap_response_payload_from_lines(
    state: GameState,
    command: str,
    scope_field: str,
    scope_id: str,
    opening_lines: list[str],
) -> dict[str, Any]:
    return {
        scope_field: scope_id,
        "command": command,
        "action_raw": command,
        "beat": "setup_scene",
        "continued": True,
        "lines": [
            *_with_paragraph_spacing(opening_lines),
            "",
            _room_lines(state, long_form=True),
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
