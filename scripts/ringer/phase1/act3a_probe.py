"""Bounded Act 3A live-smoke probe; dry mode never dispatches a model request."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ringer/stage7"))

try:
    from .act2_probe import (
        CAPS,
        CARRIED_FACTS_2C,
        MAX_COMMANDS,
        SpendBudget,
        _ask_player,
        _fact_ids,
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
    from act2_probe import (
        CAPS,
        CARRIED_FACTS_2C,
        MAX_COMMANDS,
        SpendBudget,
        _ask_player,
        _fact_ids,
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

from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.runtime.world_model import apply_scene_placements, world_for  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402
from storygame.story_package.models import scene_entry_texts  # noqa: E402

SCENE = "3A"
SUCCESSOR = "3B"
LEDGER_FACTS = {
    "transmit": (
        "rebecca_offer_active",
        "antagonist_split_known",
        "committed_to_transmit",
        "detention_sectors_sealed",
        "purge_clock_started",
        "evidence_ready_to_transmit",
        "combined_broadcast_rescue_plan_known",
        "rebecca_office_required_for_broadcast",
    ),
    "rescue": (
        "rebecca_offer_active",
        "antagonist_split_known",
        "committed_to_rescue",
        "evidence_not_transmitted",
        "purge_clock_started",
        "evidence_ready_to_transmit",
        "combined_broadcast_rescue_plan_known",
        "rebecca_office_required_for_broadcast",
    ),
}
DRY_COMMANDS = (
    "Get down into the detention sector and find Michelle where she is running her network.",
    "Go to the medical level and document what was done to the prisoners there.",
    "Meet the imprisoned official and request the emergency gate authorization.",
    "Signal the prisoners to start the uprising at the checkpoints.",
)
DRY_SELECTIONS = ("k_sl_3a_a_r1", "k_sl_3a_b_r1", "k_sl_3a_d_r1", "k_sl_3a_c_r1")
DRY_TAIL_COMMAND = "Observe the prisoners moving through the checkpoints."
ROW_FIELDS = (
    "row_id",
    "rep",
    "arm",
    "scene",
    "ledger",
    "commands",
    "responses",
    "ended_by",
    "final_scene",
    "turns",
    "turns_in_scene",
    "stale_cues",
    "clarification_count",
    "rejection_count",
    "segments_dropped",
    "request_count",
    "recovery_count",
    "repeated_response_streak_max",
    "stuck_loop",
    "final_true_facts",
    "exit_cause",
    "reunion_seen_turn",
    "signal_seen_turn",
    "entry_variant_seen",
    "reunion_text_unhurried",
    "signal_text_gives_signal",
)


def _state(package: Any, ledger: str) -> RuntimeState:
    if ledger not in LEDGER_FACTS:
        raise ValueError(f"unknown ledger: {ledger}")
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = SCENE
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == SCENE)
    state._assert_scene_entry_fact(SCENE)
    for fact_id in (*CARRIED_FACTS_2C, *LEDGER_FACTS[ledger]):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    assert set(LEDGER_FACTS[ledger]) <= _fact_ids(state.facts)
    apply_scene_placements(package, state.facts, SCENE)
    world_for(package, state.facts).seed()
    return state


def _entry_screen(package: Any, state: RuntimeState) -> str:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == state.current_scene_id)
    return "\n\n".join(scene_entry_texts(scene.metadata, _true_fact_ids(state)))


def _knowledge_texts(package: Any, ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(item.delivery_text for item in package.knowledge.knowledge if item.id in ids and item.delivery_text)


def _first_seen(texts: tuple[str, ...], turns: list[dict[str, Any]], responses: list[str]) -> int | None:
    return next(
        (
            turn["turn"]
            for turn, response in zip(turns, responses, strict=True)
            if any(text in response for text in texts)
        ),
        None,
    )


def _first_reveal(ids: tuple[str, ...], turns: list[dict[str, Any]]) -> int | None:
    return next((turn["turn"] for turn in turns if set(ids) & set(turn["committed_reveals"])), None)


def _provider_payload(package: Any, selected: str | None) -> dict[str, Any]:
    text = next(
        (item.delivery_text for item in package.knowledge.knowledge if item.id == selected),
        "The investigation continues.",
    )
    segment: dict[str, Any] = {"kind": "narration", "text": text}
    payload: dict[str, Any] = {"segments": [segment]}
    if selected:
        segment["grounding_ids"] = [selected]
        payload["selected_knowledge_ids"] = [selected]
    return payload


class _Act3aScriptedProvider(_ScriptedProvider):
    def __init__(self, package: Any, state: RuntimeState, selections: list[str | None]) -> None:
        super().__init__(state, selections)
        self.package = package

    def __call__(self, _command: str) -> dict[str, Any]:
        selected = self.selections[self.calls] if self.calls < len(self.selections) else None
        self.calls += 1
        self.request_count += 1
        return _provider_payload(self.package, selected)


def _run_row(
    package: Any,
    state: RuntimeState,
    provider: Any,
    ask_player: Callable[[str, SpendBudget], str],
    budget: SpendBudget,
    row_id: str,
    ledger: str,
    trace: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    screen = _entry_screen(package, state)
    command = ask_player(screen, budget)
    commands: list[str] = []
    responses: list[str] = []
    stale_cues: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    clarifications = rejections = segments_dropped = 0
    engine = RuntimeEngine(state, provider)
    turns_in_scene = 0
    previous_response: str | None = None
    response_streak = repeated_response_streak_max = 0
    last_transition_cause: Any = None
    while len(commands) < MAX_COMMANDS:
        scene_before = state.current_scene_id
        before_keys = _fact_keys(state)
        before = _true_fact_ids(state)
        before_reveals = {reveal_id for record in state.turn_records for reveal_id in record.reveal_ids}
        request_before = getattr(provider, "request_count", 0)
        recovery_before = getattr(provider, "recovery_count", 0)
        attempts = getattr(engine, "attempts", None)
        attempts_before = len(attempts) if attempts is not None else None
        was_scene = state.current_scene_id == SCENE
        turn = engine.turn(command)
        commands.append(command)
        if was_scene:
            turns_in_scene += 1
        response = "\n\n".join(segment.text for segment in turn.segments)
        responses.append(response)
        repeated = response == previous_response
        response_streak = response_streak + 1 if repeated else 1
        repeated_response_streak_max = max(repeated_response_streak_max, response_streak)
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
        rejection = getattr(last_attempt, "rejection", None)
        rejections += int(bool(rejection))
        segments_dropped += state.last_turn_delivery.segments_dropped
        after_keys = _fact_keys(state)
        committed = (
            sorted({reveal_id for record in state.turn_records for reveal_id in record.reveal_ids} - before_reveals)
            if state.turn_records
            else []
        )
        last_transition_cause = getattr(last_attempt, "transition_cause", None)
        turns.append(
            {
                "turn": len(commands),
                "scene_before": scene_before,
                "scene_after": state.current_scene_id,
                "facts_newly_asserted": sorted(after_keys - before_keys),
                "facts_retracted": sorted(before_keys - after_keys),
                "committed_reveals": committed,
                "reveal_selection": _reveal_selection(provider, last_attempt),
                "last_attempt_rejection": _model_dump(rejection),
                "transition_cause": last_transition_cause,
                "request_count_delta": getattr(provider, "request_count", 0) - request_before,
                "recovery_count_delta": getattr(provider, "recovery_count", 0) - recovery_before,
                "staged_cue_fact_id": state.staged_cue_fact_id,
                "staged_handoff_fact_ids": sorted(state.staged_handoff_fact_ids),
                "delivered_cue_ids": sorted(state.delivered_cue_ids),
                "segments_dropped": state.last_turn_delivery.segments_dropped,
                "repeated_response": repeated,
                "scripted": False,
            }
        )
        if state.current_scene_id != SCENE:
            ended_by = f"scene_{state.current_scene_id.lower()}"
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

    reunion_ids = ("k_sl_3a_a_r1", "k_sl_3a_a_r2")
    signal_ids = ("k_sl_3a_c_r1", "k_sl_3a_c_r2")
    reunion_texts = _knowledge_texts(package, reunion_ids)
    signal_texts = _knowledge_texts(package, signal_ids)
    reunion_seen = _first_seen(reunion_texts, turns, responses) or _first_reveal(reunion_ids, turns)
    signal_seen = _first_seen(signal_texts, turns, responses) or _first_reveal(signal_ids, turns)
    reunion_response = responses[reunion_seen - 1] if reunion_seen else ""
    signal_response = responses[signal_seen - 1] if signal_seen else ""
    scene = next(item for item in package.scenes if item.metadata.scene_id == SCENE)
    rescue_variants = [
        variant.text for variant in scene.metadata.entry_variants if "committed_to_rescue" in variant.requires
    ]
    entry_variant_seen = sorted(
        text for text in rescue_variants if text in screen or any(text in item for item in responses)
    )
    changed = any(turn["scene_after"] != SCENE for turn in turns)
    exit_cause = (
        "earned_transition"
        if changed and last_transition_cause == "earned"
        else "other_transition"
        if changed
        else "none"
    )
    return {
        "row_id": row_id,
        "rep": 1,
        "arm": "current",
        "scene": SCENE,
        "ledger": ledger,
        "commands": commands,
        "responses": responses,
        "ended_by": ended_by,
        "final_scene": state.current_scene_id,
        "turns": turns,
        "turns_in_scene": turns_in_scene,
        "stale_cues": stale_cues,
        "clarification_count": clarifications,
        "rejection_count": rejections,
        "segments_dropped": segments_dropped,
        "request_count": getattr(provider, "request_count", 0),
        "recovery_count": getattr(provider, "recovery_count", 0),
        "repeated_response_streak_max": repeated_response_streak_max,
        "stuck_loop": repeated_response_streak_max >= 3,
        "final_true_facts": sorted(_true_fact_ids(state)),
        "exit_cause": exit_cause,
        "reunion_seen_turn": reunion_seen,
        "signal_seen_turn": signal_seen,
        "entry_variant_seen": entry_variant_seen,
        "reunion_text_unhurried": "unhurried" in reunion_response.lower(),
        "signal_text_gives_signal": any(
            phrase in signal_response.lower() for phrase in ("gives the signal", "give the signal")
        ),
    }


def run(out: Path, ledger: str, n: int, dry: bool, confirm: bool) -> int:
    if not dry and not confirm:
        raise SystemExit("live mode requires --confirm")
    if ledger not in LEDGER_FACTS:
        raise ValueError(f"unknown ledger: {ledger}")
    variation = load_variation(ROOT / "bench/variations/phase1-slice-current.json")
    package = load_story_package(Path(variation["_package_path"]))
    rows: list[dict[str, Any]] = []
    trace: list[dict[str, str]] = []
    budget = SpendBudget(80, cloudflare_limit=80, player_limit=40)
    try:
        for rep in range(1, n + 1):
            state = _state(package, ledger)
            if dry:
                provider = _Act3aScriptedProvider(package, state, list(DRY_SELECTIONS))
                ask = _scripted_player(list(DRY_COMMANDS) + [DRY_TAIL_COMMAND] * 5, budget)
            else:
                provider = provider_for(state, variation)
                ask = _ask_player
            context = counted_provider(provider, budget) if not dry else None
            if context is None:
                row = _run_row(
                    package, state, provider, ask, budget, f"act3a-{ledger}-{rep:02d}-current", ledger, trace
                )
            else:
                with context:
                    row = _run_row(
                        package, state, provider, ask, budget, f"act3a-{ledger}-{rep:02d}-current", ledger, trace
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
    parser.add_argument("--ledger", choices=tuple(LEDGER_FACTS), default="transmit")
    parser.add_argument("--n", type=int, choices=(1,), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    return run(args.out, args.ledger, args.n, args.dry_run, args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
