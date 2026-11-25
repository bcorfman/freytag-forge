# ruff: noqa: E501
"""Round 34e: the hosted blind-player session start waits as long as a turn (control run 1B failed when a seeded session took 4.98 s against the default 5 s expect timeout)."""

import json
from pathlib import Path

FF = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-34e"

SPEC = (
    "You are an engineer on freytag-forge. Your current working directory IS a git worktree of the repo (detached at HEAD). Edit files here directly. "
    "NEVER git commit, NEVER call a model, NEVER use the network, never run `uv`, never run Playwright or any browser test. Write NOTES.txt (never committed) with any ambiguity and your choice.\n\n"
    "You may edit ONLY: frontend/e2e/helpers.js. Touch nothing else.\n\n"
    'PROBLEM (measured 2026-11-25 on staging). `startSceneSession` in frontend/e2e/helpers.js clicks New Session and then runs `await expect(page.locator("#status-line")).toContainText(...)` and `await expect(page.locator("#transcript")).not.toBeEmpty()` with Playwright\'s default 5 s expect timeout. '
    "A seeded session (`startScene` set) takes 3.5 to 5.0 s to create on staging, so a hosted blind-player run failed at its second replicate with the status line still reading 'Creating session...'. "
    "The same file already waits up to `TURN_TIMEOUT_MS` for slow server turns (for example `toBeEnabled({ timeout: TURN_TIMEOUT_MS })`).\n\n"
    "WHAT TO DO. Pass `{ timeout: TURN_TIMEOUT_MS }` to both of those expectations in `startSceneSession`, the same way the file's other waits do. Change nothing else. No new test is needed (the change only lengthens a browser wait); run `cd frontend && node --test src/*.test.js e2e/*.test.js` to confirm nothing else breaks."
)

CHECK = f"""set -e
WORK={WORK}
mkdir -p "$WORK/out"
[ -e frontend/node_modules ] || ln -s {FF}/frontend/node_modules frontend/node_modules
git reset -q
git add -A -- . ':(exclude)NOTES.txt'
git reset -q -- frontend/node_modules 2>/dev/null || true
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^frontend/e2e/helpers\\.js$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
grep -q 'toContainText(`Scene ${{hasStartScene ? options.startScene : "1A"}}`, {{ timeout: TURN_TIMEOUT_MS }})' frontend/e2e/helpers.js || {{ echo "status-line wait does not use TURN_TIMEOUT_MS"; grep -n 'status-line' frontend/e2e/helpers.js; exit 1; }}
grep -q 'locator("#transcript")).not.toBeEmpty({{ timeout: TURN_TIMEOUT_MS }})' frontend/e2e/helpers.js || {{ echo "transcript wait does not use TURN_TIMEOUT_MS"; grep -n 'transcript' frontend/e2e/helpers.js; exit 1; }}
n=$(git diff --cached --numstat | awk '{{s+=$1+$2}} END {{print s+0}}')
echo "changed lines: $n"
[ "$n" -le 4 ] || {{ echo "more than the two expectations changed"; git diff --cached; exit 1; }}
(cd frontend && PATH={FF}/.venv/bin:$PATH node --test src/*.test.js e2e/*.test.js) > "$WORK/out/node-test.txt" 2>&1 || {{ grep -nE "✖|ℹ fail" "$WORK/out/node-test.txt" | head -20; exit 1; }}
grep -E "ℹ (pass|fail)" "$WORK/out/node-test.txt"
git diff --cached > "$WORK/out/session-start-timeout.patch"
test -s "$WORK/out/session-start-timeout.patch"
"""

manifest = {
    "run_name": "qual-controls",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": FF,
    "tasks": [
        {
            "key": "session-start-timeout",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 300,
            "ownership": ["frontend/e2e/helpers.js"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "A seeded hosted session start waits up to TURN_TIMEOUT_MS instead of 5 s.",
        }
    ],
}
Path(__file__).with_name("round34e-session-start-timeout-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
