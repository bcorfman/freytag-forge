# ruff: noqa: E501
"""Round 29c: Step 2 task 2.2b. The pacing-only replay: which pacing events would fire this turn if the player did
nothing, and the knowledge they deliver (`null_grounding_ids`). Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-29c"
PY = ".venv/bin/python"

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""

OWNED = ["storygame/runtime/pacing_replay.py", "tests/test_pacing_replay.py", "tests/shard_durations.json"]
OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)

SPEC = b.COMMON + (
    "You may edit ONLY: storygame/runtime/pacing_replay.py (new), tests/test_pacing_replay.py (new) and tests/shard_durations.json (one entry for the new test file, same format as its neighbours, value 2.0). "
    "You may READ storygame/runtime/engine.py but must NOT edit it. Nothing else.\n\n"
    "BACKGROUND. The outcome contract (tests/fixtures/outcome_contract/README.md, read it; and .plans/qualification/null-grounding-decision.md section 'Contract wording') must tell a reveal the player earned from one the clock caused. "
    "Decision (owner, 2026-11-23): PACING-ONLY REPLAY. Before a turn's pacing pass, replay only that pass on a COPY of the pre-command state: the same turn advance and none of the command's effects. "
    "Every PACING EVENT (`package.pacing.events`) that fires in the replay is a pressure event; the knowledge it makes deliverable is the union of those events' `delivers` lists (a tuple of knowledge ids on PacingEvent, added in round 29a) and becomes `null_grounding_ids`. "
    "Storylets the clock merely opens (`package.storylet_routes.storylets`) are NEVER null grounding. A pacing event that fires only because the command changed a fact will not fire in the replay (its `when` is false on the pre-command facts), so it is the world answering the player and stays progress. No model call is made.\n\n"
    "WHAT A TURN DOES (read RuntimeEngine in storygame/runtime/engine.py): `turn_index += 1`, then the pre-narration `_activate_pacing(realize_complications=True, defer_guarded_events=True)` (it skips trailing events and events whose `when` holds an `equals is False` predicate), then the provider narrates, then the post-commit lifecycle runs `_activate_pacing(realize_complications=True)` again. "
    "The replay copies only that pacing work: on a scratch copy advance `turn_index` by one, run the pre-narration pass, then the post-commit pass (the same `_activate_pacing` code, so the rule is not re-implemented), and report which `package.pacing.events` ids newly entered `fired_event_ids`.\n\n"
    "BUILD storygame/runtime/pacing_replay.py: a frozen dataclass or pydantic model `PacingReplay` with `fired_event_ids: tuple[str, ...]` (package order) and `null_grounding_ids: tuple[str, ...]` (union of `delivers` of the fired events, package order, no duplicates), and one public function `replay_pacing(engine) -> PacingReplay`. "
    "HARD REQUIREMENTS: it must not change the live engine in any way (state, facts, fired and active event ids, last_turn_delivery, staged cue and handoff fields, turn records, attempts, provider, capture, projector), must not call the provider or the capture, and must be deterministic. "
    "A transition-firing pacing event calls `apply_proposal` on the scratch state; that must not escape either. Copy with the pattern storygame/runtime/entry_snapshots.py already uses (look at lines near 109-124) or `copy.deepcopy` of the state with the story package shared through the `memo` argument (the package is immutable and large; never deep-copy it), or build a scratch `RuntimeState` from `state.snapshot()`; choose what is simplest and proven by your tests, and state it in NOTES.txt. "
    "Story-agnostic code only (no story, scene, character or claim names in production code). Say in NOTES.txt why this is a runtime adapter and not a `World` method in packages/worldkeeper (it reads package pacing events, not only world state).\n\n"
    "TESTS, WRITE THEM FIRST in tests/test_pacing_replay.py (hermetic: no network, no model, no real provider; follow how tests/test_trailing_pacing_events.py builds a RuntimeEngine with a fake provider and how it loads `data/stories/continuity-initiative`; you may also use `compiled_story_copy` and `patch_source` from tests/story_source/helpers.py; read both first): "
    "(1) NO SIDE EFFECTS: build an engine in a scene one turn before a pacing event's `at_turn`, take `state.snapshot()` (and a dump of every field the replay might touch), call `replay_pacing`, and assert the snapshot and those fields are unchanged and the provider was called zero times; "
    "(2) FIRES ON TIME: in the real package scene 2A with `turns_since_entry` one below the `at_turn` of event `inspection_window_2a` and its `when` satisfied, the replay's `fired_event_ids` contains that id; one turn earlier it does not; "
    "(3) DELIVERS: on a package copy where that event has `delivers=('k_inspection_window_missed',)` (derive with pydantic `model_copy(update=...)` on the frozen models, or patch the source copy), `null_grounding_ids` equals ('k_inspection_window_missed',); with no `delivers` it is empty while `fired_event_ids` still lists the event; "
    "(4) CLOCK-OPENED STORYLETS ARE NOT NULL GROUNDING: at a state where a storylet is clock-open, no storylet id or storylet knowledge id appears in either field; "
    "(5) THE COMMAND'S OWN FACT: pick or build (by patching the source copy) a pacing event whose `when` needs a fact that is false before the command; in the replay it is absent; after you assert that fact on the live state it is present; "
    "(6) PARITY: play one real turn with the fake provider on a fresh engine and compare: every `package.pacing.events` id that newly fired during the real turn on a no-effect command equals the replay's `fired_event_ids` computed just before that turn (run the replay on an identical second engine so the first stays untouched); "
    "(7) TRANSITION EVENT: if a pacing event with a `transition_id` exists, the replay reports it without moving the live scene. If none can be reached cheaply, skip nothing silently: say so in NOTES.txt and add a package-copy test with such an event. "
    "(8) calling twice returns equal results.\n"
    "Run the tests; also run tests/test_trailing_pacing_events.py and tests/test_engine*.py to confirm nothing else moved (you edit no existing file)."
)

CHECK = (
    SETUP
    + f"""git add -A -- storygame tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/test_pacing_replay.py tests/test_trailing_pacing_events.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 240 s)"
[ "$took" -le 240 ] || {{ echo "over the 240 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
grep -q '"tests/test_pacing_replay.py"' tests/shard_durations.json || {{ echo "tests/shard_durations.json lacks the new test file"; exit 1; }}
{PY} -m json.tool tests/shard_durations.json > /dev/null
grep -nE "k_sl_|k_scene_|k_bridge|SL-[0-9]|\\b[123][A-C]\\b|inspection|kristin" storygame/runtime/pacing_replay.py && {{ echo "story-specific names in production code"; exit 1; }} || true
git diff --cached --name-only | grep -q "storygame/runtime/engine.py" && {{ echo "engine.py must not change"; exit 1; }} || true
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/pacing-replay.patch"
test -s "$WORK/out/pacing-replay.patch"
"""
)

manifest = {
    "run_name": "factory-29c-pacing-replay",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "pacing-replay",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2700,
            "check_timeout_s": 500,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "replay_pacing reports the pacing events that would fire with no command and their delivered knowledge, without touching the live engine, matching a real no-effect turn.",
        }
    ],
}
Path(__file__).with_name("round29c-pacing-replay-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
