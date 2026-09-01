from __future__ import annotations

from pathlib import Path

from storygame.audit_llm import LABELLED_CASES, audit_frames, extract_frame_details, score, unattested_frame_details


class FakeAsker:
    def __init__(self, verdicts: list[list[bool]] | None = None) -> None:
        self.calls: list[str] = []
        self.verdicts = verdicts or []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        verdict = self.verdicts[len(self.calls) - 1] if self.verdicts else [True]
        return '{"attested": ' + str(verdict).lower().replace("'", "") + "}"


def test_extract_frame_details_surfaces_orientation() -> None:
    assert "facedown" in extract_frame_details("The phone is facedown on the kitchen floor.")


def test_unattested_details_make_one_call_for_all_details() -> None:
    asker = FakeAsker([[False, True]])
    frame = "A phone is facedown beside a card."
    details = extract_frame_details(frame)
    result = unattested_frame_details(frame, "A phone is beside a card.", asker)
    assert result == (details[0],)
    assert len(asker.calls) == 1
    assert all(f"{index}. {detail}" in asker.calls[0] for index, detail in enumerate(details, 1))


def test_audit_frames_sweeps_package_with_injected_asker() -> None:
    calls = 0

    def ask(prompt: str) -> str:
        nonlocal calls
        calls += 1
        return '{"attested": []}'

    findings = audit_frames(Path("data/stories/continuity-initiative"), ask)
    assert calls == 9
    assert findings == []


def test_score_reports_outcomes_and_metrics() -> None:
    def ask(prompt: str) -> str:
        details = [line.split(". ", 1)[1] for line in prompt.splitlines() if ". " in line and line[:1].isdigit()]
        beats = prompt.split("SCENE BEATS:\n", 1)[1]
        expected = next(case["expected"] for case in LABELLED_CASES if case["beats"] == beats)
        return '{"attested": ' + str([detail not in expected for detail in details]).lower().replace("'", "") + "}"

    result = score(ask)
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert all(outcome["passed"] for outcome in result["outcomes"])
