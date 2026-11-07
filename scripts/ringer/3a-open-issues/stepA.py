# ruff: noqa: E501
"""Build the step A manifest for .plans/richer-3a-open-issues-plan.md (zero narrator neurons)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepA"

PREAMBLE = (
    f"Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. "
    "NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network "
    "(use grep/rg and file reads). FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; "
    "then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` "
    "(PYTHONPATH must also include $PWD/packages/worldkeeper/src or worldkeeper imports from the MAIN checkout through the .venv symlink and your model.py edit is silently ignored; confirm `.venv/bin/python -c 'import storygame; print(storygame.__file__)'` prints a path inside this worktree) and "
    "ruff as `.venv/bin/python -m ruff check <files>` / `-m ruff format <files>`. Leave changes uncommitted. "
    "Work TESTS FIRST: write or change the tests, run them and see the new ones fail for the right reason, then fix the code. "
    "You may update existing tests that assert the OLD behaviour this task deliberately changes, and only those; never "
    "weaken, skip or delete any other test. Write plain code and wording; do not invent story wording beyond what is quoted here."
)

CHECK_HEAD = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in
%(allowed)s) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
"""

CHECK_TAIL = r"""PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
mkdir -p %(out)s && git add -A && git diff --cached > %(out)s/%(key)s.patch && wc -l %(out)s/%(key)s.patch && git diff --cached --stat | tail -12
"""


def check(key, allowed, body):
    head = CHECK_HEAD % {"allowed": "\n".join(f"{a}|\\" for a in allowed).rstrip("|\\")}
    return head + body + CHECK_TAIL % {"out": OUT, "key": key}


# ---- T1: 1A frame sentence -------------------------------------------------
T1_SPEC = (
    PREAMBLE
    + """

ROLE: story-package editor plus test updater. You may edit ONLY: data/stories/continuity-initiative/knowledge.yaml, tests/test_1a_back_door_gap.py, tests/test_1a_kitchen_start.py, tests/test_richer_1a_fixes.py, and any other file under tests/ (never tests/fixtures/ historical baselines unless a failing test proves the fixture is generated from the live package) that a failing test shows pins the old sentence. Do NOT edit plot.md or any other story file.

BACKGROUND: The 1A scene frame in knowledge.yaml (`scene_frames`, scene_id 1A, `situation`) says "The lock is splintered out of the wood." The plot (plot.md, scene 1A, back-door bullet) says the splinters around the frame point OUTWARD and "The deadbolt is still thrown." The two disagree, and the narrator copies the frame sentence. 

DO: In knowledge.yaml replace exactly the sentence `The lock is splintered out of the wood.` with `The deadbolt is still thrown.` in that one `situation` string (nothing else in the string changes: Michelle's home ... Kristin did not carve them). Update the tests that pin the old sentence (tests/test_1a_back_door_gap.py SITUATION constant, tests/test_1a_kitchen_start.py required_sentences, and any other test the suite shows) to the new sentence. Add to tests/test_richer_1a_fixes.py one source-consistency test: the 1A frame situation contains `The deadbolt is still thrown.`, does NOT contain `splintered out of the wood`, and the outward-splinters clue (the plot's `splinters around the frame point outward`) is still conveyed by some earned 1A knowledge delivery or placement in the package (find which with grep for `splinter` in knowledge.yaml / handoffs.yaml / world.yaml; assert on that real location; do not add or move any clue). If any test pins a package hash or generated prompt snapshot, regenerate it with the repository's existing generator only if one exists; otherwise update the single pinned value after reading the diff.

TESTS to run: tests/test_1a_*.py tests/test_richer_1a_fixes.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_narration_safety_false_positives.py tests/test_bench_item_facts.py, then `TMPDIR=/tmp .venv/bin/python scripts/quick_suite.py` (if it cannot run in the sandbox say so in the final message and run the files above plus every tests/ file that grep finds mentioning "1A" and "scene_frames").

FINAL MESSAGE: list every file changed, the one-line diff in knowledge.yaml, and which tests you updated and why.
"""
)

