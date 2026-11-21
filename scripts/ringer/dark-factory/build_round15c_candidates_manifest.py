# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 15c: the blind-player report records the reveal candidates the engine offered. FREE: no model call, no network, no billed run.

Three parallel Codex tasks with disjoint files, joined by one contract:
  1. py-engine   - the attempt bundle's `reveal_selection` records `shortlist_ids`.
  2. js-report   - the blind-player turn log copies them to `candidates_offered` and `matched_candidate`.
  3. py-station  - station 7 builds its triage packets from those two keys.
Usage: build_round15c_candidates_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-station7-candidates"

ENGINE_OWNED = [
    "storygame/runtime/attempt_bundle.py",
    "storygame/runtime/engine.py",
    "storygame/runtime/cloudflare.py",
    "tests/test_attempt_bundle.py",
]
JS_OWNED = ["frontend/e2e/blind-player.js", "frontend/e2e/blind-player.test.js"]
STATION_OWNED = [
    "factory/stations/live_playtest.py",
    "tests/test_factory_live_playtest.py",
    "tests/fixtures/factory/blind_player_report_small.json",
]

CONTRACT = """THE SHARED CONTRACT (all three tasks; do not change it).
1. Engine. `RevealSelection` (attempt bundle `reveal_selection`) gets one new field, `shortlist_ids: tuple[str, ...] = ()` (serialised as a JSON list): the ids of the eligible reveal candidates the semantic matcher was offered on that turn, in the order offered, at most 6 (the same candidates that `shortlist_size` counts). It is `[]` whenever no shortlist was built (exact match, no eligible action, semantic fallback off). `shortlist_size == len(shortlist_ids)` always. The bundle `schema_version` stays 1 (the field is additive with a default).
2. Report. Each turn in the blind-player report's `turns` list (the `turnLog` output) gets two keys: `candidates_offered` (list of strings) and `matched_candidate` (string or null). `matched_candidate` is `attempt_bundle.reveal_selection.matched` (null when absent). `candidates_offered` is `reveal_selection.shortlist_ids` with the matched id appended when it is not already in the list; no duplicates, order kept. A turn with no bundle, or an old bundle without `shortlist_ids`, gets `[]` plus the matched id if there is one.
3. Station 7. A triage packet's `candidates_offered` is the turn's `candidates_offered` list (strings only) and its `matched_candidate` is the turn's `matched_candidate`, falling back to `semantic_match.matched` when the key is absent. An OLD report (turn has neither key) keeps today's behaviour exactly: a reported semantic match becomes `matched_candidate` and `candidates_offered = [matched]`. A NEW report (the key `candidates_offered` is present, even when empty) is trusted as is, so a stuck turn whose list is empty still has no candidates."""

ENGINE_SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. The hosted blind-player report records, per turn, `attempt_bundle.reveal_selection` = outcome, matched, `universe_size` and `shortlist_size` but not WHICH candidates were offered, so the dark factory cannot tell what a stuck turn was matched against. Read `storygame/runtime/attempt_bundle.py` (`RevealSelection`), `storygame/runtime/engine.py` around the `RevealSelection(` construction (search `raw_reveal_selection`) and `storygame/runtime/cloudflare.py` (search `last_reveal_selection`, especially `_semantic_authored_handoff`, where `shortlist_size` is set from the eligible candidates) and `tests/test_attempt_bundle.py` first.

@CONTRACT@

BUILD (point 1 only). Add `shortlist_ids` to `RevealSelection`. In `cloudflare.py` record the ids of exactly the candidates that `shortlist_size` counts into `last_reveal_selection["shortlist_ids"]` (a list of strings), in the same place and with the same cap; every place that initialises or resets `last_reveal_selection` gets `"shortlist_ids": []`. In `engine.py` pass it into `RevealSelection(...)`, tolerating a provider dict without the key (older or fake providers) and any non-string entries (drop them). Do not change which candidates are offered, the order, the cap, the matcher, any prompt, any outcome or any other bundle field. Keep `shortlist_size` as is.

