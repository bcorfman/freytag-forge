from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
PYTHON = ROOT / ".venv/bin/python"


def test_stage3_script_has_routes_port_and_caps() -> None:
    script = (ENVIRONMENT_NARRATION / "enforce_stage3.sh").read_text()
    assert "PORT=8797" in script
    assert "t9c-open/$STAGE" in script
    assert "observe_topup" in script
    assert "observe_under_first" in script
    assert "observe_look_inside_under" in script
    assert "--replicates 1 --max-calls 90" in script
    assert "--replicates 1 --max-calls 40" in script
    assert "--replicates 2 --max-calls 90" in script
    assert "--replicates 10 --max-calls 800" in script
    assert "--replicates 5 --max-calls 250" in script
    assert "--replicates 15 --max-calls 700" in script
    assert '--max-usd "$MAX_USD"' in script
    subprocess.run(["bash", "-n", str(ENVIRONMENT_NARRATION / "enforce_stage3.sh")], check=True)


def test_generated_t9c_manifests_match_committed_json() -> None:
    generator = ENVIRONMENT_NARRATION / "make_t9c_run_manifests.py"
    smoke = ENVIRONMENT_NARRATION / "run-t9c-smoke.json"
    full = ENVIRONMENT_NARRATION / "run-t9c-full.json"
    expected_smoke = smoke.read_bytes()
    expected_full = full.read_bytes()
    subprocess.run([str(PYTHON), str(generator)], check=True)
    assert smoke.read_bytes() == expected_smoke
    assert full.read_bytes() == expected_full


def test_t9c_manifests_have_caps_workdirs_checks_and_no_credential_values() -> None:
    for name, stage, usd, counts in (
        ("run-t9c-smoke.json", "smoke", 70000, (1, 9, 1, 4, 2, 6)),
        ("run-t9c-full.json", "full", 450000, (10, 9, 5, 4, 15, 6)),
    ):
        path = ENVIRONMENT_NARRATION / name
        manifest = json.loads(path.read_text())
        assert manifest["workdir"] == f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-{stage}"
        assert manifest["max_parallel"] == 1
        assert len(manifest["tasks"]) == 1
        task = manifest["tasks"][0]
        assert task["max_attempts"] == 1
        assert "enforce_stage3.sh" in task["spec"]
        assert "Run COMMAND 1 exactly once" in task["spec"]
        assert f"--max-usd {usd / 1000000:.2f}" in task["spec"]
        assert str(usd) in task["check"]
        assert all(str(count) in task["spec"] for count in counts)
        assert all(str(count) in task["check"] for count in counts)
        assert "stopped_reason" in task["check"]
        assert "no credential" in task["spec"]
        assert "credential value" in task["check"]
