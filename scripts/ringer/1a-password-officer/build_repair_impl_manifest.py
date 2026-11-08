# ruff: noqa: E501
"""Ringer task 2 of 2 for the fused-segment repair: implement against the frozen failing tests."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
TEST = f"{R}/tests/test_fused_segment_repair.py"
SHA = "c39de0c8343f9994b6e9ad1956d2950477d5dd20c4102cf1cf4c906037920405"
CF = f"{R}/storygame/runtime/cloudflare.py"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {CF} (edit) and, if a docs file under {R}/docs already describes segment salvage (grep for 'salvag'), one short added sentence there. Do NOT edit {TEST} (frozen failing tests; the check verifies its hash), anything else in storygame, data, tests or packages. Read {TEST} first, then CloudflareTurnProvider._dispatch, _salvage_malformed_segments, _parse_eligible_proposal, _recover_malformed_response and _log_segment_salvage in {CF}.

GOAL: add a typed first-reply repair for FUSED segment objects, exactly as the frozen tests encode. Implement a method (working name _repair_fused_segments(self, response)) returning a repaired reply dict or None, and call it in _dispatch in the existing 'except RuntimeContractError' branch of the FIRST reply, BEFORE _salvage_malformed_segments: if it returns a dict, try self._parse_eligible_proposal on it; if that parses, return self._accept_proposal(repaired, proposal); if it does not (RuntimeContractError), fall through to the existing salvage/recovery logic with the ORIGINAL response, unchanged. The reply to a recovery request must never be repaired (the repair is only in the first-reply branch). Rules for a segment object: it qualifies only if it is a dict whose 'kind' is one of narration, dialogue, action, whose 'text' is a non-blank str, and whose keys other than kind, text, speaker_id, grounding_ids are exactly: 'narration' (a non-blank str) plus any number of keys that contain no letter and no digit (str.isalnum() false for every character is NOT the test; use: not any(ch.isalnum() for ch in key)). A qualifying object becomes two segments in place: first {{kind, text and its speaker_id/grounding_ids only if present}}, second {{'kind': 'narration', 'text': <narration string>}} (no speaker_id, no grounding_ids). Non-qualifying segments are left exactly as they are, so a reply that still has any invalid segment after repair simply fails the normal parse and takes the normal path. Preserve every top-level key of the reply other than 'segments' (after unwrapping a 'response'/'content' wrapper the same way _salvage_malformed_segments does). Apply the same guard salvage uses for selected_knowledge_ids: if it is not a list of strings, or names an id not grounded in a surviving valid segment of the REPAIRED reply, return None. Return None unless at least one object was repaired. When it repairs, log ONE warning (same logger and style as _log_segment_salvage) with the number of repaired objects and the JSON key shapes only (never any text of the reply, use _segment_shape). No regex, no parsing of the model's prose, no new network call, no change to prompts. Keep it small and typed.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest {TEST} tests/test_cloudflare_transport.py -q --no-cov -p no:cacheprovider 2>&1 | tail -30`; `{PY} -m ruff format {CF} && {PY} -m ruff check {CF}`; then the full suite `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 > /tmp/repair-full.txt 2>&1; tail -15 /tmp/repair-full.txt`. Every test must pass."""

check = f"""set -eo pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
[ "$(sha256sum {TEST} | cut -d' ' -f1)" = "{SHA}" ] || {{ echo 'frozen test file was modified'; exit 1; }}
git diff --quiet -- data packages tests bench
git diff --name-only -- storygame | grep -vx 'storygame/runtime/cloudflare.py' && {{ echo 'unexpected storygame file changed'; exit 1; }} || true
{PY} -m ruff check storygame tests
{PY} -m ruff format --check storygame tests
{PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider > /tmp/repair-new.txt 2>&1 || {{ tail -30 /tmp/repair-new.txt; echo 'new tests failed'; exit 1; }}
tail -3 /tmp/repair-new.txt
{PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 > /tmp/repair-full.txt 2>&1 || {{ tail -40 /tmp/repair-full.txt; echo 'full suite failed'; exit 1; }}
tail -3 /tmp/repair-full.txt
"""
task = {
    "key": "implement-fused-repair",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 3000,
    "check_timeout_s": 1800,
    "ownership": [CF],
    "expect_files": [CF],
    "spec": spec,
    "check": check,
    "verified": "frozen tests pass, full suite passes, only cloudflare.py changed",
}
manifest = {
    "run_name": "fused-segment-repair",
    "workdir": "/home/bcorfman/dev/ringer-work/fused-segment-repair",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/repair-impl-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
