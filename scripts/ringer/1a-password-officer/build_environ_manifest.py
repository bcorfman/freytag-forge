# ruff: noqa: E501
"""Ringer task: stop tests from leaking os.environ changes into later tests (the shard-0 flake)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
CONF = f"{R}/tests/conftest.py"
NEWTEST = f"{R}/tests/test_environment_isolation.py"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You may edit ONLY {CONF} (add one autouse fixture), create {NEWTEST}, and update {R}/tests/shard_durations.json by running `{PY} scripts/regen_shard_durations.py --missing-only`. Nothing else: no storygame, script or data file.

ROOT CAUSE (already established; do not re-investigate): scripts/ringer/transcript_1a/live_baseline.py `main()` writes os.environ['FREYTAG_WORLD_CAPTURE'] = '1' directly (and may setdefault CLOUDFLARE_WORKER_URL). tests/test_live_baseline_feedback_routes.py calls main in-process; its monkeypatch restores only the variables it set through monkeypatch, so FREYTAG_WORLD_CAPTURE stays '1' for every later test in the same pytest process. storygame/web_demo.py engine_for then takes the world-capture path, which needs CLOUDFLARE_WORKER_URL, and session creation returns 503, so many tests in tests/test_web_demo.py fail with KeyError 'session_id' depending on how pytest-xdist spreads tests over workers. Deterministic reproduction: `{PY} -m pytest tests/test_live_baseline_feedback_routes.py tests/test_web_demo.py -q --no-cov -p no:cacheprovider -n 0` fails (26 failures) before the fix.
FIX: in {CONF} add a function-scoped autouse fixture (look at the existing autouse fixtures near lines 413 and 528 for the style and put it with them) that snapshots dict(os.environ) at test start and, at teardown, restores os.environ exactly to that snapshot (remove added keys, reset changed values, re-add removed keys) without replacing the os.environ object. A short docstring says why (a test or script that writes os.environ directly must not leak into later tests). Do not change any other fixture.
REGRESSION TEST: {NEWTEST}, a small deterministic test of the isolation that does not depend on test order. Preferred: use pytest's 'pytester' fixture (enable it in the test module with pytest_plugins = ['pytester'] only if the repo's pytest version allows that in a test module; otherwise add it via -p in a way you verify works) to run an inner two-test file in-process under the REAL repo fixture: the inner run must load the same fixture (if running the real conftest in the inner run is not practical, move the fixture body into a small importable module tests/environ_isolation.py that conftest.py imports and re-exports as the autouse fixture, and have the inner run load that module as a plugin with pytester.makeconftest('pytest_plugins = ["tests.environ_isolation"]') or equivalent). The inner file: test A sets os.environ['FREYTAG_ISOLATION_PROBE'] = '1', deletes os.environ['PATH_PROBE_REMOVED'] after setting it before the snapshot is not needed, and changes an existing variable; test B (run after A with -p no:randomly -n 0 inside the inner run) asserts the probe is gone and the changed variable has its original value. Assert the inner run passes (outcomes passed=2). If this proves impractical, instead write one plain test that calls the fixture function's underlying generator manually (next() then mutate then next() again to finish) and asserts the environment was restored, and say so in a comment. The test must FAIL if the fixture is removed (verify by temporarily commenting the fixture out, then restore it).
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest tests/test_live_baseline_feedback_routes.py tests/test_web_demo.py {NEWTEST} -q --no-cov -p no:cacheprovider -n 0 2>&1 | tail -15`; `{PY} -m ruff format {CONF} {NEWTEST} && {PY} -m ruff check {CONF} {NEWTEST}`. Then the full suite `... -m pytest -q --no-cov -p no:cacheprovider -n 4 > /tmp/env-full.txt 2>&1; tail -8 /tmp/env-full.txt`. Everything must pass."""

check = f"""set -eo pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
git diff --name-only | grep -vxE 'tests/conftest.py|tests/shard_durations.json' && {{ echo 'unexpected tracked file changed'; exit 1; }} || true
git diff --quiet -- storygame data scripts bench packages
{PY} -m ruff check tests
{PY} -m ruff format --check tests
{PY} -m pytest tests/test_live_baseline_feedback_routes.py tests/test_web_demo.py {NEWTEST} -q --no-cov -p no:cacheprovider -n 0 > /tmp/env-pair.txt 2>&1 || {{ tail -25 /tmp/env-pair.txt; echo 'the polluting pair still fails'; exit 1; }}
tail -2 /tmp/env-pair.txt
{PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 > /tmp/env-full.txt 2>&1 || {{ tail -30 /tmp/env-full.txt; echo 'full suite failed'; exit 1; }}
tail -2 /tmp/env-full.txt
"""
task = {
    "key": "isolate-test-environment",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 3000,
    "check_timeout_s": 1800,
    "ownership": [CONF, NEWTEST, f"{R}/tests/shard_durations.json", f"{R}/tests/environ_isolation.py"],
    "expect_files": [NEWTEST, CONF],
    "spec": spec,
    "check": check,
    "verified": "the known polluting pair passes, the new isolation test passes, the full suite passes",
}
manifest = {
    "run_name": "test-environment-isolation",
    "workdir": "/home/bcorfman/dev/ringer-work/test-environment-isolation",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/environ-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
