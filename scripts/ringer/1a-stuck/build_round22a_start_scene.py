"""Round 22a: seeded scene entry for the hosted blind player (backend start_scene + Playwright side)."""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-22"
REPO = "/home/bcorfman/dev/freytag-forge"

COMMON = (
    "You are an engineer. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge "
    "(detached at HEAD). Edit files here directly. NEVER git commit, never touch /home/bcorfman/dev/freytag-forge "
    "itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, never run "
    "`python -m bench run`, never write factory/state/. FIRST run: [ -e .venv ] || ln -s "
    "/home/bcorfman/dev/freytag-forge/.venv .venv ; [ -e frontend/node_modules ] || ln -s "
    "/home/bcorfman/dev/freytag-forge/frontend/node_modules frontend/node_modules . Environment for every "
    "Python command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): "
    "`.venv/bin/python -m ruff check <files>` / `.venv/bin/python -m ruff format <files>` (line length 120, "
    "Python 3.12). Never pass --cov to pytest. Run tests as "
    "`.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 <files>`. Tests must be hermetic (stub providers, no "
    "network, no real model). Shared code must stay story-agnostic (no story, scene or character names in "
    "production code; tests may use the repository's real story package). If an OLD test pins behaviour this "
    "change deliberately changes, update it and say so in NOTES.txt. Write NOTES.txt (worktree root, never "
    "committed) listing every ambiguity and your choice. Read first: AGENTS.md and docs/contributor-guide.md. "
)

CONTRACT = (
    "SHARED CONTRACT (both tasks build to it). WHY: the hosted blind-player e2e test starts every session at the "
    "first scene and replays every earlier scene live (billed narration, up to 160 turns for scene 3B), so later "
    "scenes cannot finish inside the 20-minute Playwright timeout and cost 3.5x the per-turn estimate. The engine "
    "already has offline seeding with no narration calls (bench/core.py `advance_state_to_scene`, "
    "`seeded_state_for_scene`, `package_and_state`; bench README `entry_state` `bare` or `thorough`). "
    "REQUEST: `POST /api/v1/session` body gains two optional fields: `start_scene` (string scene id) and "
    "`start_state` (`\"thorough\"` default, or `\"bare\"`). RULES: a request that carries `start_scene` is honoured "
    "ONLY when the request header `X-Freytag-Test-Clock-Token` matches the configured token under the existing "
    "test-clock opt-in (`_test_clock_token_matches`: env FREYTAG_ALLOW_TEST_CLOCK=1 and FREYTAG_TEST_CLOCK_TOKEN) "
    "AND the deployment channel is not `production`; otherwise the endpoint answers HTTP 403 with a plain detail "
    "and creates no session (it never silently ignores the field). An unknown scene id answers 422. "
    "`start_state` other than the two values answers 422. A request WITHOUT `start_scene` behaves exactly as today. "
    "RESPONSE: unchanged shape; `state.scene_id` and `opening.scene_id`/`opening.phase` describe the seeded scene; "
    "the opening text is the normal scene opening for that scene (one narration call, as today). "
)

