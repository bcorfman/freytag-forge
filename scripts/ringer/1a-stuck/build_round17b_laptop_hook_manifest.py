# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 17b: the witnessed card recovery (k_sl_1a_b_r0w) carries the laptop hook. FREE: no model call, no network.

Round 15d replicates 1 and 2 found the card while the patrol was in the house, so by k_sl_1a_b_r0w. Only the unwitnessed
k_sl_1a_b_r0 text says where the laptop is, so those players never learned how to read the card. Owner approved adding the
hook and asked for the sentence to be rewritten to fit, not appended. One Codex task, story CLI edit by record id.
Usage: build_round17b_laptop_hook_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/1a-laptop-hook"
BASELINE = "/home/bcorfman/dev/ringer-work/1a-hook-baseline/1A"

NEW_TEXT = (
    "Kristin's fingers find something taped beneath the drawer. She peels it loose, and the tape rasps. "
    "It is Michelle's memory card, and she pockets it. Her laptop is still out in her truck. "
    'The officer turns at the sound. "What have you got there?" His hand is already out.'
)

OWNED = [
    "data/stories/continuity-initiative/source/scenes/1A.yaml",
    "data/stories/continuity-initiative/source/scenes/1A.match.yaml",
    "tests/test_1a_witnessed_recovery.py",
]

SPEC = """You are a story-data editor with Python skills. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run npm, playwright or the bench run command. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (only on .py files). Never pass --cov to pytest.

THE PROBLEM. In scene 1A the player can find Michelle's memory card two ways: reveal `k_sl_1a_b_r0` (no patrol in the house) and `k_sl_1a_b_r0w` (a patrol officer is in the house). Only `k_sl_1a_b_r0`'s text ends with the sentence "Her laptop is still out in her truck." That sentence is the only place the player learns where to read the card. In live play the card is almost always found while the officer is in the house, so players never learn it. `k_sl_1a_b_r0w` must carry the same hook.

THE EDIT (exact text; the owner approved it). Set the delivery text of `k_sl_1a_b_r0w` to exactly this one paragraph, character for character:
@NEW_TEXT@
Compared with today's text, two things change: "and the tape rasps" is added after "She peels it loose" (so "the sound" the officer turns at has a source), and the sentence "Her laptop is still out in her truck." is added after the pocketing sentence. Nothing else changes. Do NOT change the text of `k_sl_1a_b_r0`, the `says`, `intent`, `earn_when`, `when`, `commits` or any other field of any record, and do not change any other scene.

HOW. Use the story CLI, not a hand edit: `.venv/bin/python -m storygame.story_cli show claim:k_sl_1a_b_r0w.text` shows the current value and the file it lives in; `.venv/bin/python -m storygame.story_cli set claim:k_sl_1a_b_r0w.text '<new text>'` writes it (read `storygame/story_cmds/cmd_set.py` for the exact address form and how it refuses generated fields). The same sentence also appears as the variant `text:` for `r2` of the reveal `find_card` in `data/stories/continuity-initiative/source/scenes/1A.yaml` (around line 942) and may appear in `1A.match.yaml`; after the edit, `grep -rn "The officer turns at the sound" data/stories/continuity-initiative/source` must show only the NEW text, in every place it appears, and `story fmt --check` and the source-tree check must pass. If the CLI refuses an address, edit the YAML by hand with the smallest change and keep the file byte-identical elsewhere (the writer round-trips the committed tree byte for byte).

ONE TEST. In `tests/test_1a_witnessed_recovery.py` add one small test that looks both card-recovery deliveries up by record id from the compiled default package (follow how the file already reads `story_text` or the knowledge indexes; copy no sentence of 45 or more characters into the test) and asserts each delivery text names the laptop and the truck, and that the witnessed one still contains the officer's challenge constant already defined in that file. It must not assert the whole sentence. New tests run in under 10 seconds and use no model.

HARD LIMITS. Edit only the three files above. Never edit `tests/fixtures/`, `storygame/`, `factory/`, `bench/` or `tests/shard_durations.json`. If any existing test fails because of the new wording, STOP and describe the failure in the notes instead of editing that test. Write NOTES_17B.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- data tests
bad=$(git diff --cached --name-only | grep -vxF -e data/stories/continuity-initiative/source/scenes/1A.yaml -e data/stories/continuity-initiative/source/scenes/1A.match.yaml -e tests/test_1a_witnessed_recovery.py || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
cat > "$WORK/out/new_text.txt" <<'TXT'
@NEW_TEXT@
TXT
probe="$WORK/out/probe.out"
.venv/bin/python - "$WORK/out/new_text.txt" > "$probe" 2>&1 <<'PY' || true
import sys
from pathlib import Path
from storygame.story_package.loader import load_story_package
from storygame.story_source.lookup import story_text

want = Path(sys.argv[1]).read_text().strip()
pkg = load_story_package(Path("data/stories/continuity-initiative"))
r0w = story_text("claim:k_sl_1a_b_r0w.text", package=pkg).strip()
r0 = story_text("claim:k_sl_1a_b_r0.text", package=pkg).strip()
assert r0w == want, ("compiled r0w text is not the approved text", r0w)
assert r0.endswith("Her laptop is still out in her truck."), r0
print("probe ok")
PY
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed (fails on the unedited story on purpose)"; exit 1; }
n=$(grep -rn "The officer turns at the sound" data/stories/continuity-initiative/source | wc -l || true)
old=$(grep -rn "pockets it. The officer turns at the sound" data/stories/continuity-initiative/source | wc -l || true)
[ "$old" -eq 0 ] || { echo "old wording still present in $old place(s)"; grep -rn "pockets it. The officer turns" data/stories/continuity-initiative/source; exit 1; }
echo "new-wording places: $n"
.venv/bin/python -m storygame.story_cli fmt --check
rm -rf "$WORK/out/after"
.venv/bin/python -m factory.stations.prompt_snapshot record --scene 1A --out "$WORK/out/after"
diff -r @BASELINE@ "$WORK/out/after/1A" || diff -r @BASELINE@ "$WORK/out/after" || { echo "prompt snapshot changed (nothing in a prompt should change)"; exit 1; }
start=$(date +%s)
.venv/bin/python scripts/quick_suite.py --also tests/test_1a_officer_press.py tests/test_1a_drawer_close_gap.py tests/test_cue_eligibility_compare.py tests/test_cue_spent_reveal.py tests/test_drawer_gap_nudge.py tests/test_impact_report.py tests/test_situation_trace.py tests/test_voiceable_knowledge.py tests/test_1a_witnessed_recovery.py
took=$(( $(date +%s) - start ))
echo "quick suite took $took s (baseline 157 s, budget 450 s)"
[ "$took" -le 450 ] || { echo "quick suite over the 450 s budget"; exit 1; }
.venv/bin/python -m ruff check tests/test_1a_witnessed_recovery.py
.venv/bin/python -m ruff format --check tests/test_1a_witnessed_recovery.py
git diff --cached > "$WORK/out/laptop-hook.patch"
test -s "$WORK/out/laptop-hook.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@NEW_TEXT@", NEW_TEXT)
            .replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@BASELINE@", BASELINE)
        )

    return {
        "run_name": "1a-laptop-hook",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "r0w-laptop-hook",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "k_sl_1a_b_r0w's delivery text is the approved text in every place it appears, nothing else in the story changed, the 1A prompt snapshot is byte-identical, story fmt passes, quick suite green under 450 s, one small test added.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round17b-laptop-hook-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
