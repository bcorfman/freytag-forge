# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 10b-2: the world-need check (factory step 4, station 2): a free script that answers the three questions per contract need.

Usage: build_round10b2_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-world-need-2"

OWNED = [
    "factory/checks/world_need.py",
    "tests/test_factory_world_need.py",
    "factory/contracts/lint.py",
    "factory/config/contract_rules.json",
    "factory/config/frozen.json",
    "tests/test_factory_contracts.py",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_world_need.py tests/test_factory_contracts.py tests/test_factory_frozen.py` (never pass --cov). Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. Before any prose is written for a scene, a free script lists the state the scene depends on (the `world_needs` of its scene contract) and answers three questions per item: (Q1) can the world model represent it; (Q2) does something earlier in the story produce it; (Q3) does something later read it. Contracts are validated by `factory/contracts/lint.py` (read it, its rules file `factory/config/contract_rules.json`, the fixture `tests/fixtures/factory_contracts/ok.json` and `tests/test_factory_contracts.py` first; read `factory/checks/gap_delta.py` for style and how it loads a story). The world model now has `WorldSchema.can_represent(relation, subject_kind, object_kind=None) -> OpResult` in `packages/worldkeeper/src/worldkeeper/model.py` (read it; do NOT edit it: all world-model logic stays there). `storygame/story_package/dependencies.py` has `producers(package, fact_id)` and `consumers(package, fact_id)` (each result has `.scene_id`, which may be None). `storygame.runtime.world_model.world_schema_data(package)` gives the data for `WorldSchema.from_data`, whose `.entities` map an entity id to an object with `.kind`.

PART 1: extend the contract lint with three OPTIONAL need fields (edit factory/contracts/lint.py, factory/config/contract_rules.json, tests/test_factory_contracts.py; additions only, existing rule ids and behaviour unchanged, the existing ok.json must still lint clean):
- `subject_kind`, `object_kind`: when present must be a non-empty string.
- `role`: when present must be one of the new rules-file key `need_roles`: ["relies_on", "creates"]; absent means relies_on.
A violation is reported as `contract.world_need` (existing rule id). Add tests for each (append new tests; do not change existing ones).

PART 2: create `factory/checks/world_need.py`.
API:
    @dataclass(frozen=True) class NeedResult: scene_id: str; need_id: str; relation: str; outcome: str ("ok", "worldkeeper_ticket" or "story_hole"); q1: str; q2: str; q3: str (each "yes", "no" or "n/a"); reasons: tuple[str, ...]
    def check_needs(contract: dict, package, *, rules: dict | None = None) -> list[NeedResult]   # one result per need, in contract order; `rules` defaults to the rules file (scene_ids gives the story order)
    def tickets_for(results) -> list[dict]   # one dict per non-ok result: {{"kind": outcome, "scene_id", "need_id", "summary": a plain sentence}}
Semantics per need (scenes are ordered by the rules file `scene_ids`):
- Resolve the kinds. subject_kind is the need's `subject_kind`, else the kind of the entity named by `subject` in the package's world schema, else unknown. object_kind likewise from `object_kind` or the entity named by `object`; for relation `know` the object is a FACT id, so its object kind is not resolved (pass None); for `axis` and `exist` the object is not needed.
- Q1: if a needed kind is unknown (no declaration, none given): q1 "no", outcome story_hole, reason says to declare the thing or give its kind. Otherwise call `schema.can_represent(relation, subject_kind, object_kind)`: ok means q1 "yes"; not ok with a reason that starts "unknown kind" means q1 "no", outcome story_hole (the story must declare that kind); any other refusal means q1 "no", outcome worldkeeper_ticket (the world model cannot say it) with the reason text in `reasons`. Also for relation `know`: a role `relies_on` need whose object is not in `package.fact_ids` AND is not created by an earlier scene's contract (see Q2) is a story_hole (q1 "no", reason "fact is not declared").
- Q2 applies only to relation `know` with role relies_on (the default): "yes" when `producers(package, object)` has a producer whose scene_id is None or not later than this scene, OR a scene EARLIER in the same contract has a need with relation `know`, the same object and role `creates`; otherwise "no" and outcome story_hole ("nothing earlier produces it"). All other needs: q2 "n/a".
- Q3 applies only to relation `know` with role `creates`: "yes" when `consumers(package, object)` has a consumer whose scene_id is None or not earlier than this scene, OR a scene LATER in the same contract has a `know` need on the same object with role relies_on; otherwise "no" and outcome story_hole ("nothing later reads it"). All other needs: q3 "n/a".
- A need with a missing or malformed field never raises: outcome story_hole, reason "malformed need".
- Outcome is "ok" only when q1 is "yes" and no applicable question is "no". When several problems exist, a worldkeeper_ticket outranks a story_hole; list every reason.
CLI: `python -m factory.checks.world_need CONTRACT.json [--story ROOT] [--json OUT.json]` where ROOT defaults to the same default story as gap_delta.py. It loads the package with `storygame.story_package.loader.load_story_package`, prints one line per non-ok need as `OUTCOME scene need: reasons`, prints `ok` when all are ok, writes the results and tickets to OUT.json when asked, exits 0 only when every need is ok, 1 otherwise, and 2 when the contract file cannot be read or is not JSON.

PART 3: add `"factory/contracts/**"` to the `frozen` list in factory/config/frozen.json (keep it valid JSON, keep every existing entry and order, add it after "factory/checks/**"). tests/test_factory_frozen.py must still pass unchanged.

TESTS (tests/test_factory_world_need.py): build the package from the mini fixture `tests/fixtures/story_source/mini_ok` (look at tests/story_source/helpers.py and `storygame.story_source` (`compile_source_tree`) for how other tests compile a fixture tree into a package). Discover ids from the loaded package at test time (an item id, an NPC id, a location id, a fact id that has a producer, a fact id that has no producer) instead of hard-coding story ids. Cover: each relation with a representable need giving outcome ok; a worldkeeper_ticket case (for example `hold` whose subject is a character); an unknown-kind story_hole; a `know` need on an undeclared fact; Q2 yes via a package producer, Q2 yes via an earlier scene's `creates`, Q2 no; Q3 yes via a package consumer, Q3 yes via a later scene's `relies_on`, Q3 no; role defaults to relies_on; kinds supplied by `subject_kind`/`object_kind` for an undeclared entity; a malformed need does not raise; worldkeeper_ticket outranks story_hole; tickets_for returns one dict per non-ok result; and the CLI (exit 0 and `ok`, exit 1 with a problem line, exit 2 on a non-JSON file, the --json file contents). Run the CLI tests as a subprocess with `--story` pointing at a copy of the fixture tree compiled in a temp directory if the loader needs that, otherwise in-process through `main(argv)`; expose a `main(argv: list[str] | None = None) -> int`. Tests must be hermetic (no network, no model call).

HARD LIMITS. Edit only the six files above. Never edit packages/, storygame/, data/, docs/, tests/shard_durations.json, other factory files or other tests. Write NOTES_10b2.txt (worktree root, never committed) for every rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_factory_world_need.py tests/test_factory_contracts.py tests/test_factory_frozen.py tests/test_factory_checks.py tests/test_factory_gap_delta.py > "$out" 2>&1 || rc=$?
tail -6 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
grep -q '"factory/contracts/\\*\\*"' factory/config/frozen.json || {{ echo "frozen.json lacks factory/contracts/**"; exit 1; }}
.venv/bin/python -m json.tool factory/config/frozen.json >/dev/null
# independent probe on the real default story: a hold need whose subject is a character is a world-model ticket; a plain exist need on a declared item is ok
probe=$(mktemp --suffix=.json)
.venv/bin/python - "$probe" <<'PY'
import json, sys
from pathlib import Path
from storygame.story_package.loader import load_story_package
root = next(p for p in sorted(Path("data/stories").iterdir()) if p.is_dir())
pkg = load_story_package(root)
item = pkg.world.items[0].id
npc = pkg.world.npcs[0].id
contract = {{"act": "1", "scenes": [{{"scene_id": "1A", "world_needs": [
    {{"id": "n1", "relation": "exist", "subject": item}},
    {{"id": "n2", "relation": "hold", "subject": npc, "object": npc}},
]}}]}}
json.dump(contract, open(sys.argv[1], "w"))
PY
rc=0; .venv/bin/python -m factory.checks.world_need "$probe" --json "$probe.out.json" > "$out" 2>&1 || rc=$?
cat "$out"
[ "$rc" -eq 1 ] || {{ echo "probe: expected exit 1, got $rc"; exit 1; }}
grep -q "worldkeeper_ticket" "$out" || {{ echo "probe: hold on a character must be a worldkeeper_ticket"; exit 1; }}
.venv/bin/python - "$probe.out.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
outcomes = {{r["need_id"]: r["outcome"] for r in data["results"]}}
assert outcomes == {{"n1": "ok", "n2": "worldkeeper_ticket"}}, outcomes
assert len(data["tickets"]) == 1, data["tickets"]
print("probe ok")
PY
# part 1 is additive: the original ok.json fixture is untouched and still clean
git diff --quiet HEAD -- tests/fixtures/factory_contracts/ok.json || {{ echo "ok.json must not change"; exit 1; }}
.venv/bin/python -m factory.contracts.lint tests/fixtures/factory_contracts/ok.json | grep -qx ok
.venv/bin/python -m ruff check factory tests/test_factory_world_need.py tests/test_factory_contracts.py
.venv/bin/python -m ruff format --check factory tests/test_factory_world_need.py tests/test_factory_contracts.py
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -v -x -e factory/checks/world_need.py -e tests/test_factory_world_need.py -e factory/contracts/lint.py -e factory/config/contract_rules.json -e factory/config/frozen.json -e tests/test_factory_contracts.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/world_need.patch
test -s {WORK}/world_need.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-world-need",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "world-need",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 400,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "World-need check: unit tests green on the mini fixture, an independent probe on the real default story (exist ok, hold on a character is a worldkeeper ticket), lint extension additive, frozen list extended, ruff clean, only six files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round10b2-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
