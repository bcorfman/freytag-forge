# ruff: noqa: E501
"""Step C manifest: one-sentence change to the A-r1 delivery, with tests (zero narrator neurons)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepC"
NEW = (
    "Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. "
    "For one unhurried moment the two of them talk to each other and nobody asks anything of either. "
    "Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait."
)

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` (use grep/rg and file reads). FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see the new-wording test fail, then make the edit.

ROLE: story-package editor plus test writer. You may edit ONLY: data/stories/continuity-initiative/knowledge.yaml (ONE line), tests/test_richer_3a.py, and any other test under tests/ that a failing test shows pins the OLD first sentence (known: tests/test_1c_closeout.py near line 110 pins the old delivery; update only that pin). Do not touch handoffs.yaml, plot.md, storylets.md, storylet-routes.yaml, world.yaml, or any Python outside tests/.

THE CHANGE (wording supplied; do not invent replacements): in knowledge.yaml, entry `k_sl_3a_a_r1`, the `delivery_text` currently begins `Kristin finds Michelle alive, speaking into a stolen radio beside the captives.` Replace ONLY that first sentence with `Kristin joins Michelle beside the captives.` The full resulting delivery_text must be exactly:
{NEW}
Keep the YAML quoting style of that line. Do NOT change that entry's `statement`, `earn_when`, `action_evidence`, `requires`, `establishes` or anything else, and do NOT change `k_sl_3a_a_r2` or handoffs.yaml's `michelle_reached` entry (its cue_text and fallback_text stay as they are).

TESTS (first, in tests/test_richer_3a.py, plain names):
1. `k_sl_3a_a_r1.delivery_text` equals the exact text above; it does not contain `finds Michelle alive`; it still contains `the dose they were given is for the trip` and `points toward the medical level`.
2. A-r1 and A-r2 still establish the same facts: literal expectations read from the file before editing (for k_sl_3a_a_r1 and k_sl_3a_a_r2: requires, establishes), and `k_sl_3a_a_r2.delivery_text` is unchanged (assert it against the literal current value).
3. No fact is earned by the opening cue display: with only the scene entry fact asserted (use `_engine()`), `michelle_reached` and `uprising_prepared` are not true after the opening is produced/projected; they become true only via the action (`Free the captives.` -> k_sl_3a_a_r1, see the existing test near line 422 of tests/test_richer_3a.py for how a command reaches the handoff).
4. Single composed turn does not repeat the quiet moment: for each of the three paths (A-r1 via `Free the captives.`; A-r2 via a command like `Ask Michelle about other sites.` if the existing tests use one, otherwise the command in that entry's action_evidence; and the fallback_text path of `michelle_reached` if the existing tests can force it), compose the turn offline the way existing tests do and assert the phrase `unhurried moment` appears at most once in the turn text. If one of the paths cannot be composed offline with existing helpers, say so in your final message instead of inventing a harness.
5. Consumed discovery cues do not recur after save/load/revisit: follow the existing cue-lifecycle tests in tests/test_discovery_continuity.py (read them first); add ONE test in tests/test_richer_3a.py that, after `michelle_reached` is established via A-r1 and the state is saved and reloaded the way those tests do, the opening cue `Michelle speaks into a stolen radio beside the captives.` is not offered again. If the existing helpers cannot express this, say so rather than adding runtime flags.
6. grep tests/ for `Kristin finds Michelle alive, speaking` and update only those pins to the new sentence.

Then run: tests/test_richer_3a.py tests/test_1c_closeout.py tests/test_discovery_continuity.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py, and every test file whose grep matched.

FINAL MESSAGE: the one-line diff, every test changed or added, and any of items 4/5 you could not express with existing helpers.
"""

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in $D/knowledge.yaml|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
test "$(git diff HEAD --numstat -- $D/knowledge.yaml | awk '{print $1+$2}')" = "2" || { echo "WHY: knowledge.yaml must change exactly one line"; exit 1; }
grep -c "delivery_text: \"Kristin joins Michelle beside the captives\. They are awake: the dose they were given is for the trip, and it wears off in the detention block\. For one unhurried moment the two of them talk to each other and nobody asks anything of either\. Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait\.\"$" $D/knowledge.yaml | grep -qx 1 || { echo "WHY: new A-r1 delivery_text not exactly as specified"; exit 1; }
grep -n "Kristin finds Michelle alive, speaking into a stolen radio" $D/knowledge.yaml tests/*.py && { echo "WHY: old first sentence remains"; exit 1; }
git diff HEAD --quiet -- $D/handoffs.yaml $D/plot.md || { echo "WHY: handoffs.yaml or plot.md edited"; exit 1; }
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_1c_closeout.py tests/test_discovery_continuity.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py > /tmp/tc.out 2>&1; rc=$?; tail -25 /tmp/tc.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
git add -A && git diff --cached > OUTDIR/stepC.patch && wc -l OUTDIR/stepC.patch && git diff --cached --stat | tail -8
""".replace("OUTDIR", OUT)

manifest = {
    "run_name": "3a-open-issues-stepC",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "ar1-delivery",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/knowledge.yaml",
                "tests/test_richer_3a.py",
                "tests/test_1c_closeout.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "one delivery sentence changed, pins and lifecycle tests pass, patch exported",
        }
    ],
}
Path(__file__).with_name("stepC-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
