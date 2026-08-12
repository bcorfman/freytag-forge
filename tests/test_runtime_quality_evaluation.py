from __future__ import annotations

from storygame.evaluation import (
    INFORMATIONAL_DIRECT_OR_REPAIRED_SLO,
    evaluate_frozen_adapter_matrix,
    load_runtime_quality_regressions,
)


def test_frozen_adapter_matrix_compares_every_supported_adapter_on_every_fixture_turn():
    report = evaluate_frozen_adapter_matrix()

    assert report["kind"] == "informational_runtime_quality"
    assert report["missing_adapters"] == ()
    assert report["slo"] == {
        "name": "direct_or_one_repair_validation_rate",
        "target": INFORMATIONAL_DIRECT_OR_REPAIRED_SLO,
        "enforced": False,
    }
    assert set(report["adapters"]) == {"openai", "ollama", "cloudflare_workers_ai"}
    assert all(adapter["turns"] == 12 for adapter in report["adapters"].values())
    assert all(adapter["direct_or_one_repair_validation_rate"] >= 0.95 for adapter in report["adapters"].values())
    assert all(adapter["protected_information_leaks"] == 0 for adapter in report["adapters"].values())
    assert all(adapter["uncommitted_state"] == 0 for adapter in report["adapters"].values())


def test_structured_runtime_quality_regressions_remain_fail_closed_and_non_accepted():
    regressions = load_runtime_quality_regressions()

    assert {regression["id"] for regression in regressions} == {
        "wrong-speaker-repair-exhausted",
        "uncommitted-narration-rejected",
    }
    assert all(not regression["accepted"] for regression in regressions)
    assert {category for regression in regressions for category in regression["failure_categories"]} == {
        "role_drift",
        "uncommitted_narration",
        "exhausted_provider_recovery",
    }
