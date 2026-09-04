import io
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

import bench.cli as bench_cli
from bench.core import (
    CRITERIA,
    aggregate_runs,
    append_ledger_row,
    count_example_leakage,
    has_example_leakage,
    ledger_rows,
    load_variation,
    prompt_for,
    score_judgments,
    welch_t_test,
)
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "stories" / "continuity-initiative"
VARIATION = ROOT / "bench" / "variations" / "arm-c.json"
NO_EXAMPLE_VARIATION = ROOT / "bench" / "variations" / "arm-c-no-example.json"
OVERLAY_VARIATION = ROOT / "bench" / "variations" / "arm-c-overlay.json"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "bench"
ARCHIVE = FIXTURE_DIR / "arm-c" / "run1"
PLAYER_INPUT = (FIXTURE_DIR / "fixture_player_input.txt").read_text(encoding="utf-8")


def test_score_matches_archived_acceptance_fixture() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bench", "score", "--run-dir", str(ARCHIVE)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "total": 12,
        "per_criterion": {
            "canon_consistent": 0,
            "scene_local": 2,
            "progressive": 0,
            "rich": 1,
            "protected_safe": 5,
            "exit_motivated": 2,
            "rewards_investigation": 2,
        },
    }
    assert result.stderr == ""


def test_arm_c_prompt_is_byte_identical_and_uses_details() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bench",
            "prompt",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--turn",
            "1",
            "--player-input",
            PLAYER_INPUT,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    prompt = json.loads(result.stdout)
    fixture = (FIXTURE_DIR / "fixture_armc_system.txt").read_text(encoding="utf-8")
    assert prompt["system"].encode() == fixture.encode()
    user_fixture = (FIXTURE_DIR / "fixture_armc_user.txt").read_text(encoding="utf-8")
    assert prompt["user"].encode() == user_fixture.encode()
    assert prompt["user"].count("<beat_detail>") == 5
    assert "<beat>" not in prompt["user"]


def test_resolved_variation_hashes_are_stable_and_distinguish_prompt_configs() -> None:
    arm_c = load_variation(VARIATION)
    arm_c_again = load_variation(VARIATION)
    no_example = load_variation(NO_EXAMPLE_VARIATION)

    assert arm_c["_variation_hash"] == arm_c_again["_variation_hash"]
    assert arm_c["_package_hash"] == arm_c_again["_package_hash"]
    assert arm_c["_variation_hash"] != no_example["_variation_hash"]
    assert arm_c["_package_hash"] == no_example["_package_hash"]


def test_example_leakage_counts_only_distinctive_contiguous_spans() -> None:
    example = "The model should narrate the concrete immediate consequence in this scene."
    leaked = "A response should narrate the concrete immediate consequence in this scene."
    short_overlap = "The model should narrate a different outcome in another scene."

    assert has_example_leakage(leaked, example)
    assert count_example_leakage([leaked, short_overlap], example) == 1
    assert count_example_leakage([leaked], None) == 0


def test_no_example_variation_has_zero_example_leakage() -> None:
    no_example = load_variation(NO_EXAMPLE_VARIATION)

    assert no_example["_resolved_output_example"] is None
    narration = ["The drawer sticks, then gives, inside a curl of packing tape."]
    assert count_example_leakage(narration, no_example["_resolved_output_example"]) == 0


