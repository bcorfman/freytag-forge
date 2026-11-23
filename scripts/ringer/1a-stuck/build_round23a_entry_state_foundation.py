"""Round 23a: worldkeeper state export/import/invariants and a deterministic canonical entry path."""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-23"
REPO = "/home/bcorfman/dev/ringer-work/pr-seeded-entry"
MAIN = "/home/bcorfman/dev/freytag-forge"

COMMON = (
    "You are an engineer. Your current working directory IS a git worktree of the freytag-forge repository "
    "(detached at HEAD). Edit files here directly. NEVER git commit, never touch any other checkout, never run `uv`, "
    "NEVER call a model (not `claude`, not `codex`), NEVER use the network, never run `python -m bench run`, never "
    f"write factory/state/. FIRST run: [ -e .venv ] || ln -s {MAIN}/.venv .venv . Environment for every command: "
    "`export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): "
    "`.venv/bin/python -m ruff check <files>` / `.venv/bin/python -m ruff format <files>` (line length 120, "
    "Python 3.12). Never pass --cov to pytest. Run tests as "
    "`.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 <files>`. Tests must be hermetic (no network, no real "
    "model). Shared code must stay story-agnostic (no story, scene or character names in production code; tests "
    "may use the repository's real story package and must also cover a synthetic package). ARCHITECTURE RULE "
    "(AGENTS.md, firm): world-model logic, meaning anything that reads or changes only world state, is a `World` "
    "method in packages/worldkeeper with its tests in packages/worldkeeper/tests; `storygame` only adapts and calls "
    "it. If an OLD test pins behaviour this change deliberately changes, update it and say so in NOTES.txt. Write "
    "NOTES.txt (worktree root, never committed) listing every ambiguity and your choice. Read first: AGENTS.md, "
    "docs/contributor-guide.md, docs/world-model-grounding.md. "
)

WHY = (
    "BACKGROUND. Scenes can now be entered without playing the preceding scenes (hosted `start_scene`, see "
    "storygame/runtime/entry_seed.py). Measured: `bare` entry (scene entry fact and placements only) leaves about 110 "
    "story facts unset and every earned item hidden at scene 3B; `thorough` entry (a persona that earns everything "
    "optional) is path-dependent and also not a state a real player has. The fix is a canonical, versioned entry "
    "state per scene: the world after a deterministic player earns only what the route requires. "
)

WORLD_SPEC = COMMON + WHY + (
    "\n\nYou may edit or create ONLY: packages/worldkeeper/src/worldkeeper/model.py, "
    "packages/worldkeeper/src/worldkeeper/state_export.py (new), packages/worldkeeper/src/worldkeeper/__init__.py, "
    "packages/worldkeeper/tests/test_state_export.py (new).\n\n"
    "TASK. Give `World` a way to export its world-only state, load it back, and check entry invariants. All three "
    "are `World` methods (implementation may live in the new module and be called from thin methods):\n"
    "1. `World.export_state() -> dict`: deterministic, JSON-safe, sorted, covering EVERY `wk_*` fact the world "
    "keeps (parent, relation, hidden, axis, name, alias, owner, companion, moved, condition, unplaced, status, "
    "place text, kind, fixed, seeded and any other `wk_` predicate used in model.py or incidental.py). Shape: "
    "{\"schema\": 1, \"facts\": [{\"predicate\", \"subject\", \"object\", \"value\"}, ...]} sorted by "
    "(predicate, subject, object, value). The FactBackend protocol has no enumeration method, so enumerate by an "
    "explicit module-level tuple `WORLD_PREDICATES` of every wk_ predicate. Add a drift test: build a World on a "
    "MemoryBackend, run representative operations (seed, place, move, take or hold, hide/reveal, set an axis, add "
    "an alias, companion, anything else the public API offers), then assert that every `wk_*` fact in the backend "
    "(`MemoryBackend.matching_all`) appears in the export, so a future wk_ predicate that is not listed fails the "
    "test.\n"
    "2. `World.import_state(state: dict) -> OpResult`: replaces the world's `wk_*` facts with the snapshot's. It "
    "refuses (OpResult(False, reason), changing nothing) a snapshot with an unknown schema number, an unknown "
    "predicate, or a subject entity the schema does not declare. Import then export round-trips to an identical "
    "dict (test it, including importing into a World that already had other state).\n"
    "3. `World.entry_problems(protagonist_id, location_id) -> tuple[str, ...]`: plain-words invariant violations, "
    "empty when sound. Check: every entity that has a parent has exactly one `wk_parent` and the parent exists; no "
    "parent cycle; the protagonist exists and its area chain contains `location_id`; no item held by the "
    "protagonist (directly or through its container chain) is still marked hidden; every `wk_axis` value is one "
    "of the axis's declared poles; every companion subject and object exists. Use the real accessors (`chain`, "
    "`holder`, `holds`, `axis_definitions`, `exists`) rather than re-deriving.\n"
    "4. A pure function `diff_states(before: dict, after: dict) -> dict` in state_export.py with keys `added`, "
    "`removed`, `changed` (facts keyed by predicate and subject) for readable review output; export it from "
    "`worldkeeper/__init__.py`.\n\n"
    "TESTS (packages/worldkeeper/tests/test_state_export.py, hermetic, whole file under 10 s): build schemas the "
    "way the existing tests in that folder do (study test_holds.py and test_can_represent.py). Cover the drift "
    "test, round trip, refusals (each of the three), each invariant (a passing and a failing case each), "
    "deterministic ordering (two worlds built in different operation orders but equal state export identically), "
    "and diff_states. Do not assert exact message strings beyond that the right entity id appears. Run "
    "`.venv/bin/python -m pytest -q -p no:cacheprovider packages/worldkeeper/tests tests/test_world_model.py`."
)

