"""Phase 1 symbol-table and reference-binding contracts."""

from __future__ import annotations

from copy import deepcopy

import pytest

from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry
from tests.test_causal_story_contract import _story


def test_registry_declares_each_namespace_once_and_sorts_ids() -> None:
    registry = SymbolRegistry.from_story(validate_causal_compiled_story(_story()))

    assert registry.ids(Namespace.TRUTH) == ("constraint", "failure", "opening", "remedy", "tradeoff")
    assert registry.ids(Namespace.REALIZATION_ROUTE) == (
        "commit",
        "commit_testimony",
        "diagnose_log",
        "diagnose_scan",
    )


def test_binding_aggregates_unknown_and_wrong_namespace_references() -> None:
    candidate = deepcopy(_story())
    participant_id = candidate["participants"][0]["id"]
    candidate["opening_truth_ids"] = [participant_id, "missing_truth"]
    candidate["connected_routes"][0]["from_location_id"] = candidate["truths"][0]["id"]

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(candidate)

    assert raised.value.code == "UNKNOWN_REFERENCE"
    assert (
        f"opening_truth_ids[0]: expected truth, supplied '{participant_id}' (participant namespace)"
        in raised.value.detail
    )
    assert "opening_truth_ids[1]: expected truth, supplied 'missing_truth'" in raised.value.detail
    assert "connected_routes[0].from_location_id: expected location" in raised.value.detail


def test_binding_suggests_declared_truth_for_opportunity_used_as_knowledge() -> None:
    candidate = deepcopy(_story())
    candidate["party_knowledge"] = [{"participant_id": "investigator", "truth_ids": ["scan"]}]

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(candidate)

    assert "party_knowledge[0].truth_ids[0]: expected truth, supplied 'scan'" in raised.value.detail
    assert "use truth_id 'failure'" in raised.value.detail


def test_duplicate_declarations_are_rejected_before_reference_semantics() -> None:
    candidate = deepcopy(_story())
    candidate["truths"].append(candidate["truths"][0].copy())

    with pytest.raises(CausalValidationError) as raised:
        validate_causal_compiled_story(candidate)

    assert raised.value.code == "DUPLICATE_ID"
    assert "truths[5].id" in raised.value.detail
