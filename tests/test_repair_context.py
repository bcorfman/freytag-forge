from storygame.authoring.repair_context import ChangeKind, is_additive_reference_change, repair_ledger, structural_diff


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
        "consequences": [{"id": "consequence_a"}],
        "storylets": [{"id": "storylet_a"}],
        "end_states": [{"id": "ending_a"}],
    }


def test_repair_ledger_uses_all_declared_namespaces_and_maps_opportunity_truth() -> None:
    ledger = repair_ledger(_candidate())

    assert ledger is not None
    assert ledger["optional_beat_ids"] == ["optional_a"]
    assert ledger["consequence_ids"] == ["consequence_a"]
    assert ledger["storylet_ids"] == ["storylet_a"]
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


def test_additive_reference_change_allows_new_declaration_without_rewriting_old_references() -> None:
    previous = _candidate()
    current = _candidate()
    current["evidence_opportunities"] = [
        *current["evidence_opportunities"],
        {"id": "opportunity_b", "truth_id": "truth_a", "route_id": "route_a"},
    ]
    current["realization_routes"][0]["opportunity_ids"] = ["opportunity_a", "opportunity_b"]

    reference_change = structural_diff(previous, current).changes[-1]

    assert reference_change.kind is ChangeKind.REFERENCE
    assert is_additive_reference_change(
        reference_change,
        previous,
        current,
        ("terminal truth 'truth_a' lacks a causal evidence/route chain",),
    )


def test_additive_reference_change_rejects_replacement_of_existing_references() -> None:
    previous = _candidate()
    current = _candidate()
    current["evidence_opportunities"] = [
        *current["evidence_opportunities"],
        {"id": "opportunity_b", "truth_id": "truth_a", "route_id": "route_a"},
    ]
    current["realization_routes"][0]["opportunity_ids"] = ["opportunity_b"]

    reference_change = structural_diff(previous, current).changes[-1]

    assert reference_change.kind is ChangeKind.REFERENCE
    assert not is_additive_reference_change(
        reference_change,
        previous,
        current,
        ("terminal truth 'truth_a' lacks a causal evidence/route chain",),
    )
