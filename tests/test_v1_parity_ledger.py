from __future__ import annotations

from pathlib import Path

import yaml

LEDGER_PATH = Path(".plans/v1-parity-ledger.yaml")
REQUIRED_ENTRY_FIELDS = {
    "id",
    "capability",
    "player_visible_example",
    "authoring_declarations",
    "canonical_v2_fact_state",
    "proposal_validation_contract",
    "persistence_artifact_impact",
    "cross_genre_test_cases",
    "intentional_v2_difference",
}
EXPECTED_GENRES = {"mystery", "fantasy", "sci-fi", "relationship"}


def test_phase_zero_ledger_describes_v2_targets_not_v1_behavior() -> None:
    ledger = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))

    assert ledger["schema_version"] == "v1-parity-ledger-v2-targets"
    assert ledger["baseline_scope"] == "intended_v2_capability"
    assert ledger["entries"]
    assert ledger["historical_evidence_policy"]
    assert "conversation_led_exploration" in {entry["id"] for entry in ledger["entries"]}

    for entry in ledger["entries"]:
        assert entry.keys() >= REQUIRED_ENTRY_FIELDS
        assert set(entry["cross_genre_test_cases"]) >= EXPECTED_GENRES
        assert entry["canonical_v2_fact_state"]
        assert entry["proposal_validation_contract"]


def test_phase_zero_ledger_has_no_retired_adapter_inventory() -> None:
    ledger = yaml.safe_load(LEDGER_PATH.read_text(encoding="utf-8"))

    assert "intentional_retirements" not in ledger
