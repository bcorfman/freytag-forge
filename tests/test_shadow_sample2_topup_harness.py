import json
import os
import subprocess
from pathlib import Path

from scripts.ringer.transcript_1a.live_baseline import ROUTES

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
SCRIPT = ENVIRONMENT_NARRATION / "shadow_sample2_topup.sh"
REPORT = ENVIRONMENT_NARRATION / "shadow_report.py"


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def _run_dry(route: str, output_dir: Path) -> tuple[dict, list[dict]]:
    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/ringer/transcript_1a/live_baseline.py",
            "--route",
            route,
            "--shadow",
            "--replicates",
            "1",
            "--dry-run",
            "--out",
            str(output_dir),
        ],
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    rows = json.loads((output_dir / "rows.json").read_text(encoding="utf-8"))
    return summary, rows


def _topup_rows() -> list[dict]:
    commands = ROUTES["observe_topup"]
    rows = []
    for _ in range(3):
        turns = []
        for command in commands:
            is_drawer_probe = command == "feel under the drawer"
            is_seat_probe = command == "inspect the passenger seat"
            observation = [] if is_drawer_probe or is_seat_probe else None
            turns.append(
                {
                    "input": command,
                    "narration": "Nothing is here.",
                    "error": None,
                    "observation_relations": observation,
                    "observation_shadow": (
                        {"outcome": "no_relations", "requests": 0, "verdicts": []} if observation is not None else None
                    ),
                    "places_before": {"laptop": "protagonist"} if is_seat_probe else None,
                    "places_after": {"laptop": "protagonist"} if is_seat_probe else None,
                    "observation_request": ({"kind": "look", "focus": "passenger seat"} if is_seat_probe else None),
                    "scene": "house",
                }
            )
        rows.append({"route": "observe_topup", "opening": None, "turns": turns})
    return rows


def test_observe_topup_route_is_frozen_and_observe_is_unchanged():
    assert ROUTES["observe"] == (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "inspect the passenger seat",
        "examine my laptop",
        "get out of the truck",
        "examine the truck",
        "go inside",
        "inspect the drawer",
    )
    assert ROUTES["observe_topup"] == (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "pick up my laptop",
        "inspect the passenger seat",
    )


def test_topup_script_has_valid_shell_and_topup_limits():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    text = SCRIPT.read_text(encoding="utf-8")
    for expected in ("shadow-sample2-topup", "observe_topup", "70", "600", "0.03", "0.20", "8793"):
        assert expected in text
    assert "shadow-sample2/" not in text
    assert "shadow-sample/" not in text


def test_unknown_topup_stage_exits_before_starting_anything():
    result = subprocess.run(
        ["bash", str(SCRIPT), "bogus"],
        cwd=ROOT,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "usage: shadow_sample2_topup.sh smoke|full\n"


def test_observe_topup_shadow_dry_run_records_planned_calls_and_matching_turn_keys(tmp_path):
    _observe_summary, observe_rows = _run_dry("observe", tmp_path / "observe")
    topup_summary, topup_rows = _run_dry("observe_topup", tmp_path / "topup")

    assert topup_summary["route"] == "observe_topup"
    assert topup_summary["replicates_requested"] == 1
    assert topup_summary["turns_recorded"] == 9
    assert topup_summary["real_calls"] == 0
    assert topup_summary["calls_made"] > 0
    observe_turn_keys = {frozenset(turn) for turn in observe_rows[0]["turns"]}
    assert len(observe_turn_keys) == 1
    expected_turn_keys = next(iter(observe_turn_keys))
    assert all(frozenset(turn) == expected_turn_keys for turn in topup_rows[0]["turns"])


def test_topup_shaped_rows_join_without_report_error(tmp_path):
    rows_path = tmp_path / "rows.json"
    labels_path = tmp_path / "labels.json"
    rows = _topup_rows()
    labels = {}
    for replicate, row in enumerate(rows):
        for turn_index, turn in enumerate(row["turns"]):
            if turn["observation_relations"] is not None:
                labels[f"r{replicate}t{turn_index}"] = {
                    "acceptable": True,
                    "refind": False,
                    "invented_object": False,
                }
    rows_path.write_text(json.dumps(rows), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")

    result = subprocess.run(
        [".venv/bin/python", str(REPORT), "join", str(rows_path), str(labels_path)],
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "5 scene-transition turns drop the requirement: INCONCLUSIVE (n=0)" in result.stdout
    assert "7 re-find of the held card: INCONCLUSIVE (n=6, refind true=0)" in result.stdout
    assert "8 invented object on the empty seat: INCONCLUSIVE (n=3, invented_object true=0)" in result.stdout
