import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
SCRIPT = ENVIRONMENT_NARRATION / "shadow_sample3_postchange.sh"
GENERATOR = ENVIRONMENT_NARRATION / "make_shadow3_postchange_run_manifests.py"
MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-shadow3-postchange-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-shadow3-postchange-full.json",
}
TOPUP_FILES = (
    "scripts/ringer/environment_narration/shadow_sample2_topup.sh",
    "scripts/ringer/environment_narration/run-shadow2-topup-smoke.json",
    "scripts/ringer/environment_narration/run-shadow2-topup-full.json",
)
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
HARD_RULES = (
    "run COMMAND 1 EXACTLY ONCE",
    "NEVER run it a second time",
    "Do not edit any file.",
    "Do not print, echo, cat or log environment variables or the .env file or any credential.",
    "Do not git commit.",
    "The script refuses to run if its port is busy (exit 4); do not do your own port checks, just run COMMAND 1 once.",
    "a non-zero exit with partial rows is a valid outcome, do not retry",
)
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-postchange-rerun-prereg.md"


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def _manifest(stage: str) -> dict:
    return json.loads(MANIFESTS[stage].read_text(encoding="utf-8"))


def _approval(stage: str) -> str:
    calls = "50" if stage == "smoke" else "495"
    cap = "70" if stage == "smoke" else "600"
    ceiling = "0.03" if stage == "smoke" else "0.20"
    ending = "." if stage == "smoke" else "; expected about nine cents."
    return (
        "This run is a re-run of the top-up route under the corrected shadow order, approved in the "
        f"preregistration {PREREG}, and the runner must not start unless the human's go for this stage was "
        f"given in the task statement (the manifest is only launched by the orchestrator after the go). It uses "
        f"about {calls} calls, cap {cap} calls, ceiling ${ceiling}{ending}"
    )


def test_postchange_script_is_the_topup_script_with_only_requested_substitutions():
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
    for expected in ("shadow-sample3-postchange", "observe_topup", "70", "600", "0.03", "0.20", "8794"):
        assert expected in text
    assert "shadow-sample2" not in text
    assert "8793" not in text

    topup = (ENVIRONMENT_NARRATION / "shadow_sample2_topup.sh").read_text(encoding="utf-8")
    old_header = (
        "# Billed shadow-verifier sample 2 top-up against a local Worker with a hard dollar cap (see\n"
        "# .plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md)."
    )
    new_header = (
        "# Billed shadow-verifier sample 3 post-change re-run against a local Worker with a hard dollar cap (see\n"
        f"# {PREREG})."
    )
    expected = topup.replace(old_header, new_header)
    expected = expected.replace("shadow_sample2_topup.sh smoke|full", "shadow_sample3_postchange.sh smoke|full")
    expected = expected.replace("PORT=8793", "PORT=8794")
    expected = expected.replace("shadow-sample2-topup/$STAGE", "shadow-sample3-postchange/$STAGE")
    assert text == expected


def test_postchange_manifests_have_only_sample3_paths_and_exact_contract():
    expected_replicates = {"smoke": 1, "full": 10}
    expected_ceiling = {"smoke": "30000", "full": "200000"}
    for stage, path in MANIFESTS.items():
        assert path.is_file()
        manifest = _manifest(stage)
        task = manifest["tasks"][0]
        serialized = json.dumps(manifest)
        path_fields = json.dumps(
            {
                "key": task["key"],
                "workdir": manifest["workdir"],
                "ownership": task["ownership"],
                "expect_files": task["expect_files"],
            }
        )

        assert task["key"] == f"billed-shadow-sample3-postchange-{stage}"
        assert manifest["workdir"] == (
            f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow3-postchange-{stage}"
        )
        assert "shadow-sample2" not in serialized
        assert "shadow_sample2" not in serialized
        assert "shadow2-topup" not in serialized
        assert "topup" not in path_fields
        assert "shadow-sample3-postchange" in path_fields
        assert "shadow_sample3_postchange.sh" in task["spec"]
        assert "observe_topup" in task["spec"]
        assert "9 commands" in task["spec"]
        assert len(ROUTE) == 9
        for command in ROUTE:
            assert command in task["spec"]
        assert _approval(stage) in task["spec"]
        assert "top-up route" in task["spec"]

        for sentence in HARD_RULES:
            assert sentence in task["spec"]
        assert f"{expected_ceiling[stage]}" in task["check"]
        assert "summary['shadow']" in task["check"]
        assert "spent_micro_usd" in task["check"]
        assert "== 9" in task["check"]
        assert "pick up my laptop" in task["check"]
        assert "inspect the passenger seat" in task["check"]
        assert "stopped_reason" in task["check"]
        assert "[-1]" in task["check"]
        assert "[7]" in task["check"]
        assert "credential" in task["check"]
        assert f"len(rows) == {expected_replicates[stage]}" in task["check"]


def test_postchange_generator_is_idempotent_and_topup_files_are_unchanged():
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
    assert {path: path.read_bytes() for path in MANIFESTS.values()} == before

    for relative in TOPUP_FILES:
        current = (ROOT / relative).read_bytes()
        expected = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert current == expected