TESTS in `tests/test_attempt_bundle.py` (extend the existing file; no new test file): the model serialises `shortlist_ids` and defaults to an empty tuple; an old bundle JSON without the field still validates; the engine passes ids through from a provider dict, tolerates a provider without the key and drops a non-string entry; and one test that drives the real `_semantic_authored_handoff` path of the Cloudflare provider with a stub `semantic_ask` that refuses, on a small eligible set, and asserts `last_reveal_selection["shortlist_ids"]` equals the eligible ids in order and its length equals `shortlist_size`. Look at how `tests/test_reveal_universe.py` and `tests/test_established_reveal_match.py` build such a provider and reuse that style (read them; do not edit them). New tests run in under 10 seconds.

HARD LIMITS. Edit only the four files above. In `engine.py` and `cloudflare.py` touch only the lines needed for this field. Never edit `factory/`, `frontend/`, `data/`, `bench/` or any other file and add no dependencies. Write NOTES_15C_ENGINE.txt (worktree root, never committed) listing every ambiguity and your choice."""

JS_SPEC = """You are a JavaScript engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, NEVER call a model, NEVER use the network, NEVER run playwright, `npm run test:e2e` or the bench. FIRST run: [ -e frontend/node_modules ] || ln -s @REPO@/frontend/node_modules frontend/node_modules . Run tests with `cd frontend && node --test e2e/blind-player.test.js e2e/merge-blind-player.test.js`.

BACKGROUND. `turnLog` in `frontend/e2e/blind-player.js` produces the per-turn records of the saved blind-player report from the full turn records, which carry `attempt_bundle`. Read `turnLog`, `turnRecord`, `analyseRun` and their tests first.

@CONTRACT@

BUILD (point 2 only). In `turnLog`, add `candidates_offered` and `matched_candidate` to every record exactly as the contract says, derived from `attempt_bundle.reveal_selection` (be defensive: a missing or malformed bundle, a non-array `shortlist_ids`, non-string entries, all give the safe default, never a throw). Do not change any other key of the record, the analysis, the aggregation or the markdown. If another function in your file copies or whitelists per-turn keys so that the new keys would be lost on the way to the saved report, fix that too.

TESTS in `blind-player.test.js`: a bundle with `shortlist_ids` ["a","b"] and matched null gives ["a","b"] and null; matched "b" gives ["a","b"] and "b"; matched "c" (not in the list) gives ["a","b","c"] and "c"; an old bundle without `shortlist_ids` and matched "k" gives ["k"] and "k"; no bundle and a rejected turn give [] and null; a malformed `shortlist_ids` (string, numbers, null) gives the safe default; the existing `turnLog` expectation tests still pass (update their expected objects only to add the two new keys). Whole files must pass.

HARD LIMITS. Edit only the two files above. Never edit `factory/`, `storygame/`, `tests/`, `bench/`, `frontend/package.json` or any other file and add no dependencies. Never log environment values. Write NOTES_15C_JS.txt (worktree root, never committed) listing every ambiguity and your choice."""

STATION_SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. `factory/stations/live_playtest.py` turns a blind-player report into one triage packet per failing turn (`_packet_for_turn`, `report_to_packets`). Today a packet's `candidates_offered` is always empty because the report had no candidate list, except for a conservative surrogate (`[matched]`) when `semantic_match.matched` is set. `factory/stations/triage.py` routes on it (rule R2 stuck with no candidates, R3 stuck with candidates and no match, R5 matched but did not commit); READ triage and its tests, never edit them. Read `tests/test_factory_live_playtest.py` and the fixture report first.

@CONTRACT@

BUILD (point 3 only). Change `_packet_for_turn` exactly as the contract says: a NEW report trusts the turn's `candidates_offered` (strings only; drop non-strings; keep order; no duplicates) and `matched_candidate` (a string or null; when it is absent fall back to `semantic_match.matched`); an OLD report keeps the current surrogate behaviour byte for byte. The matched id must appear in `candidates_offered` whenever `matched_candidate` is set. Nothing else changes: the gate, the summary line, the ledger code and the packet key names stay as they are.

FIXTURE AND TESTS. Extend `tests/fixtures/factory/blind_player_report_small.json` with the two new keys on SOME turns only (leave at least one stuck turn without the keys, to keep the old-report path under test) and update the expected values in the existing tests. Add tests: a new-report stuck turn with candidates ["a","b"] and no match gives those candidates and `matched_candidate` None and triage routes it R3 (call the public triage entry point that existing tests use); the same with an empty list stays R2; a matched stuck turn that did not commit routes R5; an old-report turn keeps the surrogate; non-string entries are dropped; the matched id is added when missing from the list. New tests run in under 10 seconds with no network and no ledger writes except under tmp_path. Do not add a test FILE.

HARD LIMITS. Edit only the three files above. Never edit `factory/stations/triage.py`, `factory/guard.py`, `factory/config/`, `frontend/`, `storygame/`, `bench/` or any other file, and add no dependencies. Write NOTES_15C_STATION.txt (worktree root, never committed) listing every ambiguity and your choice."""

