"""Round 24d: repoint the frontend judging tools at the live story through the authoring view."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-24"
OWNED = [
    "frontend/e2e/story-view.js",
    "frontend/e2e/story-view.test.js",
    "frontend/e2e/authored-spans.js",
    "frontend/e2e/knowledge-available.js",
    "frontend/e2e/roleplay-judge.test.js",
    "frontend/e2e/package-clock.test.js",
    "frontend/e2e/authored-spans.test.js",
    "frontend/e2e/knowledge-available.test.js",
    "frontend/e2e/judge-journeys.test.js",
    "frontend/e2e/attribution-audit.test.js",
    "frontend/e2e/scene-partition.test.js",
]

SPEC = b.COMMON + (
    "You may edit ONLY these files under frontend/e2e/: " + ", ".join(p.removeprefix("frontend/e2e/") for p in OWNED)
    + " (story-view.js and story-view.test.js are new). Never touch Python, story data or other JavaScript.\n\n"
    "BACKGROUND. Seven node test files fail on main: attribution-audit, authored-spans, judge-journeys, "
    "knowledge-available, roleplay-judge, scene-partition (they read data/stories/continuity-initiative/knowledge.yaml, "
    "handoffs.yaml, pacing.yaml, storylet-routes.yaml and plot.md, which moved to a frozen parity fixture when the "
    "default story became the compiled source/ tree) and package-clock (a hard-coded event list is out of date). "
    "These tools also back the hosted canon judge (@llm-canon), which must judge the LIVE story, so pointing them "
    "at the frozen fixture is NOT allowed. A Python exporter now exists: "
    "`.venv/bin/python -m storygame.story_package.authoring_view data/stories/continuity-initiative` prints one JSON "
    "object with keys knowledge, pacing, handoffs, routes, frames, each in the legacy file's shape (knowledge = "
    "knowledge.yaml, pacing = pacing.yaml, handoffs = {deliveries}, routes = storylet-routes.yaml with "
    "canonical_bridge_events and canonical_resolution_events, frames = the plot.md scene frames keyed by scene id). "
    "Run it once yourself and read the JSON before coding.\n\n"
    "STEP 0. Run `[ -e frontend/node_modules ] || ln -s /home/bcorfman/dev/freytag-forge/frontend/node_modules "
    "frontend/node_modules` (do not stage it). Baseline: `cd frontend && node --test e2e/*.test.js src/*.test.js`.\n\n"
    "STEP 1: new frontend/e2e/story-view.js exporting `loadAuthoringView(root)` (root defaults to the repository "
    "root, two levels above frontend/e2e). It runs the exporter with child_process.spawnSync (no shell): python = "
    "process.env.FREYTAG_PYTHON, else <root>/.venv/bin/python if it exists, else python3; env gets PYTHONPATH = "
    "<root>:<root>/packages/worldkeeper/src appended to any existing value; cwd = root; args "
    "['-m','storygame.story_package.authoring_view','data/stories/continuity-initiative']; maxBuffer 64 MB. It "
    "parses stdout as JSON, caches the result per root in a Map for the life of the process, and on a non-zero "
    "exit or invalid JSON throws an Error whose message names the command, the exit status and the last 400 "
    "characters of stderr. Add story-view.test.js: loads the real view, asserts the five keys, asserts a second "
    "call returns the same cached object, asserts a bad FREYTAG_PYTHON gives the descriptive error.\n\n"
    "STEP 2: change the three readers to use it, keeping every exported function name, signature and return shape: "
    "authored-spans.js `loadAuthoredText(root)` (replace parseYaml/parsePlot and the five file reads with the view's "
    "knowledge, handoffs, pacing, routes and frames; frames is already a Map-able object keyed by scene id), "
    "knowledge-available.js `loadCanonSources(root)` (knowledgePackage = view.knowledge, routePackage = view.routes), "
    "and the one knowledge.yaml read in roleplay-judge.test.js (line ~188). Remove imports that become unused. If "
    "another owned test file still reads a legacy file path, fix it the same way.\n\n"
    "STEP 3: package-clock.test.js 'loads the real package and resolves turn milestones' fails only because the "
    "expected eventOrder list lacks 'drawer_gap_returns_1a' (the real pacing now has it between "
    "'home_search_narrows_1a' and 'pursuit_1b'). Add it in that position after confirming from the failing output "
    "that nothing else differs; do not weaken any assertion.\n\n"
    "STEP 4: if any other assertion in the six judging test files fails because the live story has changed since "
    "those tests were written (a count, an id, a text), fix the assertion to the live value ONLY when the new value "
    "is clearly the same kind of fact; do NOT delete or loosen assertions, and list every such change with its old "
    "and new value in NOTES.txt for review. If a failure looks like a real bug in a reader rather than a stale pin, "
    "stop and describe it in NOTES.txt instead of patching around it.\n\n"
    "Finish with `cd frontend && node --test e2e/*.test.js src/*.test.js`: all tests pass, none skipped by you."
)

owned_re = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
[ -e frontend/node_modules ] || ln -s {b.REPO}/frontend/node_modules frontend/node_modules
git add -A -- frontend/e2e
bad=$(git diff --cached --name-only | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
( cd frontend && node --test e2e/*.test.js src/*.test.js 2>&1 | tail -25 ) > "$WORK/out/node-tests.txt"
cat "$WORK/out/node-tests.txt"
grep -Eq '^(# |ℹ )fail 0' "$WORK/out/node-tests.txt" || {{ echo "node tests failed"; exit 1; }}
took=$(( $(date +%s) - start ))
echo "node tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
! git diff --cached | grep -E '^\\+.*(tests/fixtures/parity|legacy/)' || {{ echo "reads the frozen fixture"; exit 1; }}
! grep -rnE 'knowledge\\.yaml|handoffs\\.yaml|storylet-routes\\.yaml|plot\\.md' frontend/e2e/authored-spans.js frontend/e2e/knowledge-available.js frontend/e2e/roleplay-judge.test.js || {{ echo "legacy file read remains"; exit 1; }}
git diff --cached > "$WORK/out/frontend-story-view.patch"
test -s "$WORK/out/frontend-story-view.patch"
"""

manifest = {
    "run_name": "factory-24d-frontend-story-view",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": "/home/bcorfman/dev/ringer-work/pr-frontend",
    "tasks": [
        {
            "key": "frontend-story-view",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "All frontend node tests pass and the judging tools read the live story through the authoring view.",
        }
    ],
}
Path(__file__).with_name("round24d-frontend-story-view-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