def test_custom_output_example_is_resolved_described_and_hashed(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["name"] = "custom-example"
    source["system_prompt"]["output_example"] = '{"segments":[],"selected_knowledge_ids":[]}'
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    custom = load_variation(path)
    arm_c = load_variation(VARIATION)
    assert custom["_resolved_output_example"] == source["system_prompt"]["output_example"]
    assert custom["_variation_hash"] != arm_c["_variation_hash"]
    prompt = prompt_for(custom, "1A", PLAYER_INPUT)
    assert "<output_example>{\"segments\":[],\"selected_knowledge_ids\":[]}</output_example>" in prompt["system"]


def test_non_string_output_example_is_rejected(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["system_prompt"]["output_example"] = {"segments": []}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="system_prompt.output_example must be a string"):
        load_variation(path)


def test_overlay_changes_effective_package_hash_and_assembled_prompt() -> None:
    arm_c = load_variation(VARIATION)
    overlay = load_variation(OVERLAY_VARIATION)
    assert overlay["_package_hash"] != arm_c["_package_hash"]
    assert "KMS initials in drawer" in (PACKAGE / "plot.md").read_text(encoding="utf-8")

    prompt = prompt_for(overlay, "1A", PLAYER_INPUT)
    assert "<beat_detail>KMS initials carved beneath the drawer</beat_detail>" in prompt["user"]
    assert "<beat_detail>KMS initials in drawer</beat_detail>" not in prompt["user"]


def test_ledger_rows_round_trip_through_log(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    row = {"variation_name": "arm-c", "scores": [12], "package_hash": "package"}
    append_ledger_row(row, ledger)
    append_ledger_row({**row, "variation_name": "arm-c-no-example", "scores": [14]}, ledger)
    args = bench_cli.parser().parse_args(["log", "--json", "--variation", "arm-c", "--ledger", str(ledger)])
    assert bench_cli._log(args) == 0
    assert json.loads(capsys.readouterr().out) == [row]
    assert ledger_rows(ledger) == [row, {**row, "variation_name": "arm-c-no-example", "scores": [14]}]


def _comparison_row(name: str, coverage: int, score: int, *, status: str = "ok") -> dict:
    return {
        "variation_name": name,
        "package_hash": "package",
        "scene": "1A",
        "scenes_scored": coverage,
        "max_score": coverage * len(CRITERIA),
        "status": status,
        "scores": [score],
    }


def test_compare_refuses_mismatched_scene_coverage_and_names_values(tmp_path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    append_ledger_row(_comparison_row("focused", 1, 1), ledger)
    append_ledger_row(_comparison_row("full", 9, 9), ledger)
    args = bench_cli.parser().parse_args(["compare", "focused", "full", "--ledger", str(ledger)])

    with pytest.raises(RuntimeError, match=r"scene coverage differs.*1.*9"):
        bench_cli._compare(args)


def test_compare_matching_scene_coverage_succeeds_and_override_allows_mismatch(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    append_ledger_row(_comparison_row("left", 1, 1), ledger)
    append_ledger_row(_comparison_row("right", 1, 2), ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])
    assert bench_cli._compare(args) == 0
    assert "difference (left - right): -1.00" in capsys.readouterr().out

    mismatch = tmp_path / "mismatch.jsonl"
    append_ledger_row(_comparison_row("left", 1, 1), mismatch)
    append_ledger_row(_comparison_row("right", 9, 2), mismatch)
    args = bench_cli.parser().parse_args(
        ["compare", "left", "right", "--ledger", str(mismatch), "--allow-coverage-mismatch"]
    )
    assert bench_cli._compare(args) == 0
    assert "scene coverage was not held constant" in capsys.readouterr().out


def test_compare_displays_example_leakage(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    left = _comparison_row("left", 1, 1)
    right = _comparison_row("right", 1, 2)
    left["example_leakage"] = 3
    right["example_leakage"] = 0
    append_ledger_row(left, ledger)
    append_ledger_row(right, ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])

    assert bench_cli._compare(args) == 0
    assert "example_leakage" in capsys.readouterr().out


@pytest.mark.parametrize("coverage", ["missing", "null"])
def test_compare_excludes_unknown_scale_rows_and_reports_them(tmp_path, capsys, coverage) -> None:
    ledger = tmp_path / "ledger.jsonl"
    unknown = _comparison_row("left", 1, 9)
    if coverage == "missing":
        del unknown["scenes_scored"]
    else:
        unknown["scenes_scored"] = None
    append_ledger_row(unknown, ledger)
    append_ledger_row(_comparison_row("left", 1, 1), ledger)
    append_ledger_row(_comparison_row("left", 1, 2), ledger)
    append_ledger_row(_comparison_row("right", 1, 1), ledger)
    append_ledger_row(_comparison_row("right", 1, 2), ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])

    assert bench_cli._compare(args) == 0
    output = capsys.readouterr().out
    assert "left: n=2 mean=1.50" in output
    assert "skipped 1" in output
    assert "left" in output
    assert "unknown" in output


def test_log_marks_unknown_scale_rows_without_hiding_them(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    missing = _comparison_row("left", 1, 9)
    del missing["scenes_scored"]
    null = _comparison_row("left", 1, 8)
    null["scenes_scored"] = None
    append_ledger_row(missing, ledger)
    append_ledger_row(null, ledger)
    args = bench_cli.parser().parse_args(["log", "--variation", "left", "--ledger", str(ledger)])

    assert bench_cli._log(args) == 0
    output = capsys.readouterr().out
    assert "legacy/unknown-scale" in output
    assert "unknown-scale (null)" in output
    assert output.count("left") == 2


def test_failed_replicate_is_recorded_and_excluded_from_compare(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "broken-arm",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["I investigate."]}

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(
        bench_cli,
        "run_scene",
        lambda *_: (_ for _ in ()).throw(NarrationProviderError("invalid", 502, "INVALID_PROPOSAL")),
    )
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(VARIATION), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )

    assert bench_cli._run(args) == 2
    row = ledger_rows(ledger)[0]
    assert row["status"] == "failed"
    assert "INVALID_PROPOSAL" in row["failure_reason"]
    assert row["scenes_scored"] == 0
    assert row["max_score"] == 0


def test_run_baseline_refuses_archived_nine_scene_coverage_before_live_work(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "e2e", "inputs": ["I investigate."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: pytest.fail("baseline guard ran live work"))
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path),
            "--baseline",
            str(ARCHIVE),
        ]
    )

    with pytest.raises(RuntimeError, match=r"scene coverage differs.*1.*9"):
        bench_cli._run(args)


