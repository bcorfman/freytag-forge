# ruff: noqa: E501
"""Build the one-task Ringer manifest that adds the senior official's '### ' heading to plot.md (1A source repair)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
S = "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/5249d927-7382-457d-8bc9-509a8e23fa87/scratchpad"
BIO = "A senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
TESTS = "tests/test_markdown_story_package.py tests/test_kristin_bio.py tests/test_prompt_presence.py tests/test_richer_3a.py tests/test_place_scoped_feed.py tests/test_frozen_prompts.py tests/test_cloudflare_transport.py tests/test_bench.py tests/test_senior_official_bio.py"
INV = f"{R}/bench/results/lead-up-contradictions/official-bio-inventory.md"
PLOT = f"{R}/data/stories/continuity-initiative/plot.md"
TEST = f"{R}/tests/test_senior_official_bio.py"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never revert or reformat anything already uncommitted in the working tree (the tree is deliberately dirty; other edits are not yours). You own only: {PLOT}, the new test file {TEST}, the report {INV}, and (only if a pin legitimately changes, see step 4) existing test fixtures/expectations that pin 3A CHARACTERS text.

BACKGROUND: the live 3A run showed that the imprisoned senior official's narrator-safe biography (world.yaml npc id senior_official, field narrator_bio) never reaches the narrator, because storygame/story_package/loader.py _parse_characters only builds package.characters from '### Name' headings under '## Principal Characters' in plot.md, and he has no heading. A billed probe showed that adding his bio line to the CHARACTERS block at the c6 turn removes the hostile-jailer replies (11/12 -> 0/12). world.yaml's narrator_bio is substituted for the heading's own paragraph, so the heading text is canon prose only. Do NOT change loader or runtime code, world.yaml, knowledge.yaml, or any other story file.

STEPS:
1. In plot.md, under '## Principal Characters', after the '### Rebecca Jenkins' paragraph and before the '# Expanded Scene Outline' line, add exactly: '### Imprisoned senior official', a blank line, then this paragraph verbatim, then a blank line: {BIO}  Change nothing else in plot.md. A saved copy of plot.md from before your edit is at {S}/plot.before.md; removing your added block must reproduce that copy byte for byte.
2. Write {TEST} (small, meaningful, hermetic, no network, follow neighbouring tests' conventions): (a) the loaded continuity-initiative package's characters include id 'senior_official' whose bio equals that npc's world.yaml narrator_bio; (b) the only scene whose participant_ids include senior_official is 3A; (c) a CHARACTERS block built for 3A with him present contains his line, and one built for a non-3A scene does not (reuse the helpers/patterns in tests/test_richer_3a.py or tests/test_prompt_presence.py).
3. Write the free inventory {INV}: using the offline prompt-capture pattern in {R}/scripts/ringer/shared-narrator/gue1_capture.py (bench.frozen_prompts, variation bench/variations/richer-3a-live.json, scene 3A, no network or model call), capture the narrator user prompt for each of the nine scripted 3A commands (c1..c9, the variation's first input list) at its state and write a markdown table: turn (c1..c9), command, whether CHARACTERS now contains 'Imprisoned senior official is', and for turns where it does the exact line. Add one line stating which turns carry the bio BEFORE the c6 handoff that gives out his one-use authority. Do not interpret beyond that.
4. Run the focused suites (command below). Existing tests/fixtures that pin 3A CHARACTERS or prompt text may legitimately change because of the new line; update such a pin ONLY when the sole difference is the added official line, and list each updated file and why in the inventory file. Any other failure is a real problem: fix your edit or report it, never weaken a test. Baseline before your edit was 355 passed, 1 skipped on the first eight files.

HOW TO RUN (from {R}): `TMPDIR=/tmp {R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {TESTS}`; then `{R}/.venv/bin/python -m ruff check {TEST}` and `{R}/.venv/bin/python -m ruff format {TEST}`. Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{R}/.venv/bin/python - <<'PY'
import sys
new = open("{PLOT}").read()
old = open("{S}/plot.before.md").read()
block = "### Imprisoned senior official\\n\\n{BIO}\\n\\n"
if new.count(block) != 1:
    sys.exit("heading+bio block not present exactly once with the exact text")
if new.replace(block, "", 1) != old:
    sys.exit("plot.md differs from the saved copy by more than the added block")
print("plot.md diff is exactly the added block")
PY
test -s {INV} || {{ echo 'inventory missing'; exit 1; }}
for c in c1 c2 c3 c4 c5 c6 c7 c8 c9; do grep -qi "$c" {INV} || {{ echo "inventory lacks turn $c"; exit 1; }}; done
{R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {TESTS}
{R}/.venv/bin/python -m ruff check {TEST}
{R}/.venv/bin/python -m ruff format --check {TEST}
"""
task = {
    "key": "add-senior-official-heading",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1500,
    "check_timeout_s": 900,
    "ownership": [PLOT, TEST, INV],
    "expect_files": [TEST, INV],
    "spec": spec,
    "check": check,
    "verified": "plot.md differs from its saved copy by exactly the added heading block, the new test and focused suites pass, and the inventory covers c1..c9",
}
manifest = {
    "run_name": "lead-up-contradictions-1a-heading",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-1a-heading",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{R}/scripts/ringer/lead-up-contradictions/1a-heading-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
print("written")
