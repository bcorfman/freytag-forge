# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19e: apply Opus's design of the fun review's eighth check (replaces the round 19d wording). FREE to build.

Opus drafted the text (opus-fun-design-19e.md, from opus-fun-design-19e-prompt.txt, claude-opus-5-5 high, 2026-11-22).
One Codex task. Usage: build_round19e_opus_design_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-opus-design"
OWNED = [
    "factory/stations/fun_review.py",
    "factory/stations/planner.py",
    "factory/stations/wiring.py",
    "factory/line.py",
    "tests/test_factory_fun_review.py",
    "tests/test_factory_planner.py",
    "tests/test_factory_wiring.py",
    "tests/test_factory_line.py",
    "tests/test_factory_probe_routing.py",
    "tests/test_factory_fun_feedback.py",
    "tests/shard_durations.json",
]
ALLOW_RE = (
    "^(factory/stations/(fun_review|planner|wiring)\\.py|factory/line\\.py|"
    "tests/test_factory_[a-z0-9_]+\\.py|tests/shard_durations\\.json)$"
)

REPLY = (HERE / "opus-fun-design-19e.md").read_text()


def _between(start: str, end: str) -> str:
    i = REPLY.index(start)
    j = REPLY.index(end, i + len(start))
    return REPLY[i:j].strip()


