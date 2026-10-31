# ruff: noqa: E501
"""Write build-t9h-j1c-drain.json: the free build of the enforced drain run harness (step 4 of the wiring plan)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
PREREG = f"{REPO}/.plans/grounded-llm-environment-narration/t9h-j1c-drain-enforced-prereg.md"
OWNED = [
    f"{REPO}/scripts/ringer/transcript_1a/live_baseline.py",
    f"{REPO}/scripts/ringer/environment_narration/enforce_t9h_drain.sh",
    f"{REPO}/scripts/ringer/environment_narration/enforce_drain_report.py",
    f"{REPO}/tests/test_live_baseline_scene_state.py",
    f"{REPO}/tests/test_enforce_drain_report.py",
]

SPEC = (
    f"You are the BUILD worker. Working directory: {REPO} (Python 3.12). export PYTHONPATH={REPO} TMPDIR=/tmp; run "
    "`.venv/bin/python` (never uv). Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN "
    ".venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. No network, no live model call, no billed "
    "call, no Worker, and you NEVER run enforce_t9h_drain.sh. Do not git commit. NEVER print or write any "
    "credential. NO regular expressions. Keep the code in the style of the surrounding files (comment density, "
    "naming, idiom). METHOD: write the tests FIRST, watch them fail for the right reason, then implement. "
    "You own ONLY: " + ", ".join(OWNED) + ". Never touch other files (enforce_report.py, enforce_t9h.sh, storygame/, "
    "the plan files, other tests); import from enforce_report.py instead of editing it. "
    f"Read the preregistration FIRST and follow it exactly: {PREREG}. "
    "1) live_baseline.py: add route `observe_storm_drain_1b` with the single command 'inspect the storm drain', "
    "register it in NEW_ROUTES and ROUTE_START_SCENES (start scene 1B, the same checkpoint the "
    "observe_park_bench_1b route uses); add a `--scene-state` flag that is only valid together with `--enforce` "
    "(argparse error otherwise) and builds the enforcing verifier with ObservationVerifier(capture_ask, "
    "scene_state=True); the default (no flag) must behave exactly as today. Every entry of the per-turn "
    "`enforce_attempts` records gains `scene_state` (the verifier report's `scene_state` field, a bool), and the "
    "summary/row metadata records whether the run used --scene-state. The counted_verify wrapper must forward the "
    "scene keyword to the real verify (verify(narration, relations, scene=scene)) so the J1c state is actually "
    "sent; keep old behaviour when scene is not given. A --dry-run of the new route with and without "
    "--scene-state must work and write rows. "
    "2) enforce_t9h_drain.sh smoke|full: model it on scripts/ringer/environment_narration/enforce_t9h.sh (local "
    "worker on a NEW port 8797, same env handling, no rerun, spent.json). It runs the OFF arm first "
    "(`--route observe_storm_drain_1b --enforce`, output $OUT/off/rows) and only if that arm's summary has "
    "stopped_reason null, the ON arm (same plus `--scene-state`, output $OUT/on/rows). smoke: --replicates 3, "
    "--max-calls 40 per arm, worker --max-usd 0.04. full: --replicates 20, --max-calls 220 per arm, worker "
    "--max-usd 0.20. OUT is bench/results/environment-narration/t9h-drain/$STAGE. `bash -n` must pass. "
    "3) enforce_drain_report.py: modes `--sheets --rows-off F --rows-on F --out DIR` writes a BLIND sheet (arm "
    "identity hidden: turns from both arms are shuffled with a fixed seed and given opaque ids; a separate "
    "key file maps ids to arm/replicate, written but not shown on the sheet) listing, per turn, every rejected "
    "first attempt and the committed narration, plus a labels template with the tags from the preregistration "
    "(opens_drain, moves_drain, gives_contents per committed narration; really_deficient per rejected attempt); "
    "reuse enforce_report.py's sheet and labels helpers where they fit. `--report --rows-off F --rows-on F "
    "--labels F --out F` joins the labels through the key file, and prints the gates D1 to D6 of the "
    "preregistration for the ON arm with the OFF arm printed beside it: D1 at least 18 of 20 ON turns committed "
    "(Wilson interval printed); D2 at least 16 of 20 ON turns accepted on the first attempt; D3 zero committed ON "
    "narrations labelled opens_drain, moves_drain or gives_contents; D4 every ON verifier request has scene_state "
    "true and no OFF request has it; D5 every unsuccessful ON turn has places_after == places_before, a typed error "
    "and no narration, and no turn used more than 2 narration attempts or 2 verifier requests; D6 at most 1 "
    "rejected ON first attempt labelled not really_deficient. The thresholds are for 20 replicates; with a "
    "different replicate count the report prints the counts and marks the gate 'not applicable (smoke)'. Printed "
    "not gated: OFF commit and first-attempt rates, verdict scores per arm with ranges, attempts per turn, the "
    "`call timing` block per arm if the rows carry it. Exit 1 when any gate fails; refuse (exit 2) if labels are "
    "missing for any turn. The labels file hash is printed. "
    "TESTS (hermetic, no live worker): test_live_baseline_scene_state.py: the new route's command and start "
    "scene; --scene-state without --enforce is rejected; a dry run with --scene-state records scene_state true on "
    "the enforcing attempts and a dry run without it records false/absent, and the OFF dry run's rows otherwise "
    "equal today's; the scene keyword reaches the verifier. test_enforce_drain_report.py: sheets are blind (arm "
    "names absent from the sheet text) and deterministic; report gate arithmetic on hand-made rows for a pass and "
    "for a fail of each of D1 to D6; missing labels refuse; non-20 replicate counts print not-applicable. Add only "
    "tests that cover real behavior; no redundant ones. Existing tests/test_live_baseline_*.py and "
    "tests/test_enforce_*.py must stay green. Finally run `.venv/bin/python -m ruff check --fix` and `ruff format` "
    "on the Python files you own and report the test counts and a --dry-run of the new route in both modes."
)

CHECK = (
    f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail "
    "&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
    "-p no:cacheprovider --no-cov tests/test_live_baseline_scene_state.py tests/test_enforce_drain_report.py "
    "tests/test_live_baseline_enforce.py tests/test_live_baseline_evidence.py tests/test_live_baseline_scene_start.py "
    "tests/test_live_baseline_default_output.py tests/test_enforce_report.py tests/test_enforce_report_t9h.py "
    "tests/test_observation_scene_state.py "
    "2>&1 | tee /tmp/j1c-drain-build-tests.out | tail -15 "
    "&& ! grep -Eq '[0-9]+ failed|FAILED|ERROR' /tmp/j1c-drain-build-tests.out "
    "&& grep -Eq '[0-9]+ passed' /tmp/j1c-drain-build-tests.out "
    "&& bash -n scripts/ringer/environment_narration/enforce_t9h_drain.sh "
    "&& .venv/bin/python -m ruff check scripts/ringer/transcript_1a/live_baseline.py "
    "scripts/ringer/environment_narration/enforce_drain_report.py tests/test_live_baseline_scene_state.py "
    "tests/test_enforce_drain_report.py "
    "&& .venv/bin/python -m ruff format --check scripts/ringer/transcript_1a/live_baseline.py "
    "scripts/ringer/environment_narration/enforce_drain_report.py tests/test_live_baseline_scene_state.py "
    "tests/test_enforce_drain_report.py "
    "&& rm -rf /tmp/j1c-drain-dry && .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py "
    "--route observe_storm_drain_1b --enforce --scene-state --dry-run --replicates 1 --out /tmp/j1c-drain-dry/on "
    "&& .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe_storm_drain_1b --enforce "
    "--dry-run --replicates 1 --out /tmp/j1c-drain-dry/off && test -s /tmp/j1c-drain-dry/on/rows.json "
    "&& test -s /tmp/j1c-drain-dry/off/rows.json"
)

MANIFEST = {
    "run_name": "t9h-j1c-drain-build",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-j1c-drain-build",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "j1c-drain-harness",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "ownership": OWNED,
            "expect_files": OWNED,
            "verified": "storm-drain bench route, --scene-state flag, OFF/ON launcher and blind-label report with gates D1-D6; nothing billed",
            "spec": SPEC,
            "check": CHECK,
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("build-t9h-j1c-drain.json")
    out.write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(out)
