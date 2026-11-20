from datetime import UTC, datetime

import factory.breakers as breakers
from factory.drill import BREAKER_NAMES, DrillResult, drill_passed, render_report, run_drill

NOW = datetime(2026, 11, 16, 12, tzinfo=UTC)


def test_all_breakers_pass_the_real_drill(tmp_path):
    results = run_drill(tmp_path, NOW)

    assert [result.name for result in results] == list(BREAKER_NAMES)
    assert "paid_usage" in [result.name for result in results]
    assert drill_passed(results)
    assert all(result.passed for result in results)


def test_drill_passed_requires_every_breaker():
    results = [DrillResult(name, True, "ok") for name in BREAKER_NAMES]

    assert drill_passed(results[:-1]) is False
    assert drill_passed(results[:-1] + [DrillResult(BREAKER_NAMES[-1], False, "broken")]) is False


def test_render_report_lists_every_breaker_and_total():
    results = [DrillResult(name, True, "ok") for name in BREAKER_NAMES]

    report = render_report(results)

    assert all(name in report for name in BREAKER_NAMES)
    assert "PASS" in report
    assert report.endswith(f"TOTAL: {len(BREAKER_NAMES)}/{len(BREAKER_NAMES)} PASS")


def test_mutated_checker_makes_non_crash_drills_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(breakers, "check_breakers", lambda **kwargs: [])

    results = run_drill(tmp_path, NOW)
    by_name = {result.name: result for result in results}

    assert all(not by_name[name].passed for name in BREAKER_NAMES if name != "crash")
    assert by_name["crash"].passed