BULLET = _between("- delights_the_player:", "**(b)")
TEMPLATE_RULES = _between("In reasons, when delights_the_player", "Block when any answer is no or missing.")
PLANNER_A = _between("Among the fixes that would have let", 'Replace "Keep reason')
PLANNER_B = _between("After the cause, name in a few words", "Add these after")
PLANNER_C = _between("When a story editor's block is shown", "**(d)")

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run` (it bills a real narrator). FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. HEAD already holds round 19d: the story factory's fun review (`factory/stations/fun_review.py`, station 10) has an eighth check `delights_the_player`, an `improvement` reply field, and `factory/line.py` sends a block back to the planner for up to `MAX_FUN_ROUNDS` rounds with `fun_feedback`; `wiring.py` and `planner.py` carry it (read all four, and `tests/test_factory_fun_feedback.py`). The OWNER REJECTED that wording because I wrote it, not Opus. Opus (claude-opus-5-5) has now DESIGNED the check, the reply field and the planner sentences. THIS ROUND REPLACES the 19d wording and settings with Opus's design, VERBATIM where text is given. Do not paraphrase, improve or shorten Opus's text; only join it into the code's string style (the brief is a tuple of concatenated string literals joined into one string; the planner brief is a triple-quoted string with hard-wrapped lines; line wrapping inside a sentence may differ, but every word, in order, must stay).

OPUS'S EXACT TEXT.
(a) The new bullet, replacing the 19d `delights_the_player` bullet (the key stays `delights_the_player`, last of the checks; "eight" stays in "Answer these eight yes/no questions:"; there is NO blank line between the seventh and eighth bullets):
@BULLET@

(b) The reply template and the instruction lines. The JSON object is exactly: {"verdict": "pass" or "block", "checks": {"fits_scene": true, "gives_a_reason_to_act": true, "keeps_pace": true, "fits_freytag_phase": true, "characters_in_character": true, "continuity_within_scene": true, "continuity_between_scenes": true, "delights_the_player": true}, "reasons": "one to three plain sentences", "fun_advice": "empty on pass; one or two plain sentences on block"}
After the JSON line and before "Block when any answer is no or missing." these lines (each a plain line of the brief):
@TEMPLATE_RULES@
The reply field is therefore named `fun_advice` everywhere (rename `improvement` -> `fun_advice` in the reply parsing, `review.json`, payloads, `line.py`, tests); its cap is 300 characters (was 600). A reply without `fun_advice` stays valid (empty string).

(c) PLANNER BRIEF (`factory/stations/planner.py`). Replace the block that 19d wrote (the lines from "Among the changes that would let the failing turns succeed" through "in your new plan.") with exactly these sentences:
@PLANNER_A@
Replace the existing line "Keep reason at 400 characters or fewer." with:
@PLANNER_B@
Add these sentences right after the existing sentence that begins "When check output is shown" (and its continuation line); if the planner brief has no such sentence, add them right after the sentences about the retry of a plan; read the brief and pick the nearest sensible place, and say which in NOTES_19E.txt:
@PLANNER_C@
Keep every other planner sentence. The "Fun review feedback" label in wiring.py (`FUN_CHECK_LABEL`) must still mention fun_advice: change its text to "Fun review feedback (this plan was applied and the story editor blocked it; its failed checks, reasons and fun_advice follow):".

(d) BEHAVIOUR OPUS ASKED FOR.
1. ROUND LIMIT 2. `MAX_FUN_ROUNDS = 2` in `line.py` (the first block sends the ticket back to station 4; the second block ends the ladder: OPUS_REFRESH + record_failure(max_attempts=1), no merge). Keep a payload list `fun_history` (append one dict per block: the blocked `plan`, `reasons`, `fun_advice` and the failed check keys) that survives to the failure so the owner can read both plans, both reasons and the last advice; never pop `fun_history`.
2. WHAT THE PLANNER GETS BACK. `fun_feedback` becomes a plain multi-line string of three labelled parts: `Failed checks: <the check keys whose answer was not true, comma separated>`, `Reasons: <reasons>`, `fun_advice: <fun_advice>` (omit the last when empty). It never contains the reviewer's brief or the check QUESTIONS, only the key names. The block's `payload_updates["fun_review"]` gains `failed_checks` (list of keys) so the line can build it; `wiring.py` keeps passing `feedback_plan` (the blocked plan) as before.
3. REVISIONS ARE RE-CHECKED. After a send-back the revised plan already passes lint, then station 5/6 and the probe before the fun review again (that is the existing routing); add a test that proves a fun-feedback send-back ends at station 4 with `plan` cleared and that a later pass reaches FUN_REVIEW only through PROBE for a merge ticket (use the existing routing helpers).
4. REVIEWER PACKET. The review prompt must carry, for a plan of kind `edit_claim_evidence`, the claim's existing `action_evidence` groups (read from the loaded package for the ticket scene, bounded at 8 groups and 12 phrases per group, one line of compact JSON under a heading `Claim evidence:`), because without them the no-visible-text clause of the new question cannot be answered. The failing turns' typed commands are already in the packet (`_turn_evidence`, `player_input`); keep that. If the plan is another kind, add nothing. Read the plan from the ticket payload or the saved plan file the way `_plan_reason` does.
5. PASS REASONS ARE LOGGED. A pass already saves `reasons` in `review.json`; also keep them in the ticket payload (`fun_review.reasons` already) and make sure the pass reasons are never trimmed below the existing three-sentence rule. No new feature is needed beyond a test that a pass record carries the reasons and the key list.
Not built this round (note them in NOTES_19E.txt as follow-ups, do not build): recording a passing-after-block fix in the precedents file, and the human escalation message.

TESTS (hermetic; stubs and temp dirs; no process; never edit real story data). Update `tests/test_factory_fun_feedback.py`, `tests/test_factory_fun_review.py`, `tests/test_factory_line.py`, `tests/test_factory_wiring.py` and `tests/test_factory_planner.py` where the renamed field, the limit of two, the feedback format, the new text and the new packet section change expectations; change the expectation, never delete a test for unrelated reasons, never weaken what a test proves. Add tests for: the exact Opus bullet and planner sentences present in the briefs (whitespace-collapsed compare); `fun_advice` capped at 300 characters; `fun_history` after two blocks holds two entries and survives the failure; `fun_feedback` format (failed checks, reasons, advice; no check question text); the reviewer packet carries `Claim evidence:` for an `edit_claim_evidence` plan and not for others. Total new test time under 10 seconds. If you add a test file, add it to `tests/shard_durations.json` with `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. NEVER edit `fix_plan.py`, `probe.py`, `diagnose.py`, `tickets.py`, `factory/config/*`, story data, `bench/` or `storygame/`. Story-agnostic code: no story names, places, characters or facts in `factory/`. Write NOTES_19E.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
for f in factory/stations/fix_plan.py factory/stations/probe.py factory/stations/diagnose.py factory/tickets.py; do
  git diff --cached --name-only | grep -qx "$f" && { echo "$f must not change"; exit 1; } || true