PATH_SPEC = COMMON + WHY + (
    "\n\nYou may edit or create ONLY: storygame/personas.py, storygame/runtime/entry_seed.py, "
    "tests/test_canonical_entry_path.py (new), tests/shard_durations.json.\n\n"
    "TASK. Add a deterministic CANONICAL path: a player who earns only what the route requires, so the state at "
    "each scene's entry is the story's own minimum, not a thorough sweep. Read storygame/personas.py "
    "(`_select_thorough`, `_run`, `PERSONAS`, `run_persona`), storygame/story_package/obligations.py "
    "(`required_storylet_ids`: the storylets the route events and bridge events need, with prerequisites), "
    "storygame/runtime/entry_seed.py and tests/test_persona_escalation.py first.\n"
    "1. In personas.py add persona `canonical` (a short plain description like the others) and "
    "`_select_canonical(package, state, candidates)`: among candidates that survive the turn "
    "(`_candidate_survives_turn`), choose only those whose storylet is in `required_storylet_ids(package)`, ranked "
    "exactly as `_select_thorough` ranks (bridge-missing facts first, then id) restricted to that set; when none "
    "qualifies return None (the player waits, so pacing and bridge events advance). Wire it into `_run` the way "
    "thorough and wrong_lead are wired, without changing their behaviour. No story, scene or fact names in the "
    "code.\n"
    "2. In entry_seed.py give `advance_state_to_scene(package, state, scene_id, persona='thorough')` a `persona` "
    "parameter (default keeps today's behaviour; the selector is chosen by name, `thorough` or `canonical`; any "
    "other name raises ValueError) and add `canonical_path_report(package) -> list[dict]`: starting from "
    "`RuntimeState.bootstrap(package)`, advance scene by scene with the canonical persona and return one row per "
    "hop `{from_scene, to_scene, turns, earned, transition_cause, storylets_delivered}` where `earned` is true "
    "only when the engine records an earned transition (read how the runtime records the transition cause and the "
    "persona report's `turns_to_exit`; a transition forced by the handoff timer is NOT earned). The report must "
    "never raise just because a hop was forced: it records it. If the canonical player cannot reach a scene at "
    "all within `_turn_cap`, the row says `reached: false` instead of raising.\n\n"
    "TESTS (new tests/test_canonical_entry_path.py, hermetic, whole file under 40 s): (a) canonical path reaches "
    "every scene of the repository's real story package in order; (b) it is deterministic: two runs give identical "
    "`state.facts` (compare the sorted tuples of every asserted fact) at every scene entry; (c) the canonical "
    "state at each scene is a subset, by true story facts, of the thorough state at the same scene "
    "(`canonical <= thorough` on true non-wk facts) and strictly smaller for at least one scene; (d) "
    "`canonical_path_report` returns one row per hop with the keys above; (e) an unknown persona name raises "
    "ValueError; (f) `thorough` behaviour is unchanged (an existing persona test still passes, and the default "
    "call equals the old result). IMPORTANT: do not hide a failure. Whatever the real earned/forced result is for "
    "each hop, assert only the report's SHAPE and write the real per-hop table into NOTES.txt (scene, turns, "
    "earned, cause) so a reviewer can read it. Add the test file to tests/shard_durations.json with "
    "`.venv/bin/python scripts/regen_shard_durations.py --missing-only` (never `uv`; by hand with a measured "
    "duration rounded up if that needs network). Run tests/test_canonical_entry_path.py "
    "tests/test_persona_escalation.py tests/test_start_scene_session.py and the bench seeding tests "
    "(`ls tests/test_bench*.py`)."
)

