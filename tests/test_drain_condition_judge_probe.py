import json
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import drain_condition_judge_probe as probe


def frozen_cases() -> list[dict]:
    cases, _ = probe._validated_cases()
    return cases


def test_variant_question_text_names_inside_description() -> None:
    inside = "what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells"  # noqa: E501
    expected_a = {
        "type": "noul",
        "instructions": (
            "Decide whether the narration stays inside what is declared for the thing named in the state. "
            f"Treat a claim that the thing is open, ajar, lifted, covered, or entered, or a claim about {inside}, "
            "as a violation when the narration states it as fact."
        ),
        "criteria": {
            "true": f"The narration does not state that the thing is open, ajar, lifted, covered, or entered, and does not state {inside}, as fact.",  # noqa: E501
            "false": f"The narration states that the thing is open, ajar, lifted, covered, or entered, or states {inside}, as fact.",  # noqa: E501
        },
    }
    expected_b = {
        "type": "noul",
        "instructions": (
            "Decide whether the narration is consistent with the declared sentence for the thing named in the state. "
            f"It is consistent when it does not state any open, ajar, lifted, covered, or entered condition, or state {inside}, unless the declared sentence supports it. "  # noqa: E501
            "The declared sentence says whether the engine opened the thing this turn, and an opening the engine performed is supported. Looking at, approaching, kneeling beside, touching the outside, or wondering what might be inside are consistent."  # noqa: E501
        ),
        "criteria": {
            "true": f"The narration is consistent with the declared sentence. It does not state an unsupported open, ajar, lifted, covered, or entered condition or {inside}, as fact.",  # noqa: E501
            "false": f"The narration is not consistent with the declared sentence. It states an unsupported open, ajar, lifted, covered, or entered condition or {inside}, as fact.",  # noqa: E501
        },
    }
    expected_c = {
        **expected_b,
        "instructions": expected_b["instructions"]
        + " A condition or contents that the declared sentence does not mention is not supported.",
    }

    assert probe._variant_a_question() == expected_a
    assert probe._variant_b_question() == expected_b
    assert probe._variant_c_question() == expected_c


def test_lock_detects_edited_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cases, data = probe._validated_cases()
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps({"cases_sha256": probe._sha256(data), "case_count": len(cases)}))
    monkeypatch.setattr(probe, "LOCK_PATH", lock_path)
    edited = data.replace(b"inspect the storm drain", b"inspect the drain", 1)
    assert not probe._lock_matches(edited)


def test_cases_and_payloads_never_contain_open_state_after() -> None:
    cases = frozen_cases()
    assert "open_state_after" not in json.dumps(cases)
    for case in cases[:3] + cases[-3:]:
        for variant in probe.VARIANTS:
            state, questions = probe._payload(case, variant)
            payload = {"state": state, "questions": questions}
            assert set(state) == (
                {"narration", "thing"} if variant == "A" else {"narration", "thing", "command", "declared"}
            )
            assert set(questions) == {probe.QUESTION_KEY}
            assert questions[probe.QUESTION_KEY]["type"] == "noul"
            assert "open_state_after" not in json.dumps(payload)


def test_dry_run_counts_2100(capsys: pytest.CaptureFixture[str]) -> None:
    assert probe.main(["--dry-run", "--max-calls", "2100", "--max-usd", "0.06"]) == 0
    assert "planned calls: 2100" in capsys.readouterr().out


def test_dry_run_prints_pacing_interval_and_duration(capsys: pytest.CaptureFixture[str]) -> None:
    assert probe.main(["--dry-run", "--max-calls", "2100", "--max-usd", "0.08", "--min-interval-s", "0.5"]) == 0
    output = capsys.readouterr().out
    assert "minimum interval: 0.500000 s" in output
    assert "estimated minimum duration: 1050.00 s" in output


def test_negative_pacing_interval_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert probe.main(["--dry-run", "--min-interval-s", "-1"]) == 2
    assert "non-negative" in capsys.readouterr().err