done
others=$(git diff --cached --name-only | grep '^factory/config/' || true)
[ -z "$others" ] || { echo "config files touched: $others"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt|warehouse" factory/stations/fun_review.py factory/line.py; then echo "story-specific word"; exit 1; fi
.venv/bin/python - <<'EOPY'
import json, re, sys
from factory.line import MAX_FUN_ROUNDS
from factory.stations.fun_review import FUN_REVIEW_BRIEF, FUN_REVIEW_CHECKS
from factory.stations.planner import PLANNER_BRIEF
exp = json.load(open("@WORK@/inputs/expected.json"))
norm = lambda t: re.sub(r"\\s+", " ", t).strip()
brief, planner = norm(FUN_REVIEW_BRIEF), norm(PLANNER_BRIEF)
fails = []
if FUN_REVIEW_CHECKS[-1] != "delights_the_player" or len(FUN_REVIEW_CHECKS) != 8:
    fails.append("checks tuple is not eight with delights_the_player last")
if MAX_FUN_ROUNDS != 2:
    fails.append(f"MAX_FUN_ROUNDS is {MAX_FUN_ROUNDS}, Opus said 2")
if "Answer these eight yes/no questions" not in brief:
    fails.append("brief does not say eight questions")
for name, text, where in (("bullet", exp["bullet"], brief), ("template rules", exp["template_rules"], brief),
                          ("planner A", exp["planner_a"], planner), ("planner B", exp["planner_b"], planner),
                          ("planner C", exp["planner_c"], planner)):
    if norm(text) not in where:
        fails.append(f"Opus text missing or altered: {name}")
for needle in ('"fun_advice"', '"delights_the_player": true'):
    if needle not in FUN_REVIEW_BRIEF:
        fails.append(f"reply template lacks {needle}")
if "improvement" in FUN_REVIEW_BRIEF:
    fails.append("old field name improvement still in the brief")
for p in ("Prefer the smallest change that would have", "Among the changes that would let the failing turns succeed, prefer"):
    if p in PLANNER_BRIEF:
        fails.append(f"old planner sentence still present: {p}")
if fails:
    print("\\n".join(fails))
    sys.exit(1)
print("opus text present, eight checks, limit 2")
EOPY
grep -n "improvement" factory/line.py factory/stations/fun_review.py && { echo "old field name improvement still used"; exit 1; } || true
grep -q "fun_history" factory/line.py || { echo "fun_history missing"; exit 1; }
grep -q "Claim evidence:" factory/stations/fun_review.py || { echo "Claim evidence section missing"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fun_review.py tests/test_factory_fun_feedback.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_fix_plan.py tests/test_factory_claim_edit.py tests/test_factory_stations.py tests/test_factory_probe.py tests/test_factory_diagnose.py tests/test_factory_followups.py tests/test_factory_frozen.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_fun_feedback.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fun_feedback.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/opus-design.patch"
test -s "$WORK/out/opus-design.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@BULLET@", BULLET)
            .replace("@TEMPLATE_RULES@", TEMPLATE_RULES)
            .replace("@PLANNER_A@", PLANNER_A)
            .replace("@PLANNER_B@", PLANNER_B)
            .replace("@PLANNER_C@", PLANNER_C)
            .replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    inputs = Path(WORK) / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "expected.json").write_text(
        json.dumps(
            {
                "bullet": BULLET.removeprefix("- "),
                "template_rules": TEMPLATE_RULES,
                "planner_a": PLANNER_A,
                "planner_b": PLANNER_B,
                "planner_c": PLANNER_C,
            },
            indent=2,
        )
    )
    return {
        "run_name": "factory-opus-design",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "opus-design",
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
                "verified": "Opus's own wording of the eighth check, the fun_advice field and the planner sentences is in the code verbatim; two fun rounds, fun_history kept, claim evidence in the reviewer packet.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19e-opus-design-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
