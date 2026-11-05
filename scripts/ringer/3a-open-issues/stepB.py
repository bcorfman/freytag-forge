# ruff: noqa: E501
"""Step B manifest: the three R wording edits with tests (zero narrator neurons)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepB"

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network (use grep/rg and file reads). FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout through the .venv symlink). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the three story edits.

ROLE: story-package editor plus test writer. You may edit ONLY: data/stories/continuity-initiative/knowledge.yaml, data/stories/continuity-initiative/plot.md, tests/test_richer_3a.py, and any other test under tests/ that a failing test shows pins one of the three OLD strings below (update only that pin). Do not touch handoffs.yaml, storylets.md, storylet-routes.yaml, world.yaml or any Python outside tests/.

THE CHANGE (exactly three lines, wording supplied; do not invent replacements):
1. data/stories/continuity-initiative/knowledge.yaml, `scene_frames` entry for scene_id 3A: change `pressure: Reach Michelle and join the uprising` to `pressure: Join the uprising`. Leave that entry's `situation` (which ends `Michelle is beside the captives.`) byte-identical.
2. knowledge.yaml, entry `k_scene_3a_entry`: change `statement: Reaching Michelle and supporting the uprising are immediate priorities.` to `statement: Supporting the uprising is the immediate priority.` Change nothing else in that entry (entity_ids, aliases, audience, available_in_scenes, establishes, source stay identical).
3. data/stories/continuity-initiative/plot.md, the 3A scene metadata block (scene_id: 3A, the line `objective: Reach Michelle`): change it to `objective: Join the uprising`. Do not change the section heading or any prose.

TESTS (write first, in tests/test_richer_3a.py, plain names, no new test file):
- The 3A frame pressure equals `Join the uprising`; the 3A frame situation still ends with `Michelle is beside the captives.`; the `k_scene_3a_entry` statement equals the new sentence; the 3A scene's `objective` equals `Join the uprising` (read it from the loaded package scene metadata, see `_scene()` in that file).
- The opening cue stays unchanged: the delivery for fact `michelle_reached` has `cue_text` exactly `Michelle speaks into a stolen radio beside the captives.` and its fallback_text and must_convey groups are unchanged (assert against the literal current values you read from handoffs.yaml before editing).
- The reveal IDs and prerequisites are unchanged: the set of `k_sl_3a_*` ids, and for each of k_sl_3a_a_r1, k_sl_3a_a_r2, k_sl_3a_c_r1, k_sl_3a_c_r2 the `requires` and `establishes` equal the literal values you read before editing. Use compact literal expectations.
- No fact is auto-completed by the edit: with only the scene-entry fact asserted (use `_engine()`), `michelle_reached`, `uprising_prepared` and `detention_uprising_started` are not true.
- The 3A opening prompt keeps the same CHARACTERS names after the edit: before editing, capture the character names present in the recorded 3A opening prompt (find how tests/test_richer_3a.py or tests/test_speaker_presence.py / tests/test_prompt_presence.py build a 3A opening or entry prompt offline; use the same helper, no model call) and assert the set equals the literal set you captured. Also write the prompt SCENE and CONSTRAINTS lines mentioning `Michelle` or `uprising` for the opening to {OUT}/opening-scene-after.txt (create the directory) so the orchestrator can diff against the pre-edit text; write the pre-edit version to {OUT}/opening-scene-before.txt BEFORE you edit the three lines.
- If an existing test pins one of the three old strings (grep the tests/ directory for `Reaching Michelle and supporting`, `Reach Michelle and join`, `objective: Reach Michelle`, `Reach Michelle`), update only that pin to the new text.

Then run: tests/test_richer_3a.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py, and every test file whose grep for the three old strings matched.

FINAL MESSAGE: the three diffs in one line each, every test changed or added, and the character-name set you captured.
"""

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in $D/knowledge.yaml|$D/plot.md|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
test "$(git diff HEAD --numstat -- $D/knowledge.yaml | awk '{print $1+$2}')" = "4" || { echo "WHY: knowledge.yaml must change exactly 2 lines"; exit 1; }
test "$(git diff HEAD --numstat -- $D/plot.md | awk '{print $1+$2}')" = "2" || { echo "WHY: plot.md must change exactly 1 line"; exit 1; }
grep -c "^  pressure: Join the uprising$" $D/knowledge.yaml | grep -qx 1 || { echo "WHY: 3A pressure line missing"; exit 1; }
grep -c "^  statement: Supporting the uprising is the immediate priority\.$" $D/knowledge.yaml | grep -qx 1 || { echo "WHY: k_scene_3a_entry statement missing"; exit 1; }
grep -c "^objective: Join the uprising$" $D/plot.md | grep -qx 1 || { echo "WHY: plot objective missing"; exit 1; }
grep -n "Reaching Michelle and supporting the uprising\|pressure: Reach Michelle and join" $D/knowledge.yaml && { echo "WHY: old text remains"; exit 1; }
grep -q "Michelle is beside the captives\." $D/knowledge.yaml || { echo "WHY: scene frame sentence lost"; exit 1; }
git diff HEAD --quiet -- $D/handoffs.yaml || { echo "WHY: handoffs.yaml was edited"; exit 1; }
test -s OUTDIR/opening-scene-before.txt && test -s OUTDIR/opening-scene-after.txt || { echo "WHY: before/after opening scene dumps missing"; exit 1; }
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py > /tmp/tb.out 2>&1; rc=$?; tail -25 /tmp/tb.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
git add -A && git diff --cached > OUTDIR/stepB.patch && wc -l OUTDIR/stepB.patch && git diff --cached --stat | tail -8
""".replace("OUTDIR", OUT)

manifest = {
    "run_name": "3a-open-issues-stepB",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "r-wording",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/knowledge.yaml",
                "data/stories/continuity-initiative/plot.md",
                "tests/test_richer_3a.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "three lines changed, pins and unchanged-cue tests pass, patch exported",
        }
    ],
}
Path(__file__).with_name("stepB-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