def test_default_pacing_interval_does_not_call_clock_or_sleep(tmp_path: Path) -> None:
    def fail_clock() -> float:
        raise AssertionError("default pacing must not use the injected clock")

    def fail_sleep(_: float) -> None:
        raise AssertionError("default pacing must not sleep")

    document = probe.run_cases(
        frozen_cases()[:1],
        samples=2,
        max_calls=2,
        out=tmp_path / "rows.json",
        client=FakeClient([]),
        cases_hash="hash",
        clock=fail_clock,
        sleep=fail_sleep,
    )
    assert len(document["rows"]) == 2


def test_pacing_is_enforced_between_request_starts_with_fake_clock(tmp_path: Path) -> None:
    class FakeClock:
        def __init__(self) -> None:
            self.now = 0.0
            self.sleeps: list[float] = []

        def monotonic(self) -> float:
            return self.now

        def sleep(self, seconds: float) -> None:
            self.sleeps.append(seconds)
            self.now += seconds

    clock = FakeClock()
    starts: list[float] = []

    class RecordingClient(FakeClient):
        def ask(self, state: object, questions: object) -> dict | None:
            starts.append(clock.now)
            return super().ask(state, questions)

    document = probe.run_cases(
        frozen_cases()[:1],
        samples=1,
        max_calls=3,
        out=tmp_path / "rows.json",
        client=RecordingClient([]),
        cases_hash="hash",
        min_interval_s=0.5,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )
    assert len(document["rows"]) == 3
    assert starts == [0.0, 0.5, 1.0]
    assert clock.sleeps == [0.5, 0.5]


def test_dry_run_refuses_caps_before_any_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_client() -> object:
        raise AssertionError("client must not be created")

    monkeypatch.setattr(probe.JevClient, "from_environment", fail_client)
    assert probe.main(["--dry-run", "--max-calls", "10", "--max-usd", "0.0000001"]) == 2


def test_run_without_confirm_refuses() -> None:
    assert probe.main(["--run", "--out", "/tmp/drain-condition-no-run.json"]) == 2


class FakeClient:
    def __init__(self, scores: list[float | None], status: int | None = None) -> None:
        self.scores = scores
        self.status = status
        self.last_status = None
        self.last_model = "fake"
        self.last_version = "fake"

    def ask(self, state: object, questions: object) -> dict | None:
        assert "open_state_after" not in json.dumps({"state": state, "questions": questions})
        self.last_status = self.status
        score = self.scores.pop(0) if self.scores else 0.9
        if score is None:
            return None
        return {probe.QUESTION_KEY: {"noul": score}}


def test_stop_on_429_preserves_the_failed_row(tmp_path: Path) -> None:
    cases = frozen_cases()[:1]
    client = FakeClient([None], status=429)
    document = probe.run_cases(
        cases,
        samples=1,
        max_calls=3,
        out=tmp_path / "rows.json",
        client=client,
        cases_hash="hash",
    )
    assert document["stop_reason"] == "http_429"
    assert len(document["rows"]) == 1
    assert document["rows"][0]["verdict"] == "unavailable"


def test_partial_run_writes_rows_and_stops(tmp_path: Path) -> None:
    cases = frozen_cases()[:1]
    document = probe.run_cases(
        cases,
        samples=2,
        max_calls=2,
        out=tmp_path / "rows.json",
        client=FakeClient([]),
        cases_hash="hash",
    )
    assert document["stop_reason"] == "max_calls"
    assert len(document["rows"]) == 2


def _document_for(
    cases: list[dict],
    score_for,
    *,
    stop_reason: str | None = None,
) -> dict:
    rows = []
    for case in cases:
        for variant in probe.VARIANTS:
            for sample in range(5):
                rows.append(
                    {
                        "case_id": case["id"],
                        "variant": variant,
                        "sample": sample,
                        "score": score_for(case, variant, sample),
                    }
                )
    return {
        "samples": 5,
        "calls_planned": len(rows),
        "rows": rows,
        "stop_reason": stop_reason,
    }


