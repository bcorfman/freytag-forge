# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19i: apply the real findings of Opus's check of its lessons code (opus-fun-check-19i.md). FREE to build.

One Codex task. Usage: build_round19i_lessons_fixes_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-lessons-fixes"
OWNED = [
    "factory/lessons.py",
    "factory/stations/fix_plan.py",
    "tests/test_factory_lessons.py",
    "tests/test_factory_fix_plan.py",
]
ALLOW_RE = "^(factory/lessons\\.py|factory/stations/fix_plan\\.py|tests/test_factory_(lessons|fix_plan)\\.py)$"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/lessons.py` records what a fun-review block taught and renders proven lessons into the planner's evidence (`build_evidence` in `factory/stations/fix_plan.py`). Opus designed it and then reviewed the applied code (`scripts/ringer/1a-stuck/opus-fun-check-19i.md`). Apply exactly these four real findings and change NOTHING else (do not touch `line.py`, the planner brief, the record fields, thresholds, rendered line templates, the cap or the sort order):

A. PRECEDENT TEXT (Opus finding 2). `_precedent(plan)` stores everything up to the first period of the text after "Precedent: ". The planner is told to write "Precedent: none; list checks and the reason it does not apply", so reason prose leaks into the record and splits the common `none` key. New rule: take the text after "Precedent: "; if it starts with "none" (case-insensitive) store exactly `none`; otherwise cut at the first `.`, `;` or newline, strip, cap at 80 characters, and store `none` if empty.

B. NO "unknown" LESSONS (Opus finding 6). When a plan's kind is missing or not a string, the record would use fix_kind `unknown`, and unrelated plans from different tickets would merge under one key. Do not write a record whose `fix_kind` would be `unknown` (blocked or won), and `render_lessons` must also skip any stored record whose `fix_kind` is `unknown`.

C. BAD RECORDS MUST NOT BREAK THE PLANNER (Opus finding 4). `_read_records` only checks that the field names exist. Also require: `lesson_id`, `ticket_id`, `scene_id`, `outcome`, `fix_kind`, `precedent`, `recorded_at` are strings; `outcome` is `blocked` or `won_after_block`; `failed_checks` is a list of strings; `fun_round` is an int that is not a bool. A line that fails any of these is skipped. In `fix_plan.build_evidence` wrap the `render_lessons(...)` call so that ANY exception gives `fun_lessons = None` instead of failing the station.

D. ONE PATH FUNCTION (Opus finding 10). The writer (`lessons._store_path`) and the reader (`fix_plan.build_evidence`) each work out the lessons file path on their own. Add one public function in `factory/lessons.py`, `lessons_path(payload: Mapping) -> Path | None`, holding the whole rule that exists today (payload key `fun_lessons_path`, absolute or repository-relative, default `factory/state/fun_lessons.jsonl` under the repository root; a value that is neither a string nor a Path gives None), and make both the writer and `build_evidence` call it. Behaviour must not change.

TESTS (hermetic; temp files only; never write the real `factory/state/` directory). Add to `tests/test_factory_lessons.py` (and `tests/test_factory_fix_plan.py` for the evidence guard): "Precedent: none; list checks and the reason..." stores `none`; "Precedent: Foo bar. More text" stores `Foo bar`; a newline and a semicolon cut; a plan with no kind writes no record and a stored `unknown` record is not rendered; a file with garbage lines (wrong types, a list for `ticket_id`, non-JSON) renders only the good lines and does not raise; `build_evidence` returns `fun_lessons` None when `render_lessons` raises (monkeypatch); `lessons_path` honours the payload key and the default. Update existing tests only where behaviour legitimately changed; never delete or weaken one. New test time under 5 seconds.

HARD LIMITS. Edit only: @OWNED@. NEVER edit `line.py`, `planner.py`, `tickets.py`, `fun_review.py`, `wiring.py`, `factory/config/*`, `factory/precedents/*`, story data, `bench/` or `storygame/`. Story-agnostic code. Write NOTES_19I.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git diff --cached --name-only | grep -q '^factory/state/' && { echo "factory/state must not be staged"; exit 1; } || true
.venv/bin/python - <<'EOPY'
import json, sys, tempfile
from pathlib import Path
import factory.lessons as L
fails = []
class T:
    id = "t"; scene = "s"
    def __init__(self, plan, hist=None): self.payload = {"plan": plan, "fun_history": hist or [{"plan": plan, "failed_checks": ["x"]}]}
if L._precedent({"reason": "Precedent: none; list checks and the reason it does not apply."}) != "none":
    fails.append("Precedent: none; ... must store exactly none")
if L._precedent({"reason": "Precedent: Foo bar. More text"}) != "Foo bar":
    fails.append("first period cut broken")
if L._precedent({"reason": "Precedent: Foo bar; more"}) != "Foo bar":
    fails.append("semicolon cut broken")
if not callable(getattr(L, "lessons_path", None)):
    fails.append("lessons_path missing")
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "l.jsonl"
    good = {"lesson_id": "a:1:blocked", "ticket_id": "a", "scene_id": "S1", "outcome": "blocked", "fix_kind": "k", "precedent": "p", "failed_checks": ["c"], "fun_round": 1, "recorded_at": "2026-01-01T00:00:00+00:00"}
    good2 = dict(good, lesson_id="b:1:blocked", ticket_id="b", scene_id="S2")
    bad = dict(good, ticket_id=["x"])
    p.write_text("\\n".join([json.dumps(good), json.dumps(good2), json.dumps(bad), "not json"]) + "\\n")
    try:
        out = L.render_lessons(p)
    except Exception as error:
        fails.append(f"render_lessons raised on garbage lines: {error!r}")
    else:
        if "Avoid:" not in out:
            fails.append("good records no longer render")
if fails:
    print("\\n".join(fails))
    sys.exit(1)
print("lessons fixes present")
EOPY
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_lessons.py tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_line.py tests/test_factory_fun_feedback.py tests/test_factory_probe_routing.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 100 s)"
[ "$took" -le 100 ] || { echo "over the 100 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_lessons.py
.venv/bin/python -m ruff format --check factory tests/test_factory_lessons.py
[ ! -e factory/state/fun_lessons.jsonl ] || { echo "a test wrote factory/state/fun_lessons.jsonl"; exit 1; }
git diff --cached > "$WORK/out/lessons-fixes.patch"
test -s "$WORK/out/lessons-fixes.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    return {
        "run_name": "factory-lessons-fixes",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "lessons-fixes",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Lessons store only a clean precedent label and never an unknown fix kind; one bad stored line cannot break the planner's evidence; writer and reader share one path function.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19i-lessons-fixes-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
