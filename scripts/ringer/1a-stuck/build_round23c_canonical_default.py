"""Round 23c: carry-in refinement, layering fix, canonical entry as the hosted default (backend and frontend)."""

import json
from pathlib import Path

import build_round23a_entry_state_foundation as a

WORK = a.WORK
REPO = a.REPO
MAIN = a.MAIN

CONTEXT = (
    "ALREADY BUILT in this tree (rounds 23a and 23b; read them first): worldkeeper `World.export_state`, "
    "`import_state`, `entry_problems`; storygame/runtime/entry_seed.py (`canonical` persona, "
    "`canonical_path_report`); storygame/runtime/entry_snapshots.py (golden `entry/<SCENE>.json` files for the "
    "default story, `load_entry_snapshot`, `state_from_snapshot`, `check_entry_snapshots`, `carry_in_report`, CLI); "
    "storygame/web_demo.py (gated `start_scene` with `start_state` `thorough` or `bare`). "
    "CONTRACT for this round: `start_state` accepts `canonical`, `thorough` and `bare`, and the DEFAULT becomes "
    "`canonical`: the hosted session loads the committed golden snapshot for `start_scene` through "
    "`load_entry_snapshot` and `state_from_snapshot` (no replay), then opens the scene as today. A stale or "
    "invalid snapshot (`EntrySnapshotError`) answers HTTP 422 with its plain message and creates no session. "
    "Everything else in the gate stays: 403 without the opted-in token or in production, 422 for an unknown "
    "scene or state. "
)

BACKEND_SPEC = a.COMMON + a.WHY + CONTEXT + (
    "\n\nYou may edit or create ONLY: storygame/runtime/entry_snapshots.py, storygame/story_package/default_root.py "
    "(new), storygame/web_demo.py, tests/test_entry_snapshots.py, tests/test_start_scene_session.py, "
    "docs/testing-runbook/hosted-e2e.md.\n\n"
    "TASK. (1) LAYERING FIX. storygame/runtime/entry_snapshots.py imports `_default_package_root` from "
    "storygame/web_demo.py: the runtime must not depend on the HTTP layer, and web_demo is about to import "
    "entry_snapshots, which would be a cycle. Move the default-root resolution into the new "
    "storygame/story_package/default_root.py (`default_package_root() -> Path`, same result as today); make "
    "web_demo.py and entry_snapshots.py import it from there (keep the name `_default_package_root` working in "
    "web_demo.py as an alias so nothing else breaks). Prove with a test that importing "
    "`storygame.runtime.entry_snapshots` does not import `storygame.web_demo` (check `sys.modules` in a "
    "subprocess). (2) CARRY-IN REFINEMENT. The real story gives three carry-in gate rows (a storylet and its claim "
    "each) whose consumers are OPTIONAL storylets (not in `required_storylet_ids`) gated on facts produced by "
    "optional earlier storylets; a canonical player never earns those, so they are optional chains the canonical "
    "entry cannot reach, not entry-state defects. Change `carry_in_report` rows to add `consumer_required` "
    "(true when the consumer's storylet, or for a claim its source storylet, is in `required_storylet_ids`; use "
    "`storygame/story_package/obligations.py`). `check_entry_snapshots` reports a gate problem ONLY when "
    "`consumer_required` is true and `supplied` is false; optional-chain rows are returned by "
    "`carry_in_report` and printed by the CLI under a heading `optional chains not reachable from canonical "
    "entry` (informational, exit code unaffected). After this the CLI `check` must exit 0 on the real story. "
    "Update tests/test_entry_snapshots.py: the real-story check is now fully clean, the optional-chain rows are "
    "listed with `consumer_required` false, and a synthetic case with a REQUIRED gated consumer still produces a "
    "gate problem. (3) CANONICAL DEFAULT in web_demo.py per the contract above: map each package to its source "
    "root (where it was loaded from) so the right `entry/` directory is used; `start_state` accepts "
    "`canonical`, `thorough`, `bare`, default `canonical`. (4) Tests in tests/test_start_scene_session.py (update "
    "the earlier ones whose default changed, say so in NOTES.txt): default session at the SECOND scene id (read "
    "from the loaded package, never hardcode names) equals `state_from_snapshot` of that scene's snapshot "
    "(compare facts and world export) and a following turn works with the stub provider; `thorough` and `bare` "
    "still work; with the `entry/` file edited in a tmp copy of the story root (use `create_demo_app("
    "package_roots=(tmp_root,))`) the session answers 422 and the store holds no session; the 403 and 422 gate "
    "cases still pass; a request without `start_scene` is unchanged. (5) docs/testing-runbook/hosted-e2e.md: "
    "update the existing paragraph (do not add a section): seeded entry defaults to the committed canonical "
    "snapshot; `thorough` and `bare` are labelled stress options. Run tests/test_entry_snapshots.py "
    "tests/test_start_scene_session.py tests/test_web_demo.py tests/test_canonical_entry_path.py "
    "tests/test_world_model.py packages/worldkeeper/tests and `ls tests/test_bench*.py`."
)

