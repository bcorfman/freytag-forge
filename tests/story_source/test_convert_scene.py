"""Tests for lossless conversion of package-owned scene records."""

# NOTE: the current compiler accepts `kind: resolution` in validation but only
# returns bridge events; the converter still emits both contract-defined event kinds.
# NOTE: package models retain storylet and realization IDs, not authoring handles;
# tests use those IDs as deterministic handles because the compiler resolves by them.

from collections import Counter
from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source.convert_scene import convert_scenes

PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _operations(values):
    return {item.fact_id: "retract" if item.op == "retract" else item.value for item in values}


def _predicates(values):
    return {item.fact_id: item.equals for item in values}


def _claim_ids(package):
    return {
        claim.id
        for claim in package.knowledge.knowledge
        if claim.source.kind == "scene_entry"
        or claim.source.kind == "canonical_route_event"
        or any(
            (claim.source.storylet_id, claim.source.realization_id) == (outcome.storylet_id, outcome.realization_id)
            for incident in package.incidents
            for outcome in incident.outcomes
        )
    }


def test_conversion_contains_every_owned_record_once():
    package = load_story_package(PACKAGE_ROOT)
    result = convert_scenes(package)

    assert list(result.scene_docs) == [scene.metadata.scene_id for scene in package.scenes]
    assert Counter(beat["id"] for document in result.scene_docs.values() for beat in document["beats"]) == Counter(
        event.id for event in package.pacing.events
    )
    event_ids = [
        event.id for event in package.storylet_routes.bridge_events + package.storylet_routes.resolution_events
    ]
    event_claims = {}
    for claim in package.knowledge.knowledge:
        if claim.source.kind == "canonical_route_event":
            event_claims.setdefault(claim.source.canonical_event_id, []).append(claim.id)
    expected_event_ids = [
        item_id
        for event_id in event_ids
        for item_id in [event_id, *[f"{event_id}_claim_{claim_id}" for claim_id in event_claims.get(event_id, [])[1:]]]
    ]
    assert Counter(event["id"] for document in result.scene_docs.values() for event in document["bridge"]) == Counter(
        expected_event_ids
    )
    assert Counter(
        incident["id"] for document in result.scene_docs.values() for incident in document["incidents"]
    ) == Counter(incident.id for incident in package.incidents)
    assert Counter(
        claim["claim_id"] for document in result.scene_docs.values() for claim in document["entry_claims"]
    ) == Counter(claim.id for claim in package.knowledge.knowledge if claim.source.kind == "scene_entry")
    assert set(result.match_docs) == {
        claim.available_in_scenes[0] for claim in package.knowledge.knowledge if claim.id in _claim_ids(package)
    }
    assert Counter(claim_id for document in result.match_docs.values() for claim_id in document["claims"]) == Counter(
        _claim_ids(package)
    )


def test_scene_1a_and_2c_headers_and_beats_match_package():
    package = load_story_package(PACKAGE_ROOT)
    result = convert_scenes(package)

    for scene_id in ("1A", "2C"):
        scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
        frame = next(frame for frame in package.knowledge.scene_frames if frame.scene_id == scene_id)
        pacing = next(pacing for pacing in package.pacing.scenes if pacing.scene_id == scene_id)
        document = result.scene_docs[scene_id]
        assert document["scene"] == scene_id
        assert document["location"] == scene.metadata.location_id
        assert document["objective"] == scene.metadata.objective
        assert document["freytag_phase"] == scene.metadata.freytag_phase
        assert document["situation"] == frame.situation
        assert document["pressure"] == frame.pressure
        assert document["turns"] == {
            "min": pacing.min_turns,
            "nudge": pacing.nudge_after_turns,
            "handoff": pacing.handoff_after_turns,
        }
        assert document["participants"] == list(scene.metadata.participant_ids)
        assert document["items"] == list(scene.metadata.item_ids)
        expected_beats = [event for event in package.pacing.events if event.scene_id == scene_id]
        assert [beat["id"] for beat in document["beats"]] == [event.id for event in expected_beats]
        for record, event in zip(document["beats"], expected_beats, strict=False):
            assert record["at_turn"] == event.at_turn
            assert record["sets"] == _predicates(event.effects)
            assert record.get("when", {}) == _predicates(event.when)
            assert record.get("trailing", False) == event.trailing
            assert [entry["text"] for entry in record.get("say", [])] == [item.text for item in event.realizations]


def test_representative_scene_owned_records_match_package():
    package = load_story_package(PACKAGE_ROOT)
    result = convert_scenes(package)

    for scene in package.scenes[:3]:
        document = result.scene_docs[scene.metadata.scene_id]
        assert document["location"] == scene.metadata.location_id
        assert document["objective"] == scene.metadata.objective
        assert document["entry"] == scene.metadata.entry_text
        assert document["participants"] == list(scene.metadata.participant_ids)
        assert document["items"] == list(scene.metadata.item_ids)
    for transition in package.pacing.transitions[:3]:
        document = result.scene_docs[transition.source_scene_id]["exit"]
        assert document["id"] == transition.id
        assert document["to"] == transition.target_scene_id
        assert document["priority"] == transition.priority
        assert document["when_all"] == [item.fact_id for item in transition.triggers]
        assert [item["item"] for item in document["needs"]] == list(transition.required_dependencies)
    events = package.storylet_routes.bridge_events + package.storylet_routes.resolution_events
    for event in events[:3]:
        record = next(item for item in result.scene_docs[event.scene_id]["bridge"] if item["id"] == event.id)
        assert record["when"] == list(event.activation.all_facts_true)
        assert record["commits"] == _operations(event.operations)
        assert record["realized_by"] == [item.lower().replace("-", "_") for item in event.realization_storylets]
    for incident in package.incidents[:3]:
        record = next(item for item in result.scene_docs[incident.scene_id]["incidents"] if item["id"] == incident.id)
        assert record["outcomes"] == [
            item.realization_id.removeprefix(f"{item.storylet_id}-").lower().replace("-", "_")
            for item in incident.outcomes
        ]
        assert record["recovery"] == incident.recovery_storylet_id.lower().replace("-", "_")
        assert record["missed_window"] == incident.missed_window_event_id
        observed = list(incident.observation_knowledge_ids)
        outcome_claims = {
            claim.source.realization_id: claim.id
            for claim in package.knowledge.knowledge
            if claim.source.kind == "storylet_realization"
        }
        for outcome in incident.outcomes:
            claim_id = outcome_claims.get(outcome.realization_id)
            if claim_id is not None and claim_id not in observed:
                observed.append(claim_id)
        assert record["observed_by"] == observed
    entry_claims = [claim for claim in package.knowledge.knowledge if claim.source.kind == "scene_entry"]
    for claim in entry_claims[:3]:
        record = next(
            item
            for document in result.scene_docs.values()
            for item in document["entry_claims"]
            if item["claim_id"] == claim.id
        )
        assert record["says"] == claim.statement
        assert record["entities"] == list(claim.entity_ids)
        expected_audience = claim.audience.model_dump(mode="python")
        expected_audience["character_ids"] = list(expected_audience["character_ids"])
        assert record["audience"] == expected_audience


def test_match_entries_are_expanded_plain_values():
    result = convert_scenes(load_story_package(PACKAGE_ROOT))

    def assert_plain(value):
        assert not isinstance(value, tuple)
        if isinstance(value, dict):
            for child in value.values():
                assert_plain(child)
        elif isinstance(value, list):
            for child in value:
                assert_plain(child)

    assert_plain(result.scene_docs)
    assert_plain(result.match_docs)