T1_CHECK = check(
    "t1-1a-frame",
    [
        "data/stories/continuity-initiative/knowledge.yaml",
        "tests/*",
    ],
    r"""D=data/stories/continuity-initiative
grep -n "splintered out of the wood" $D/knowledge.yaml && { echo "WHY: old frame sentence remains in knowledge.yaml"; exit 1; }
grep -c "The deadbolt is still thrown\." $D/knowledge.yaml | grep -qx 1 || { echo "WHY: exactly one 'The deadbolt is still thrown.' expected in knowledge.yaml"; exit 1; }
test "$(git diff HEAD --numstat -- $D/knowledge.yaml | awk '{print $1+$2}')" = "2" || { echo "WHY: knowledge.yaml change must be exactly the one line replaced"; exit 1; }
git diff HEAD --quiet -- $D/plot.md || { echo "WHY: plot.md edited"; exit 1; }
$PY -m pytest -q -p no:cacheprovider tests/test_1a_back_door_gap.py tests/test_1a_kitchen_start.py tests/test_richer_1a_fixes.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_narration_safety_false_positives.py tests/test_bench_item_facts.py > /tmp/t1.out 2>&1; rc=$?; tail -25 /tmp/t1.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
""",
)

# ---- T2: stale placement text ---------------------------------------------
T2_SPEC = (
    PREAMBLE
    + """

ROLE: world-model fixer. You may edit ONLY: packages/worldkeeper/src/worldkeeper/model.py, packages/worldkeeper/tests/test_world.py (or a new file packages/worldkeeper/tests/test_place_text.py), tests/test_world_placements.py, and any other test file a failing test shows pins the OLD behaviour. Do NOT edit any file under data/stories/ (no world.yaml or plot.md patch is authorized) and do not touch storygame/ unless the diagnosis below proves the bug is in the adapter (then stop and explain in your final message instead of patching).

BACKGROUND: Scene 1C (plot.md ~line 304) places the `captives` group with `character_placements: captives: {parent: processing_line, text: moving through the processing line below}`. Scene 3A (plot.md ~line 720) places the same group with `captives: {parent: detention_level}` and NO text. storygame/runtime/world_model.py `apply_scene_placements` calls `world.place(group_id, placement.parent, text=placement.text)`. In packages/worldkeeper/src/worldkeeper/model.py `World.place` only writes `wk_place_text` when `text is not None` (line ~1055), so the old 1C text survives the move. Recorded 3A prompts for the first command show the captives "moving through the processing line below" while their parent is the detention level. This is a stale-state bug in World.place, because World.place_text/place_label then return the old authored text for the new parent.

DO, in this order:
1. Reproduce at the package level in tests/test_world_placements.py: build real state with the repo's helpers (look at how other tests in that file and tests/test_richer_3a.py bootstrap RuntimeState/facts from load_story_package(Path("data/stories/continuity-initiative"))), call apply_scene_placements for scene 1C, then 2C (if it has captive placements) and then 3A in order, and assert that after 3A the world's place text/label for `captives` is NOT the 1C text ("moving through the processing line below") and that its parent is detention_level. Run it and confirm it FAILS with that text. Also assert that a REVISIT of 1C (apply_scene_placements for 1C again after 3A, if the code allows it) restores 1C's text, and that applying the same scene twice leaves text unchanged (revisit custody must not break).
2. Add a worldkeeper unit test in packages/worldkeeper/tests (use the fixtures and style of test_world.py): placing an entity with text, then placing it again at a new parent with no text, leaves place_text None and place_label the new parent's name; placing again with text sets that text; an item placed with text and moved by a player action (wk_moved path) still behaves as before.
3. Fix `World.place` so a placement without `text` clears any previous authored placement text for that entity (retract/replace the wk_place_text fact), keeping the existing wk_moved retraction and all other behaviour. Look at how `_replace` and fact retraction work in model.py and follow them; make the smallest change. World-model logic lives in worldkeeper; storygame only adapts (AGENTS.md).
4. Run: packages/worldkeeper/tests (all), tests/test_world_placements.py, tests/test_richer_3a.py, tests/test_richer_1c.py, tests/test_richer_2c.py, tests/test_markdown_story_package.py, tests/test_package_audit.py, tests/test_narration_place_names.py, tests/test_prompt_presence.py, tests/test_place_feed*.py and every other test whose name the grep `grep -rl "place_text\\|place_label\\|apply_scene_placements" tests packages` returns. If a legitimately OLD-behaviour test fails (it relied on text surviving a text-less re-place), fix it only if the surviving text was clearly unintended and say so; if it reveals an authored scene that depends on the survival, STOP, revert your model.py change, and explain precisely which scene/entity in your final message.

FINAL MESSAGE: root cause in one paragraph with file:line, the diff summary, every test added or changed, and the exact assertion output of the step-1 failure before the fix.
"""
)