FRONTEND_SPEC = a.COMMON + a.WHY + CONTEXT + (
    "\n\nYou may edit or create ONLY: frontend/e2e/helpers.js, frontend/e2e/blind-player.spec.js, "
    "frontend/e2e/start-scene.test.js. Do NOT edit frontend/src. Run `[ -e frontend/node_modules ] || ln -s "
    f"{MAIN}/frontend/node_modules frontend/node_modules` first.\n\n"
    "TASK. The Playwright side currently defaults `startState` to `thorough` (helpers.js `sessionBodyWithStart`, "
    "`installStartSceneRoute`, blind-player.spec.js `E2E_BLIND_ENTRY_STATE`). Change every default to "
    "`canonical`, accept `canonical`, `thorough` and `bare` from `E2E_BLIND_ENTRY_STATE`, and keep the run label "
    "`entry: { mode: \"seeded\", state: <state> }` honest (state is what was requested). An unknown "
    "`E2E_BLIND_ENTRY_STATE` value throws a clear error before any billed call. Update frontend/e2e/"
    "start-scene.test.js to the new default and add cases: canonical default in the rewritten body; thorough and "
    "bare when asked; an unknown value throws. Prove with: `cd frontend && node --test e2e/start-scene.test.js "
    "e2e/affordances.test.js e2e/alias-smoke-record.test.js e2e/api-token.test.js e2e/blind-player.test.js "
    "e2e/canon-journey.test.js e2e/canon-policy.test.js e2e/knowledge-timeline-record.test.js "
    "e2e/merge-blind-player.test.js e2e/negation-scope.test.js e2e/package-clock-controller.test.js "
    "e2e/package-clock-request.test.js e2e/reference-copy.test.js e2e/scene-walk.test.js e2e/spine-record.test.js "
    "src/clarification.test.js src/turn_rendering.test.js` (seven OTHER test files already fail on main because "
    "they read a removed data file; do not run or touch them) and `node --check e2e/blind-player.spec.js "
    "e2e/helpers.js`."
)

BACKEND_OWNED = (
    r"storygame/runtime/entry_snapshots\.py|storygame/story_package/default_root\.py|storygame/web_demo\.py"
    r"|tests/test_entry_snapshots\.py|tests/test_start_scene_session\.py|docs/testing-runbook/hosted-e2e\.md"
)
FRONTEND_OWNED = r"frontend/e2e/helpers\.js|frontend/e2e/blind-player\.spec\.js|frontend/e2e/start-scene\.test\.js"

BACKEND_BODY = """.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_entry_snapshots.py tests/test_start_scene_session.py tests/test_web_demo.py tests/test_canonical_entry_path.py tests/test_world_model.py packages/worldkeeper/tests $(ls tests/test_bench*.py)
.venv/bin/python -m storygame.runtime.entry_snapshots check
.venv/bin/python -c "import sys; import storygame.runtime.entry_snapshots; sys.exit(1 if 'storygame.web_demo' in sys.modules else 0)" || { echo 'entry_snapshots imports web_demo'; exit 1; }
grep -q 'consumer_required' storygame/runtime/entry_snapshots.py || { echo 'consumer_required missing'; exit 1; }
grep -q 'canonical' storygame/web_demo.py || { echo 'canonical default missing in web_demo'; exit 1; }"""

FRONTEND_BODY = """(cd frontend && node --test e2e/start-scene.test.js e2e/affordances.test.js e2e/alias-smoke-record.test.js e2e/api-token.test.js e2e/blind-player.test.js e2e/canon-journey.test.js e2e/canon-policy.test.js e2e/knowledge-timeline-record.test.js e2e/merge-blind-player.test.js e2e/negation-scope.test.js e2e/package-clock-controller.test.js e2e/package-clock-request.test.js e2e/reference-copy.test.js e2e/scene-walk.test.js e2e/spine-record.test.js src/clarification.test.js src/turn_rendering.test.js)
node --check frontend/e2e/blind-player.spec.js
node --check frontend/e2e/helpers.js
grep -q 'canonical' frontend/e2e/helpers.js || { echo 'canonical default missing in helpers.js'; exit 1; }
grep -q 'canonical' frontend/e2e/blind-player.spec.js || { echo 'canonical default missing in blind-player.spec.js'; exit 1; }"""


def check(owned_re, body, patch, budget):
    return (
        a.check(owned_re, body, patch, budget)
        .replace("git add -A -- storygame bench tests packages docs", "git add -A -- storygame bench tests packages docs data frontend/e2e")
        .replace(f"[ -e .venv ] || ln -s {MAIN}/.venv .venv", f"[ -e .venv ] || ln -s {MAIN}/.venv .venv\n[ -e frontend/node_modules ] || ln -s {MAIN}/frontend/node_modules frontend/node_modules")
    )


manifest = {
    "run_name": "entry-state-canonical-default",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "backend-canonical-default",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/runtime/entry_snapshots.py",
                "storygame/story_package/default_root.py",
                "storygame/web_demo.py",
                "tests/test_entry_snapshots.py",
                "tests/test_start_scene_session.py",
                "docs/testing-runbook/hosted-e2e.md",
            ],
            "spec": BACKEND_SPEC,
            "check": check(BACKEND_OWNED, BACKEND_BODY, "backend-canonical-default", 420),
            "expect_files": [],
            "verified": "Canonical snapshot entry is the hosted default; stale snapshots are refused; the runtime no longer imports the HTTP layer; the real story's entry check is clean.",
        },
        {
            "key": "frontend-canonical-default",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 600,
            "ownership": [
                "frontend/e2e/helpers.js",
                "frontend/e2e/blind-player.spec.js",
                "frontend/e2e/start-scene.test.js",
            ],
            "spec": FRONTEND_SPEC,
            "check": check(FRONTEND_OWNED, FRONTEND_BODY, "frontend-canonical-default", 180),
            "expect_files": [],
            "verified": "The blind player requests canonical entry by default and rejects unknown entry states before any billed call.",
        },
    ],
}
Path(__file__).with_name("round23c-canonical-default-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
