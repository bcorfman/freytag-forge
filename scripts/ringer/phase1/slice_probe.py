"""Bounded 1C-to-2B smoke probe; dry mode never dispatches a model request."""

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
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.runtime.world_model import apply_scene_placements, world_for  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402
from storygame.story_package.models import scene_entry_texts  # noqa: E402

CAPS = {"cloudflare": 80, "player": 40}
MAX_COMMANDS = 30
INCIDENT_FACTS = {
    "copy_numbers": "processing_numbers_copied",
    "secure_route": "service_level_access_known",
    "missed_window": "transfer_window_missed",
    "recovery": "terminal_sweep_closing",
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
)


def _state(package: Any) -> RuntimeState:
    """Build the synthetic 1C arrival used by the continuity tests."""
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1C"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "1C")
    state._assert_scene_entry_fact("1C")
    state.active_event_ids.update({"SL-1C-A", "SL-1C-B", "SL-1C-C"})
    apply_scene_placements(package, state.facts, "1C")
    world_for(package, state.facts).seed()
    return state


def _true_fact_ids(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.value == "true"}


def detect_stale_cue(cue_fact_id: str | None, facts_before: set[str]) -> bool:
    """A cue is stale when its target was already true before the turn."""
    return cue_fact_id is not None and cue_fact_id in facts_before


def _fact_ids(value: Any) -> set[str]:
    if isinstance(value, set):
        return value
    if isinstance(value, (tuple, list)):
        return {str(item) for item in value}
    return {fact.predicate for fact in value.asserted if fact.value == "true"}


def _operation_fact_ids(values: Any) -> set[str]:
    return {value if isinstance(value, str) else value.fact_id for value in values}


def classify_exit_cause(facts: Any, incident: Any) -> str:
    """Classify only from declared incident advantages and recovery facts."""
    ids = _fact_ids(facts)
    missed = INCIDENT_FACTS["missed_window"] in ids
    for outcome in incident.outcomes:
        advantages = _operation_fact_ids(outcome.advantages)
        if advantages <= ids:
            if outcome.id == "copy_numbers":
                return "copy_numbers"
            if outcome.id == "secure_route":
                return "secure_route" if not missed else "missed_window_plus_recovery"
    if missed:
        recovery = next((o for o in incident.outcomes if o.id == "secure_route"), None)
        if recovery and _operation_fact_ids(recovery.advantages) <= ids:
            return "missed_window_plus_recovery"
    return "other"


def _provider_payload(selected: str | None, text: str | None = None) -> dict[str, Any]:
    text = text or {
        "k_sl_1c_a_r1": "Kristin finds electrical load and fresh ventilation that prove the active facility.",
        "k_sl_1c_b_r2": (
            "Kristin watches the processing line and sees sedated captives alive; a woman could be Michelle."
        ),
        "k_sl_1c_c_copy_numbers": "Kristin copies the prisoner numbers and matches them to missing-person records.",
        "k_sl_1c_c_secure_route": "Brandon explains the transfer route and opens the service entrance.",
        "k_sl_1c_d_r1": "Brandon leads Kristin through the service entrance while the sweep closes in.",
        "k_sl_2a_c_r3": (
            "Kristin uses the copied prisoner numbers to support the cooling-water explanation. "
            "The supervisor grants restricted corridor access."
        ),
        "k_sl_2a_c_r4": "Kristin uses the known service route to explain the inspection approach to the supervisor.",
        "k_sl_2a_b_r1": "Kristin checks the cooling-water weakness and Brandon builds their inspection cover.",
        "k_sl_2a_e_r1": (
            "Kristin presents the inspector credentials at the facility checkpoint and reaches the facility perimeter."
        ),
        "k_sl_2a_a_r1": "Kristin explains the cooling-water risk to the supervisor.",
    }.get(selected, "The investigation continues.")
    segment: dict[str, Any] = {"kind": "narration", "text": text}
    payload: dict[str, Any] = {"segments": [segment]}
    if selected:
        segment["grounding_ids"] = [selected]
        payload["selected_knowledge_ids"] = [selected]
    return payload


class _ScriptedProvider:
    def __init__(self, state: RuntimeState, selections: list[str | None]) -> None:
        self.state = state
        self.selections = selections
        self.calls = 0
        self.request_count = 0
        self.recovery_count = 0

    def __call__(self, _command: str) -> dict[str, Any]:
        selected = self.selections[self.calls] if self.calls < len(self.selections) else None
        self.calls += 1
        self.request_count += 1
        return _provider_payload(selected)


def _scripted_player(commands: list[str], budget: SpendBudget) -> Callable[[str, SpendBudget], str]:
    iterator = iter(commands)

    def ask(_screen: str, spend: SpendBudget) -> str:
        spend.reserve("raw_player", "dry-scripted-player")
        try:
            command = next(iterator)
        except StopIteration as error:
            spend.acknowledge("raw_player", False, "script exhausted")
            raise RuntimeError("scripted player exhausted") from error
        spend.acknowledge("raw_player", True)
        return command

    return ask


