"""Bounded Act 2 live-smoke probe; dry mode never dispatches a model request.

Synthetic arrivals carry no whole-game history.  Scene 2A starts with only its
entry fact.  Scene 2B carries ``restricted_corridor_access`` and
``supervisor_convinced`` from the clean 2A exit.  Scene 2C carries the clean
``SL-2B-D-R1`` durable facts: ``brandon_name_kept``, ``janus_known``,
``kristin_was_bait``, ``michelle_selected_for_resistance_influence``,
``brandon_janus_role_known``, ``brandon_claimed_reform_motive``,
``janus_evidence``, ``michelle_resistance_known``,
``michelle_reply_received``, and ``archive_crisis_understood``.  Its
``copied_janus_files`` item is placed with Kristin by the 2C scene metadata.

The prefix commands are deliberately neutral scene actions.  They use no
player request budget; the dry scripted player takes over after the prefix.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ringer/stage7"))

from door_probe import _ask_player  # noqa: E402
from door_transport import SpendBudget, counted_provider  # noqa: E402

from bench.core import load_variation, provider_for  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.runtime.world_model import apply_scene_placements, world_for  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402
from storygame.story_package.models import scene_entry_texts  # noqa: E402

try:
    from .slice_probe import (  # noqa: E402
        _fact_keys,
        _model_dump,
        _reveal_selection,
        _scripted_player,
        _ScriptedProvider,
        _true_fact_ids,
        detect_stale_cue,
    )
except ImportError:
    from slice_probe import (  # noqa: E402
        _fact_keys,
        _model_dump,
        _reveal_selection,
        _scripted_player,
        _ScriptedProvider,
        _true_fact_ids,
        detect_stale_cue,
    )

CAPS = {"cloudflare": 80, "player": 40}
MAX_COMMANDS = 30
SCENES = ("2A", "2B", "2C")
SUCCESSORS = {"2A": "2B", "2B": "2C", "2C": "3A"}

SCRIPTED_PREFIXES = {
    "none": (),
    "missed_window": {
        "2A": (
            "Inspect my work order beside the facility gate.",
            "Check the facility gate for a maintenance access panel.",
            "Examine the cooling manifold for a safe footing.",
            "Trace the ventilation duct above the gate.",
            "Read my inspector badge under the gate light.",
        ),
        "2B": (
            "Inspect the archive shelves for a clear aisle.",
            "Trace the audit lights along the archive aisle.",
            "Check the medical terminal for a maintenance line.",
            "Examine the cooling-service panel behind the archive stacks.",
            "Read my notes beside the archive terminal.",
        ),
        "2C": (
            "Inspect my copied files beside the command corridor.",
            "Examine the guards at the corridor entrance.",
            "Check Rebecca's tablet for a safe passage.",
            "Trace the maintenance channel along the wall.",
            "Read the purge warning on the corridor panel.",
        ),
    },
    "stall": {
        "2A": (
            "Inspect my work order beside the facility gate.",
            "Check the facility gate for a maintenance access panel.",
            "Examine the cooling manifold for a safe footing.",
            "Trace the ventilation duct above the gate.",
            "Read my inspector badge under the gate light.",
            "Study the warning lights above the cooling manifold.",
            "Examine the nearest service pipe for vibration.",
            "Check the gate tablet for its latest reading.",
        ),
        "2B": (
            "Inspect the archive shelves for a clear aisle.",
            "Trace the audit lights along the archive aisle.",
            "Check the medical terminal for a maintenance line.",
            "Examine the cooling-service panel behind the archive stacks.",
            "Read my notes beside the archive terminal.",
            "Study the shelf labels nearest the audit lights.",
            "Inspect the floor marks between the archive stacks.",
            "Check the terminal cables for a safe path.",
        ),
        "2C": (
            "Inspect my copied files beside the command corridor.",
            "Examine the guards at the corridor entrance.",
            "Check Rebecca's tablet for a safe passage.",
            "Trace the maintenance channel along the wall.",
            "Read the purge warning on the corridor panel.",
            "Study the corridor cameras above the guards.",
            "Inspect the tablet's warning light.",
            "Examine the nearest maintenance grille.",
        ),
    },
}
PREFIXES = {prefix: values if prefix == "none" else values["2A"] for prefix, values in SCRIPTED_PREFIXES.items()}

CARRIED_FACTS_2C = (
    "brandon_name_kept",
    "janus_known",
    "kristin_was_bait",
    "michelle_selected_for_resistance_influence",
    "brandon_janus_role_known",
    "brandon_claimed_reform_motive",
    "janus_evidence",
    "michelle_resistance_known",
    "michelle_reply_received",
    "archive_crisis_understood",
)
RECOVERY_READY_FACTS = {
    "2A": "inspection_recovery_ready",
    "2B": "audit_recovery_ready",
    "2C": "purge_recovery_ready",
}
WINDOW_FACTS = {
    "2A": "inspection_window_missed",
    "2B": "audit_window_missed",
    "2C": "purge_window_missed",
}
NUDGE_EVENT_IDS = {
    "2A": "inspection_nudge_2a",
    "2B": "audit_nudge_2b",
    "2C": "purge_nudge_2c",
}
RECOVERY_KNOWLEDGE_IDS = {
    "2A": ("k_supervisor_escorting",),
    "2B": ("k_audit_window_missed",),
    "2C": ("k_purge_window_missed",),
}
DRY_NUDGE_TEXT = {
    "2A": "The shift supervisor stays close. He tells Kristin to prove what is wrong with the cooling water.",
    "2B": (
        "The shift supervisor is close to the archive stacks. Kristin must keep her confrontation with Brandon "
        "to a whisper."
    ),
    "2C": (
        "The purge alarm is active. A maintenance channel is open. Kristin must follow it without making a "
        "commitment here."
    ),
}
DRY_OUTCOME_COMMANDS = {
    "2A": (
        "Feel the cooling lines and read the gauge at the cooling manifold.",
        "Explain the cooling-water pressure reading to the supervisor.",
    ),
    "2B": (
        "Pull my own file at the archive terminals.",
        "Keep Brandon's name in the build record.",
        "Type my reply to the maintenance line.",
    ),
    "2C": ("Head to the uplink and start sending my copied files.",),
}
DRY_OUTCOME_SELECTIONS = {
    "2A": ("k_sl_2a_b_r1", "k_sl_2a_c_r5"),
    "2B": ("k_sl_2b_a_r1", "k_sl_2b_b_r4", "k_sl_2b_c_r3"),
    "2C": ("k_sl_2c_d_r3",),
}
NEUTRAL_DRY_COMMAND = {
    "2A": "Inspect the cooling manifold for a safe footing.",
    "2B": "Inspect the archive floor for a safe route.",
    "2C": "Inspect the maintenance grille for a safe route.",
}
ROW_FIELDS = (
    "row_id",
    "rep",
    "arm",
    "commands",
    "responses",
    "exit_cause",
    "turns_in_1c",
    "entry_variants_seen",
    "stale_cues",
    "clarification_count",
    "rejection_count",
    "segments_dropped",
    "request_count",
    "recovery_count",
    "final_scene",
    "ended_by",
    "turns",
    "repeated_response_streak_max",
    "final_true_facts",
    "stuck_loop",
    "prefix",
    "scripted_turns",
    "nudge_seen_turn",
    "withdrawal_seen_turn",
    "scene",
    "turns_in_scene",
    "successor_entry_variants_seen",
    "exit_seen_turn",
    "unearned_facts",
)


def _provider_payload(selected: str | None) -> dict[str, Any]:
    text = {
        "k_sl_2a_b_r1": (
            "Kristin feels the cooling lines, reads the gauge and traces the vent. The water pressure is falling on "
            'the return line, and the ventilation is hiding the drop. The shift supervisor says, "Well? What is '
            'failing, and what happens if nobody fixes it?"'
        ),
        "k_sl_2a_c_r5": (
            "Kristin proves that the genuine cooling-water pressure fault is real. She finds a ventilation fault. "
            "The shift supervisor grants access to the restricted infrastructure corridors. "
            "The limited console can report faults and cycle noncritical systems. "
            "It cannot open detention cells or change the main flood controls."
        ),
        "k_sl_2a_c_r6": (
            "Kristin gives a vague account of the cooling-water pressure fault and the ventilation fault. "
            "The shift supervisor logs them for a follow-up audit. He lets them enter the restricted infrastructure "
            "corridors under closer watch. The limited console can report faults and cycle noncritical systems. "
            "It cannot open detention cells or change the main flood controls."
        ),
        "k_sl_2b_a_r1": (
            "Kristin pulls her own file. It says she was retained to lead investigators to Corfman. Kristin was bait. "
            'The build record for the system names Brandon Corfman as an author. Brandon whispers, "Let me delete '
            'my name from the record before we copy the files. Or tell me to leave it. Your call."'
        ),
        "k_sl_2b_b_r4": (
            "Kristin pulls her own file first. It says she was retained to lead investigators to Corfman. Kristin was "
            "bait. The file names the system JANUS. The build record names Brandon Corfman as an author. "
            "Brandon admits that he helped write JANUS. He says he tried to stop it after he learned its purpose. "
            "Kristin keeps his name "
            "in the record. The JANUS files are copied. Kristin carries the copied files."
        ),
        "k_sl_2b_b_r5": (
            "Kristin pulls her own file first. It says she was retained to lead investigators to Corfman. Kristin was "
            "bait. The file names the system JANUS. The build record names Brandon Corfman as an author. "
            "Brandon admits that he helped write JANUS. He says he tried to stop it after he learned its purpose. "
            "Kristin lets him erase his name from the record. The development record now has a gap. "
            "The JANUS files are copied. Kristin carries "
            "the copied files."
        ),
        "k_sl_2b_c_r3": (
            "Kristin types one reply to the maintenance line. Michelle answers once. She is alive. "
            "She is working inside "
            "the facility. She will send a route."
        ),
        "k_sl_2c_d_r3": (
            "Rebecca offers a way to remove Charles. She promises Michelle's release. The purge order starts a clock. "
            "Kristin heads to the uplink and starts sending the copied files. The detention sectors seal. Michelle's "
            "route leads to Rebecca's secured office. The office can broadcast the evidence and open the detention "
            "cells."
        ),
        "k_sl_2c_d_r4": (
            "Rebecca offers a way to remove Charles. She promises Michelle's release. The purge order starts a clock. "
            "Kristin heads to the transfer carts and frees a cart of captives. The evidence is not transmitted. "
            "Michelle's route leads to Rebecca's secured office. The office can broadcast the evidence and open the "
            "detention cells."
        ),
    }.get(selected, "The investigation continues.")
    segment: dict[str, Any] = {"kind": "narration", "text": text}
    payload: dict[str, Any] = {"segments": [segment]}
    if selected:
        segment["grounding_ids"] = [selected]
        payload["selected_knowledge_ids"] = [selected]
    return payload


class _Act2ScriptedProvider(_ScriptedProvider):
    def __call__(self, _command: str) -> dict[str, Any]:
        selected = self.selections[self.calls] if self.calls < len(self.selections) else None
        self.calls += 1
        self.request_count += 1
        payload = _provider_payload(selected)
        if selected is None:
            scene_id = self.state.current_scene_id
            turn_number = self.calls
            if turn_number == 6:
                payload["segments"][0]["text"] += f"\n\n{DRY_NUDGE_TEXT[scene_id]}"
        return payload


def _state(package: Any, scene_id: str) -> RuntimeState:
    """Build one synthetic Act 2 scene arrival with only declared carry facts."""
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == scene_id)
    state._assert_scene_entry_fact(scene_id)
    carried = {
        "2B": ("restricted_corridor_access", "supervisor_convinced"),
        "2C": CARRIED_FACTS_2C,
    }.get(scene_id, ())
    for fact_id in carried:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    apply_scene_placements(package, state.facts, scene_id)
    world_for(package, state.facts).seed()
    return state


def _entry_screen(package: Any, state: RuntimeState) -> str:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == state.current_scene_id)
    return "\n\n".join(scene_entry_texts(scene.metadata, _true_fact_ids(state)))


def _fact_ids(value: Any) -> set[str]:
    if isinstance(value, set):
        return value
    if isinstance(value, (tuple, list)):
        return {str(item) for item in value}
    return {fact.predicate for fact in value.asserted if str(fact.value).lower() == "true"}


def _operation_fact_ids(values: Any) -> set[str]:
    return {value if isinstance(value, str) else value.fact_id for value in values}


def _recovery_fired(scene_id: str, facts: Any, explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    return RECOVERY_READY_FACTS[scene_id] in _fact_ids(facts)


def classify_exit_cause(facts: Any, incident: Any, recovery_fired: bool | None = None) -> str:
    """Classify an outcome, missed-window recovery, or neutral recovery."""
    ids = _fact_ids(facts)
    scene_id = incident.scene_id
    missed = WINDOW_FACTS[scene_id] in ids
    recovery = _recovery_fired(scene_id, facts, recovery_fired)
    if recovery and missed:
        return "missed_window_plus_recovery"
    for outcome in incident.outcomes:
        if _operation_fact_ids(outcome.advantages) <= ids:
            return outcome.id
    if recovery:
        return "neutral_recovery"
    return "other"


def _incident_fact_ids(incident: Any) -> set[str]:
    return {fact_id for outcome in incident.outcomes for fact_id in (*outcome.advantages, *outcome.costs)}


def _unearned_facts(incident: Any, facts: Any, exit_cause: str) -> list[str]:
    ids = _fact_ids(facts)
    return sorted(
        {
            fact_id
            for outcome in incident.outcomes
            if outcome.id != exit_cause
            for fact_id in (*outcome.advantages, *outcome.costs)
            if fact_id in ids
        }
    )


def _event_text(package: Any, event_id: str) -> str:
    event = next(event for event in package.pacing.events if event.id == event_id)
    return next(realization.text for realization in event.realizations)


def _knowledge_texts(package: Any, ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        knowledge.delivery_text
        for knowledge in package.knowledge.knowledge
        if knowledge.id in ids and knowledge.delivery_text
    )


def _first_seen(texts: tuple[str, ...], turns: list[dict[str, Any]], responses: list[str]) -> int | None:
    return next(
        (
            turn["turn"]
            for turn, response in zip(turns, responses, strict=True)
            if any(text in response for text in texts)
        ),
        None,
    )


def _run_row(
    package: Any,
    state: RuntimeState,
    provider: Any,
    ask_player: Callable[[str, SpendBudget], str],
    budget: SpendBudget,
    row_id: str,
    scene_id: str,
    trace: list[dict[str, str]] | None = None,
    prefix: str = "none",
) -> dict[str, Any]:
    incident = next(item for item in package.incidents if item.scene_id == scene_id)
    screen = _entry_screen(package, state)
    prefix_commands = SCRIPTED_PREFIXES[prefix] if prefix == "none" else SCRIPTED_PREFIXES[prefix][scene_id]
    prefix_index = 0
    command = prefix_commands[0] if prefix_commands else ask_player(screen, budget)
    commands: list[str] = []
    responses: list[str] = []
    stale_cues: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    clarifications = rejections = segments_dropped = 0
    engine = RuntimeEngine(state, provider)
    turns_in_scene = 0
    previous_response: str | None = None
    current_response_streak = 0
    repeated_response_streak_max = 0
    while len(commands) < MAX_COMMANDS:
        is_scripted_prefix_turn = prefix_index < len(prefix_commands)
        scene_before = state.current_scene_id
        before = _true_fact_ids(state)
        before_keys = _fact_keys(state)
        before_reveals = {reveal_id for record in state.turn_records for reveal_id in record.reveal_ids}
        request_before = getattr(provider, "request_count", 0)
        recovery_before = getattr(provider, "recovery_count", 0)
        attempts = getattr(engine, "attempts", None)
        attempts_before = len(attempts) if attempts is not None else None
        was_scene = state.current_scene_id == scene_id
        turn = engine.turn(command)
        commands.append(command)
        if was_scene:
            turns_in_scene += 1
        response = "\n\n".join(segment.text for segment in turn.segments)
        responses.append(response)
        repeated_response = response == previous_response
        current_response_streak = current_response_streak + 1 if repeated_response else 1
        repeated_response_streak_max = max(repeated_response_streak_max, current_response_streak)
        previous_response = response
        if trace is not None:
            trace.append({"command": command, "response": response})
        cue = state.last_turn_delivery.cue_fact_id
        stale_cues.append({"turn": len(commands), "cue_fact_id": cue, "stale": detect_stale_cue(cue, before)})
        clarifications += int(hasattr(turn, "clarification"))
        if attempts is None:
            last_attempt = getattr(engine, "last_attempt", None)
        else:
            last_attempt = engine.last_attempt if len(attempts) > attempts_before else None
        rejections += int(bool(getattr(last_attempt, "rejection", None)))
        segments_dropped += state.last_turn_delivery.segments_dropped
        after_keys = _fact_keys(state)
        turns.append(
            {
                "turn": len(commands),
                "scene_before": scene_before,
                "scene_after": state.current_scene_id,
                "facts_newly_asserted": sorted(after_keys - before_keys),
                "facts_retracted": sorted(before_keys - after_keys),
                "committed_reveals": sorted(
                    {reveal_id for record in state.turn_records for reveal_id in record.reveal_ids} - before_reveals
                )
                if state.turn_records
                else [],
                "reveal_selection": _reveal_selection(provider, last_attempt),
                "last_attempt_rejection": _model_dump(getattr(last_attempt, "rejection", None)),
                "transition_cause": getattr(last_attempt, "transition_cause", None),
                "request_count_delta": getattr(provider, "request_count", 0) - request_before,
                "recovery_count_delta": getattr(provider, "recovery_count", 0) - recovery_before,
                "staged_cue_fact_id": state.staged_cue_fact_id,
                "staged_handoff_fact_ids": sorted(state.staged_handoff_fact_ids),
                "delivered_cue_ids": sorted(state.delivered_cue_ids),
                "segments_dropped": state.last_turn_delivery.segments_dropped,
                "repeated_response": repeated_response,
                "scripted": is_scripted_prefix_turn,
            }
        )
        if is_scripted_prefix_turn:
            prefix_index += 1
        if state.current_scene_id != scene_id:
            ended_by = f"scene_{state.current_scene_id.lower()}"
            break
        if state.story_complete:
            ended_by = "story_end"
            break
        if len(commands) >= MAX_COMMANDS:
            ended_by = "command_cap"
            break
        if prefix_index < len(prefix_commands):
            command = prefix_commands[prefix_index]
        else:
            command = ask_player(screen + "\n\n" + "\n".join(responses), budget)
    else:
        ended_by = "command_cap"

    successor_scene = SUCCESSORS[scene_id]
    target_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == successor_scene)
    successor_texts = tuple(scene_entry_texts(target_scene.metadata, _true_fact_ids(state)))
    seen = sorted(text for text in successor_texts if any(text in response for response in responses))
    nudge_text = (_event_text(package, NUDGE_EVENT_IDS[scene_id]),)
    exit_texts = _knowledge_texts(package, RECOVERY_KNOWLEDGE_IDS[scene_id])
    nudge_seen = _first_seen(nudge_text, turns, responses)
    exit_seen = _first_seen(exit_texts, turns, responses)
    if exit_seen is None:
        exit_seen = next((turn["turn"] for turn in turns if turn["scene_after"] != scene_id), None)
    recovery = _recovery_fired(scene_id, state.facts)
    exit_cause = classify_exit_cause(state.facts, incident, recovery)
    return {
        "row_id": row_id,
        "rep": 1,
        "arm": "current",
        "commands": commands,
        "responses": responses,
        "exit_cause": exit_cause,
        "turns_in_1c": 0,
        "entry_variants_seen": seen,
        "stale_cues": stale_cues,
        "clarification_count": clarifications,
        "rejection_count": rejections,
        "segments_dropped": segments_dropped,
        "request_count": getattr(provider, "request_count", 0),
        "recovery_count": getattr(provider, "recovery_count", 0),
        "final_scene": state.current_scene_id,
        "ended_by": ended_by,
        "turns": turns,
        "repeated_response_streak_max": repeated_response_streak_max,
        "final_true_facts": sorted(_true_fact_ids(state)),
        "stuck_loop": repeated_response_streak_max >= 3,
        "prefix": prefix,
        "scripted_turns": sum(turn["scripted"] for turn in turns),
        "nudge_seen_turn": nudge_seen,
        "withdrawal_seen_turn": None,
        "scene": scene_id,
        "turns_in_scene": turns_in_scene,
        "successor_entry_variants_seen": seen,
        "exit_seen_turn": exit_seen,
        "unearned_facts": _unearned_facts(incident, state.facts, exit_cause),
    }


def _commands_for(scene_id: str, prefix: str) -> tuple[list[str], list[str | None]]:
    if prefix == "none":
        return list(DRY_OUTCOME_COMMANDS[scene_id]), list(DRY_OUTCOME_SELECTIONS[scene_id])
    neutral = NEUTRAL_DRY_COMMAND[scene_id]
    return [neutral] * (MAX_COMMANDS - len(SCRIPTED_PREFIXES[prefix][scene_id])), [None] * (
        MAX_COMMANDS - len(SCRIPTED_PREFIXES[prefix][scene_id])
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(out: Path, scene: str, n: int, dry: bool, confirm: bool, prefix: str = "none") -> int:
    if not dry and not confirm:
        raise SystemExit("live mode requires --confirm")
    if scene not in SCENES:
        raise ValueError(f"unknown scene: {scene}")
    if prefix not in PREFIXES:
        raise ValueError(f"unknown prefix: {prefix}")
    variation = load_variation(ROOT / "bench/variations/phase1-slice-current.json")
    package = load_story_package(Path(variation["_package_path"]))
    rows: list[dict[str, Any]] = []
    trace: list[dict[str, str]] = []
    budget = SpendBudget(80, cloudflare_limit=80, player_limit=40)
    try:
        for rep in range(1, n + 1):
            state = _state(package, scene)
            if dry:
                commands, selections = _commands_for(scene, prefix)
                provider = _Act2ScriptedProvider(state, selections)
                ask = _scripted_player(commands, budget)
            else:
                provider = provider_for(state, variation)

                def ask(screen: str, spend: SpendBudget) -> str:
                    return _ask_player(screen, spend)

            provider_context = counted_provider(provider, budget) if not dry else None
            if provider_context is None:
                row = _run_row(
                    package,
                    state,
                    provider,
                    ask,
                    budget,
                    f"act2-{scene.lower()}-{rep:02d}-current",
                    scene,
                    trace,
                    prefix,
                )
            else:
                with provider_context:
                    row = _run_row(
                        package,
                        state,
                        provider,
                        ask,
                        budget,
                        f"act2-{scene.lower()}-{rep:02d}-current",
                        scene,
                        trace,
                        prefix,
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
    parser.add_argument("--scene", choices=SCENES, required=True)
    parser.add_argument("--prefix", choices=tuple(PREFIXES), required=True)
    parser.add_argument("--n", type=int, required=True, choices=(1,))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return run(args.out, args.scene, args.n, args.dry_run, args.confirm, args.prefix)


if __name__ == "__main__":
    raise SystemExit(main())