def test_report_passes_only_when_candidate_passes(tmp_path: Path) -> None:
    cases = frozen_cases()
    document = _document_for(cases, lambda case, variant, sample: 0.1 if case["forbidden"] else 0.9)
    document["cases_sha256"] = probe._sha256(probe._load_cases()[1])
    rows_path = tmp_path / "rows.json"
    out = tmp_path / "report.md"
    rows_path.write_text(json.dumps(document))
    assert probe.report_rows(rows_path, out) == 0
    report = out.read_text()
    assert "Overall: PASS" in report
    assert "Variant B passed" in report


@pytest.mark.parametrize(
    ("set_name", "forbidden", "score"),
    [("drain", True, 0.9), ("drain", False, 0.1), ("heldout", True, 0.9), ("heldout", False, 0.1)],
)
def test_report_shows_each_failing_gate(tmp_path: Path, set_name: str, forbidden: bool, score: float) -> None:
    cases = frozen_cases()

    def score_for(case: dict, variant: str, sample: int) -> float:
        if case["set"] == set_name and case["forbidden"] is forbidden:
            return score
        return 0.1 if case["forbidden"] else 0.9

    document = _document_for(cases, score_for)
    document["cases_sha256"] = probe._sha256(probe._load_cases()[1])
    rows_path = tmp_path / "rows.json"
    out = tmp_path / "report.md"
    rows_path.write_text(json.dumps(document))
    assert probe.report_rows(rows_path, out) == 1
    assert "FAIL" in out.read_text()


def test_report_uses_median_and_reports_uncertain(tmp_path: Path) -> None:
    cases = frozen_cases()
    target = cases[0]

    def score_for(case: dict, variant: str, sample: int) -> float:
        if case["id"] == target["id"] and variant == "B":
            return [0.1, 0.1, 0.1, 0.1, 0.9][sample]
        if case["id"] == cases[1]["id"] and variant == "B":
            return 0.5
        return 0.1 if case["forbidden"] else 0.9

    document = _document_for(cases, score_for)
    document["cases_sha256"] = probe._sha256(probe._load_cases()[1])
    rows_path = tmp_path / "rows.json"
    out = tmp_path / "report.md"
    rows_path.write_text(json.dumps(document))
    probe.report_rows(rows_path, out)
    report = out.read_text()
    assert f"{target['id']}" not in report.split("### False accepts", 1)[1].split("### False rejects", 1)[0]
    variant_b = report.split("## Variant B", 1)[1].split("## Variant C", 1)[0]
    assert "uncertain=1" in next(line for line in variant_b.splitlines() if "- drain:" in line)


def test_partial_report_is_inconclusive(tmp_path: Path) -> None:
    cases = frozen_cases()
    document = _document_for(
        cases,
        lambda case, variant, sample: 0.1 if case["forbidden"] else 0.9,
        stop_reason="http_429",
    )
    document["rows"] = document["rows"][:1]
    document["calls_planned"] = 2100
    document["cases_sha256"] = probe._sha256(probe._load_cases()[1])
    rows_path = tmp_path / "rows.json"
    out = tmp_path / "report.md"
    rows_path.write_text(json.dumps(document))
    assert probe.report_rows(rows_path, out) == 1
    assert "Overall: INCONCLUSIVE" in out.read_text()


def test_report_mentions_other_variant_finding(tmp_path: Path) -> None:
    cases = frozen_cases()

    def score_for(case: dict, variant: str, sample: int) -> float:
        if variant == "B":
            return 0.9
        return 0.1 if case["forbidden"] else 0.9

    document = _document_for(cases, score_for)
    document["cases_sha256"] = probe._sha256(probe._load_cases()[1])
    rows_path = tmp_path / "rows.json"
    out = tmp_path / "report.md"
    rows_path.write_text(json.dumps(document))
    assert probe.report_rows(rows_path, out) == 1
    assert (
        "candidate failed; another variant passed, which is a finding for a new preregistration, not a pass"
        in out.read_text()
    )