def _entry_screen(package: Any, state: RuntimeState) -> str:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1C")
    return "\n\n".join(scene_entry_texts(scene.metadata, _true_fact_ids(state)))


def _commands_for(mode: str) -> tuple[list[str], list[str | None]]:
    if mode == "dry":
        return (
            [
                "Inspect the loading docks for power and ventilation.",
                "Watch the processing line for Michelle.",
                "Copy the prisoner numbers.",
                "Check the cooling-water weakness.",
                "Present the inspector credentials at the facility checkpoint.",
                "Use the copied prisoner numbers to explain the cooling-water inspection to the supervisor.",
                *["Check the restricted corridor for a safe passage."] * 5,
            ],
            [
                "k_sl_1c_a_r1",
                "k_sl_1c_b_r2",
                "k_sl_1c_c_copy_numbers",
                "k_sl_2a_b_r1",
                "k_sl_2a_e_r1",
                "k_sl_2a_c_r3",
                None,
                None,
                None,
                None,
                None,
            ],
        )
    return ([], [])


def _run_row(
    package: Any,
    state: RuntimeState,
    provider: Any,
    ask_player: Callable[[str, SpendBudget], str],
    budget: SpendBudget,
    row_id: str,
    trace: list[dict[str, str]] | None = None,
    scripted: bool = False,
) -> dict[str, Any]:
    incident = package.incidents[0]
    screen = _entry_screen(package, state)
    commands: list[str] = []
    responses: list[str] = []
    stale_cues: list[dict[str, Any]] = []
    clarifications = rejections = segments_dropped = 0
    engine = RuntimeEngine(state, provider)
    command = ask_player(screen, budget)
    turns_in_1c = 0
    while len(commands) < MAX_COMMANDS:
        before = _true_fact_ids(state)
        was_1c = state.current_scene_id == "1C"
        turn = engine.turn(command)
        commands.append(command)
        if was_1c:
            turns_in_1c += 1
        response = "\n\n".join(segment.text for segment in turn.segments)
        responses.append(response)
        if trace is not None:
            trace.append({"command": command, "response": response})
        cue = state.last_turn_delivery.cue_fact_id
        stale_cues.append({"turn": len(commands), "cue_fact_id": cue, "stale": detect_stale_cue(cue, before)})
        clarifications += int(hasattr(turn, "clarification"))
        rejections += int(bool(getattr(getattr(engine, "last_attempt", None), "rejection", None)))
        segments_dropped += state.last_turn_delivery.segments_dropped
        if scripted and state.current_scene_id == "2A":
            state.active_event_ids.add("SL-2A-C")
        if state.current_scene_id == "2B":
            ended_by = "scene_2b"
            break
        if state.story_complete:
            ended_by = "story_end"
            break
        if len(commands) >= MAX_COMMANDS:
            ended_by = "command_cap"
            break
        command = ask_player(screen + "\n\n" + "\n".join(responses), budget)
    else:
        ended_by = "command_cap"
    final_scene = state.current_scene_id
    target_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "2A")
    target_texts = set(scene_entry_texts(target_scene.metadata, _true_fact_ids(state)))
    seen = sorted(text for text in target_texts if any(text in response for response in responses))
    return {
        "row_id": row_id,
        "rep": 1,
        "arm": "current",
        "commands": commands,
        "responses": responses,
        "exit_cause": classify_exit_cause(state.facts, incident),
        "turns_in_1c": turns_in_1c,
        "entry_variants_seen": seen,
        "stale_cues": stale_cues,
        "clarification_count": clarifications,
        "rejection_count": rejections,
        "segments_dropped": segments_dropped,
        "request_count": getattr(provider, "request_count", 0),
        "recovery_count": getattr(provider, "recovery_count", 0),
        "final_scene": final_scene,
        "ended_by": ended_by,
    }


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(out: Path, n: int, dry: bool, confirm: bool) -> int:
    if not dry and not confirm:
        raise SystemExit("live mode requires --confirm")
    variation = load_variation(ROOT / "bench/variations/phase1-slice-current.json")
    package = load_story_package(Path(variation["_package_path"]))
    rows: list[dict[str, Any]] = []
    trace: list[dict[str, str]] = []
    budget = SpendBudget(80, cloudflare_limit=80, player_limit=40)
    try:
        for rep in range(1, n + 1):
            state = _state(package)
            if dry:
                commands, selections = _commands_for("dry")
                provider = _ScriptedProvider(state, selections)
                ask = _scripted_player(commands, budget)
                row = _run_row(package, state, provider, ask, budget, f"phase1-slice-{rep:02d}-current", trace, True)
            else:
                provider = provider_for(state, variation)
                with counted_provider(provider, budget):
                    row = _run_row(
                        package,
                        state,
                        provider,
                        lambda screen, b: _ask_player(screen, b),
                        budget,
                        f"phase1-slice-{rep:02d}-current",
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
    parser.add_argument("--n", type=int, required=True, choices=(1,))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return run(args.out, args.n, args.dry_run, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