WORLD_OWNED = (
    r"packages/worldkeeper/src/worldkeeper/model\.py|packages/worldkeeper/src/worldkeeper/state_export\.py"
    r"|packages/worldkeeper/src/worldkeeper/__init__\.py|packages/worldkeeper/tests/test_state_export\.py"
)
PATH_OWNED = (
    r"storygame/personas\.py|storygame/runtime/entry_seed\.py|tests/test_canonical_entry_path\.py"
    r"|tests/shard_durations\.json"
)


def check(owned_re: str, body: str, patch: str, budget: int) -> str:
    return f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {MAIN}/.venv .venv
git add -A -- storygame bench tests packages docs
bad=$(git diff --cached --name-only | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
{body}
took=$(( $(date +%s) - start ))
echo "checks took $took s (budget {budget} s)"
[ "$took" -le {budget} ] || {{ echo "over the {budget} s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only | grep '\\.py$' || true)
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/{patch}.patch"
test -s "$WORK/out/{patch}.patch"
"""


WORLD_BODY = """.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 packages/worldkeeper/tests tests/test_world_model.py
grep -q 'def export_state' packages/worldkeeper/src/worldkeeper/model.py || { echo 'World.export_state missing'; exit 1; }
grep -q 'def import_state' packages/worldkeeper/src/worldkeeper/model.py || { echo 'World.import_state missing'; exit 1; }
grep -q 'def entry_problems' packages/worldkeeper/src/worldkeeper/model.py || { echo 'World.entry_problems missing'; exit 1; }
grep -q 'WORLD_PREDICATES' packages/worldkeeper/src/worldkeeper/state_export.py || { echo 'WORLD_PREDICATES missing'; exit 1; }"""

PATH_BODY = """.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_canonical_entry_path.py tests/test_persona_escalation.py tests/test_start_scene_session.py $(ls tests/test_bench*.py)
if grep -nEi "'(1A|1B|1C|2A|2B|2C|3A|3B|3C)'|\\"(1A|1B|1C|2A|2B|2C|3A|3B|3C)\\"" storygame/personas.py storygame/runtime/entry_seed.py; then echo 'scene names in production code'; exit 1; fi
grep -q '_select_canonical' storygame/personas.py || { echo '_select_canonical missing'; exit 1; }
grep -q 'canonical_path_report' storygame/runtime/entry_seed.py || { echo 'canonical_path_report missing'; exit 1; }"""

manifest = {
    "run_name": "entry-state-foundation",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "worldkeeper-state-export",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "packages/worldkeeper/src/worldkeeper/model.py",
                "packages/worldkeeper/src/worldkeeper/state_export.py",
                "packages/worldkeeper/src/worldkeeper/__init__.py",
                "packages/worldkeeper/tests/test_state_export.py",
            ],
            "spec": WORLD_SPEC,
            "check": check(WORLD_OWNED, WORLD_BODY, "worldkeeper-state-export", 300),
            "expect_files": [],
            "verified": "World exports, imports and checks its world-only state; a drift test catches any unlisted wk_ predicate.",
        },
        {
            "key": "canonical-entry-path",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/personas.py",
                "storygame/runtime/entry_seed.py",
                "tests/test_canonical_entry_path.py",
                "tests/shard_durations.json",
            ],
            "spec": PATH_SPEC,
            "check": check(PATH_OWNED, PATH_BODY, "canonical-entry-path", 300),
            "expect_files": [],
            "verified": "A deterministic required-only player reaches every scene and reports each hop as earned or forced.",
        },
    ],
}
Path(__file__).with_name("round23a-entry-state-foundation-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
