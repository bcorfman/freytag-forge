# ruff: noqa: E501
"""Ringer task: fix two flawed frozen tests and revert an unrequested helper change in the fused-segment repair."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
TEST = f"{R}/tests/test_fused_segment_repair.py"
CF = f"{R}/storygame/runtime/cloudflare.py"
KEEP = (
    "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/181d1eb2-ab7c-4a1f-b9cb-3cef730d1076/scratchpad/keep-hashes.json"
)

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You may edit ONLY {TEST} and {CF}.
CONTEXT. {CF} now has a new method _repair_fused_segments (keep it exactly; it is correct) called from _dispatch. Two of the tests in {TEST} are flawed, and the worker that wrote the method also changed the existing helper CloudflareTurnProvider._segment_shape (it changed the sort key of the keys) only to match one test's assumed string; that change is outside scope.
1. In {CF} restore _segment_shape to exactly its original form: the line `keys = ",".join(sorted(str(key) for key in value))` (see `git diff -- {CF}`: revert only that hunk). Keep the rest of the diff.
2. In {TEST} rewrite ONLY these two tests, keep their names, leave every other test and helper byte-identical (the check compares their source hashes):
 - test_repair_is_logged_once_with_shapes_only: keep the checks that exactly one warning containing 'repair' is logged, that it contains the count 1, and that neither reply text appears in it; replace the exact-string assertion on the shape with order-independent assertions that each of the key names 'kind', 'text', 'narration' and the junk key '}},{{' appears in the warning (the original _segment_shape sorts the keys as strings, so the junk key comes last).
 - test_repaired_second_segment_carries_no_grounding_or_speaker: the old fixture used grounding_ids=['known-id'], which the real provider rejects for eligibility whether or not a repair happens, so the test could never pass. Make it two parts: (a) end to end through the provider: a fused object with speaker_id='officer_reyes' only (no grounding_ids; check that a speaker_id passes the provider; if the provider rejects an unknown speaker, drop speaker_id from the end-to-end part and say so in a comment), assert the first repaired segment keeps its speaker_id and the second has neither speaker_id nor grounding_ids; (b) a direct unit assertion on provider._repair_fused_segments(reply) for a fused object carrying speaker_id and grounding_ids=['known-id'] (and selected_knowledge_ids=['known-id']): the first part keeps both keys, the second part has neither.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest {TEST} tests/test_cloudflare_transport.py -q --no-cov -p no:cacheprovider 2>&1 | tail -20`; `{PY} -m ruff format {TEST} {CF} && {PY} -m ruff check {TEST} {CF}`. All tests must pass."""

check = f"""set -eo pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} - <<'PY'
import ast, hashlib, json, sys
src = open('{TEST}').read()
tree = ast.parse(src)
want = json.load(open('{KEEP}'))
now = {{n.name: hashlib.sha256(ast.get_source_segment(src, n).encode()).hexdigest() for n in tree.body if isinstance(n, ast.FunctionDef)}}
bad = [k for k, v in {{**want['tests'], **want['helpers']}}.items() if now.get(k) != v]
missing = [k for k in ('test_repaired_second_segment_carries_no_grounding_or_speaker', 'test_repair_is_logged_once_with_shapes_only') if k not in now]
if bad or missing:
    print('frozen tests or helpers changed:', bad, 'missing:', missing); sys.exit(1)
print('untouched tests and helpers identical')
PY
git diff -U0 -- {CF} | grep -E '^[-+].*keys = ' && {{ echo '_segment_shape was not restored'; exit 1; }} || true
git diff --name-only -- storygame data packages bench docs | grep -vx 'storygame/runtime/cloudflare.py' && {{ echo 'unexpected file changed'; exit 1; }} || true
{PY} -m ruff check storygame tests
{PY} -m ruff format --check storygame tests
{PY} -m pytest tests/test_fused_segment_repair.py tests/test_cloudflare_transport.py -q --no-cov -p no:cacheprovider > /tmp/repair-new.txt 2>&1 || {{ tail -30 /tmp/repair-new.txt; echo 'tests failed'; exit 1; }}
tail -2 /tmp/repair-new.txt
{PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 > /tmp/repair-full.txt 2>&1 || {{ tail -40 /tmp/repair-full.txt; echo 'full suite failed'; exit 1; }}
tail -2 /tmp/repair-full.txt
"""
task = {
    "key": "fix-fused-repair-tests",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 2400,
    "check_timeout_s": 1800,
    "ownership": [TEST, CF],
    "expect_files": [TEST],
    "spec": spec,
    "check": check,
    "verified": "the two flawed tests are fixed, other tests identical, helper restored, full suite green",
}
manifest = {
    "run_name": "fused-segment-repair",
    "workdir": "/home/bcorfman/dev/ringer-work/fused-segment-repair",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/repair-fix-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
