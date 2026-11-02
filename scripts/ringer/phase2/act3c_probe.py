"""Bounded Act 3C live-smoke probe; dry mode never dispatches a model request."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ringer/phase1"))
sys.path.insert(0, str(ROOT / "scripts/ringer/stage7"))

try:
    from ..phase1.act2_probe import (  # noqa: E402
        CAPS,
        MAX_COMMANDS,
        SpendBudget,
        _ask_player,
        _fact_keys,
        _model_dump,
        _reveal_selection,
        _scripted_player,
        _ScriptedProvider,
        _true_fact_ids,
        _write,
        counted_provider,
        detect_stale_cue,
        load_variation,
        provider_for,
    )
except ImportError:
    from act2_probe import (  # noqa: E402
        CAPS,
        MAX_COMMANDS,
        SpendBudget,
        _ask_player,
        _fact_keys,
        _model_dump,
        _reveal_selection,
        _scripted_player,
        _ScriptedProvider,
        _true_fact_ids,
        _write,
        counted_provider,
        detect_stale_cue,
        load_variation,
        provider_for,
    )

from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, _matches_all  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.runtime.world_model import apply_scene_placements, world_for  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402
from storygame.story_package.models import scene_entry_texts  # noqa: E402

SCENE = "3C"
CAPS = {"cloudflare": 80, "player": 40}
MAX_COMMANDS = 30

# These are the three facts produced by the 3B broadcast bridge and carried by
# the 3B -> 3C ``broadcast_started`` transition.  In particular, truth_no_longer_containable
# and rebecca_captured are deliberately not seeded: SL-3C-A and SL-3C-B must be
# reachable by ordinary player commands before the evacuation incident can resolve.
CARRIED_FACTS_3B = (
    "broadcast_started",
    "brandon_confession_available",
    "detention_locations_secured",
)

BROADCAST_COMMAND = "Send the evidence package."
ARCHIVE_COMMAND = "Take the Portable data case from Rebecca."
CLEAN_COMMAND = "Restore the drainage pumps."
COSTLY_COMMAND = "Give up the lower levels."
RECOVERY_COMMAND = "Let the surge carry the captives through the gates."
NEUTRAL_COMMANDS = (
    "Walk across the concrete floor.",
    "Move beside the steel railing.",
    "Stand near the west wall.",
    "Kneel by the stairwell.",
    "Step toward the central corridor.",
    "Turn toward the north passage.",
    "Circle the support columns.",
    "Pause beside the concrete pillar.",
)

SCRIPTED_PREFIXES = {
    "none": (),
    "clean": (BROADCAST_COMMAND, ARCHIVE_COMMAND, CLEAN_COMMAND),
    "costly": (BROADCAST_COMMAND, ARCHIVE_COMMAND, COSTLY_COMMAND),
    # The two prerequisite commands are scripted as part of the stall route so
    # its eight neutral commands can close the window without making either
    # guarded prerequisite unreachable.
    "stall": NEUTRAL_COMMANDS,
}
PREFIXES = tuple(SCRIPTED_PREFIXES)

KNOWLEDGE_IDS = (
    "k_sl_3c_a_r1",
    "k_sl_3c_a_r2",
    "k_sl_3c_b_r1",
    "k_sl_3c_b_r2",
    "k_sl_3c_c_r1",
    "k_sl_3c_c_r2",
    "k_sl_3c_h_r1",
    "k_sl_3c_d_r1",
    "k_sl_3c_d_r2",
    "k_sl_3c_e_r1",
    "k_sl_3c_e_r2",
)

SCRIPTED_EXPECTATIONS = {
    "none": (
        (BROADCAST_COMMAND, "k_sl_3c_a_r1"),
        (ARCHIVE_COMMAND, "k_sl_3c_b_r1"),
        (CLEAN_COMMAND, "k_sl_3c_c_r1"),
    ),
    "clean": (
        (BROADCAST_COMMAND, "k_sl_3c_a_r1"),
        (ARCHIVE_COMMAND, "k_sl_3c_b_r1"),
        (CLEAN_COMMAND, "k_sl_3c_c_r1"),
    ),
    "costly": (
        (BROADCAST_COMMAND, "k_sl_3c_a_r1"),
        (ARCHIVE_COMMAND, "k_sl_3c_b_r1"),
        (COSTLY_COMMAND, "k_sl_3c_c_r2"),
    ),
    "stall": (
        (BROADCAST_COMMAND, "k_sl_3c_a_r1"),
        (ARCHIVE_COMMAND, "k_sl_3c_b_r1"),
        *((command, None) for command in NEUTRAL_COMMANDS),
        (RECOVERY_COMMAND, "k_sl_3c_h_r1"),
    ),
}

ROW_FIELDS = (
    "row_id",
    "rep",
    "arm",
    "scene",
    "prefix",
    "commands",
    "responses",
    "turns",
    "turns_in_scene",
    "turns_in_3c",
    "stale_cues",
    "clarification_count",
    "rejection_count",
    "first_turn_clarification_count",
    "first_turn_rejection_count",
    "segments_dropped",
    "request_count",
    "player_request_count",
    "recovery_count",
    "repeated_response_streak_max",
    "stuck_loop",
    "final_true_facts",
    "final_scene",
    "ended_by",
    "exit_cause",
    "story_complete",
    "ending_segments",
    "final_ending_segments",
    "ending_variants_seen",
    "ending_variant_paragraphs",
    "window_event_fired_turn",
    "nudge_event_fired_turn",
)


def _state(package: Any) -> RuntimeState:
    """Build a synthetic 3C arrival from the authored 3B bridge facts only."""
    scene = next(item for item in package.scenes if item.metadata.scene_id == SCENE)
    state = RuntimeState(package=package, current_scene_id=SCENE, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(SCENE)
    for fact_id in CARRIED_FACTS_3B:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    apply_scene_placements(package, state.facts, SCENE)
    world_for(package, state.facts).seed()
    return state


def _entry_screen(package: Any, state: RuntimeState) -> str:
    scene = next(item for item in package.scenes if item.metadata.scene_id == state.current_scene_id)
    return "\n\n".join(scene_entry_texts(scene.metadata, _true_fact_ids(state)))


def _knowledge_candidates(package: Any) -> tuple[ActionEvidenceCandidate, ...]:
    return tuple(
        ActionEvidenceCandidate(id=item.id, required_groups=item.action_evidence)
        for item in package.knowledge.knowledge
        if item.id in KNOWLEDGE_IDS and item.action_evidence
    )


def _verify_scripted_commands(package: Any) -> None:
    candidates = _knowledge_candidates(package)
    expected_ids = set(KNOWLEDGE_IDS)
    if {candidate.id for candidate in candidates} != expected_ids:
        raise RuntimeError("the 3C matcher audit does not cover every authored action-evidence entry")
    for prefix, expectations in SCRIPTED_EXPECTATIONS.items():
        for command, expected_id in expectations:
            matches = [candidate.id for candidate in candidates if _matches_all(candidate.required_groups, command)]
            if expected_id is None:
                if matches:
                    raise RuntimeError(f"{prefix} command unexpectedly matches 3C knowledge: {command!r}: {matches}")
            elif matches != [expected_id]:
                raise RuntimeError(f"{prefix} command matches {matches}, expected [{expected_id}]: {command!r}")


def _provider_payload(package: Any, selected: str | None) -> dict[str, Any]:
    item = next((knowledge for knowledge in package.knowledge.knowledge if knowledge.id == selected), None)
    text = item.delivery_text if item is not None and item.delivery_text else "The water continues to rise."
    segment: dict[str, Any] = {"kind": "narration", "text": text}
    payload: dict[str, Any] = {"segments": [segment]}
    if selected:
        segment["grounding_ids"] = [selected]
        payload["selected_knowledge_ids"] = [selected]
    return payload


class _Act3cScriptedProvider(_ScriptedProvider):
    def __init__(self, package: Any, state: RuntimeState, selections: list[str | None]) -> None:
        super().__init__(state, selections)
        self.package = package

    def __call__(self, _command: str) -> dict[str, Any]:
        selected = self.selections[self.calls] if self.calls < len(self.selections) else None
        self.calls += 1
        self.request_count += 1
        return _provider_payload(self.package, selected)


def _scripted_route(prefix: str) -> tuple[list[str], list[str | None]]:
    if prefix == "none":
        return [BROADCAST_COMMAND, ARCHIVE_COMMAND, CLEAN_COMMAND], [
            "k_sl_3c_a_r1",
            "k_sl_3c_b_r1",
            "k_sl_3c_c_r1",
        ]
    if prefix == "clean":
        return list(SCRIPTED_PREFIXES[prefix]), [
            "k_sl_3c_a_r1",
            "k_sl_3c_b_r1",
            "k_sl_3c_c_r1",
        ]
    if prefix == "costly":
        return list(SCRIPTED_PREFIXES[prefix]), [
            "k_sl_3c_a_r1",
            "k_sl_3c_b_r1",
            "k_sl_3c_c_r2",
        ]
    if prefix == "stall":
        commands = [BROADCAST_COMMAND, ARCHIVE_COMMAND, *NEUTRAL_COMMANDS, RECOVERY_COMMAND]
        selections: list[str | None] = ["k_sl_3c_a_r1", "k_sl_3c_b_r1"]
        selections.extend([None] * len(NEUTRAL_COMMANDS))
        selections.append("k_sl_3c_h_r1")
        return commands, selections
    raise ValueError(f"unknown prefix: {prefix}")


def _event_turn(turns: list[dict[str, Any]], event_id: str) -> int | None:
    for turn in turns:
        if event_id in turn.get("fired_event_ids", ()):
            return int(turn["turn"])
    return None


def _run_row(
    package: Any,
    state: RuntimeState,
    provider: Any,
    ask_player: Callable[[str, SpendBudget], str],
    budget: SpendBudget,
    row_id: str,
    prefix: str,
    scripted_commands: list[str] | None = None,
    trace: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    screen = _entry_screen(package, state)
    scripted_commands = scripted_commands or []
    scripted_index = 0
    command = scripted_commands[0] if scripted_commands else ask_player(screen, budget)
    commands: list[str] = []
    responses: list[str] = []
    ending_segments: list[str] = []
    stale_cues: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    clarifications = rejections = segments_dropped = 0
    first_turn_clarifications = first_turn_rejections = 0
    repeated_response_streak_max = 0
    response_streak = 0
    previous_response: str | None = None
    engine = RuntimeEngine(state, provider)
    turns_in_scene = 0
    while len(commands) < MAX_COMMANDS:
        scripted = scripted_index < len(scripted_commands)
        scene_before = state.current_scene_id
        before = _true_fact_ids(state)
        before_keys = _fact_keys(state)
        before_reveals = {reveal_id for record in state.turn_records for reveal_id in record.reveal_ids}
        fired_events_before = set(state.fired_event_ids)
        request_before = getattr(provider, "request_count", 0)
        recovery_before = getattr(provider, "recovery_count", 0)
        attempts = getattr(engine, "attempts", None)
        attempts_before = len(attempts) if attempts is not None else None
        was_scene = scene_before == SCENE
        turn = engine.turn(command)
        commands.append(command)
        if was_scene:
            turns_in_scene += 1
        response_parts = [segment.text for segment in turn.segments]
        response = "\n\n".join(response_parts)
        responses.append(response)
        repeated = response == previous_response
        response_streak = response_streak + 1 if repeated else 1
        repeated_response_streak_max = max(repeated_response_streak_max, response_streak)
        previous_response = response
        if state.story_complete:
            ending_segments = response_parts
        if trace is not None:
            trace.append({"command": command, "response": response})
        cue = state.last_turn_delivery.cue_fact_id
        stale_cues.append({"turn": len(commands), "cue_fact_id": cue, "stale": detect_stale_cue(cue, before)})
        is_clarification = int(hasattr(turn, "clarification"))
        clarifications += is_clarification
        if len(commands) == 1:
            first_turn_clarifications = is_clarification
        if attempts is None:
            last_attempt = getattr(engine, "last_attempt", None)
        else:
            last_attempt = engine.last_attempt if len(attempts) > attempts_before else None
        is_rejection = int(bool(getattr(last_attempt, "rejection", None)))
        rejections += is_rejection
        if len(commands) == 1:
            first_turn_rejections = is_rejection
        segments_dropped += state.last_turn_delivery.segments_dropped
        after_keys = _fact_keys(state)
        committed = (
            sorted({reveal_id for record in state.turn_records for reveal_id in record.reveal_ids} - before_reveals)
            if state.turn_records
            else []
        )
        turns.append(
            {
                "turn": len(commands),
                "scene_before": scene_before,
                "scene_after": state.current_scene_id,
                "facts_newly_asserted": sorted(after_keys - before_keys),
                "facts_retracted": sorted(before_keys - after_keys),
                "committed_reveals": committed,
                "reveal_selection": _reveal_selection(provider, last_attempt),
                "last_attempt_rejection": _model_dump(getattr(last_attempt, "rejection", None)),
                "transition_cause": getattr(last_attempt, "transition_cause", None),
                "request_count_delta": getattr(provider, "request_count", 0) - request_before,
                "recovery_count_delta": getattr(provider, "recovery_count", 0) - recovery_before,
                "staged_cue_fact_id": state.staged_cue_fact_id,
                "staged_handoff_fact_ids": sorted(state.staged_handoff_fact_ids),
                "delivered_cue_ids": sorted(state.delivered_cue_ids),
                "event_ids": list(state.turn_records[-1].event_ids) if state.turn_records else [],
                "deadline_event_ids": list(state.turn_records[-1].deadline_event_ids) if state.turn_records else [],
                "fired_event_ids": sorted(set(state.fired_event_ids) - fired_events_before),
                "segments_dropped": state.last_turn_delivery.segments_dropped,
                "repeated_response": repeated,
                "scripted": scripted,
            }
        )
        if scripted:
            scripted_index += 1
        if state.current_scene_id != SCENE:
            ended_by = f"scene_{state.current_scene_id.lower()}"
            break
        if state.story_complete:
            ended_by = "story_end"
            break
        if len(commands) >= MAX_COMMANDS:
            ended_by = "command_cap"
            break
        if scripted_index < len(scripted_commands):
            command = scripted_commands[scripted_index]
        else:
            command = ask_player(screen + "\n\n" + "\n".join(responses), budget)
    else:
        ended_by = "command_cap"

    facts = _true_fact_ids(state)
    exit_cause = (
        "evacuation_clean"
        if "barrier_held" in facts
        else "evacuation_costly"
        if "lower_levels_lost" in facts
        else "neutral_recovery"
        if "surge_forced_evacuation" in facts
        else "none"
    )
    ending = package.pacing.ending
    ending_variants_seen = [variant.requires[0] for variant in ending.variants if variant.text in ending_segments]
    ending_variant_paragraphs = [variant.text for variant in ending.variants if variant.text in ending_segments]
    return {
        "row_id": row_id,
        "rep": 1,
        "arm": "current",
        "scene": SCENE,
        "prefix": prefix,
        "commands": commands,
        "responses": responses,
        "turns": turns,
        "turns_in_scene": turns_in_scene,
        "turns_in_3c": turns_in_scene,
        "stale_cues": stale_cues,
        "clarification_count": clarifications,
        "rejection_count": rejections,
        "first_turn_clarification_count": first_turn_clarifications,
        "first_turn_rejection_count": first_turn_rejections,
        "segments_dropped": segments_dropped,
        "request_count": getattr(provider, "request_count", 0),
        "cloudflare_request_count": getattr(provider, "request_count", 0),
        "player_request_count": budget.raw_player_attempts,
        "recovery_count": getattr(provider, "recovery_count", 0),
        "repeated_response_streak_max": repeated_response_streak_max,
        "stuck_loop": repeated_response_streak_max >= 3,
        "final_true_facts": sorted(facts),
        "final_scene": state.current_scene_id,
        "ended_by": ended_by,
        "exit_cause": exit_cause,
        "story_complete": state.story_complete,
        "ending_segments": ending_segments,
        "final_ending_segments": ending_segments,
        "ending_variants_seen": ending_variants_seen,
        "ending_variant_paragraphs": ending_variant_paragraphs,
        "window_event_fired_turn": _event_turn(turns, "evacuation_window_3c"),
        "nudge_event_fired_turn": _event_turn(turns, "evacuation_nudge_3c"),
    }


def run(out: Path, prefix: str, n: int, dry: bool, confirm: bool) -> int:
    if prefix not in PREFIXES:
        raise ValueError(f"unknown prefix: {prefix}")
    if not dry and not confirm:
        raise SystemExit("live mode requires --confirm")
    variation = load_variation(ROOT / "bench/variations/phase1-slice-current.json")
    package = load_story_package(Path(variation["_package_path"]))
    _verify_scripted_commands(package)
    rows: list[dict[str, Any]] = []
    trace: list[dict[str, str]] = []
    budget = SpendBudget(80, cloudflare_limit=80, player_limit=40)
    try:
        for rep in range(1, n + 1):
            state = _state(package)
            if dry:
                scripted_commands, selections = _scripted_route(prefix)
                provider = _Act3cScriptedProvider(package, state, selections)
                ask_commands = (
                    [RECOVERY_COMMAND] if prefix == "stall" else [BROADCAST_COMMAND, ARCHIVE_COMMAND, CLEAN_COMMAND]
                )
                ask = _scripted_player(ask_commands, budget)
            else:
                scripted_commands = (
                    [BROADCAST_COMMAND, ARCHIVE_COMMAND, *NEUTRAL_COMMANDS]
                    if prefix == "stall"
                    else list(SCRIPTED_PREFIXES[prefix])
                )
                provider = provider_for(state, variation)
                ask = _ask_player
            context = counted_provider(provider, budget) if not dry else None
            row = (
                _run_row(
                    package,
                    state,
                    provider,
                    ask,
                    budget,
                    f"act3c-{prefix}-{rep:02d}-current",
                    prefix,
                    scripted_commands,
                    trace,
                )
                if context is None
                else None
            )
            if context is not None:
                with context:
                    row = _run_row(
                        package,
                        state,
                        provider,
                        ask,
                        budget,
                        f"act3c-{prefix}-{rep:02d}-current",
                        prefix,
                        scripted_commands,
                        trace,
                    )
            rows.append(row)
            _write(out / "results.json", {"mode": "dry" if dry else "live", "rows": rows, "caps": CAPS, "n": n})
    except Exception as error:
        _write(out / "results.json", {"mode": "dry" if dry else "live", "rows": rows, "caps": CAPS, "n": n})
        _write(out / "partial-trace.json", trace)
        (out / "run-failure.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        return 1
    _write(
        out / "summary.json",
        {
            "mode": "dry" if dry else "live",
            "rows": len(rows),
            "n": n,
            "caps": CAPS,
            "cloudflare_requests": budget.cloudflare_requests,
            "player_requests": budget.raw_player_attempts,
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", choices=PREFIXES, default="none")
    parser.add_argument("--n", type=int, choices=(1,), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return run(args.out, args.prefix, args.n, args.dry_run, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