BACKEND_SPEC = COMMON + CONTRACT + (
    "\n\nYou may edit or create ONLY: storygame/runtime/entry_seed.py (new), bench/core.py, storygame/web_demo.py, "
    "tests/test_start_scene_session.py (new), tests/shard_durations.json, docs/testing-runbook/hosted-e2e.md.\n\n"
    "TASK. (1) `storygame` must not import `bench`. Move the scene-seeding logic out of bench/core.py into a new "
    "module storygame/runtime/entry_seed.py exposing `bare_state_for_scene(package, scene_id)` and "
    "`advance_state_to_scene(package, state, scene_id)` (same behaviour as today: read bench/core.py "
    "`package_and_state`, `advance_state_to_scene`, `seeded_state_for_scene` first; keep the world seeding, scene "
    "placements and world effects of the bare path) and make bench/core.py import and use them (keep the names "
    "`package_and_state`, `advance_state_to_scene`, `seeded_state_for_scene` working for existing callers; no "
    "duplicated logic). Existing bench tests must still pass unchanged. (2) In storygame/web_demo.py add the "
    "contract above to `SessionRequest` and `create_session`. thorough: `RuntimeState.bootstrap(package)` then "
    "`advance_state_to_scene`; bare: `bare_state_for_scene`. Seeding failure (RuntimeError, ValueError) answers 422 "
    "with a plain detail, never a 500. Build the opening exactly as today but report the CURRENT scene's id and "
    "phase (today it reads `package.scenes[0]`; fix that for the seeded case without changing the first-scene "
    "output). Persist the seeded state with the normal store. The rate limit applies as today. (3) One short "
    "paragraph in docs/testing-runbook/hosted-e2e.md (the runbook must stay short; do not add a section) saying "
    "the blind player enters later scenes with seeded entry on staging only, and that results from seeded runs are "
    "labelled `seeded entry`.\n\n"
    "TESTS (new tests/test_start_scene_session.py, hermetic, fast: whole file under 20 s; build the app like "
    "tests/test_web_demo.py does with a stub `provider_factory`, `monkeypatch.setenv` for the opt-in): (a) with "
    "token and opt-in, `start_scene` set to the package's SECOND scene id (read it from the loaded package, do not "
    "hardcode a name) returns 200, `state.scene_id` and `opening.scene_id` equal it, and a following turn on that "
    "session works against the stub; (b) the same with `start_state` `bare`; (c) no token header, wrong token, and "
    "no opt-in each answer 403 and the store holds no new session; (d) channel `production` with a correct token "
    "answers 403; (e) unknown scene 422; bad `start_state` 422; (f) a request without `start_scene` still opens at "
    "the first scene and is identical in shape to today's response; (g) bench still seeds the same state: assert "
    "that `bench.core.seeded_state_for_scene` for thorough and bare returns a state whose `current_scene_id` is the "
    "target. Then add the new test file to tests/shard_durations.json by running "
    "`.venv/bin/python scripts/regen_shard_durations.py --missing-only` (never `uv`; if it needs network or uv, "
    "add the entry by hand with a measured duration rounded up). Run the existing tests/test_web_demo.py and the "
    "bench test files (`ls tests/test_bench*.py`) to prove nothing broke."
)

FRONTEND_SPEC = COMMON + CONTRACT + (
    "\n\nYou may edit or create ONLY: frontend/e2e/helpers.js, frontend/e2e/blind-player.spec.js, "
    "frontend/e2e/start-scene.test.js (new). Do NOT edit frontend/src (the product UI is unchanged).\n\n"
    "TASK. Read frontend/e2e/helpers.js (`startSceneSession`, `installApiToken`), frontend/e2e/blind-player.spec.js "
    "(the `walkScenes` prefix for any scene other than 1A, `playScene`, the report written at the end) and "
    "frontend/e2e/api-token.js. (1) `startSceneSession(page, options = {})`: with no options it behaves exactly as "
    "today. With `options.startScene` (and optional `options.startState`, default `\"thorough\"`), it registers a "
    "Playwright `page.route` for POST `**/api/v1/session` that rewrites the JSON body to add `start_scene` and "
    "`start_state` (use `route.fallback({ postData })` so the existing token route still adds the "
    "`x-freytag-test-clock-token` header; keep the original body fields), and the status-line check expects "
    "`Scene <startScene>` instead of `Scene 1A`. Fail clearly (throw) if `startScene` is set but no "
    "FREYTAG_TEST_CLOCK_TOKEN is configured, because the server would answer 403. (2) blind-player.spec.js: for a "
    "requested scene other than 1A (not the `all` mode) the DEFAULT becomes seeded entry: call "
    "`startSceneSession(page, { startScene: requestedScene, startState: process.env.E2E_BLIND_ENTRY_STATE || "
    "\"thorough\" })` and read the opening text from `.entry-output` as the 1A path does, with no `walkScenes` "
    "prefix. Environment `E2E_BLIND_ENTRY=walk` keeps today's full-prefix walk for comparison runs. (3) Label the "
    "result: every scene run in the report gains `entry: { mode: \"seeded\" | \"walk\" | \"start\", state: "
    "\"thorough\" | \"bare\" | null }` (`start` for the real first scene), so seeded runs are never mistaken for "
    "whole-path runs; look at how the report object is built and add the field without changing existing fields. "
    "(4) Keep `test.setTimeout` logic as is.\n\n"
    "TESTS (new frontend/e2e/start-scene.test.js, node:test, no browser, no network): with a fake `page` object "
    "that records `route` registrations and a fake route object, assert: without options no session route is "
    "added; with `startScene` the handler is registered for the session POST, the body passed to `fallback` keeps "
    "`story_id` and adds `start_scene` and `start_state` (default thorough, and `bare` when asked); a non-POST or "
    "other path is passed through untouched; missing token throws. Keep helpers testable by exporting a small pure "
    "function (for example `sessionBodyWithStart(body, startScene, startState)`) rather than only closures. "
    "Prove nothing else broke with `cd frontend && node --test e2e/*.test.js src/*.test.js` and "
    "`node --check e2e/blind-player.spec.js e2e/helpers.js`."
)