PYTEST_ENV = 'export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp\n[ -e .venv ] || ln -s @REPO@/.venv .venv\n'

ENGINE_CHECK = (
    """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
"""
    + PYTEST_ENV
    + """git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -vxF -e storygame/runtime/attempt_bundle.py -e storygame/runtime/engine.py -e storygame/runtime/cloudflare.py -e tests/test_attempt_bundle.py || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
grep -q "shortlist_ids" storygame/runtime/attempt_bundle.py || { echo "RevealSelection has no shortlist_ids"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_attempt_bundle.py tests/test_bundle_report.py tests/test_reveal_universe.py tests/test_established_reveal_match.py tests/test_recent_cue_unit.py tests/test_reference_evidence_append.py tests/test_act2_knowledge_sources.py
took=$(( $(date +%s) - start ))
echo "engine tests took $took s (budget 90 s)"
[ "$took" -le 90 ] || { echo "engine tests over the 90 s budget"; exit 1; }
.venv/bin/python -m ruff check storygame/runtime/attempt_bundle.py storygame/runtime/engine.py storygame/runtime/cloudflare.py tests/test_attempt_bundle.py
.venv/bin/python -m ruff format --check storygame/runtime/attempt_bundle.py storygame/runtime/engine.py storygame/runtime/cloudflare.py tests/test_attempt_bundle.py
# independent probe: the field exists, defaults empty, round-trips, and an old bundle still validates
probe="$WORK/out/engine-probe.out"
.venv/bin/python - > "$probe" 2>&1 <<'PY'
from storygame.runtime.attempt_bundle import RevealSelection
a = RevealSelection(outcome="semantic_refusal", universe_size=3, shortlist_size=2, shortlist_ids=("x", "y"))
assert a.model_dump(mode="json")["shortlist_ids"] == ["x", "y"], a.model_dump(mode="json")
b = RevealSelection.model_validate({"outcome": "exact_match", "matched": "k", "universe_size": 3, "shortlist_size": 0})
assert tuple(b.shortlist_ids) == (), b
print("probe ok")
PY
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed"; exit 1; }
git diff --cached > "$WORK/out/py-engine.patch"
test -s "$WORK/out/py-engine.patch"
"""
)

