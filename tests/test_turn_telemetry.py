from __future__ import annotations

import json
from pathlib import Path

from factory.contract_scene import build_contract_scene
from factory.outcome_contract import classify_run
from factory.turn_telemetry import build_turn_telemetry, pacing_effects_by_event
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.pacing_replay import replay_pacing
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE_ROOT = Path(__file__).parents[1] / "data/stories/continuity-initiative"


def _bundle(**updates: object) -> dict:
    bundle = {
        "outcome": "committed",
        "story_complete": False,
        "transition_cause": "none",
        "committed_delta": {"fact_predicates": ["command_fact"]},
        "reveal_selection": {"shortlist_ids": ["k_a", "k_a"], "matched": "k_b"},
    }
    bundle.update(updates)
    return bundle


def _telemetry(**kwargs: object) -> dict:
    defaults = {
        "turn": 1,
        "player_input": "Wait.",
        "text": "Nothing changes.",
        "bundle": _bundle(),
        "grounding_ids": [],
        "replay_fired_ids": (),
        "null_grounding_ids": [],
        "fired_before": set(),
        "fired_after": set(),
        "pacing_effects": {},
    }
    defaults.update(kwargs)
    return build_turn_telemetry(**defaults)


def test_new_pacing_effects_are_subtracted_but_command_facts_remain() -> None:
    result = _telemetry(
        bundle=_bundle(committed_delta={"fact_predicates": ["clock_fact", "command_fact"]}),
        fired_before={"old_event"},
        fired_after={"old_event", "new_event"},
        pacing_effects={"old_event": ["old_fact"], "new_event": ["clock_fact"]},
    )

    assert result["committed_facts"] == ["command_fact"]


def test_earlier_event_is_not_subtracted_again() -> None:
    result = _telemetry(
        bundle=_bundle(committed_delta={"fact_predicates": ["old_fact", "command_fact"]}),
        fired_before={"old_event"},
        fired_after={"old_event"},
        pacing_effects={"old_event": ["old_fact"]},
    )

    assert result["committed_facts"] == ["old_fact", "command_fact"]
    assert result["pressure_event"] is False


def test_pressure_event_tracks_new_fired_events() -> None:
    assert _telemetry(fired_before={"a"}, fired_after={"a", "b"})["pressure_event"] is True
    assert _telemetry(fired_before={"a"}, fired_after={"a"})["pressure_event"] is False


def test_candidates_reveal_selection_and_grounding_sources() -> None:
    result = _telemetry(
        grounding_ids=["matched", "paced", "prior", "narrator"],
        bundle=_bundle(reveal_selection={"shortlist_ids": ["matched", "shortlist", "shortlist"], "matched": "matched"}),
        null_grounding_ids=["paced"],
        delivered_before=frozenset({"prior"}),
    )

    assert result["candidates_offered"] == ["matched", "shortlist"]
    assert result["matched_candidate"] == "matched"
    assert result["grounding_source"] == {
        "matched": "command_match",
        "paced": "pacing",
        "prior": "re_grounded",
        "narrator": "narrator_selection",
    }


def test_null_reveal_selection_has_no_candidates() -> None:
    result = _telemetry(bundle=_bundle(reveal_selection=None))
    assert result["candidates_offered"] == []
    assert result["matched_candidate"] is None


def test_rejected_and_game_break_fields() -> None:
    rejected = _telemetry(bundle=_bundle(outcome="rejected"))
    assert rejected["rejected"] is True
    assert rejected["game_break"] is None

    game_break = _telemetry(bundle=_bundle(outcome="game_break"))
    assert game_break["game_break"] == {"outcome": "game_break"}
    assert game_break["rejected"] is False


class _Provider:
    def __call__(self, _command: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The room remains quiet."}]}


def _engine(*, package=None, turns_since_entry: int = 0) -> RuntimeEngine:
    package = package or load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "2A")
    state.current_scene_id = "2A"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2A")
    state.turn_index = state.scene_entered_at_turn + turns_since_entry
    return RuntimeEngine(state, _Provider())


def _run(engine: RuntimeEngine, package, count: int) -> list[dict]:
    event_ids = {event.id for event in package.pacing.events}
    effects = pacing_effects_by_event(package)
    records = []
    for turn in range(1, count + 1):
        replay = replay_pacing(engine)
        before = set(engine.state.fired_event_ids) & event_ids
        proposal = engine.turn("Wait and observe.", clock_seconds=1)
        after = set(engine.state.fired_event_ids) & event_ids
        bundle = engine.last_attempt.model_dump(mode="json")
        grounding_ids = [grounding_id for segment in proposal.segments for grounding_id in segment.grounding_ids]
        records.append(
            build_turn_telemetry(
                turn=turn,
                player_input="Wait and observe.",
                text=" ".join(segment.text for segment in proposal.segments),
                bundle=bundle,
                grounding_ids=grounding_ids,
                replay_fired_ids=replay.fired_event_ids,
                null_grounding_ids=list(replay.null_grounding_ids),
                fired_before=before,
                fired_after=after,
                pacing_effects=effects,
            )
        )
    return records


def test_real_engine_round_trip_has_no_unknown_telemetry() -> None:
    engine = _engine()
    package = engine.state.package
    run = {"replicate": 1, "entry_facts": [], "turns": _run(engine, package, 4)}
    result = classify_run(run, build_contract_scene(package, "2A"))
    assert all(turn["action_outcome"] != "unknown_telemetry" for turn in result["turns"])
    assert result["unresolved"] == []


def test_real_engine_round_trip_records_pacing_pressure_and_null_grounding() -> None:
    package = load_story_package(PACKAGE_ROOT)
    event = next(event for event in package.pacing.events if event.id == "inspection_window_2a")
    event = event.model_copy(update={"delivers": ("k_inspection_window_missed",)})
    pacing_events = tuple(event if candidate.id == event.id else candidate for candidate in package.pacing.events)
    pacing = package.pacing.model_copy(update={"events": pacing_events})
    package = package.model_copy(update={"pacing": pacing})
    engine = _engine(package=package, turns_since_entry=4)
    effects = pacing_effects_by_event(package)
    replay = replay_pacing(engine)
    record = _run(engine, package, 1)[0]
    fired = set(replay.fired_event_ids)
    assert record["pressure_event"] is True
    assert record["null_grounding_ids"] == list(replay.null_grounding_ids)
    assert not set().union(*(effects[event_id] for event_id in fired)) & set(record["committed_facts"])


def test_output_is_json_serialisable_and_deterministic() -> None:
    first = _telemetry(grounding_ids=["g"])
    second = _telemetry(grounding_ids=["g"])
    assert first == second
    json.dumps(first)


def test_pacing_effects_are_sorted() -> None:
    package = load_story_package(PACKAGE_ROOT)
    effects = pacing_effects_by_event(package)
    assert all(facts == sorted(facts) for facts in effects.values())