T2_CHECK = check(
    "t2-stale-placement",
    [
        "packages/worldkeeper/src/worldkeeper/model.py",
        "packages/worldkeeper/tests/*",
        "tests/*",
    ],
    r"""git diff HEAD --quiet -- data || { echo "WHY: data/ was edited"; exit 1; }
git diff HEAD --name-only | grep -q '^packages/worldkeeper/src/worldkeeper/model.py$' || { echo "WHY: model.py not changed"; exit 1; }
git diff --name-only; git ls-files --others --exclude-standard | grep -v '^.venv' || true
git diff HEAD --name-only -- tests packages/worldkeeper/tests | grep -q . || git ls-files --others --exclude-standard -- tests packages/worldkeeper/tests | grep -q . || { echo "WHY: no test added or changed"; exit 1; }
grep -rn "moving through the processing line below" tests/test_world_placements.py >/dev/null || { echo "WHY: test_world_placements.py lacks the 1C stale-text assertion"; exit 1; }
$PY -m pytest -q -p no:cacheprovider packages/worldkeeper/tests tests/test_world_placements.py tests/test_richer_3a.py tests/test_richer_1c.py tests/test_richer_2c.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_narration_place_names.py tests/test_prompt_presence.py > /tmp/t2.out 2>&1; rc=$?; tail -30 /tmp/t2.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
""",
)

# ---- T3: judge provenance + rubric ----------------------------------------
T3_SPEC = (
    PREAMBLE
    + """

ROLE: bench judge-input engineer. You may edit ONLY: bench/judge_input.py, bench/core.py (only the turn-record dict near `"authored_handoff_candidate_id"` and the minimal code that feeds it), tests/test_judge_input.py, bench/continuity-judge.mjs, bench/continuity-judge.test.mjs, and a new fixture file tests/fixtures/judge_provenance_cases.json if you want one. If the authored segments truly cannot reach bench/core.py without a runtime change in storygame/runtime/, STOP and describe exactly which function and field in your final message instead of editing storygame/. Do not change any prompt sent to the narrator.

BACKGROUND (verified): bench/judge_input.py `_story_text` rebuilds what the judge treats as "story" (authored, canon, always true) text from only two sources: the base `delivery_text` of `turn["authored_handoff_candidate_id"]` and one transition bridge. It does not know the cue text, the delivery VARIANT actually used, a complication text, or the destination entry text. So authored text the engine appended (for example the 1A pocketing line in the memory-card delivery, or a scene-entry text) can be judged as the narrator's own action, and narrator text that repeats a prior-turn authored signal cannot be told apart from the story's own segment. The judge distinguishes game/narrator/story passages (see bench/continuity-judge.mjs, `SYSTEM_MESSAGE`, and `judge_turns`/`turn_text` in judge_input.py). `_narrator_narration` removes authored text from the narration by matching strings at the end of the narration.

DO, TESTS FIRST in tests/test_judge_input.py (and bench/continuity-judge.test.mjs for the rubric):
1. Record ordered authored segments at the time the turn is recorded. In bench/core.py add to the turn record an `authored_segments` list of {"kind": ..., "text": ...} in the order the player reads them, built from what actually happened this turn (the handoff delivery text the provider actually appended, including a variant if the provider recorded one; the cue text shown; a complication text; entry/bridge text), using only data already available at that point (look at how `narration`, `cue_text`, `complication_text`, `provider.authored_handoff`, `delivery`, and the segment tuple at bench/core.py ~1060-1075 are produced). Read bench/core.py ~1040-1260 and storygame/runtime/engine.py `_finish_turn`-style code (lines ~360-460, where canonical/entry/resolution segments are appended) first. Do not search prose to decide what was authored.
2. `judge_turns` uses `authored_segments` when a turn record has it. For legacy records without it, keep the current reconstruction, and add a field `story_text_provenance` = "recorded" or "reconstructed" on each judged turn so it is visible; do not subtract today's strings from older narration. A narrator passage that repeats an authored segment word for word (a real repeat from a prior turn) must stay narrator text; only the segment the engine really appended this turn is story text.
3. Calibration cases as tests (build turn dicts by hand; no model calls): (a) authored 1A pocketing line ("It is Michelle's memory card, and she pockets it.") is in story_text, not narrator_narration, so no protagonist fault can be pinned on it; (b) narrator repeating a prior-turn signal sentence stays in narrator_narration while the true authored delivery segment this turn is story; (c) ordinary approach/spotting narration, no authored segments: narrator_narration unchanged; (d) a second emotional reunion paragraph by the narrator after a completed reunion stays narrator text; (e) a new incorrect shared memory stays narrator text; (f) authored arrival / final custody text appended from a bridge or entry stays story text. Cases (a),(b),(f) must fail before your change and pass after, or you must say precisely why one already passes.
4. Rubric clarification in bench/continuity-judge.mjs: in the existing `restarts_scene` sentences of SYSTEM_MESSAGE (the sentence that begins "Continuing to act inside the location is not a restart.") append exactly these two sentences right after it: "Seeing or approaching someone who is already nearby is not a restart. Repeating a completed reunion as a new meeting is a restart." Change nothing else in SYSTEM_MESSAGE or the physical-action question. Extend bench/continuity-judge.test.mjs to assert the system message contains both sentences once and still contains the unchanged `protagonist_acts_beyond_command` text. Mark this change in a code comment as unproven until held-out calibration.

TESTS to run: `PYTHONPATH=$PWD TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_judge_input.py tests/test_bench_item_facts.py` plus every other tests/ file that `grep -rl "judge_turns\\|judge_input\\|authored_handoff_candidate_id" tests bench` returns, and `node --test bench/continuity-judge.test.mjs`.

FINAL MESSAGE: the record schema you chose, where each segment kind comes from, the diff summary, and which of cases (a)-(f) failed before the change.
"""
)

