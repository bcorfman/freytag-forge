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


def test_t9d_script_has_routes_port_and_caps() -> None:
    script = (ENVIRONMENT_NARRATION / "enforce_t9d.sh").read_text()
    assert "T9d" in script
    assert "PORT=8797" in script
    assert "t9d-search/$STAGE" in script
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
    subprocess.run(["bash", "-n", str(ENVIRONMENT_NARRATION / "enforce_t9d.sh")], check=True)


def test_generated_t9d_manifests_match_committed_json() -> None:
    generator = ENVIRONMENT_NARRATION / "make_t9d_run_manifests.py"
    smoke = ENVIRONMENT_NARRATION / "run-t9d-smoke.json"
    full = ENVIRONMENT_NARRATION / "run-t9d-full.json"
    expected_smoke = smoke.read_bytes()
    expected_full = full.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        temporary_generator = Path(directory) / generator.name
        shutil.copy2(generator, temporary_generator)
        subprocess.run([str(PYTHON), str(temporary_generator)], check=True)
        assert (Path(directory) / smoke.name).read_bytes() == expected_smoke
        assert (Path(directory) / full.name).read_bytes() == expected_full


def test_t9d_manifests_have_caps_workdirs_checks_and_no_credential_values() -> None:
    for name, stage, usd, counts in (
        ("run-t9d-smoke.json", "smoke", 70000, (1, 9, 1, 4, 2, 6)),
        ("run-t9d-full.json", "full", 450000, (10, 9, 5, 4, 15, 6)),
    ):
        path = ENVIRONMENT_NARRATION / name
        manifest = json.loads(path.read_text())
        serialized = path.read_text()
        assert manifest["workdir"] == f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9d-{stage}"
        assert manifest["max_parallel"] == 1
        assert len(manifest["tasks"]) == 1
        task = manifest["tasks"][0]
        assert task["max_attempts"] == 1
        assert "enforce_t9d.sh" in task["spec"]
        assert "Run COMMAND 1 exactly once" in task["spec"]
        assert ".plans/grounded-llm-environment-narration/t9d-search-opens-prereg.md" in task["spec"]
        assert f"--max-usd {usd / 1000000:.2f}" in task["spec"]
        assert task["ownership"] == [f"bench/results/environment-narration/t9d-search/{stage}"]
        assert str(usd) in task["check"]
        assert all(str(count) in task["spec"] for count in counts)
        assert all(str(count) in task["check"] for count in counts)
        assert "stopped_reason" in task["check"]
        assert "no credential" in task["spec"]
        assert "credential value" in task["check"]
        for name in ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_WORKER_TOKEN"):
            value = os.environ.get(name, "").strip()
            assert not value or value not in serialized
