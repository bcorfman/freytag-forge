from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.runtime.facts import Fact
from storygame.runtime.observation_preview import CallMemo, CandidatePreview
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_evidence", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def test_world_structure_records_every_entity_and_all_mutable_world_fields() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    state, _ = module._start_state(package, "observe_park_bench_1b")

    before = module._world_structure(state)
    places_before = module._places(state)
    world = world_for(package, state.facts)
    assert set(before) == set(world.entity_ids())
    assert all(set(value) == {"parent", "relation", "hidden", "axes"} for value in before.values())

    world.place("transit_card", "park_bench", under=True)
    first_digest = module._state_digest(state)
    first = module._world_structure(state)
    world.place("transit_card", "park_bench")
    world.set_axis("michelle_drawer", "open")
    state.facts.assert_fact(Fact(predicate="wk_hidden", subject="number_sequence", value="true"))
    created = world.create("borrowed lantern", parent="park_bench")
    assert created.ok
    second_digest = module._state_digest(state)
    after = module._world_structure(state)
    places_after = module._places(state)

    assert first["transit_card"]["parent"] == after["transit_card"]["parent"] == "park_bench"
    assert first["transit_card"]["relation"] == "under"
    assert after["transit_card"]["relation"] == "on"
    assert places_after == places_before
    assert first_digest != second_digest
    assert after["number_sequence"]["hidden"] is True
    assert after["michelle_drawer"]["axes"] != first["michelle_drawer"]["axes"]
    assert created.id in after


def test_world_structure_helper_handles_a_synthetic_world_with_other_names(monkeypatch) -> None:
    module = _module()

    class SyntheticWorld:
        def entity_ids(self):
            return ("lantern", "table")

        def parent(self, entity_id):
            return "table" if entity_id == "lantern" else None

        def relation(self, entity_id):
            return "on" if entity_id == "lantern" else None

        def is_hidden(self, entity_id):
            return entity_id == "lantern"

        def axis_values(self, entity_id):
            return {"lit": "yes"} if entity_id == "lantern" else {}

    monkeypatch.setattr("storygame.runtime.world_model.world_for", lambda _package, _facts: SyntheticWorld())
    state = SimpleNamespace(package=object(), facts=object())

    assert module._world_structure(state) == {
        "lantern": {"parent": "table", "relation": "on", "hidden": True, "axes": {"lit": "yes"}},
        "table": {"parent": None, "relation": None, "hidden": False, "axes": {}},
    }


def test_preview_record_contains_contract_fields_and_relations() -> None:
    module = _module()
    preview = CandidatePreview(
        required=True,
        accepted=False,
        outcome="unavailable",
        failure="ask_raised",
        verdicts=(),
        moved_unrelated=("lantern",),
        changed=("lantern",),
        facts_after={"lantern": {"place": "table"}},
        command="look at the table",
        narration="The table is bare.",
        memo=CallMemo(),
    )

    record = module._preview_record(preview, [{"thing": "lantern", "place": "table", "holder": None}])

    assert record == {
        "outcome": "unavailable",
        "failure": "ask_raised",
        "accepted": False,
        "required": True,
        "moved_unrelated": ["lantern"],
        "changed": ["lantern"],
        "relations": [{"thing": "lantern", "place": "table", "holder": None}],
        "narration": "The table is bare.",
    }
    json.dumps(record)


def test_turn_outcome_classification_covers_all_terminal_states() -> None:
    module = _module()
    assert module._turn_outcome("A change.", None) == "committed"
    assert module._turn_outcome(None, None) == "rejected"
    assert module._turn_outcome(None, "MAX_CALLS_EXCEEDED") == "stopped_call_cap"
    assert module._turn_outcome(None, "AI_QUOTA_EXCEEDED") == "stopped_quota"


def test_rejected_preview_terminals_keep_world_and_legacy_places_unchanged() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    state, _ = module._start_state(package, "observe_park_bench_1b")
    places_before = module._places(state)
    world_before = module._world_structure(state)
    digest_before = module._state_digest(state)
    cases = (
        CandidatePreview(
            required=True,
            accepted=False,
            outcome="unrelated_move",
            failure="unrelated_move",
            verdicts=(),
            moved_unrelated=("lantern",),
            changed=("lantern",),
            facts_after=None,
            command="look under the table",
            narration="Nothing moves.",
            memo=CallMemo(),
        ),
        CandidatePreview(
            required=True,
            accepted=False,
            outcome="unavailable",
            failure="ask_raised",
            verdicts=(),
            moved_unrelated=(),
            changed=(),
            facts_after=None,
            command="look under the table",
            narration="Nothing moves.",
            memo=CallMemo(),
        ),
        CandidatePreview(
            required=True,
            accepted=False,
            outcome="budget_exhausted",
            failure="request_budget",
            verdicts=(),
            moved_unrelated=(),
            changed=(),
            facts_after=None,
            command="look under the table",
            narration="Nothing moves.",
            memo=CallMemo(),
        ),
    )

    for preview in cases:
        evidence = module._preview_record(preview, [])
        assert evidence["accepted"] is False
        assert module._places(state) == places_before
        assert module._world_structure(state) == world_before
        assert module._state_digest(state) == digest_before


