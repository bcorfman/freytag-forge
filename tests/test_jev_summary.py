import json
from pathlib import Path

import bench.cli as bench_cli
from bench.core import CRITERIA

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "stories" / "continuity-initiative"
VARIATION = ROOT / "bench" / "variations" / "example.json"


def _run(monkeypatch, tmp_path, *, jev_snapshot=None):
    variation = {
        "name": "jev-summary",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
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
    judgment = {criterion: False for criterion in CRITERIA} | {"missing_or_wrong": []}
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "e2e", "inputs": ["Look around."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    if jev_snapshot is not None:
        monkeypatch.setattr(bench_cli, "jev_stats", lambda: jev_snapshot)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(VARIATION), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )
    assert bench_cli._run(args) == 0
    return json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))


def test_summary_budget_contains_zero_jev_snapshot_when_unused(monkeypatch, tmp_path):
    summary = _run(monkeypatch, tmp_path)

    assert summary["budget"]["jev"] == {
        "calls": 0,
        "ok": 0,
        "failures": {},
        "stopped": None,
        "cap_reached": False,
        "requests": 0,
    }


def test_summary_budget_reports_jev_failures_cap_and_quota_stop(monkeypatch, tmp_path):
    summary = _run(
        monkeypatch,
        tmp_path,
        jev_snapshot={
            "calls": 4,
            "ok": 1,
            "failures": {"http_status": 1, "timeout": 2},
            "stopped": "AI_QUOTA_EXCEEDED",
            "cap_reached": True,
        },
    )

    assert summary["budget"]["jev"] == {
        "calls": 4,
        "ok": 1,
        "failures": {"http_status": 1, "timeout": 2},
        "stopped": "AI_QUOTA_EXCEEDED",
        "cap_reached": True,
        "requests": 4,
    }


def test_second_run_resets_jev_snapshot(monkeypatch, tmp_path):
    snapshots = iter(
        [
            {
                "calls": 3,
                "ok": 0,
                "failures": {"request": 3},
                "stopped": "max_consecutive_failures",
                "cap_reached": False,
            },
            {"calls": 0, "ok": 0, "failures": {}, "stopped": None, "cap_reached": False},
        ]
    )
    reset_calls = []
    monkeypatch.setattr(bench_cli, "jev_stats", lambda: next(snapshots))
    monkeypatch.setattr(bench_cli, "reset_jev_stats", lambda: reset_calls.append(True))

    first = _run(monkeypatch, tmp_path / "first")
    second = _run(monkeypatch, tmp_path / "second")

    assert first["budget"]["jev"]["calls"] == 3
    assert second["budget"]["jev"] == {
        "calls": 0,
        "ok": 0,
        "failures": {},
        "stopped": None,
        "cap_reached": False,
        "requests": 0,
    }
    assert len(reset_calls) == 2
