# ruff: noqa: E501
"""Build the one-task Ringer manifest that fixes the five red tests (plus the shard manifest) the full suite found before the PR."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
OWN = [
    f"{R}/storygame/story_package/models.py",
    f"{R}/tests/test_speaker_text.py",
    f"{R}/tests/test_bench_item_facts.py",
    f"{R}/tests/shard_durations.json",
]

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never revert or reformat uncommitted work that is not yours (the tree is deliberately dirty and will be committed as it stands). You own only: {OWN[0]}, {OWN[1]}, {OWN[2]}, {OWN[3]}. Edit nothing else.

The full suite (`TMPDIR=/tmp .venv/bin/python -m pytest -q --no-cov -p no:cacheprovider`) shows exactly six red tests. Fix each at its cause:
1. tests/test_hidden_bench_matcher_probe.py (4 tests: test_shortlists_use_projection_and_head_package_has_no_new_candidates, test_dry_measurement_has_120_evaluations_and_fresh_provider_each_time, test_dry_run_refuses_an_over_budget_plan, test_429_stops_after_the_failing_row) fail with `TypeError: speaker_text is immutable` raised during `copy.deepcopy` of a package. Cause: `_FrozenSpeakerText` in storygame/story_package/models.py is a dict subclass whose mutators raise, and copy/pickle rebuild a dict subclass by calling `__setitem__`. Fix it in the class so deepcopy, copy.copy and pickle round-trip a populated `_FrozenSpeakerText` into an equal, still-immutable `_FrozenSpeakerText` (for example a `__reduce__` returning `(type(self), (dict(self),))`). Do not weaken immutability. Add ONE meaningful test to tests/test_speaker_text.py that deep-copies and pickles a loaded package's populated speaker_text mapping, checks equality, and checks that the copy still raises TypeError on item assignment.
2. tests/test_bench_item_facts.py::test_prepare_turn_refers_to_nested_place_but_not_current_place expects the referred line '- Michelle. Place: detention level.' but the current story authors Michelle's 3A placement text 'beside the captives' (plot.md `michelle: {{parent: detention_level, text: beside the captives}}`, already in the tree), so the line is '- Michelle. Place: beside the captives.'. Update only the Michelle expectation(s) in that test to the authored placement text; keep every other assertion.
3. tests/test_regen_shard_durations.py::test_real_manifest_covers_test_files fails because the manifest lacks the new test file tests/test_senior_official_bio.py. Run `TMPDIR=/tmp {R}/.venv/bin/python scripts/regen_shard_durations.py --missing-only` (it may also add other new test files; that is expected) so tests/shard_durations.json lists them. Do not rewrite durations of files already listed.
HOW TO RUN (from {R}): `TMPDIR=/tmp {R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/test_hidden_bench_matcher_probe.py tests/test_speaker_text.py tests/test_bench_item_facts.py tests/test_regen_shard_durations.py`; then `{R}/.venv/bin/python -m ruff check . && {R}/.venv/bin/python -m ruff format --check .`; then the full suite once. Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp
{R}/.venv/bin/python -m ruff check .
{R}/.venv/bin/python -m ruff format --check .
{R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider
"""

task = {
    "key": "fix-red-tests",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1500,
    "check_timeout_s": 1200,
    "ownership": OWN,
    "expect_files": [OWN[1]],
    "spec": spec,
    "check": check,
    "verified": "the full suite passes with Ruff clean, so the PR starts green",
}
m = {
    "run_name": "lead-up-contradictions-fix-red-tests",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-fix-red-tests",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/fix-red-tests-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("written")
