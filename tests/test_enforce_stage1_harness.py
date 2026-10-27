from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
SCRIPT = ENVIRONMENT_NARRATION / "enforce_stage1.sh"
GENERATOR = ENVIRONMENT_NARRATION / "make_enforce_stage1_run_manifests.py"
MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-enforce-stage1-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-enforce-stage1-full.json",
}
PREREG = ".plans/grounded-llm-environment-narration/t9-enforce-stage1-prereg.md"
ROUTE = (
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


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def _generator_module():
    spec = importlib.util.spec_from_file_location("make_enforce_stage1_run_manifests", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stage1_script_has_only_stage1_runtime_settings() -> None:
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
    for expected in ("8795", "--enforce", "enforce-stage1", "--max-calls 70", "0.03", "--max-calls 700", "0.20"):
        assert expected in text
    assert "--shadow" not in text
    for forbidden in ("shadow-sample", "8793", "8794"):
        assert forbidden not in text


def test_stage1_manifests_are_generated_byte_for_byte_and_keep_stage_paths(tmp_path: Path) -> None:
    for path in MANIFESTS.values():
        assert path.is_file()

    module = _generator_module()
    generated = tmp_path / "manifests"
    generated.mkdir()
    module.main(generated)
    for stage, path in MANIFESTS.items():
        assert (generated / path.name).read_bytes() == path.read_bytes()
        manifest = json.loads(path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        paths = json.dumps(
            {
                "workdir": manifest["workdir"],
                "ownership": task["ownership"],
                "expect_files": task["expect_files"],
            }
        )
        serialized = path.read_text(encoding="utf-8")
        assert "shadow-sample3" not in paths
        assert "topup" not in paths
        assert "enforce-stage1" in paths
        assert "observe_topup" in serialized
        assert task["key"] == f"billed-enforce-stage1-{stage}"
        assert manifest["workdir"] == (
            f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-enforce-stage1-{stage}"
        )
        assert "gpt-5.6-luna" in serialized
        assert "model_reasoning_effort=low" in serialized
        assert "full_access" in serialized
        assert "max_attempts" in serialized
        assert PREREG in task["spec"]
        assert "run COMMAND 1 EXACTLY ONCE" in task["spec"]
        assert "NEVER run it a second time" in task["spec"]
        assert "Do not edit any file." in task["spec"]
        assert (
            "Do not print, echo, cat or log environment variables or the .env file or any credential." in task["spec"]
        )
        assert "Do not git commit." in task["spec"]
        assert "FOREGROUND" in task["spec"]
        assert "wait for it to exit" in task["spec"]
        assert "enforcing observation verifier ON" in task["spec"]
        assert "9 commands" in task["spec"]
        for command in ROUTE:
            assert command in task["spec"]


def test_stage1_manifest_checks_have_caps_and_telemetry_contract() -> None:
    for stage, path in MANIFESTS.items():
        task = json.loads(path.read_text(encoding="utf-8"))["tasks"][0]
        ceiling = "30000" if stage == "smoke" else "200000"
        assert ceiling in task["check"]
        assert "summary['enforce'] is True" in task["check"]
        assert "summary.get('shadow', False) is False" in task["check"]
        assert "turn_elapsed_s" in task["check"]
        assert "enforce_attempts" in task["check"]
        assert "narration_attempts" in task["check"]
        assert "stopped_reason" in task["check"]
        assert "spent_micro_usd" in task["check"]
        assert "pick up my laptop" in task["check"]
        assert "inspect the passenger seat" in task["check"]
        assert "credential" in task["check"]
