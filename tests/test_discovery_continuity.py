from __future__ import annotations

import contextlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactDelivery, RouteOperation

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _canonical_snapshot(state: RuntimeState) -> dict[str, object]:
    snapshot = json.loads(state.snapshot().model_dump_json())

    def canonicalize(value: object, *, key: str | None = None) -> object:
        if isinstance(value, dict):
            return {item_key: canonicalize(item, key=item_key) for item_key, item in value.items()}
        if isinstance(value, list):
            items = [canonicalize(item) for item in value]
            if key == "asserted":
                return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
            return items
        return value

    return canonicalize(snapshot)  # type: ignore[return-value]


def _state_1a(*, card_recovered: bool) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.turn_index = 3
    if card_recovered:
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    return state


def test_gap_cue_is_staged_before_the_card_is_found() -> None:
    state = _state_1a(card_recovered=False)

    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing()

    assert state.staged_cue_fact_id == "continuity_initiative_known"


def test_gap_cue_is_not_staged_once_the_card_is_recovered() -> None:
    state = _state_1a(card_recovered=True)

    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing()

    cue_text = next(
        (item.cue_text for item in PACKAGE.deliveries if item.fact_id == state.staged_cue_fact_id),
        None,
    )
    assert cue_text is None or "thin gap" not in cue_text


def test_cue_is_unavailable_when_a_cost_fact_its_cue_points_toward_is_already_true() -> None:
    """Generic rule, shown on a story unrelated to the card: a cue that points at an
    earlier step is spent once that step's fact is established."""

    delivery = FactDelivery(
        fact_id="report_read",
        scene_id="2B",
        source_kind="observation",
        must_convey=(("report",), ("read",)),
        fallback_text="The report is read.",
        cue_text="Somewhere a report is waiting to be found.",
        costs=(RouteOperation(op="assert", fact_id="report_found", value=True),),
    )

    def available(*, found: bool) -> bool:
        facts = FactStore()
        if found:
            facts.assert_fact(Fact(predicate="report_found", subject="story", value="true"))
        state = SimpleNamespace(
            current_scene_id="2B",
            facts=facts,
            package=SimpleNamespace(
                deliveries=(delivery,),
                knowledge=SimpleNamespace(knowledge=()),
            ),
        )
        return RuntimeEngine._cue_reveal_available(SimpleNamespace(state=state), "report_read")

    assert available(found=False) is True
    assert available(found=True) is False


def _reveal_provider(*knowledge_ids: str):
    """Scripted narrator: each call delivers the next authored reveal (None = plain prose)."""

    queue = list(knowledge_ids)

    def provider(_command: str) -> dict[str, object]:
        knowledge_id = queue.pop(0) if queue else None
        if knowledge_id is None:
            return {"segments": [{"kind": "narration", "text": "The room is quiet."}]}
        knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
        return {
            "segments": [{"kind": "narration", "text": knowledge.delivery_text, "grounding_ids": [knowledge_id]}],
            "selected_knowledge_ids": [knowledge_id],
        }

    return provider


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true"}


def _card_parent(state: RuntimeState) -> str:
    return world_for(PACKAGE, state.facts).parent("memory_card")


def _play(state: RuntimeState, commands: list[tuple[str, str | None]]) -> RuntimeEngine:
    engine = RuntimeEngine(state, _reveal_provider(*(knowledge_id for _, knowledge_id in commands)))
    for command, _ in commands:
        engine.turn(command)
    return engine


def _staged_cue_text(state: RuntimeState) -> str | None:
    return next((item.cue_text for item in PACKAGE.deliveries if item.fact_id == state.staged_cue_fact_id), None)


def test_direct_search_commits_recovery_and_custody_together() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    _play(state, [("Search beneath the drawer.", "k_sl_1a_b_r0"), ("Examine the drawer.", None)])

    assert "memory_card_recovered" in _true_facts(state)
    assert _card_parent(state) == "kristin"
    assert "thin gap" not in (_staged_cue_text(state) or "")
    assert "SL-1A-E" not in state.active_event_ids


def test_gap_then_acquire_does_not_redeliver_either_discovery() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    _play(
        state,
        [
            ("Open the drawer.", "k_sl_1a_f_r1"),
            ("Search beneath the drawer.", "k_sl_1a_b_r0"),
            ("Examine the carved initials.", None),
        ],
    )

    assert {"drawer_gap_pointed_out", "memory_card_recovered"} <= _true_facts(state)
    assert "thin gap" not in (_staged_cue_text(state) or "")
    assert "SL-1A-F" not in state.active_event_ids


def test_recovery_and_custody_survive_a_snapshot_round_trip() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    _play(state, [("Search beneath the drawer.", "k_sl_1a_b_r0")])

    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json()))
    engine = RuntimeEngine(restored, _reveal_provider("k_sl_1a_b_r1"))
    engine.turn("Read Michelle's memory card.")

    assert "memory_card_recovered" in _true_facts(restored)
    assert "continuity_initiative_known" in _true_facts(restored)
    assert _card_parent(restored) == "kristin"