def test_call_cap_fixture_distinguishes_logical_verifier_request_from_http_call() -> None:
    module = _module()
    row = {
        "verifier_requests": 1,
        "verifier_http_calls": module._verifier_http_calls([]),
        "turn_outcome": module._turn_outcome(None, "MAX_CALLS_EXCEEDED"),
    }

    assert row == {
        "verifier_requests": 1,
        "verifier_http_calls": 0,
        "turn_outcome": "stopped_call_cap",
    }


def test_real_call_cap_inside_preview_records_logical_request_without_http_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from storygame.runtime.capture import WorldCapture
    from storygame.runtime.observation import ObservationContext, ObservationRequest
    from storygame.runtime.observation_verifier import Relation
    from tests.test_live_baseline_enforce import _run_live

    module = _module()
    original_before_call = module.CallCounter.before_call
    original_before_turn = WorldCapture.before_turn

    def force_observation(self, command):
        result = original_before_turn(self, command)
        self.provider.observation_request = ObservationRequest(command, "look", "michelle_drawer")
        return result

    monkeypatch.setattr(WorldCapture, "before_turn", force_observation)
    monkeypatch.setattr(
        WorldCapture,
        "_observation_context_for_verification",
        lambda _self, entered_scene: ObservationContext(
            observer="observer",
            action="look",
            completed_actions=(),
            visible_things=(),
            contingent_things=(),
            required=("drawer",),
            omitted_optional=(),
            scope_complete=True,
        ),
    )
    monkeypatch.setattr(
        "storygame.runtime.capture.relations_from_context",
        lambda _context: (Relation(thing="drawer", place="kitchen"),),
    )

    def stop_before_preview(self):
        if self.calls_made >= 4:
            self.stop_reason = "MAX_CALLS_EXCEEDED"
            raise module.CallCapExceeded("max-calls exceeded")
        return original_before_call(self)

    monkeypatch.setattr(module.CallCounter, "before_call", stop_before_preview)
    turns, _ = _run_live(monkeypatch, module, tmp_path / "cap", turns=1)
    turn = turns[0]

    assert turn["turn_outcome"] == "stopped_call_cap"
    assert turn["verifier_requests"] == 1
    assert turn["verifier_http_calls"] == 0
    assert turn["state_unchanged"] is False


def test_opening_item_facts_are_collected_from_nested_provider_json() -> None:
    module = _module()
    responses = [
        json.dumps(
            {
                "narration": json.dumps(
                    {
                        "segments": [{"kind": "narration", "text": "A lantern waits."}],
                        "item_facts": {"lantern": {"place": "table"}},
                    }
                )
            }
        ),
        "not JSON",
    ]

    assert module._proposed_item_facts(responses) == [{"lantern": {"place": "table"}}]


def test_enforced_row_evidence_is_serializable_and_preserves_legacy_values(tmp_path) -> None:
    module = _module()
    output = tmp_path / "run"
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "movement",
                "--replicates",
                "1",
                "--turns",
                "1",
                "--enforce",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    row = json.loads((output / "rows.json").read_text())[0]
    turn = row["turns"][0]

    assert turn["before"] == turn["places_before"]
    assert turn["after"] == turn["places_after"]
    assert turn["turn_outcome"] == "committed"
    assert turn["state_unchanged"] is False
    assert isinstance(turn["world_before"], dict)
    assert isinstance(turn["world_after"], dict)
    assert len(turn["previews"]) == 1
    json.dumps(row)


def test_opening_evidence_is_only_added_when_enforcing(tmp_path) -> None:
    module = _module()
    output = tmp_path / "run"
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_park_bench_1b",
                "--replicates",
                "1",
                "--turns",
                "0",
                "--enforce",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    opening = json.loads((output / "rows.json").read_text())[0]["opening"]
    assert {
        "world_before",
        "world_after",
        "state_digest_before",
        "state_digest_after",
        "state_unchanged",
        "proposed_item_facts",
    } <= set(opening)
    assert opening["state_unchanged"] is True
