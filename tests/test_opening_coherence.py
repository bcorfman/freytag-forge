from __future__ import annotations

from storygame.llm.opening_coherence import opening_coherence_issues


def test_opening_coherence_detects_generic_role_conflicts_for_named_characters() -> None:
    lines = [
        "Mina Cole, your assistant, keeps pace at your shoulder.",
        "Mina Cole is the prime suspect you came here to expose.",
    ]

    issues = opening_coherence_issues(
        lines,
        assistant_name="Mina Cole",
        actionable_objective="Review the evidence and choose which lead to press first.",
        item_labels=("route key",),
        character_names=("Mina Cole", "Victor Hale"),
    )

    assert any("mina cole" in issue.lower() and "role" in issue.lower() for issue in issues)


def test_opening_coherence_detects_generic_item_state_conflicts() -> None:
    lines = [
        "Victor Hale carries the route key in one gloved hand.",
        "The route key rests in the mud beside the gate.",
    ]

    issues = opening_coherence_issues(
        lines,
        assistant_name="Mina Cole",
        actionable_objective="Review the grounds and identify the strongest lead.",
        item_labels=("route key", "case file"),
        character_names=("Mina Cole", "Victor Hale"),
    )

    assert any("route key" in issue.lower() and "victor hale" in issue.lower() for issue in issues)


def test_opening_coherence_reports_multiple_generic_conflicts() -> None:
    lines = [
        "You are the detective.",
        "Mina Cole, your assistant, keeps pace at your shoulder.",
        "Mina Cole is the prime suspect you came here to expose.",
        "Victor Hale carries the route key in one gloved hand while the route key rests in the mud beside the gate.",
    ]

    issues = opening_coherence_issues(
        lines,
        assistant_name="Mina Cole",
        actionable_objective="Interview Mina Cole about her involvement before anyone else slips away.",
        item_labels=("route key", "case file"),
        character_names=("Mina Cole", "Victor Hale"),
    )

    assert any("mina cole" in issue.lower() and "role" in issue.lower() for issue in issues)
    assert any("mina cole" in issue.lower() and "question target" in issue.lower() for issue in issues)
    assert any("route key" in issue.lower() and "victor hale" in issue.lower() for issue in issues)


def test_opening_coherence_catches_subtle_assistant_question_target_conflict() -> None:
    lines = [
        "As the Detective looked around, they noticed Daria Stone, the assistant assigned to help with the case.",
        "The Detective's gaze fell to the ledger page clutched in Daria's hand.",
        "They knew they had to review the case file, question Daria, and identify the strongest lead.",
    ]

    issues = opening_coherence_issues(
        lines,
        assistant_name="Daria Stone",
        actionable_objective="Review the case file, question Daria, and identify the strongest lead.",
        item_labels=("ledger page", "case file"),
        character_names=("Daria Stone",),
    )
    assert any("daria stone" in issue.lower() and "question target" in issue.lower() for issue in issues)