def test_run_baseline_with_unknown_scale_skips_baseline_statistics(monkeypatch, tmp_path, capsys) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    (baseline / "summary.json").write_text(json.dumps({"replicate_scores": [99]}), encoding="utf-8")
    script = {"name": "e2e", "inputs": ["I look around."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
            "--baseline",
            str(baseline),
        ]
    )

    assert bench_cli._run(args) == 0
    output = capsys.readouterr().out
    assert "skipped unknown-scale baseline" in output
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert "comparison" not in summary


def test_aggregate_reports_actual_scene_denominator() -> None:
    runs = [{"replicate": 1, "script": "e2e", "scene_id": "1A", "example_leakage": 2}]
    judgments = [{criterion: criterion == "protected_safe" for criterion in CRITERIA}]
    aggregate = aggregate_runs(runs, judgments, 1)
    assert aggregate["scenes_scored"] == 1
    assert aggregate["max_score"] == 7
    assert aggregate["score_metric"].startswith("7-point record")
    assert aggregate["example_leakage"] == 2


def test_score_exposes_graded_missing_entries_without_changing_record_score() -> None:
    result = score_judgments(
        [
            {
                "canon_consistent": False,
                "scene_local": True,
                "progressive": False,
                "rich": False,
                "protected_safe": True,
                "exit_motivated": False,
                "rewards_investigation": False,
                "missing_or_wrong": ["missing detail", {"criterion": "progressive"}],
            }
        ]
    )
    assert result["total"] == 2
    assert result["graded_secondary"]["total"] == 2
    assert result["graded_secondary"]["per_criterion_where_attributable"] == {"progressive": 1}
    assert result["graded_secondary"]["unattributed"] == 1


def test_quota_header_and_app_rate_limit_are_distinguished() -> None:
    quota = HTTPError(
        "https://worker.example",
        429,
        "quota",
        {"X-Narration-Error-Code": "AI_QUOTA_EXCEEDED"},
        io.BytesIO(b'{"detail":"narration service is at capacity"}'),
    )
    rate_limit = HTTPError(
        "https://worker.example",
        429,
        "rate",
        {},
        io.BytesIO(b'{"detail":"rate limit exceeded"}'),
    )
    assert CloudflareTurnProvider._worker_error_code(quota) == "AI_QUOTA_EXCEEDED"
    assert CloudflareTurnProvider._worker_error_code(rate_limit) == "RATE_LIMITED"


def test_welch_report_says_when_difference_is_inside_noise() -> None:
    result = welch_t_test([13, 14, 13, 15], [12, 13, 12, 14])
    assert result["test"] == "two-sided Welch t-test"
    assert result["inside_noise"] is True
    assert "nothing detectable" in result["statement"]


def test_focused_run_allows_one_explicit_replicate_without_calling_live_services(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["I look around."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())

    def fake_judges(_input, output):
        result = {"judgments": [judgment], "judge_calls": 1}
        output.write_text(json.dumps(result), encoding="utf-8")
        return result

    monkeypatch.setattr(bench_cli, "run_judges", fake_judges)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path),
        ]
    )

    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["replicates"] == 1
    assert summary["pooled"]["score_points"]["n"] == 1
    assert summary["pooled"]["score_points"]["standard_deviation"] is None
    assert summary["budget"]["actual_openai_judge_calls"] == 1


def test_chat_contract_accepts_variation_argument() -> None:
    args = bench_cli.parser().parse_args(["chat", "--variation", str(VARIATION)])
    assert args.command == "chat"
    assert args.variation == VARIATION


def test_judge_bridge_imports_both_existing_judge_exports() -> None:
    result = subprocess.run(
        [
            "node",
            "-e",
            "import('./frontend/e2e/roleplay-judge.js').then(({judgeSceneNarration, sceneCanon}) => { "
            "if (typeof judgeSceneNarration !== 'function' || typeof sceneCanon !== 'function') process.exit(1); })",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