BACKEND_OWNED = (
    r"storygame/runtime/entry_seed\.py|bench/core\.py|storygame/web_demo\.py|tests/test_start_scene_session\.py"
    r"|tests/shard_durations\.json|docs/testing-runbook/hosted-e2e\.md"
)
FRONTEND_OWNED = r"frontend/e2e/helpers\.js|frontend/e2e/blind-player\.spec\.js|frontend/e2e/start-scene\.test\.js"


def check(owned_re: str, body: str, patch: str, budget: int) -> str:
    return f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
[ -e frontend/node_modules ] || ln -s {REPO}/frontend/node_modules frontend/node_modules
git add -A -- storygame bench tests docs frontend/e2e
bad=$(git diff --cached --name-only | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
{body}
took=$(( $(date +%s) - start ))
echo "checks took $took s (budget {budget} s)"
[ "$took" -le {budget} ] || {{ echo "over the {budget} s budget"; exit 1; }}
git diff --cached > "$WORK/out/{patch}.patch"
test -s "$WORK/out/{patch}.patch"
"""


BACKEND_BODY = """.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_start_scene_session.py tests/test_web_demo.py $(ls tests/test_bench*.py)
PYFILES=$(git diff --cached --name-only | grep '\\.py$' || true)
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
if grep -rnE '^(from|import) bench' storygame; then echo "storygame imports bench"; exit 1; fi
grep -q 'start_scene' storygame/web_demo.py || { echo 'no start_scene in web_demo.py'; exit 1; }
grep -q '403' storygame/web_demo.py || { echo 'no 403 rejection path'; exit 1; }"""

FRONTEND_BODY = """(cd frontend && node --test e2e/*.test.js src/*.test.js)
node --check frontend/e2e/blind-player.spec.js
node --check frontend/e2e/helpers.js
grep -q 'start_scene' frontend/e2e/helpers.js || { echo 'no start_scene in helpers.js'; exit 1; }
grep -q 'E2E_BLIND_ENTRY' frontend/e2e/blind-player.spec.js || { echo 'no E2E_BLIND_ENTRY switch'; exit 1; }
grep -q 'seeded' frontend/e2e/blind-player.spec.js || { echo 'no seeded label'; exit 1; }"""

manifest = {
    "run_name": "start-scene-seeded-entry",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "backend-start-scene",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/runtime/entry_seed.py",
                "bench/core.py",
                "storygame/web_demo.py",
                "tests/test_start_scene_session.py",
                "tests/shard_durations.json",
                "docs/testing-runbook/hosted-e2e.md",
            ],
            "spec": BACKEND_SPEC,
            "check": check(BACKEND_OWNED, BACKEND_BODY, "backend-start-scene", 300),
            "expect_files": [],
            "verified": "start_scene seeds a later scene offline, is refused without the test token or in production, and bench still seeds identically.",
        },
        {
            "key": "frontend-seeded-entry",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": [
                "frontend/e2e/helpers.js",
                "frontend/e2e/blind-player.spec.js",
                "frontend/e2e/start-scene.test.js",
            ],
            "spec": FRONTEND_SPEC,
            "check": check(FRONTEND_OWNED, FRONTEND_BODY, "frontend-seeded-entry", 180),
            "expect_files": [],
            "verified": "The blind player enters later scenes through a seeded session, labels the run, and keeps a walk mode for comparison.",
        },
    ],
}
Path(__file__).with_name("round22a-start-scene-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
