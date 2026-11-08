# ruff: noqa: E501
"""Build the one-task Ringer manifest that implements the `trailing` pacing-event flag against the frozen failing tests."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
TEST = f"{R}/tests/test_trailing_pacing_events.py"
TEST_SHA = "9ed2a2c2f0aef5274edb06abcd096e4d41f92aab56284dea94d27618f0b01842"
MODELS = f"{R}/storygame/story_package/models.py"
ENGINE = f"{R}/storygame/runtime/engine.py"
DOC = f"{R}/docs/markdown-story-authoring/pacing-and-incidents.md"
FOCUSED = " ".join(
    f"tests/{name}"
    for name in (
        "test_trailing_pacing_events.py",
        "test_1a_patrol.py",
        "test_1a_officer_press.py",
        "test_markdown_story_package.py",
        "test_scene_relative_pacing.py",
        "test_pacing_handoff.py",
        "test_canon_journey.py",
        "test_scene_progression_phase4.py",
        "test_scene_roleplay_contract.py",
    )
)

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY these three files: {MODELS}, {ENGINE}, {DOC}. Do NOT edit {TEST} (frozen failing tests; the check verifies its hash) or anything under {R}/data, {R}/tests, {R}/bench, {R}/packages. Read the frozen tests first: {TEST}.

GOAL: add an authored per-event flag so a pacing event can trail the player's action instead of firing before the narrator is called.
1. {MODELS}: class PacingEvent gets `trailing: StrictBool = Field(default=False, exclude_if=lambda value: value is False)` (the file already uses StrictBool with exclude_if for `voiceable`/`repeatable`; follow that style; add a short description). Default False so every shipped package is unchanged and serializes unchanged.
2. {ENGINE}: in RuntimeEngine._activate_pacing, an event with `trailing` true must be skipped in the PRE-narration pass, which is the call made with `defer_guarded_events=True` (engine.py around line 517), exactly as events guarded by an `equals: false` predicate are already skipped there. Every other caller (the post-commit lifecycle: _record_turn then _advance_pacing then _activate_pacing(realize_complications=True), and the resume path) must fire it as today, so the post-commit pass fires the event, applies its effects and world on_assert moves, and appends its verbatim realization text once after the story. Make the smallest change; do not rename the parameter unless needed (if you do, update every caller and any test that passes it). Note for the comment: the parameter now also defers trailing events. Do not change when non-trailing events fire. Do not touch the capture/reference code (storygame/runtime/capture.py, item_facts.py): with the event skipped pre-narration, the whole narrator request sees the pre-event world, which is the goal.
3. {DOC}: add one short paragraph (12th-grade plain words, one idea per sentence) to the pacing event section saying: set `trailing: true` on an event whose effects should land after the player's action; the narrator sees the world as it was before the event, then the event's effects apply and its verbatim text is added after the story; use it for an arrival or departure the player's own command should still be able to address; the default is false. The word `trailing` must appear.
Then make ALL tests in {TEST} pass without editing them. If one cannot pass because the test itself is wrong, stop and write the exact reason into {D}/trailing-impl-notes.txt (you may create this one extra file) instead of changing the test.

HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest {FOCUSED} -q -p no:cacheprovider 2>&1 | tail -30`; `{PY} -m ruff format {MODELS} {ENGINE} && {PY} -m ruff check {MODELS} {ENGINE}`. Pre-existing tests that pin old behavior may be updated only if they pin the engine's internal parameter name, never a turn number or story behavior."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
[ "$(sha256sum {TEST} | cut -d' ' -f1)" = "{TEST_SHA}" ] || {{ echo 'frozen test file was modified'; exit 1; }}
git diff --quiet -- data bench packages || {{ echo 'data, bench or packages changed'; git diff --stat -- data bench packages; exit 1; }}
git diff --name-only | grep -v -E '^(storygame/story_package/models.py|storygame/runtime/engine.py|docs/markdown-story-authoring/pacing-and-incidents.md|docs/testing-runbook/prompt-inspection.md)$' && {{ echo 'unexpected tracked file changed'; exit 1; }}
{PY} -m ruff check storygame
{PY} -m ruff format --check storygame/story_package/models.py storygame/runtime/engine.py
{PY} -m pytest {FOCUSED} -q -p no:cacheprovider 2>&1 | tail -25
"""

task = {
    "key": "implement-trailing-events",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 2400,
    "check_timeout_s": 1200,
    "ownership": [MODELS, ENGINE, DOC, f"{D}/trailing-impl-notes.txt"],
    "expect_files": [MODELS, ENGINE, DOC],
    "spec": spec,
    "check": check,
    "verified": "the frozen tests pass, shipped packages are unchanged, and the focused 1A/pacing suites still pass",
}
manifest = {
    "run_name": "trailing-pacing-events",
    "workdir": "/home/bcorfman/dev/ringer-work/trailing-pacing-events",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/trailing-impl-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