JS_CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
[ -e frontend/node_modules ] || ln -s @REPO@/frontend/node_modules frontend/node_modules
git add -A -- frontend/e2e
bad=$(git diff --cached --name-only | grep -vxF -e frontend/e2e/blind-player.js -e frontend/e2e/blind-player.test.js || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
cd frontend
start=$(date +%s)
node --test e2e/blind-player.test.js e2e/merge-blind-player.test.js
took=$(( $(date +%s) - start ))
echo "node tests took $took s (budget 30 s)"
[ "$took" -le 30 ] || { echo "node tests over the 30 s budget"; exit 1; }
probe="$WORK/out/js-probe.out"
node --input-type=module - > "$probe" 2>&1 <<'JS'
import { turnLog } from "./e2e/blind-player.js";
const mk = (reveal) => ({ turn: 1, input: "x", raw_input: "x", text: "t", attempt_bundle: reveal === undefined ? null : { outcome: "committed", transition_cause: "none", reveal_selection: reveal } });
const one = (turn) => turnLog([turn])[0];
const a = one(mk({ outcome: "semantic_refusal", matched: null, shortlist_ids: ["a", "b"] }));
if (JSON.stringify(a.candidates_offered) !== '["a","b"]' || a.matched_candidate !== null) throw new Error("refusal case: " + JSON.stringify([a.candidates_offered, a.matched_candidate]));
const b = one(mk({ outcome: "semantic_match", matched: "c", shortlist_ids: ["a", "b"] }));
if (JSON.stringify(b.candidates_offered) !== '["a","b","c"]' || b.matched_candidate !== "c") throw new Error("matched-not-listed case: " + JSON.stringify(b));
const c = one(mk({ outcome: "exact_match", matched: "k" }));
if (JSON.stringify(c.candidates_offered) !== '["k"]' || c.matched_candidate !== "k") throw new Error("old bundle case");
const d = one(mk(undefined));
if (JSON.stringify(d.candidates_offered) !== "[]" || d.matched_candidate !== null) throw new Error("no bundle case");
console.log("probe ok");
JS
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed"; exit 1; }
cd ..
git diff --cached > "$WORK/out/js-report.patch"
test -s "$WORK/out/js-report.patch"
"""

STATION_CHECK = (
    """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
"""
    + PYTEST_ENV
    + """git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/stations/live_playtest.py -e tests/test_factory_live_playtest.py -e tests/fixtures/factory/blind_player_report_small.json || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_live_playtest.py tests/test_factory_triage.py tests/test_factory_stations.py tests/test_factory_line.py tests/test_factory_followups.py
took=$(( $(date +%s) - start ))
echo "station tests took $took s (budget 30 s)"
[ "$took" -le 30 ] || { echo "station tests over the 30 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations tests/test_factory_live_playtest.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_live_playtest.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
probe="$WORK/out/station-probe.out"
.venv/bin/python - > "$probe" 2>&1 <<'PY'
from factory.stations.live_playtest import report_to_packets
def run(turn_extra, semantic=None):
    turn = {"turn": 2, "raw_input": "Examine the calendar.", "text": "n", "outcome": "committed", **turn_extra}
    if semantic is not None:
        turn["semantic_match"] = semantic
    report = {"scene": "1A", "replicates": [{"replicate": 1, "scene": "1A", "stuck_turns": [2], "turns": [turn]}]}
    packets = report_to_packets(report)
    assert len(packets) == 1, packets
    return packets[0]
new = run({"candidates_offered": ["a", "b"], "matched_candidate": None})
assert new["candidates_offered"] == ["a", "b"] and new["matched_candidate"] is None, new
empty = run({"candidates_offered": [], "matched_candidate": None}, {"ran": True, "matched": "z"})
assert empty["candidates_offered"] == [] or empty["matched_candidate"] == "z", empty
old = run({}, {"ran": True, "matched": "m"})
assert old["candidates_offered"] == ["m"] and old["matched_candidate"] == "m", old
print("probe ok")
PY
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed"; exit 1; }
git diff --cached > "$WORK/out/py-station.patch"
test -s "$WORK/out/py-station.patch"
"""
)


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@CONTRACT@", CONTRACT).replace("@REPO@", REPO).replace("@WORK@", WORK)

    def task(key: str, owned: list[str], spec: str, check: str, verified: str, effort: str) -> dict:
        return {
            "key": key,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", f"model_reasoning_effort={effort}"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": owned,
            "spec": fill(spec),
            "check": fill(check),
            "expect_files": [],
            "verified": verified,
        }

    return {
        "run_name": "factory-station7-candidates",
        "workdir": WORK,
        "max_parallel": 3,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            task(
                "py-engine",
                ENGINE_OWNED,
                ENGINE_SPEC,
                ENGINE_CHECK,
                "RevealSelection carries shortlist_ids (default empty, old bundles still validate), the Cloudflare provider records the offered ids in the same place and cap as shortlist_size, the engine passes them through; neighbouring bundle and reveal tests green under 90 s; ruff clean; only four files changed.",
                "high",
            ),
            task(
                "js-report",
                JS_OWNED,
                JS_SPEC,
                JS_CHECK,
                "turnLog emits candidates_offered and matched_candidate from the bundle per the contract, safe on missing or malformed bundles; node tests under 30 s; the probe covers refusal, matched-not-listed, old bundle and no bundle; two files changed.",
                "medium",
            ),
            task(
                "py-station",
                STATION_OWNED,
                STATION_SPEC,
                STATION_CHECK,
                "Station 7 packets take candidates_offered and matched_candidate from a new report and keep the surrogate for an old one; triage routes R2, R3 and R5 as expected on the fixtures; tests under 30 s; ruff clean; real ledger untouched; three files changed.",
                "medium",
            ),
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round15c-candidates-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
