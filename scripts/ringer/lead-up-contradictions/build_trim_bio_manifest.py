# ruff: noqa: E501
"""Build the one-task Ringer manifest that trims the senior official's narrator_bio in world.yaml (comparison 1A2 adopted)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
OLD = "  narrator_bio: A senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
NEW = "  narrator_bio: A senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."
TESTS = "tests/test_markdown_story_package.py tests/test_kristin_bio.py tests/test_prompt_presence.py tests/test_richer_3a.py tests/test_place_scoped_feed.py tests/test_frozen_prompts.py tests/test_cloudflare_transport.py tests/test_bench.py tests/test_senior_official_bio.py"
W = f"{R}/data/stories/continuity-initiative/world.yaml"
T = f"{R}/tests/test_senior_official_bio.py"
INV = f"{R}/bench/results/lead-up-contradictions/official-bio-inventory.md"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never revert or reformat any uncommitted change that is not yours. You own only {W} (one line), {T}, and {INV}. Do not edit any other file (plot.md already carries the '### Imprisoned senior official' heading; leave it).

BACKGROUND: a billed, preregistered probe (comparison 1A2 in .plans/lead-up-contradictions-prereg.md) showed the senior official's narrator-safe bio keeps the replies non-hostile without the plot-fact clause. A story-wide bio must hold lasting traits only: the clause 'has kept one piece of emergency authority out of Charles's hands' is a plot fact he hands over at 3A turn c6, so the narrator must not know it on c1-c5.

STEPS:
1. In {W}, change exactly one line (npc id senior_official) from
`{OLD}`
to
`{NEW}`
Nothing else in world.yaml changes (other hunks in the file may pre-exist as uncommitted work; leave them).
2. In {T} add ONE small test: the senior_official npc's narrator_bio equals exactly the new text (without the 'narrator_bio: ' key) and does not contain the word 'authority'. Keep the file's existing tests; if one hard-codes the old bio text, make it read the text from the loaded package instead.
3. Regenerate {INV} the same way it was produced before (offline prompt capture of the nine scripted 3A turns c1..c9: table of turn, command, whether CHARACTERS contains the line, the exact line; the one-line note of which turns carry the bio before the c6 handoff; keep the pin-update notes already in the file). The exact line now ends 'He is exhausted and observant.' Add one line under the table: 'The bio no longer names the one-use authority, so c1-c5 carry no earned-later fact.'
4. Run the focused suites: `TMPDIR=/tmp {R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {TESTS}` (all must pass), then `{R}/.venv/bin/python -m ruff check {T}` and `{R}/.venv/bin/python -m ruff format {T}`. Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
grep -qF 'He is exhausted and observant.' {W} || {{ echo 'new bio line missing'; exit 1; }}
if grep -qF 'kept one piece of emergency authority' {W}; then echo 'old clause still in world.yaml'; exit 1; fi
grep -q 'He is exhausted and observant.' {INV} || {{ echo 'inventory not regenerated'; exit 1; }}
if grep -qF 'kept one piece of emergency authority' {INV}; then echo 'inventory still shows the old line'; exit 1; fi
for c in c1 c2 c3 c4 c5 c6 c7 c8 c9; do grep -qi "$c" {INV} || {{ echo "inventory lacks $c"; exit 1; }}; done
{R}/.venv/bin/python -m pytest -q --no-cov -p no:cacheprovider {TESTS}
{R}/.venv/bin/python -m ruff check {T}
{R}/.venv/bin/python -m ruff format --check {T}
"""

task = {
    "key": "trim-senior-official-bio",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 900,
    "ownership": [W, T, INV],
    "expect_files": [T, INV],
    "spec": spec,
    "check": check,
    "verified": "world.yaml carries the trimmed bio, the inventory is regenerated, and the focused suites pass",
}
manifest = {
    "run_name": "lead-up-contradictions-trim-bio",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-trim-bio",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/trim-bio-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