T3_CHECK = check(
    "t3-judge-provenance",
    [
        "bench/judge_input.py",
        "bench/core.py",
        "bench/continuity-judge.mjs",
        "bench/continuity-judge.test.mjs",
        "tests/*",
    ],
    r"""git diff HEAD --name-only | grep -q '^bench/judge_input.py$' || { echo "WHY: judge_input.py not changed"; exit 1; }
git diff HEAD --name-only | grep -q '^bench/core.py$' || { echo "WHY: bench/core.py does not record authored_segments"; exit 1; }
grep -q "authored_segments" bench/core.py bench/judge_input.py || { echo "WHY: authored_segments missing"; exit 1; }
grep -c "Seeing or approaching someone who is already nearby is not a restart. Repeating a completed reunion as a new meeting is a restart." bench/continuity-judge.mjs | grep -qx 1 || { echo "WHY: rubric sentences must appear exactly once in continuity-judge.mjs"; exit 1; }
git diff HEAD -U0 bench/continuity-judge.mjs | grep '^[-+]' | grep -v '^+++\|^---' | wc -l | awk '{exit !($1<=8)}' || { echo "WHY: too many changed lines in continuity-judge.mjs"; exit 1; }
LS=$(grep -rl --include="test_*.py" "judge_turns\|judge_input\|authored_handoff_candidate_id" tests | sort | tr '\n' ' ')
$PY -m pytest -q -p no:cacheprovider tests/test_judge_input.py tests/test_bench_item_facts.py $LS > /tmp/t3.out 2>&1; rc=$?; tail -30 /tmp/t3.out; [ $rc -eq 0 ] || { echo "WHY: python suites failed"; exit 1; }
node --test bench/continuity-judge.test.mjs 2>&1 | tail -15; node --test bench/continuity-judge.test.mjs >/dev/null 2>&1 || { echo "WHY: node judge tests failed"; exit 1; }
""",
)


def task(key, spec, chk, ownership, effort="medium"):
    return {
        "key": key,
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", f"model_reasoning_effort={effort}"],
        "max_attempts": 2,
        "timeout_s": 3000,
        "check_timeout_s": 900,
        "ownership": ownership,
        "spec": spec,
        "check": chk,
        "expect_files": [],
        "verified": "tests added first, change in place, suites and ruff pass, patch exported",
    }


manifest = {
    "run_name": "3a-open-issues-stepA",
    "workdir": OUT,
    "max_parallel": 3,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        task("t1-1a-frame", T1_SPEC, T1_CHECK, ["data/stories/continuity-initiative/knowledge.yaml", "tests/"]),
        task(
            "t2-stale-placement",
            T2_SPEC,
            T2_CHECK,
            [
                "packages/worldkeeper/src/worldkeeper/model.py",
                "packages/worldkeeper/tests/",
                "tests/test_world_placements.py",
            ],
            "high",
        ),
        task(
            "t3-judge-provenance",
            T3_SPEC,
            T3_CHECK,
            [
                "bench/judge_input.py",
                "bench/core.py",
                "bench/continuity-judge.mjs",
                "bench/continuity-judge.test.mjs",
                "tests/test_judge_input.py",
            ],
            "high",
        ),
    ],
}

Path(__file__).with_name("stepA-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote manifest")
