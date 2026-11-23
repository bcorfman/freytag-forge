"""Round 24c: export the live story package in the shapes the frontend judging tools read."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-24"
OWNED = [
    "storygame/story_package/authoring_view.py",
    "tests/test_authoring_view.py",
    "tests/shard_durations.json",
]

SPEC = b.COMMON + (
    "You may edit ONLY: " + ", ".join(OWNED) + " (the first two are new files).\n\n"
    "BACKGROUND. Frontend judging tools (frontend/e2e/authored-spans.js, knowledge-available.js, "
    "roleplay-judge.test.js and the tools that import them) read the story through five flat legacy files "
    "(knowledge.yaml, handoffs.yaml, pacing.yaml, storylet-routes.yaml, plot.md) that no longer exist in "
    "data/stories/continuity-initiative/; the default story is now the compiled tree under source/ and is loaded by "
    "`storygame.story_package.loader.load_story_package(Path(root))` into a pydantic `StoryPackage`. The old files "
    "survive only as a FROZEN parity fixture in tests/fixtures/parity/continuity-initiative/legacy/ (use it to learn "
    "the SHAPES; its text is out of date, never read it at runtime). Task: build a Python exporter that projects the "
    "LIVE package into those legacy shapes, so the JavaScript can be repointed in the next round without changing "
    "its consumers or its inline test fixtures.\n\n"
    "BUILD `storygame/story_package/authoring_view.py` (shared code: story-agnostic, no story, scene or character "
    "names):\n"
    "  def authoring_view(package: StoryPackage) -> dict[str, object]  # JSON-serialisable, deterministic\n"
    "returning exactly these top-level keys, each in the legacy file's shape:\n"
    "  'knowledge'  : same shape as legacy knowledge.yaml (`package.knowledge.model_dump(mode='json')` already has "
    "the same top-level keys: facts, knowledge, scene_frames, schema_version).\n"
    "  'pacing'     : same shape as legacy pacing.yaml (`package.pacing.model_dump(mode='json')`: budget_seconds, "
    "ending, events, scenes, transitions).\n"
    "  'handoffs'   : {'deliveries': [...]} with the legacy delivery records (fact_id, cue_text, fallback_text and "
    "whatever other keys the legacy records carry that the JS reads) projected from `package.deliveries`.\n"
    "  'routes'     : legacy storylet-routes.yaml shape for the keys the JS reads: 'canonical_bridge_events' and "
    "'canonical_resolution_events' (the compiled package names them bridge_events and resolution_events), each "
    "event with its id, fallback_text and produces list (items with fact_id) plus the other keys the JS reads, and "
    "'storylets'. Read the frontend files to learn exactly which keys are read: grep for routePackage, routes., "
    "knowledgePackage, handoffs., pacing., frame. in frontend/e2e/*.js (read only).\n"
    "  'frames'     : the plot.md scene frames the JS reads, as {scene_id: {'scene_id', 'entry_text', "
    "'entry_variants': [{'text', ...}], 'bridge_text': {transition_id: text}}} built from each loaded scene's "
    "metadata (entry_text, entry_variants, bridge_text).\n"
    "Also add a module CLI: `python -m storygame.story_package.authoring_view STORY_ROOT [--out PATH]` that loads "
    "the package from STORY_ROOT and prints the JSON (or writes it to PATH), exit 0; non-existent root exits "
    "non-zero with a one-line message.\n\n"
    "TESTS (tests/test_authoring_view.py, hermetic, no network, fast): (1) against the default story root "
    "`data/stories/continuity-initiative`: top-level keys exactly the five above; knowledge top-level keys equal "
    "the frozen fixture's; every knowledge item with a delivery_text keeps it; routes has both canonical lists "
    "non-empty and each event has an id; frames has an entry_text for every scene that has one in the loaded "
    "package, equal to the scene metadata value; handoffs deliveries non-empty with fact_id; (2) shape check "
    "against the frozen fixture: for each of knowledge claim items, pacing events/transitions and route events, "
    "the set of keys the exporter emits is a superset of the keys the JavaScript reads (list those keys in the "
    "test as constants with a comment naming the JS file that reads them); (3) the result round-trips through "
    "json.dumps/json.loads and two calls return equal dicts; (4) the CLI via subprocess prints valid JSON for the "
    "default root and fails on a missing root. Register the new test file: run "
    "`.venv/bin/python scripts/regen_shard_durations.py --missing-only` and keep only the one new entry.\n\n"
    "Do NOT edit any JavaScript, any story data, or any existing test. Say in NOTES.txt which keys you found the "
    "JS reading and any compiled-versus-legacy difference you could not project."
)

OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_authoring_view.py tests/test_loader_source_dispatch.py tests/test_story_package_cache.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
.venv/bin/python -m storygame.story_package.authoring_view data/stories/continuity-initiative --out "$WORK/out/authoring-view.json"
.venv/bin/python - <<'PYV'
import json
d = json.load(open("{b.WORK}/out/authoring-view.json"))
assert sorted(d) == ["frames", "handoffs", "knowledge", "pacing", "routes"], sorted(d)
assert d["routes"]["canonical_bridge_events"], "no bridge events"
assert d["handoffs"]["deliveries"], "no deliveries"
assert any(f.get("entry_text") for f in d["frames"].values()), "no entry text"
print("view ok:", {{k: len(v) for k, v in d.items()}})
PYV
! .venv/bin/python -m storygame.story_package.authoring_view /nonexistent/root >/dev/null 2>&1 || {{ echo "missing root did not fail"; exit 1; }}
git diff --cached > "$WORK/out/authoring-view.patch"
test -s "$WORK/out/authoring-view.patch"
"""

manifest = {
    "run_name": "factory-24c-authoring-view",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "authoring-view",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The live package exports in the five legacy shapes; tests, ruff and the CLI pass.",
        }
    ],
}
Path(__file__).with_name("round24c-authoring-view-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
