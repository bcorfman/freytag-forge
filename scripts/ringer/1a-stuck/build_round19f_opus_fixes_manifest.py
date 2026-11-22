# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19f: apply the four real findings of Opus's check of its own 19e design (opus-fun-check-19f.md). FREE to build.

One Codex task. Usage: build_round19f_opus_fixes_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-opus-fixes"
OWNED = [
    "factory/stations/fun_review.py",
    "factory/line.py",
    "tests/test_factory_fun_review.py",
    "tests/test_factory_line.py",
    "tests/test_factory_probe_routing.py",
    "tests/test_factory_fun_feedback.py",
]
ALLOW_RE = "^(factory/stations/fun_review\\.py|factory/line\\.py|tests/test_factory_[a-z0-9_]+\\.py)$"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The factory's fun review (`factory/stations/fun_review.py`, station 10) and its send-back loop (`factory/line.py`, `MAX_FUN_ROUNDS`, `fun_history`, `fun_feedback`) were designed by Opus (read `scripts/ringer/1a-stuck/opus-fun-design-19e.md`) and applied. Opus then reviewed the applied code (`scripts/ringer/1a-stuck/opus-fun-check-19f.md`). Four of its findings are real; apply EXACTLY these four and change NOTHING else. Do NOT reword the review brief's questions, the reply template, the rule lines or the planner brief; the only brief change allowed is moving one blank line (finding D). Do not touch `planner.py` or `wiring.py`.

A. DUPLICATE HISTORY (Opus finding 1). When the second fun block ends the ladder, the ticket is set aside and may later return; the review reuses the saved block, so the line would fail again and append another `fun_history` entry. Fix in `line.py`: on a final block set `payload["fun_rounds"] = next_fun_round` (so the count is stored), and append to `fun_history` only if the last entry is not already equal to the new entry (same plan, reasons, fun_advice and failed checks). Never pop `fun_history`.

B. PROBE REJECT KEEPS THE FUN ADVICE (Opus finding 2). In the probe-reject branch of `line.py`, which pops `fun_feedback` and sets `probe_feedback`: when `payload["fun_history"]` is a non-empty list, append to the `probe_feedback` string a blank line then `Earlier fun review advice (still applies):` then the `Reasons:` and `fun_advice:` lines of the LAST `fun_history` entry (omit the advice line when empty; never include check questions, only what `fun_history` holds). When `fun_history` is empty or missing, `probe_feedback` is exactly what it is today.

D. BLANK LINE (Opus finding 4). In `fun_review.py` the `continuity_between_scenes` bullet now ends with `?\\n` and the new `delights_the_player` bullet ends with `\\n`; the blank line before "Reply with ONE JSON object and nothing else:" got lost. Put it back: the `delights_the_player` bullet's last literal ends `\\n\\n`, the `continuity_between_scenes` bullet stays at `\\n`. Whitespace only; every word of the brief unchanged.

E. EMPTY FAILED-CHECKS LINE (Opus finding 6). Where the feedback string's `Failed checks:` line is built (read `line.py`), when the failed-check list is empty (every check true but the verdict was block), write exactly `Failed checks: none (blocked by the rule against only moving words)`. Otherwise unchanged.

TESTS (hermetic, stubs only). Add to `tests/test_factory_fun_feedback.py` (and adjust existing assertions only where a legitimate behaviour change requires it): a second block stores `fun_rounds` 2 and one history entry per distinct block, and a repeat of the same final block adds no duplicate; a probe reject after a fun round carries the last fun reasons and advice in `probe_feedback`, and a probe reject with no fun history is unchanged; the empty-failed-checks line; the blank line before "Reply with ONE JSON object" exists in `FUN_REVIEW_BRIEF` and no words changed (compare the whitespace-collapsed brief with the previous one captured as a literal in the test only if that is simple; otherwise assert the `\\n\\nReply with ONE JSON object` substring). New test time under 5 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. NEVER edit `fix_plan.py`, `probe.py`, `diagnose.py`, `tickets.py`, `planner.py`, `wiring.py`, `factory/config/*`, story data, `bench/` or `storygame/`. Story-agnostic code. Write NOTES_19F.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git diff --cached --name-only | grep -qx "factory/stations/planner.py" && { echo "planner.py must not change"; exit 1; } || true
git diff --cached --name-only | grep -qx "factory/stations/wiring.py" && { echo "wiring.py must not change"; exit 1; } || true
.venv/bin/python - <<'EOPY'
import re, subprocess, sys
from factory.stations.fun_review import FUN_REVIEW_BRIEF
old = subprocess.run(["git", "show", "HEAD:factory/stations/fun_review.py"], capture_output=True, text=True, check=True).stdout
ns = {}
m = re.search(r"FUN_REVIEW_BRIEF = \\((.*?)\\n\\)\\n", old, re.S)
old_brief = eval("(" + m.group(1) + ")")
norm = lambda t: re.sub(r"\\s+", " ", t).strip()
fails = []
if norm(old_brief) != norm(FUN_REVIEW_BRIEF):
    fails.append("the brief's words changed; only a blank line may move")
if "\\n\\nReply with ONE JSON object" not in FUN_REVIEW_BRIEF:
    fails.append("blank line before the reply instructions is missing")
if "\\n\\n- delights_the_player" in FUN_REVIEW_BRIEF:
    fails.append("blank line wrongly between the seventh and eighth bullets")
if fails:
    print("\\n".join(fails))
    sys.exit(1)
print("brief words unchanged, blank line restored")
EOPY
grep -q "none (blocked by the rule against only moving words)" factory/line.py || { echo "empty failed-checks line missing"; exit 1; }
grep -q "Earlier fun review advice (still applies):" factory/line.py || { echo "probe reject does not carry fun advice"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fun_review.py tests/test_factory_fun_feedback.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_fix_plan.py tests/test_factory_claim_edit.py tests/test_factory_stations.py tests/test_factory_probe.py tests/test_factory_diagnose.py tests/test_factory_followups.py tests/test_factory_frozen.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_fun_feedback.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fun_feedback.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/opus-fixes.patch"
test -s "$WORK/out/opus-fixes.patch"
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
        "run_name": "factory-opus-fixes",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "opus-fixes",
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
                "verified": "The four real findings of Opus's check are fixed: no duplicate fun history, probe rejects keep the fun advice, the brief's blank line is back with no word changed, and an empty failed-checks list is explained.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19f-opus-fixes-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
