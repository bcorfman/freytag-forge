# ruff: noqa: E501
"""Generate the Ringer manifest that declares the 1A passenger seat a complete scope and documents the field."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-seat-scope.json"
WORLD = "data/stories/continuity-initiative/world.yaml"
TEST = "tests/test_seat_scope.py"
DOC = "docs/markdown-story-authoring.md"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>` (tests that build the provider set CLOUDFLARE_WORKER_URL themselves with monkeypatch). "
    f"YOU MAY EDIT ONLY: {WORLD} (exactly one added line), the NEW file {TEST}, and {DOC} (one short added passage). Never edit storygame/, packages/, plot.md, knowledge.yaml or any other data file. No network, no live model call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "READ FIRST: docs/world-model-grounding.md (the rules for declaring anything in a story package), docs/markdown-story-authoring.md, tests/test_observation_prompt.py and tests/test_observation_mode.py (how the observation prompt is built and tested), storygame/runtime/item_facts.py methods `_observation_scope_is_empty` and `_section_user_prompt`, storygame/runtime/observation.py (`scope_complete`). "
    "BACKGROUND (measured, do not redo). The engine already supports `contents_complete: true` on a world.yaml item (storygame/story_package/models.py Item.contents_complete, passed through world_schema.py to worldkeeper). When the observation focus is a complete scope and nothing visible is inside it, the narrator prompt gets the CONSTRAINTS line 'Nothing is left in or under the <name>. Searching the <name> finds nothing.' No shipped story declares it, so that line never fires in the product. A billed probe on the real scene-1A prompt for 'Inspect the passenger seat' showed the narrator invents objects on the empty seat in 19 of 25 samples without that line and 0 of 25 with it. "
    f"DATA CHANGE. In {WORLD} add `contents_complete: true` to the entity `truck_passenger_seat` (name: passenger seat, kind: seat) and to NOTHING else. Do not declare the driver's seat or any other entity. "
    f"TESTS in the new file {TEST} (real package data/stories/continuity-initiative; build states and the provider as tests/test_observation_mode.py does; no model call): (1) the loaded package's world reports `contents_complete('truck_passenger_seat')` True and False for every other entity in the package (assert by iterating all entity ids except that one, so a stray second declaration fails). (2) State where the player is outside the house by the truck and the laptop is held by the protagonist (move the laptop to the protagonist with the world model): with an observation request of kind 'look' focused on the passenger seat, the provider's user prompt contains exactly the line '- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing.' once. (3) Same state but the laptop on the passenger seat: the prompt does NOT contain that line and does contain the laptop as a required mention. (4) A look at the driver's seat or the truck with the same state never gets the line. If the way to build the prompt is awkward, follow what test_observation_prompt.py does for the drawer scope line. "
    f"DOC. In {DOC}, in the place where world.yaml item fields are described, add a short passage (plain words, at most 8 lines) for `contents_complete: true`: it says the world model lists everything that can be in or on this place; when a player looks at or searches it and nothing is there, the engine tells the narrator nothing is left, so the narrator does not invent an object; leave it off (the default) for any place where the story may add things; it applies to the exact place, not to what is inside it. If you find a better existing spot, use it. "
    "FINALLY run `.venv/bin/python scripts/quick_suite.py` with CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN unset and report the exact counts. If a test that pins the package (a hash, a golden snapshot, the markdown-package round trip) fails because of the one added line, do NOT edit it: report the test name and message. Run ruff check and ruff format on the test file."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py 2>&1 | tee /tmp/seat-quick.out | grep -E 'passed|failed|FAILED' | tail -5 && "
    "! grep -Eq '[0-9]+ failed|FAILED' /tmp/seat-quick.out && grep -Eq '[0-9]+ passed' /tmp/seat-quick.out && "
    f"test -s {TEST} && "
    f"test $(git diff -U0 -- {WORLD} | grep -E '^\\+' | grep -vE '^\\+\\+\\+' | wc -l) -eq 1 && git diff -U0 -- {WORLD} | grep -qE '^\\+ +contents_complete: true' && "
    f"test $(grep -c 'contents_complete' {WORLD}) -eq 1 && "
    f"! git diff --name-only | grep -vE '^({WORLD}|{DOC})$' | grep -q . && "
    f"grep -q 'contents_complete' {DOC} && "
    f".venv/bin/python -m ruff check {TEST} && .venv/bin/python -m ruff format --check {TEST}"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-seat-scope",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "declare-passenger-seat-scope",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 1800,
            "ownership": [WORLD, TEST, DOC],
            "expect_files": [f"{REPO}/{TEST}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the 1A passenger seat is a complete scope: an empty seat gets the nothing-left line, a seat with the laptop does not; nothing else is declared; the quick suite is green",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
