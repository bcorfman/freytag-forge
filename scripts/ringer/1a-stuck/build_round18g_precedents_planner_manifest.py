# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18g: the planner is given the verified precedents and must name the one it follows. FREE: no model call.

One Codex task. Usage: build_round18g_precedents_planner_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-precedents-planner"
OWNED = [
    "factory/stations/fix_plan.py",
    "factory/stations/planner.py",
    "tests/test_factory_fix_plan.py",
    "tests/test_factory_planner.py",
    "tests/test_factory_wiring.py",
    "tests/test_factory_manifests.py",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/planner.py` asks Sonnet for one story-data fix plan, and `factory/stations/fix_plan.py` builds the evidence packet (`build_evidence`) and lints the plan (`lint_plan`). Read both and their tests first. The project's rule is: precedents first. The planner must start from what the project already proved, try the proven technique first, and only then propose something unprecedented, saying what it checked. A verified precedents file now exists at `factory/precedents/stuck_turns.md` (five sections: Winners, Lost or rejected, Never do, Pacing events and effect facts, Transitions and exits; every bullet carries a quote and a source). The planner has never been given it.

BUILD 1, evidence. `build_evidence` adds a key `precedents` holding the text of a precedents file: the path comes from the ticket payload key `precedents_path` (absolute, or relative to the repository root) and defaults to `factory/precedents/stuck_turns.md` under the repository root (derive the root from the module location, the way the other stations do). The text is cut to 20000 characters. A missing or unreadable file gives `precedents: null` (never an exception). Nothing else in the packet changes.

BUILD 2, brief. In `PLANNER_BRIEF` add, at a 12th grade reading level and story-agnostic (no story names): the evidence holds precedents, which are fixes the project already proved, fixes that lost, and things that must never be done; try a proven technique first and never choose a fix the precedents list as lost or never do; begin the `reason` with `Precedent: ` followed by the name of the proven technique you follow; when no precedent covers the case, begin it with `Precedent: none` and say in the reason what you checked and why no precedent covers it. Keep every existing sentence and the JSON shape; the `reason` limit of 400 characters stays, so keep the instruction short.

BUILD 3, lint. In `lint_plan`, a new rule with the problem prefix `plan.precedent`: the plan's `reason` must start with `Precedent:` (case-sensitive, after stripping leading whitespace); message `plan.precedent reason must begin with Precedent: and name the proven technique followed, or Precedent: none with what was checked`. Keep every other rule and message unchanged.

TESTS (hermetic; stubs only). Update every existing plan fixture in the owned test files so its `reason` begins with `Precedent: `, keeping their intent. New tests, named exactly, in `tests/test_factory_fix_plan.py`: `test_evidence_carries_the_precedents_text` (the default file's text appears under `precedents`, cut to 20000 characters when longer; a payload `precedents_path` to a temp file is used instead), `test_evidence_precedents_is_null_when_the_file_is_missing`, `test_lint_requires_a_precedent_prefix_in_the_reason` (a plan without it gets exactly one `plan.precedent` problem; with `Precedent: none, nothing covers a fixed exit` it gets none). In `tests/test_factory_planner.py`: `test_planner_brief_asks_for_precedents_first` (the brief mentions precedents, the `Precedent:` prefix and `Precedent: none`), and `test_planner_prompt_includes_the_precedents_text` (the built prompt contains a marker string from a temp precedents file given through the payload). Each test file still runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@ (plus an existing `tests/test_factory_*.py` only where the new rule forces a fixture change). Never edit `factory/precedents/`, story data, `storygame/`, `factory/config/`, `factory/stations/wiring.py` or `factory/stations/fun_review.py`. Write NOTES_18G.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f factory/precedents/stuck_turns.md || { echo "precedents file missing"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/(fix_plan|planner)\\.py|tests/test_factory_[a-z0-9_]+\\.py)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt" factory/stations/planner.py; then echo "story-specific word in planner.py"; exit 1; fi
grep -q "plan.precedent" factory/stations/fix_plan.py || { echo "plan.precedent rule missing"; exit 1; }
for name in test_evidence_carries_the_precedents_text test_evidence_precedents_is_null_when_the_file_is_missing test_lint_requires_a_precedent_prefix_in_the_reason test_planner_brief_asks_for_precedents_first test_planner_prompt_includes_the_precedents_text; do
  grep -rq "def $name" tests || { echo "test $name missing"; exit 1; }
done
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_fix_plan.py tests/test_factory_planner.py
took=$(( $(date +%s) - start ))
echo "fix plan and planner tests took $took s (budget 30 s)"
[ "$took" -le 30 ] || { echo "over the 30 s budget"; exit 1; }
.venv/bin/python -m pytest -q -p no:cacheprovider -n 6 tests/test_factory_wiring.py tests/test_factory_manifests.py tests/test_factory_line.py tests/test_factory_stations.py tests/test_factory_fun_review.py
.venv/bin/python -m ruff check factory tests/test_factory_fix_plan.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fix_plan.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/precedents-planner.patch"
test -s "$WORK/out/precedents-planner.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK).replace("@OWNED@", ", ".join(OWNED))

    return {
        "run_name": "factory-precedents-planner",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "precedents-planner",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "The planner's evidence carries the verified precedents (bounded, null when missing), its brief asks for proven techniques first, and plan lint requires the reason to begin with Precedent:; tests use stubs only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18g-precedents-planner-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
