import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT_NARRATION = ROOT / "scripts/ringer/environment_narration"
GENERATOR = ENVIRONMENT_NARRATION / "make_shadow2_topup_run_manifests.py"
MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-shadow2-topup-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-shadow2-topup-full.json",
}
SAMPLE2_MANIFESTS = {
    "smoke": ENVIRONMENT_NARRATION / "run-shadow2-smoke.json",
    "full": ENVIRONMENT_NARRATION / "run-shadow2-full.json",
}


def _safe_environment() -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "TMPDIR": "/tmp"}


def test_topup_manifests_exist_and_have_topup_paths_and_checks():
    hard_rule_sentences = (
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
    )

    for stage, path in MANIFESTS.items():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        serialized = json.dumps(manifest)
        check = task["check"]
        spec = task["spec"]
        output = f"bench/results/environment-narration/shadow-sample2-topup/{stage}"

        assert task["key"] == f"billed-shadow-sample2-topup-{stage}"
        assert manifest["workdir"] == (
            f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-topup-{stage}"
        )
        assert "shadow-sample2/" not in serialized
        assert "shadow_sample2.sh" not in serialized
        assert "shadow_sample2_topup.sh" in spec
        assert "observe_topup" in spec
        assert "pick up my laptop" in spec
        assert output in task["ownership"]
        assert all(output in expected for expected in task["expect_files"])

        assert "summary['shadow']" in check
        assert "spent_micro_usd" in check
        assert ("30000" if stage == "smoke" else "200000") in check
        assert "== 9" in check
        assert "pick up my laptop" in check
        assert "inspect the passenger seat" in check
        assert "stopped_reason" in check
        assert "[-1]" in check
        assert "[7]" in check
        assert "credential" in check

        for sentence in hard_rule_sentences:
            assert sentence in spec
        assert "approved in the sample-2 preregistration" in spec
        assert "the runner must not start unless the human's go for this stage was given in the task statement" in spec


def test_topup_generator_is_idempotent_and_preserves_sample2_bytes():
    before_topup = {path: path.read_bytes() for path in MANIFESTS.values()}
    before_sample2 = {
        stage: subprocess.run(
            ["git", "show", f"HEAD:{path.relative_to(ROOT)}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        for stage, path in SAMPLE2_MANIFESTS.items()
    }

    result = subprocess.run(
        [".venv/bin/python", str(GENERATOR)],
        cwd=ROOT,
        env=_safe_environment(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert {path: path.read_bytes() for path in MANIFESTS.values()} == before_topup
    for stage, path in SAMPLE2_MANIFESTS.items():
        assert path.read_bytes() == before_sample2[stage]


def test_topup_specs_state_topup_numbers_not_sample2_numbers():
    expected = {
        "smoke": "about 46 calls, cap 70 calls, ceiling $0.03",
        "full": "about 460 calls, cap 600 calls, ceiling $0.20",
    }
    for stage, path in MANIFESTS.items():
        spec = json.loads(path.read_text(encoding="utf-8"))["tasks"][0]["spec"]
        assert expected[stage] in spec
        for stale in ("67 calls", "670 calls", "cap 100 calls", "cap 900 calls", "$0.05", "$0.30"):
            assert stale not in spec
