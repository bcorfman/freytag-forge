# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 10a: the scene-contract schema and its lint (factory step 4, station 0 and 1 pass rule).

Usage: build_round10a_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-contracts"

OWNED = [
    "factory/contracts/__init__.py",
    "factory/contracts/lint.py",
    "factory/contracts/template.json",
    "factory/config/contract_rules.json",
    "tests/test_factory_contracts.py",
    "tests/fixtures/factory_contracts/ok.json",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_contracts.py` (never pass --cov). Run ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies, standard library only).

BACKGROUND. The factory (`factory/`) writes a story by contract. A planner model fills one JSON *act contract* per act (three acts, nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A free, deterministic lint must accept it before any prose is written. You build the contract format, an example, and the lint. Read `factory/checks/library.py` and `tests/test_factory_checks.py` first to match the style of the existing factory code. The rules below come from the owner's plan; implement them exactly. Do NOT invent extra rules.

FILES YOU OWN (create exactly these, edit nothing else):
- factory/contracts/__init__.py : exports `lint_contract`, `load_rules`, `Problem`.
- factory/contracts/lint.py : the lint; also runnable as `python -m factory.contracts.lint FILE.json [--rules RULES.json]`, which prints one line per problem as `RULE_ID path: message`, prints `ok` when there are none, and exits 1 on any problem (2 when the file cannot be read or is not JSON).
- factory/config/contract_rules.json : the rule constants (below). The lint reads them from here, never from literals in code.
- factory/contracts/template.json : the blank template the planner fills in (below).
- tests/fixtures/factory_contracts/ok.json : one valid act contract (Act 1: scenes 1A, 1B, 1C) that passes the lint.
- tests/test_factory_contracts.py : tests.

RULES FILE (contract_rules.json) keys: "protected_characters": ["michelle"]; "cost_kinds": ["riskier_storylet", "npc_harm", "captive_harm"]; "beat_kinds": ["entry", "pressure", "relief", "reveal", "setpiece", "exit"]; "relations": ["hold", "know", "reach", "exist", "hidden", "seated", "companion", "axis"]; "bond_kinds": ["favor", "joke", "confession", "habit"]; "scene_ids": ["1A","1B","1C","2A","2B","2C","3A","3B","3C"]; "first_pressure_turns": [3, 4]; "min_gap_turns": 2; "reading_verbs": ["read", "search", "look", "examine", "check"].

CONTRACT SHAPE (an act contract; every key below is required unless marked optional):
{{
  "act": "1",
  "prior_bonds": ["brandon"],                      // optional: characters with a bond beat in an earlier act
  "harm_ladder": [{{"rung": 1, "kind": "riskier_storylet", "harm": "text"}}, ...],   // >= 2 rungs, rung numbers 1,2,3.. consecutive and increasing, kind in cost_kinds
  "scenes": [ SCENE, ... ]                          // >= 1 scene, scene_id unique and in scene_ids
}}
SCENE = {{
  "scene_id": "1A",
  "entry_prior_exit_sets_threat": false,             // optional bool, default false
  "feeling": "dread",                                // non-empty: the one thing the player should feel
  "clock": {{"running_out": "text", "bridge_hook": "text"}},   // both non-empty
  "npc_in_the_way": {{"character": "id", "named_in_entry": true}},   // character non-empty and named_in_entry must be true
  "beats": [ {{"id": "b1", "kind": "entry", "turn": 1, "summary": "text"}}, ...],
  "delay_costs": [ DELAY_COST, ... ],                // >= 1
  "bond_beats": [ {{"id": "bb1", "character": "id", "kind": "favor", "summary": "text"}}, ...],   // >= 1
  "world_needs": [ NEED, ... ]                       // >= 1
}}
A setpiece beat also carries "outcomes": [{{"id": "o1", "verb": "hold"}}, ...].
DELAY_COST = {{"id": "dc1", "window": "what was missed", "cost_kind": one of cost_kinds, "passage_id": "non-empty id of the authored passage shown when the cost lands",
  "riskier_storylet_id": "required when cost_kind is riskier_storylet",
  "cost_fact": "required when cost_kind is npc_harm or captive_harm: the fact id that records the harm",
  "harmed": ["ids"]  // required and non-empty when cost_kind is npc_harm or captive_harm
  "read_by_scene": "required when cost_fact is present: a later scene_id (later in the scene_ids order) that reads the cost fact"}}
NEED = {{"id": "n1", "relation": one of relations, "subject": "non-empty id", "object": "required for hold, know, reach, hidden, seated, companion", "axis": "required for axis", "pole": "required for axis"}}

LINT RULES (each problem has a stable rule id; one problem per violation; path is like `scenes[1].beats[2]`):
- contract.shape : a required key is missing, has the wrong type, is empty, an unknown scene_id, a duplicate scene_id or a duplicate id inside one list, or a cost_kind/beat kind/relation/bond kind not in the rules file.
- contract.placeholder : any string value equal to "TODO" anywhere in the document.
- contract.harm_ladder : fewer than 2 rungs, or rungs not consecutive increasing from 1.
- contract.beats : a scene must have exactly one `entry` beat at turn 1, exactly one `exit` beat, with the exit turn greater than every other beat's turn; beat turns are integers >= 1; at least one pressure, one relief and one setpiece beat.
- contract.first_pressure : the earliest `pressure` beat turn must be in first_pressure_turns, unless the scene sets entry_prior_exit_sets_threat true, in which case any turn >= 1 is allowed.
- contract.pacing : walking the pressure and relief beats in turn order, two pressure beats may not be adjacent without a relief beat between them, and any two consecutive pressure/relief beats must be at least min_gap_turns apart.
- contract.setpiece : a setpiece beat needs at least 2 outcomes with distinct verbs, none of which is in reading_verbs (case-insensitive, compared to the first word of the verb).
- contract.npc : npc_in_the_way is missing or named_in_entry is not true.
- contract.clock : clock.running_out or clock.bridge_hook is empty.
- contract.delay_cost : cost_kind outside cost_kinds (so a trust-only penalty or a substitute item is rejected); a riskier_storylet without riskier_storylet_id; an npc_harm/captive_harm without cost_fact, harmed or read_by_scene; read_by_scene not strictly later than this scene in the scene_ids order; no passage_id.
- contract.protected : any id in `harmed` is in protected_characters (case-insensitive).
- contract.bond : a character in `harmed` has no bond beat in this scene, an earlier scene of the same contract, or prior_bonds. (A scene with no bond beat at all is contract.shape.)
- contract.world_need : relation needs a field that is missing (see NEED).
- contract.feeling : feeling is empty.
Do not also report contract.shape for a field another rule already reports; each violation is reported once.

TEMPLATE (template.json): the same structure with every string value "TODO", one scene whose scene_id is "1A" (a real id, not TODO), one beat of each kind (a setpiece with two outcomes), one delay cost, one bond beat, one need, two harm rungs. Linting it must report contract.placeholder and nothing that is not caused by the placeholders or by the template being incomplete as a story (it is fine for other rules to fire on it; the test only requires contract.placeholder to be present).

TESTS: (1) ok.json lints clean and is JSON with 3 scenes whose scene_ids are 1A, 1B, 1C in order, and its content must be a plausible spy-thriller act, NOT copied from any file in data/. (2) One test per rule id above: copy ok.json in memory, apply one minimal mutation, and assert that exact rule id appears (and that ok.json itself stays clean). Parametrize them. (3) A test that each of the protected and cost_kinds values is read from the rules file: lint ok.json with a rules dict whose protected_characters contains a character ok.json harms, and assert contract.protected appears. (4) The CLI: exit 0 and `ok` for ok.json, exit 1 for a mutated file, exit 2 for a file that is not JSON. (5) template.json parses and reports contract.placeholder. Make ok.json deliberately include at least one npc_harm delay cost (harming a non-protected character who has a bond beat) so the bond, protected and read_by_scene rules are exercised on real data.

HARD LIMITS. Edit only the six files above. Never edit factory/config/frozen.json, factory/__main__.py or any other file. Write a short NOTES_10a.txt (worktree root, never committed) listing anything in these rules that you found ambiguous and the choice you made.
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_factory_contracts.py > "$out" 2>&1 || rc=$?
tail -8 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
# the CLI must accept the valid fixture and reject a mutated one
.venv/bin/python -m factory.contracts.lint tests/fixtures/factory_contracts/ok.json | grep -qx ok || {{ echo "ok.json does not lint clean"; exit 1; }}
bad=$(mktemp --suffix=.json)
.venv/bin/python - "$bad" <<'PY'
import json, sys
data = json.load(open("tests/fixtures/factory_contracts/ok.json"))
data["scenes"][0]["clock"]["bridge_hook"] = ""
json.dump(data, open(sys.argv[1], "w"))
PY
rc=0; .venv/bin/python -m factory.contracts.lint "$bad" > "$out" 2>&1 || rc=$?
cat "$out"
[ "$rc" -eq 1 ] || {{ echo "a broken contract must exit 1, got $rc"; exit 1; }}
grep -q "contract.clock" "$out" || {{ echo "contract.clock not reported"; exit 1; }}
# every rule id named in the spec appears in the lint source
for rule in shape placeholder harm_ladder beats first_pressure pacing setpiece npc clock delay_cost protected bond world_need feeling; do
  grep -q "contract.$rule" factory/contracts/lint.py || {{ echo "rule contract.$rule missing from lint.py"; exit 1; }}
done
# rule constants live in the rules file
grep -q '"michelle"' factory/config/contract_rules.json || {{ echo "protected list missing from rules file"; exit 1; }}
! grep -qi "michelle" factory/contracts/lint.py || {{ echo "protected names must not be hard-coded in lint.py"; exit 1; }}
.venv/bin/python -m ruff check factory/contracts tests/test_factory_contracts.py
.venv/bin/python -m ruff format --check factory/contracts tests/test_factory_contracts.py
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -v -x -e factory/contracts/__init__.py -e factory/contracts/lint.py -e factory/contracts/template.json -e factory/config/contract_rules.json -e tests/test_factory_contracts.py -e tests/fixtures/factory_contracts/ok.json || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/contracts.patch
test -s {WORK}/contracts.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-contracts",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "contracts",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 300,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "Contract lint: valid fixture clean, one failing mutation per rule id, CLI exit codes, rule constants in the rules file, ruff clean, only the six owned files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round10a-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
