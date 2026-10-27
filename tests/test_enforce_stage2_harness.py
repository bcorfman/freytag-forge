from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
SCRIPT = ENVIRONMENT_NARRATION / "enforce_stage2.sh"
GENERATOR = ENVIRONMENT_NARRATION / "make_enforce_stage2_run_manifests.py"
MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-t9b-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-t9b-full.json",
}
PREREG = ".plans/grounded-llm-environment-narration/t9b-scope-prereg.md"


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def _generator_module():
    spec = importlib.util.spec_from_file_location("make_enforce_stage2_run_manifests", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stage2_script_has_preregistered_routes_ports_caps_and_cleanup() -> None:
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
    for expected in (
        "8796",
        "t9b-scope",
        "observe_topup",
        "observe_under_first",
        "--enforce",
        "--max-calls 90",
        "--max-calls 40",
        "--max-calls 800",
        "--max-calls 250",
        "0.05",
        "0.30",
    ):
        assert expected in text
    for forbidden in ("--shadow", "8795", "enforce-stage1", "8794"):
        assert forbidden not in text


def test_stage2_manifests_are_generated_byte_for_byte_and_have_caps(tmp_path: Path) -> None:
    module = _generator_module()
    for path in MANIFESTS.values():
        assert path.is_file()
    generated = tmp_path / "manifests"
    module.main(generated)
    for stage, path in MANIFESTS.items():
        assert (generated / path.name).read_bytes() == path.read_bytes()
        manifest = json.loads(path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        serialized = path.read_text(encoding="utf-8")
        assert ("50000" if stage == "smoke" else "300000") in task["check"]
        assert "enforce-stage1" not in serialized
        assert "shadow-sample" not in serialized
        assert "gpt-5.6-luna" in serialized
        assert "full_access" in serialized
        assert "max_attempts" in serialized
        assert PREREG in task["spec"]
        assert "run COMMAND 1 EXACTLY ONCE" in task["spec"]
        assert "FOREGROUND" in task["spec"]
        assert "do not finish while the script is running" in task["spec"]
        assert "observation_request" in task["check"]
        assert "credential" in task["check"]


def test_stage2_manifest_checks_cover_both_routes_and_exact_turns() -> None:
    for stage, path in MANIFESTS.items():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        serialized = json.dumps(manifest)
        assert "a/rows/rows.json" in serialized
        assert "a/rows/summary.json" in serialized
        assert "b/rows/rows.json" in serialized
        assert "b/rows/summary.json" in serialized
        assert "stopped_reason" in task["check"]
        assert "turn_elapsed_s" in task["check"]
        assert "enforce_attempts" in task["check"]
        assert "narration_attempts" in task["check"]
        assert "pull out the drawer" in task["check"]
        assert "pick up my laptop" in task["check"]
        assert ("--replicates 1" if stage == "smoke" else "--replicates 10") in task["spec"]
