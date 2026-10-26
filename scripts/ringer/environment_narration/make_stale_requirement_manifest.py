# ruff: noqa: E501
"""Generate the Ringer manifest that drops observation requirements after a scene or area change."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-stale-requirement.json"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "No story vocabulary (no Kristin, truck, laptop, drawer, Michelle) in non-test code. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement until they pass. "
    "YOU MAY EDIT ONLY: storygame/runtime/capture.py and the NEW file tests/test_observation_stale_requirement.py. "
    "Run ruff check and ruff format on your files at the end. "
    "PROBLEM. WorldCapture (storygame/runtime/capture.py) builds the observation request in before_turn from the command, and the required relations are rebuilt AFTER the turn is applied by "
    "`self.provider._observation_context()` in two places: `preview_commit` (enforcement path) and the shadow-verifier block of `after_commit`. When the turn changed the scene or moved the "
    "protagonist to another area (for example an engine-authored move or a scene transition), the request still names the OLD focus, so the verifier asks whether the old focus's contents "
    "appear in narration that now describes a new place. A live shadow sample showed 5 of 5 scene-transition turns carried such a stale requirement and would have been rejected. "
    "BUILD. (1) In before_turn, record the protagonist's area id and the current scene id as the turn origin (a small frozen value or two fields on WorldCapture; they must be reset every before_turn, "
    "including when no observation request is set). Use world.area(protagonist_id) from the worldkeeper World that `self.provider._world()` returns and `self.provider.state.current_scene_id`. "
    "(2) Add one private helper on WorldCapture that returns the observation context for verification, or None when the requirement is stale: stale means `entered_scene` is true, or the scene id "
    "differs from the origin, or the protagonist's area differs from the origin area. When the origin was never recorded, behave as before (not stale). Otherwise return `self.provider._observation_context(...)` exactly as today. "
    "(3) Use that helper in preview_commit and in the shadow block of after_commit instead of calling `_observation_context()` directly there. Keep `_moved_unrelated` behavior unchanged except that it receives the helper's context (None when stale; confirm it already tolerates None). "
    "(4) A stale turn behaves like a no-relations turn: the shadow record gets outcome 'no_relations', requests 0, accepted True, empty verdicts (match what the verifier returns for no relations, do not invent a new outcome string) plus an extra key `requirement_dropped` set to 'scene_or_area_changed'; the enforcement preview treats it as accepted with no verdicts but STILL rejects an unrelated move of a pre-existing item. Non-stale turns must produce records byte-identical to today (no extra key). "
    "TESTS (tests/test_observation_stale_requirement.py, reuse helpers from tests/test_observation_shadow.py and tests/test_observation_enforcement.py and `_state_at` from tests/test_observation_mode.py; add a synthetic second story with different vocabulary in at least one test). Cover: "
    "a) shadow: a turn that enters a new scene yields no verifier ask (counting fake `ask` sees zero calls) and the record carries requirement_dropped; "
    "b) shadow: a turn where the protagonist's area changed inside the same scene yields the same; "
    "c) shadow: an ordinary same-area observation turn still asks once and has no requirement_dropped key (unchanged behavior); "
    "d) preview with enforcement on: a stale turn is accepted (not rejected) and makes zero verifier asks, while an unrelated item move on that turn is still rejected; "
    "e) origin is reset each before_turn: a stale turn followed by a normal observation turn verifies normally; "
    "f) the default product path with shadow and enforcement both off is untouched (no extra asks, record unchanged). "
    "Do not touch the verifier, item_facts.py, engine.py, docs, worker or data."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov "
    "tests/test_observation_stale_requirement.py tests/test_observation_shadow.py tests/test_observation_preview.py tests/test_observation_enforcement.py "
    "tests/test_observation_resume.py tests/test_observation_mode.py tests/test_observation_prompt.py tests/test_observation_context.py tests/test_observation_verifier.py "
    "tests/test_runtime_capture.py tests/test_3c_world_capture_wiring.py tests/test_3c_item_facts_capture.py tests/test_shadow_report.py 2>&1 | tee /tmp/stale-req.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/stale-req.out && grep -q 'requirement_dropped' storygame/runtime/capture.py && "
    "test -f tests/test_observation_stale_requirement.py && "
    "! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' && "
    ".venv/bin/python -m ruff check storygame/runtime/capture.py tests/test_observation_stale_requirement.py && "
    ".venv/bin/python -m ruff format --check storygame/runtime/capture.py tests/test_observation_stale_requirement.py"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-stale-requirement",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "drop-stale-observation-requirement",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "ownership": ["storygame/runtime/capture.py", "tests/test_observation_stale_requirement.py"],
            "expect_files": [f"{REPO}/tests/test_observation_stale_requirement.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "a scene or area change during the turn drops the observation requirement for shadow and preview",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
