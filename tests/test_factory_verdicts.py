import pytest

from factory.verdicts import Verdict, assert_no_leak, report_hash, strip_for_worker, to_worker_report


def test_report_hash_is_the_first_16_sha256_hex_characters():
    assert report_hash("hello") == "2cf24dba5fb0a30e"


def test_check_report_preserves_output_in_full():
    verdict = Verdict("check", False, 2, "full compiler and test output")

    assert to_worker_report(verdict) == {
        "source": "check",
        "passed": False,
        "exit_code": 2,
        "output": "full compiler and test output",
    }


def test_judge_report_hashes_reasoning_and_omits_transcript_when_passing():
    verdict = Verdict("judge", True, None, "ignored", reasoning="private judge explanation", transcript="private")

    report = to_worker_report(verdict)

    assert report == {
        "source": "judge",
        "passed": True,
        "reasoning_hash": report_hash("private judge explanation"),
    }
    assert "private judge explanation" not in str(report)


def test_judge_failure_includes_only_sanitized_transcript():
    verdict = Verdict(
        "judge",
        False,
        None,
        "ignored",
        reasoning="private judge explanation",
        transcript="failing transcript",
    )

    report = to_worker_report(verdict)

    assert report["transcript"] == "failing transcript"
    assert "private judge explanation" not in str(report)
    assert "output" not in report


def test_holdout_report_hashes_scenario_and_omits_transcript_when_passing():
    verdict = Verdict("holdout", True, None, "ignored", scenario_text="private scenario")

    report = to_worker_report(verdict)

    assert report == {
        "source": "holdout",
        "passed": True,
        "scenario_hash": report_hash("private scenario"),
    }
    assert "private scenario" not in str(report)


def test_holdout_failure_includes_transcript_but_not_scenario():
    verdict = Verdict(
        "holdout",
        False,
        None,
        "ignored",
        scenario_text="private scenario",
        transcript="failing transcript",
    )

    report = to_worker_report(verdict)

    assert report["transcript"] == "failing transcript"
    assert "private scenario" not in str(report)


def test_failing_transcript_redacts_verbatim_scenario_text():
    verdict = Verdict(
        "holdout",
        False,
        None,
        "ignored",
        scenario_text="the locked scenario",
        transcript="the locked scenario produced this failure",
    )

    assert to_worker_report(verdict)["transcript"] == "[redacted] produced this failure"


def test_redaction_is_case_insensitive():
    verdict = Verdict("holdout", False, None, "ignored", scenario_text="Locked Scenario", transcript="locked scenario")

    assert to_worker_report(verdict)["transcript"] == "[redacted]"


def test_assert_no_leak_raises_for_a_seeded_reasoning_leak():
    verdict = Verdict("judge", True, None, "ignored", reasoning="secret reasoning")

    with pytest.raises(ValueError):
        assert_no_leak({"nested": ["This contains SECRET REASONING."]}, verdict)


def test_strip_for_worker_projects_each_record():
    records = [Verdict("check", True, 0, "ok"), Verdict("holdout", True, None, "", scenario_text="scenario")]

    assert strip_for_worker(records) == [
        {"source": "check", "passed": True, "exit_code": 0, "output": "ok"},
        {"source": "holdout", "passed": True, "scenario_hash": report_hash("scenario")},
    ]
