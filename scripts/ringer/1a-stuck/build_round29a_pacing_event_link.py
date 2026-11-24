# ruff: noqa: E501
"""Round 29a: Step 2 task 2.2b, the typed pacing-event link (code half). Adds an optional `delivers` list to a pacing
beat (source, compiler, model, legacy converter, docs) and a pure validator `pacing_link_problems(package)`.
The story data (the 11 beats) and the loader wiring come in round 29b. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-29"
PY = ".venv/bin/python"

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""

OWNED = [
    "storygame/story_package/models.py",
    "storygame/story_source/c_scene.py",
    "storygame/story_source/l1_scene.py",
    "storygame/story_source/convert_scene.py",
    "storygame/story_package/pacing_links.py",
    "tests/test_pacing_links.py",
    "tests/shard_durations.json",
    "docs/markdown-story-authoring/pacing-and-incidents.md",
]
owned_re = "|".join(p.replace(".", r"\.") for p in OWNED)

SPEC = b.COMMON + (
    "You may edit ONLY: storygame/story_package/models.py, storygame/story_source/c_scene.py, storygame/story_source/l1_scene.py, "
    "storygame/story_source/convert_scene.py, storygame/story_package/pacing_links.py (new), tests/test_pacing_links.py (new), "
    "tests/shard_durations.json (add exactly one entry for the new test file, same format as its neighbours, value 2.0) and "
    "docs/markdown-story-authoring/pacing-and-incidents.md (one short paragraph). Do NOT edit any file under data/ (story source changes go through the story CLI in a later round). Nothing else.\n\n"
    "BACKGROUND. A pacing event is a scene `beats:` record (id, at_turn, when, sets, say, trailing, exit) compiled into `PacingEvent` (storygame/story_package/models.py). "
    "The outcome contract (factory/outcome_contract.py, read-only here) must know which knowledge a pacing event makes deliverable, because a reveal that the clock caused is a pressure event, not the player's progress. "
    "Today there is no typed link; the only connection is the facts: an event `sets` facts and a knowledge item that has no `earn_when` and no `action_evidence` is delivered by the runtime when it reads or commits those same facts. "
    "The owner decided to DECLARE the link in story source. Precedent for adding an optional beat field: commit 49d5b214 (`trailing`): see models.py `PacingEvent.trailing` (exclude_if keeps the default out of serialized packages), "
    "c_scene.py `build_events`, l1_scene.py `_check_beats` rules, convert_scene.py around the `trailing` line.\n\n"
    "PART 1, THE FIELD. Add an optional beat key `delivers`: a list of knowledge claim ids (strings). "
    "(a) models.py: `PacingEvent.delivers: tuple[str, ...] = Field(default=(), exclude_if=lambda value: not value)`; each id must match the same id pattern knowledge ids use; duplicates are rejected. A package that does not use the field must serialize byte for byte as before. "
    "(b) l1_scene.py `_check_beats`: accept `delivers` as a list of non-empty strings; reject any other shape with the same style of issue the neighbouring rules produce. "
    "(c) c_scene.py `build_events`: copy it into `PacingEvent`. (d) convert_scene.py: emit `delivers` in the beat record when non-empty (so the legacy converter round-trips it). "
    "(e) the docs file: one short paragraph, plain words, saying what `delivers` is for and that the validator checks it against the facts.\n\n"
    "PART 2, THE VALIDATOR. New module storygame/story_package/pacing_links.py with one public pure function `pacing_link_problems(package) -> list[str]` (empty list means clean; never mutates the package; story-agnostic, no story, scene or claim names in production code; standard library plus storygame.story_package.models only). Definitions: "
    "a PRESSURE ITEM is a knowledge item (`package.knowledge.knowledge`) with `earn_when is None`, no `action_evidence`, and `source.kind != 'scene_entry'`. "
    "An item's FACTS are the fact ids in its `requires` plus the fact ids in its `establishes` (every RouteOperation and FactPredicate has `fact_id`). An event's FACTS are the fact ids in its `effects`. "
    "A pressure item is LINKABLE to an event when the event's `scene_id` is in the item's `available_in_scenes` and the two fact sets intersect. Problems to report, one string each, each naming the event id and/or item id and saying what to change:\n"
    "1. a declared id (an event's `delivers`) names no knowledge item;\n"
    "2. a declared item is not a pressure item (it has `earn_when` or `action_evidence`, or is an entry item);\n"
    "3. a declared item is not available in the event's scene;\n"
    "4. a declared item shares no fact with the event's effects;\n"
    "5. a pressure item that is linkable to at least one event is declared by none of the events it is linkable to (the 'unlinked pacing-linked item').\n"
    "A pressure item with no linkable event is fine (bridges, resolutions and route-effect items are delivered by other routes). Problems are returned in a stable sorted order.\n\n"
    "TESTS, WRITE THEM FIRST in tests/test_pacing_links.py (hermetic, no network, no model; build small packages by loading the real one with `load_story_package(default_package_root())` from storygame.story_package.loader and storygame.story_package.default_root and then deriving modified copies with pydantic `model_copy(update=...)`; the models are frozen, so never assign): "
    "(1) a PacingEvent with no `delivers` serializes with no `delivers` key and an event with `delivers=('k_x',)` round-trips through model_dump/model_validate; duplicate ids are rejected; "
    "(2) the L1 beat check accepts a list of strings and rejects a string, a list holding a non-string, and a list holding an empty string (find the existing way the tests under tests/story_source/ run `_check_beats` or the L1 scene check and reuse it; read tests/story_source/ first); "
    "(3) compile: a minimal scene source dict with a beat carrying `delivers` compiles to a PacingEvent with that tuple (reuse an existing fixture or helper under tests/story_source/); "
    "(4) converter round trip through convert_scene when the event has `delivers`; "
    "(5) validator on the REAL unchanged package: the problems list is non-empty, every problem is of kind 5, and the set of unlinked pressure items it names has exactly 11 members; assert the 11 as a count and assert these three are among them: `k_supervisor_escorting`, `k_inspection_window_missed`, `k_purge_window_missed` (record the full list in NOTES.txt); "
    "(6) validator on a derived package where every event declares exactly the items the validator named: the problems list is empty; (7) one test per problem kind 1 to 4 on a derived package, asserting the problem text names the event id and item id; "
    "(8) the validator does not mutate the package (compare a model_dump before and after) and is deterministic across two calls.\n"
    "Then run the existing neighbours: tests/story_source, tests/test_trailing_pacing_events.py and any test file that imports PacingEvent (grep). If an OLD test pins behaviour this change deliberately changes, update it and say so in NOTES.txt (an old test file you edit must be added to NOTES.txt; but the ownership list above is a hard limit, so if an unlisted test needs a change, stop and report it in NOTES.txt instead).\n"
)

CHECK = (
    SETUP
    + f"""git add -A -- storygame tests docs
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/test_pacing_links.py tests/story_source tests/test_trailing_pacing_events.py tests/test_contract_scene.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 240 s)"
[ "$took" -le 240 ] || {{ echo "over the 240 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
{PY} -m json.tool tests/shard_durations.json > /dev/null
grep -q '"tests/test_pacing_links.py"' tests/shard_durations.json || {{ echo "tests/shard_durations.json lacks the new test file"; exit 1; }}
grep -nE "k_sl_|k_scene_|k_bridge|SL-[0-9]|\\b[123][A-C]\\b" storygame/story_package/pacing_links.py && {{ echo "story-specific ids in production code"; exit 1; }} || true
{PY} - <<'PYV'
from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import load_story_package
from storygame.story_package.pacing_links import pacing_link_problems
pkg = load_story_package(default_package_root())
p = pacing_link_problems(pkg)
assert len(p) == 11, (len(p), p)
text = "\\n".join(p)
for k in ("k_supervisor_escorting", "k_inspection_window_missed", "k_purge_window_missed"):
    assert k in text, k
dumped = pkg.model_dump_json()
assert '"delivers"' not in dumped, "an unused delivers field leaked into the serialized package"
print("validator names 11 unlinked pressure items on the unchanged package")
PYV
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/pacing-link.patch"
test -s "$WORK/out/pacing-link.patch"
"""
)

manifest = {
    "run_name": "factory-29a-pacing-event-link",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "pacing-link",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 500,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "A beat may declare `delivers`; the validator reports the 11 unlinked pressure items on the unchanged package and nothing on a fully declared one; an unused field leaves serialized packages unchanged.",
        }
    ],
}
Path(__file__).with_name("round29a-pacing-event-link-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
