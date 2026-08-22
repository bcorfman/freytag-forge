from storygame.authoring.repair_context import ChangeKind, repair_ledger, structural_diff


def _candidate() -> dict[str, object]:
    return {
        "truths": [{"id": "truth_a"}],
        "participants": [{"id": "person_a"}],
        "locations": [{"id": "room_a"}],
        "connected_routes": [],
        "causal_events": [{"id": "event_a"}],
        "evidence_opportunities": [{"id": "opportunity_a", "truth_id": "truth_a", "route_id": "route_a"}],
        "realization_routes": [{"id": "route_a", "opportunity_ids": ["opportunity_a"]}],
        "revelations": [{"id": "revelation_a"}],
        "required_outcomes": [{"id": "outcome_a"}],
        "required_beats": [{"id": "beat_a"}],
        "optional_beats": [{"id": "optional_a"}],
        "end_states": [{"id": "ending_a"}],
    }


def test_repair_ledger_uses_all_declared_namespaces_and_maps_opportunity_truth() -> None:
    ledger = repair_ledger(_candidate())

    assert ledger is not None
    assert ledger["optional_beat_ids"] == ["optional_a"]
    assert ledger["end_state_ids"] == ["ending_a"]
    assert ledger["evidence_opportunity_truth_ids"] == {"opportunity_a": "truth_a"}


def test_structural_diff_classifies_rename_ownership_and_reference_changes() -> None:
    previous = _candidate()
    current = _candidate()
    current["truths"] = [{"id": "truth_renamed"}]
    current["evidence_opportunities"] = [{"id": "opportunity_a", "truth_id": "truth_renamed", "route_id": "route_b"}]

    diff = structural_diff(previous, current)

    assert [change.kind for change in diff.changes] == [
        ChangeKind.RENAME,
        ChangeKind.OWNERSHIP,
        ChangeKind.REFERENCE,
    ]
    assert diff.changes[0].previous_identifier == "truth_a"
    assert diff.changes[1].path.endswith("route_id")


def test_structural_diff_reports_unrelated_declaration_removal() -> None:
    previous = _candidate()
    current = _candidate()
    current["participants"] = []

    diff = structural_diff(previous, current)

    assert diff.changes[0].kind is ChangeKind.REMOVAL
    assert diff.changes[0].namespace.value == "participant"
