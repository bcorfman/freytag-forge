import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
SCRIPT = ENVIRONMENT_NARRATION / "shadow_sample2.sh"
GENERATOR = ENVIRONMENT_NARRATION / "make_shadow2_run_manifests.py"
MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-shadow2-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-shadow2-full.json",
}


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def test_shadow_sample2_script_has_valid_shell_and_sample2_limits():
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
    for expected in ("shadow-sample2", "100", "900", "0.05", "0.30", "8793"):
        assert expected in text
    assert "shadow-sample/" not in text
    assert "8792" not in text


def test_unknown_stage_exits_before_starting_anything():
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
    assert result.stderr.strip() == "usage: shadow_sample2.sh smoke|full"
    assert "source" not in result.stderr
    assert "port" not in result.stderr


def test_sample2_manifests_are_sample2_only_and_keep_hard_rules():
    required_sentences = (
        "run COMMAND 1 EXACTLY ONCE",
        "NEVER run it a second time",
        "Do not edit any file.",
        "Do not print, echo, cat or log environment variables or the .env file or any credential.",
        "Do not git commit.",
        (
            "The script refuses to run if its port is busy (exit 4); do not do your own port checks, "
            "just run COMMAND 1 once."
        ),
        "a non-zero exit with partial rows is a valid outcome, do not retry",
        "approved in the sample-2 preregistration",
        "the runner must not start unless the human's go for this stage was given in the task statement",
    )

    for stage, path in MANIFESTS.items():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        serialized = json.dumps(manifest)
        assert task["key"] == f"billed-shadow-sample2-{stage}"
        assert f"grounded-environment-narration-shadow2-{stage}" in manifest["workdir"]
        assert "shadow-sample/" not in serialized
        assert "shadow_sample.sh" not in task["spec"]
        assert f"shadow_sample2.sh {stage}" in task["spec"]
        assert "summary['shadow']" in task["check"]
        assert "spent_micro_usd" in task["check"]
        assert "50000" in task["check"] or "300000" in task["check"]
        assert "row" in task["check"]
        assert "replicates" in task["check"]
        assert "13" in task["check"]
        for sentence in required_sentences:
            assert sentence in task["spec"]


def test_shadow2_generator_is_idempotent():
    before = {path: path.read_bytes() for path in MANIFESTS.values()}
    result = subprocess.run(
        [".venv/bin/python", str(GENERATOR)],
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    after = {path: path.read_bytes() for path in MANIFESTS.values()}
    assert after == before


def test_observe_shadow_dry_run_records_planned_calls_without_real_calls(tmp_path):
    output_dir = tmp_path / "dry-run"
    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/ringer/transcript_1a/live_baseline.py",
            "--route",
            "observe",
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
    assert summary["route"] == "observe"
    assert summary["replicates_requested"] == 1
    assert summary["turns_recorded"] == 13
    assert summary["calls_made"] > 0
    assert summary["real_calls"] == 0
    assert "calls_made" in (result.stdout + result.stderr + (output_dir / "summary.json").read_text())
