from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
PYTHON = ROOT / ".venv/bin/python"


def test_t9h_script_has_routes_port_and_caps() -> None:
    script = (ENVIRONMENT_NARRATION / "enforce_t9h.sh").read_text()
    assert "T9h" in script
    assert "PORT=8798" in script
    assert "t9h/$STAGE" in script
    routes = (
        "observe_look_inside_under",
        "observe_supporters_1a",
        "observe_park_bench_1b",
        "observe_executive_desk_3b",
    )
    positions = [script.index(route) for route in routes]
    assert positions == sorted(positions)
    assert "--replicates 1 --max-calls 50" in script
    assert script.count("--replicates 2 --max-calls 90") == 3
    assert "--replicates 5 --max-calls 250" in script
    assert script.count("--replicates 10 --max-calls 450") == 3
    assert '--max-usd "$MAX_USD"' in script
    subprocess.run(["bash", "-n", str(ENVIRONMENT_NARRATION / "enforce_t9h.sh")], check=True)


def test_generated_t9h_manifests_match_committed_json() -> None:
    generator = ENVIRONMENT_NARRATION / "make_t9h_run_manifests.py"
    smoke = ENVIRONMENT_NARRATION / "run-t9h-smoke.json"
    full = ENVIRONMENT_NARRATION / "run-t9h-full.json"
    expected_smoke = smoke.read_bytes()
    expected_full = full.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        temporary_generator = Path(directory) / generator.name
        shutil.copy2(generator, temporary_generator)
        subprocess.run([str(PYTHON), str(temporary_generator)], check=True)
        assert (Path(directory) / smoke.name).read_bytes() == expected_smoke
        assert (Path(directory) / full.name).read_bytes() == expected_full


def test_generated_t9h_probe_manifest_matches_committed_json() -> None:
    generator = ENVIRONMENT_NARRATION / "make_t9h_probe_run_manifest.py"
    expected = (ENVIRONMENT_NARRATION / "run-t9h-probe-live.json").read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        temporary_generator = Path(directory) / generator.name
        shutil.copy2(generator, temporary_generator)
        subprocess.run([str(PYTHON), str(temporary_generator)], check=True)
        assert (Path(directory) / "run-t9h-probe-live.json").read_bytes() == expected


def test_t9h_manifests_have_caps_workdirs_checks_and_no_credential_values() -> None:
    for name, stage, usd, counts in (
        ("run-t9h-smoke.json", "smoke", 70000, (1, 6, 2, 6, 2, 6, 2, 6)),
        ("run-t9h-full.json", "full", 450000, (5, 6, 10, 6, 10, 6, 10, 6)),
    ):
        path = ENVIRONMENT_NARRATION / name
        manifest = json.loads(path.read_text())
        serialized = path.read_text()
        assert manifest["workdir"] == (f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9h-{stage}")
        assert manifest["max_parallel"] == 1
        assert len(manifest["tasks"]) == 1
        task = manifest["tasks"][0]
        assert task["max_attempts"] == 1
        assert "enforce_t9h.sh" in task["spec"]
        assert "Run COMMAND 1 exactly once" in task["spec"]
        assert "wait for the billed process" in task["spec"]
        assert ".plans/grounded-llm-environment-narration/t9h-confirmation-prereg.md" in task["spec"]
        assert f"--max-usd {usd / 1000000:.2f}" in task["spec"]
        assert task["ownership"] == [f"bench/results/environment-narration/t9h/{stage}"]
        assert str(usd) in task["check"]
        assert all(str(count) in task["spec"] for count in counts)
        assert all(str(count) in task["check"] for count in counts)
        assert "stopped_reason" in task["check"]
        assert "call_timings" in task["check"]
        for last_input in (
            "look under the drawer",
            "look under the workstation chair",
            "inspect the storm drain",
            "look under the executive desk",
        ):
            assert last_input in task["check"]
        assert "no credential" in task["spec"]
        assert "credential value" in task["check"]
        for credential in (
            "CLOUDFLARE_AI_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_WORKER_TOKEN",
        ):
            value = os.environ.get(credential, "").strip()
            assert not value or value not in serialized


def test_t9h_probe_manifest_has_request_cap_and_integrity_check() -> None:
    path = ENVIRONMENT_NARRATION / "run-t9h-probe-live.json"
    manifest = json.loads(path.read_text())
    serialized = path.read_text()
    assert manifest["workdir"] == "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9h-probe"
    assert len(manifest["tasks"]) == 1
    task = manifest["tasks"][0]
    assert "under_question_probe.py --corpus v4" in task["spec"]
    assert "--max-calls 48 --max-usd 0.01" in task["spec"]
    assert "bench/results/environment-narration/t9h/probe/" in task["spec"]
    assert "len(rows)==48" in task["check"]
    assert "stop_reason" in task["check"]
    assert "credential value" in task["check"]
    for credential in (
        "CLOUDFLARE_AI_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_WORKER_TOKEN",
        "OPENAI_API_KEY",
        "RAILWAY_TOKEN",
        "RAILWAY_PROJECT_ID",
        "FREYTAG_TEST_CLOCK_TOKEN",
    ):
        value = os.environ.get(credential, "").strip()
        assert not value or value not in serialized
