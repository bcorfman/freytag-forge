# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19g: record what a fun block taught (Opus's follow-up 1 design). FREE to build.

Opus designed this (opus-fun-followups-19g.md, from opus-fun-followups-19g-prompt.txt, claude-opus-5-5 high, 2026-11-22).
One Codex task. Usage: build_round19g_lessons_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-lessons"
OWNED = [
    "factory/lessons.py",
    "factory/line.py",
    "factory/stations/fix_plan.py",
    "factory/stations/planner.py",
    "tests/test_factory_lessons.py",
    "tests/test_factory_line.py",
    "tests/test_factory_fix_plan.py",
    "tests/test_factory_planner.py",
    "tests/test_factory_fun_feedback.py",
    "tests/shard_durations.json",
]
ALLOW_RE = (
    "^(factory/lessons\\.py|factory/line\\.py|factory/stations/(fix_plan|planner)\\.py|"
    "tests/test_factory_[a-z0-9_]+\\.py|tests/shard_durations\\.json)$"
)

REPLY = (HERE / "opus-fun-followups-19g.md").read_text()
DESIGN = REPLY[REPLY.index("### Follow-up 1") : REPLY.index("### Follow-up 2")].strip()
SENTENCE = (
    "Fun review lessons describe patterns, not fixes; never repeat an Avoid pattern for a scene unless your reason "
    "names the lesson and why this scene differs."
)
HEADER = "FUN REVIEW LESSONS (machine-recorded, proven across ≥2 scenes)"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The factory's fun review (station 10) blocks a repair that is not fun and returns advice; a block sends the ticket back to the planner (`factory/line.py`, `MAX_FUN_ROUNDS = 2`, payload `fun_history` = list of {plan, reasons, fun_advice, failed_checks}). Opus (claude-opus-5-5) designed a way for the factory to LEARN from those blocks. Its design is below; implement it exactly, VERBATIM where it gives text or numbers. Read `factory/line.py` (where a LIVE_PLAYTEST pass for a merge ticket calls `record_pass`; where the second fun block calls `record_failure`; where a failing LIVE_PLAYTEST goes to TRIAGE), `factory/stations/fix_plan.py` (`build_evidence`, `_precedents_text`, `_bound_evidence`), `factory/stations/planner.py` (`PLANNER_BRIEF`) and the existing tests for the style. Opus could not read the code, so where its design assumes a payload key name (it says so: `plan["kind"]`, the plan's `reason`, scene id), use the keys the code really uses and write what you chose in NOTES_19G.txt.

CALL POINTS (the design says "from record_pass and record_failure"; do it in `factory/line.py`, NOT in `factory/tickets.py`, which you must not edit): call `record_lessons(ticket, outcome)` (a) when a LIVE_PLAYTEST pass for a merge ticket records the delivery, with outcome "delivered"; (b) when the second fun block ends the ladder (the branch that sets OPUS_REFRESH and calls `record_failure`), with outcome "fun_exhausted"; (c) when a failing LIVE_PLAYTEST sends a ticket that has a non-empty `fun_history` to TRIAGE (the ticket leaves the fun path), with outcome "fun_exhausted" semantics = blocked records only (a fun pass whose live playtest fails writes blocked records only). A writer exception must never stop the line: catch it, ignore it, continue. The writer never runs when `fun_history` is empty or missing.

PLANNER EVIDENCE. `build_evidence` gets a new key `fun_lessons`: the string from `render_lessons(path, cap=4000)` or null when there is nothing to show; the default path is `factory/state/fun_lessons.jsonl` under the repository root and a ticket payload key `fun_lessons_path` may override it (tests use a temp file). It is separate from the `precedents` key and not part of the curated 20,000-character cap; keep `_bound_evidence` working (the lessons text is at most 4,000 characters; count it so the existing size bound tests still pass or exclude it the same way `precedents` is excluded; say which in NOTES). `PLANNER_BRIEF` gets exactly this one new sentence on its own line, placed right after the existing sentences about precedents: @SENTENCE@

OPUS'S DESIGN (follow-up 1):
@DESIGN@

TESTS (hermetic; temp files only; never write the real `factory/state/` directory). New `tests/test_factory_lessons.py` (under 10 seconds) covering Opus's item 11 list exactly, plus: the three call points in the line, a writer exception does not stop the line, `build_evidence` carries `fun_lessons` and honours `fun_lessons_path`, the planner brief has the sentence. Update existing tests only where a legitimate behaviour change requires it (the evidence packet gains a key); never delete or weaken a test. Add the new test file to `tests/shard_durations.json` with `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. NEVER edit `tickets.py`, `breakers.py`, `__main__.py`, `wiring.py`, `fun_review.py`, `probe.py`, `diagnose.py`, `factory/config/*`, `factory/precedents/*`, story data, `bench/` or `storygame/`. Story-agnostic code (no story names, places, characters or facts in `factory/`). Write NOTES_19G.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f factory/lessons.py || { echo "factory/lessons.py missing"; exit 1; }
test -f tests/test_factory_lessons.py || { echo "tests/test_factory_lessons.py missing"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
for f in factory/tickets.py factory/stations/fun_review.py factory/stations/wiring.py factory/precedents/stuck_turns.md; do
  git diff --cached --name-only | grep -qx "$f" && { echo "$f must not change"; exit 1; } || true
done
git diff --cached --name-only | grep -q '^factory/state/' && { echo "factory/state must not be staged"; exit 1; } || true
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt|warehouse" factory/lessons.py factory/line.py; then echo "story-specific word"; exit 1; fi
.venv/bin/python - <<'EOPY'
import re, sys
from factory.stations.planner import PLANNER_BRIEF
import factory.lessons as lessons
norm = lambda t: re.sub(r"\\s+", " ", t).strip()
fails = []
if norm("@SENTENCE@") not in norm(PLANNER_BRIEF):
    fails.append("the planner lessons sentence is missing or altered")
src = open("factory/lessons.py", encoding="utf-8").read()
for needle in ("@HEADER@", "tends to fail", "passed fun review and live playtest", "wins,", "more lessons not shown"):
    if needle not in src:
        fails.append(f"factory/lessons.py lacks Opus text: {needle}")
if not hasattr(lessons, "record_lessons") or not hasattr(lessons, "render_lessons"):
    fails.append("record_lessons / render_lessons missing")
if fails:
    print("\\n".join(fails))
    sys.exit(1)
print("lessons module and planner sentence present")
EOPY
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_lessons.py
took=$(( $(date +%s) - start ))
echo "lessons tests took $took s (budget 10 s)"
[ "$took" -le 10 ] || { echo "over the 10 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fun_review.py tests/test_factory_fun_feedback.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_fix_plan.py tests/test_factory_claim_edit.py tests/test_factory_stations.py tests/test_factory_probe.py tests/test_factory_diagnose.py tests/test_factory_followups.py tests/test_factory_frozen.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_lessons.py
.venv/bin/python -m ruff format --check factory tests/test_factory_lessons.py
[ ! -e factory/state/fun_lessons.jsonl ] || { echo "a test wrote factory/state/fun_lessons.jsonl"; exit 1; }
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/lessons.patch"
test -s "$WORK/out/lessons.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@DESIGN@", DESIGN)
            .replace("@SENTENCE@", SENTENCE)
            .replace("@HEADER@", HEADER)
            .replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    return {
        "run_name": "factory-lessons",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "lessons",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "The factory records what each fun block taught in an untracked jsonl file (blocks at ticket end, wins only after the live playtest passes), and the planner sees proven lessons (2+ tickets in 2+ scenes) in a separate 4,000-character evidence section.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19g-lessons-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
