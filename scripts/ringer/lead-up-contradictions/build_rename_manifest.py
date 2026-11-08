# ruff: noqa: E501
"""Build the one-task Ringer manifest that renames 'coded announcements' -> 'secret messages' and 'coded words' -> 'code words' in the 3A story text."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
PRE = "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/5249d927-7382-457d-8bc9-509a8e23fa87/scratchpad/rename_pre"
FILES = [
    "data/stories/continuity-initiative/plot.md",
    "data/stories/continuity-initiative/knowledge.yaml",
    "data/stories/continuity-initiative/handoffs.yaml",
    "tests/test_richer_3a.py",
    "tests/test_1c_closeout.py",
    "tests/test_speaker_text.py",
    "scripts/ringer/lead-up-contradictions/capture_3a.py",
    "scripts/ringer/lead-up-contradictions/build_3a_manifest.py",
    ".plans/lead-up-contradictions-prereg.md",
]
OWN = [f"{R}/{f}" for f in FILES] + [
    f"{R}/bench/results/lead-up-contradictions/frozen-3A-CUR.json",
    f"{R}/bench/results/lead-up-contradictions/frozen-3A-CAND.json",
]
TESTS = "tests/test_richer_3a.py tests/test_1c_closeout.py tests/test_speaker_text.py tests/test_knowledge_projection.py tests/test_markdown_story_package.py tests/test_prompt_presence.py tests/test_cloudflare_transport.py tests/test_place_scoped_feed.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_senior_official_bio.py tests/test_speaker_lines.py tests/test_voiceable_knowledge.py tests/test_referred_reach.py tests/test_richer_1b_value.py tests/test_richer_1c_voice.py tests/test_bench_item_facts.py"
DESEL = "--deselect tests/test_bench_item_facts.py::test_prepare_turn_refers_to_nested_place_but_not_current_place"
file_list = "\n".join(f"- {f}" for f in FILES)

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never revert or reformat uncommitted work that is not yours (the tree is deliberately dirty). You own only the files listed below and the two frozen JSON files that capture_3a.py rewrites. Do not read or edit {D}/validate_rename.py or {D}/validate_3a.py (independent checks; only run them).

GOAL: a pure wording rename in the Scene 3A story text, approved by Brandon. 'coded announcements' (the phrase has little meaning) becomes 'secret messages', and 'coded words' becomes 'code words'. Exactly these replacements, nothing else:
- 'coded announcement' -> 'secret message' (so 'coded announcements' -> 'secret messages', 'her coded announcements' -> 'her secret messages'), and capitalised 'Coded announcements' -> 'Secret messages'.
- 'coded words' -> 'code words' (and 'Coded words' -> 'Code words').
- Python strings that are split across lines, such as `... and coded "` followed by a next-line `"announcements."`, are renamed the same way (`secret "` / `"messages."`); a line that gets longer or shorter may be re-wrapped by `ruff format`, but the joined string must be exactly the renamed text.
Do NOT touch any other use of the word 'coded' (for example 'coded message', 'coded maintenance messages', 'coded route', 'coded records', 'coded path'): those are other story ideas. Do NOT touch the speaker lines that say 'secret announcements' (Brandon's approved organizing wording stays). Do NOT edit anything under tests/fixtures/, bench/frozen/, bench/results/ (except the two frozen-3A files written by the script), docs/, or any other file.
Files to change (the only files you may edit):
{file_list}
A copy of each file as it was before your edit is under {PRE}/<same relative path>; applying the rename above to that copy must reproduce your result (Python files only need to match as parsed code).

THEN refresh the frozen payloads: from {R} run `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_3a.py` (zero model calls). Then `{R}/.venv/bin/python -m ruff format {" ".join(f for f in FILES if f.endswith(".py"))}` and `{R}/.venv/bin/python -m ruff check` on the same files.
Then run the focused suites: `TMPDIR=/tmp {R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {DESEL} {TESTS}`. One test in tests/test_bench_item_facts.py (test_prepare_turn_refers_to_nested_place_but_not_current_place) was already failing before this task because of unrelated uncommitted work; it is deselected, leave it. Every other failure is yours to fix (a test that pins the old phrase should be updated by the same rename, never weakened). Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_rename.py {PRE}
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_3a.py > /dev/null
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_3a.py
{R}/.venv/bin/python -m ruff check {" ".join(f for f in FILES if f.endswith(".py"))}
{R}/.venv/bin/python -m ruff format --check {" ".join(f for f in FILES if f.endswith(".py"))}
{R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {DESEL} {TESTS}
"""

task = {
    "key": "rename-coded-announcements",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1500,
    "check_timeout_s": 900,
    "ownership": OWN,
    "expect_files": [f"{R}/bench/results/lead-up-contradictions/frozen-3A-CUR.json"],
    "spec": spec,
    "check": check,
    "verified": "every owned file equals its saved copy with only the rename applied, the 3A payloads are refreshed and validate, and the focused suites pass",
}
m = {
    "run_name": "lead-up-contradictions-rename-phrase",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-rename-phrase",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/rename-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("written")