def test_putting_the_card_down_and_picking_it_up_changes_custody_only() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    _play(state, [("Search beneath the drawer.", "k_sl_1a_b_r0")])

    world_for(PACKAGE, state.facts).place("memory_card", "mcgehee_home")
    assert _card_parent(state) == "mcgehee_home"
    assert "memory_card_recovered" in _true_facts(state)
    RuntimeEngine(state, _reveal_provider(None)).turn("Look around.")
    assert "thin gap" not in (_staged_cue_text(state) or "")

    world_for(PACKAGE, state.facts).place("memory_card", "kristin")
    RuntimeEngine(state, _reveal_provider(None)).turn("Look around.")
    assert _card_parent(state) == "kristin"
    assert "memory_card_recovered" in _true_facts(state)
    assert "thin gap" not in (_staged_cue_text(state) or "")


def test_rejected_acquisition_leaves_facts_custody_and_cue_state_untouched() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = _canonical_snapshot(state)
    cue_before = state.staged_cue_fact_id
    engine = RuntimeEngine(state, _reveal_provider("k_sl_1a_b_r1"))

    with pytest.raises(ProposalValidationError):
        engine.turn("Read Michelle's memory card.")

    assert engine.last_attempt.outcome == "rejected"
    assert _canonical_snapshot(state) == before
    assert state.staged_cue_fact_id == cue_before
    assert "memory_card_recovered" not in _true_facts(state)
    assert _card_parent(state) != "kristin"


def test_acquire_then_recording_then_remaining_files_keeps_each_lead_distinct() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    _play(
        state,
        [
            ("Search beneath the drawer.", "k_sl_1a_b_r0"),
            ("Play the damaged recording on the card.", "k_sl_1a_b_r2"),
        ],
    )
    facts = _true_facts(state)
    assert {"memory_card_recovered", "michelle_warning_known"} <= facts
    assert "michelle_lead_actionable" not in facts
    assert "SL-1A-B" in state.fired_event_ids

    RuntimeEngine(state, _reveal_provider("k_sl_1a_d_r1")).turn("Read the remaining files on the card.")

    assert "michelle_lead_actionable" in _true_facts(state)
    assert _card_parent(state) == "kristin"


@pytest.mark.parametrize("turn_index", [3, 8, 11, 13])
def test_acquiring_before_pressure_or_deadline_leaves_no_gap_cue_or_escalation(turn_index: int) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.turn_index = turn_index

    engine = _play(state, [("Search beneath the drawer.", "k_sl_1a_b_r0")])
    RuntimeEngine(state, _reveal_provider(None)).turn("Look around.")

    assert "thin gap" not in (_staged_cue_text(state) or "")
    for delivery in PACKAGE.deliveries:
        if delivery.fact_id == state.staged_cue_fact_id and state.staged_cue_stage == 2:
            assert "gap" not in (delivery.escalation_text or "")
    assert engine.last_attempt.outcome == "committed"


class _WorkerReply:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _WorkerReply:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _card_grabbing_worker(monkeypatch) -> None:
    """Worst-case narrator: whatever the player says, it claims the card reveal."""

    knowledge = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    reply = {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text, "grounding_ids": ["k_sl_1a_b_r0"]}],
        "selected_knowledge_ids": ["k_sl_1a_b_r0"],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _WorkerReply(reply))


def _live_provider_turn(command: str) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    engine = RuntimeEngine(state, provider)
    with contextlib.suppress(ProposalValidationError):
        engine.turn(command)
    return state, engine


def test_live_provider_commits_the_card_for_a_command_that_reaches_it(monkeypatch) -> None:
    _card_grabbing_worker(monkeypatch)

    state, engine = _live_provider_turn("Search beneath the drawer.")

    assert engine.last_attempt.outcome == "committed"
    assert "memory_card_recovered" in _true_facts(state)
    assert _card_parent(state) == "kristin"


@pytest.mark.parametrize(
    "command",
    ["Look out the window.", "Open the KMS drawer.", "Inspect the drawer.", "Take the note.", "Inspect the back door."],
)
def test_live_provider_does_not_commit_the_card_for_a_command_that_misses_it(monkeypatch, command: str) -> None:
    _card_grabbing_worker(monkeypatch)

    state, engine = _live_provider_turn(command)

    assert engine.last_attempt.outcome == "rejected"
    assert "memory_card_recovered" not in _true_facts(state)
    assert _card_parent(state) != "kristin"


_MOVE_EFFECTS = [
    (fact_id, effect.move, effect.parent)
    for fact_id, effects in PACKAGE.world.fact_effects.items()
    for effect in effects
    if effect.move is not None
]


def _after_fact(fact_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    assert apply_world_effects(PACKAGE, state.facts) == ()
    return state


@pytest.mark.parametrize(("fact_id", "item_id", "parent_id"), _MOVE_EFFECTS)
def test_every_declared_custody_effect_lands_and_survives_a_snapshot(fact_id, item_id, parent_id) -> None:
    state = _after_fact(fact_id)
    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(RuntimeSnapshot.model_validate_json(state.snapshot().model_dump_json()))

    assert world_for(PACKAGE, state.facts).parent(item_id) == parent_id
    assert world_for(PACKAGE, restored.facts).parent(item_id) == parent_id


@pytest.mark.parametrize(("fact_id", "item_id", "parent_id"), _MOVE_EFFECTS)
def test_a_custody_effect_is_applied_once_so_later_moves_stand(fact_id, item_id, parent_id) -> None:
    state = _after_fact(fact_id)
    elsewhere = "mcgehee_home" if parent_id != "mcgehee_home" else "kristin"
    world_for(PACKAGE, state.facts).place(item_id, elsewhere)

    assert apply_world_effects(PACKAGE, state.facts) == ()

    assert world_for(PACKAGE, state.facts).parent(item_id) == elsewhere
