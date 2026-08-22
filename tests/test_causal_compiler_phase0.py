"""Phase 0 characterization for causal compiler symbol references."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from storygame.authoring.blueprint_compiler import _reference_inventory
from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from tests.test_causal_story_contract import _story

FIXTURE_PATH = Path("tests/fixtures/causal_compiler_phase0.json")


def _fixtures() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_phase0_fixture_covers_every_reference_namespace() -> None:
    namespaces = _fixtures()["namespaces"]

    assert set(namespaces) == {
        "truth",
        "participant",
        "location",
        "connected_route",
        "causal_event",
        "evidence_opportunity",
        "realization_route",
        "revelation",
        "required_outcome",
        "required_beat",
    }
    assert all(namespaces.values())


def test_phase0_reference_inventory_is_sorted_and_maps_opportunities_to_truths() -> None:
    inventory = _reference_inventory(_story())

    assert inventory is not None
    assert inventory["truth_ids"] == sorted(inventory["truth_ids"])
    assert inventory["realization_route_ids"] == [
        "commit",
        "commit_testimony",
        "diagnose_log",
        "diagnose_scan",
    ]
    assert inventory["evidence_opportunity_truth_ids"]["scan"] == "failure"


def test_phase0_records_known_wrong_namespace_and_ambiguous_cases() -> None:
    cases = _fixtures()["cases"]

    assert cases["known"]["expected_code"] is None
    assert cases["wrong_namespace"]["supplied_namespace"] != cases["wrong_namespace"]["expected_namespace"]
    assert cases["ambiguous"]["matching_namespaces"] == ["truth", "participant"]


def test_phase0_multiple_reference_errors_have_stable_order() -> None:
    first = deepcopy(_story())
    first["evidence_opportunities"][0]["route_id"] = "missing_scan_route"
    first["evidence_opportunities"][1]["route_id"] = "missing_log_route"

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(first)

    assert raised.value.code == "UNKNOWN_REFERENCE"
    assert raised.value.detail == _fixtures()["cases"]["multiple_errors"]["expected_detail"]

    second = deepcopy(_story())
    second["evidence_opportunities"][:2] = reversed(second["evidence_opportunities"][:2])
    second["evidence_opportunities"][0]["route_id"] = "missing_log_route"
    second["evidence_opportunities"][1]["route_id"] = "missing_scan_route"

    with pytest.raises(CausalValidationError) as repeated:
        validate_causal_compiled_story(second)

    assert repeated.value.detail == (
        "invalid opportunity references: log.route_id->missing_log_route, scan.route_id->missing_scan_route"
    )


@pytest.mark.parametrize("genre", ["mystery", "fantasy", "sci-fi", "relationship"])
def test_phase0_baseline_uses_the_same_reference_contract_across_genres(genre: str) -> None:
    candidate = _story()
    candidate["genre"] = genre
    candidate["profile"] = genre
    candidate["id"] = f"phase0_{genre.replace('-', '_')}"

    assert validate_causal_compiled_story(candidate).genre == genre
