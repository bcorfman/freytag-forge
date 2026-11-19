# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6e-2: source-layer checks the legacy loader enforced (2 parallel tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6e2"

COMMON = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML and pydantic only).

BACKGROUND. The default story's data moved from legacy files to a source tree (data/stories/continuity-initiative/source/) compiled by `storygame.story_source.compile_source_tree`; the format is fixed by .plans/story-data-schema-contract.md (read sections 2, 4, 10 and the diagnostics table; never edit it). The package under storygame/story_source/ has a strict reader, layer 1 shape checks (l1_*.py) and layer 2 reference/semantic checks (l2_*.py), discovered by the registry in checks.py (read it, l2_facts.py and l2_claims.py first to copy their style: diagnostics are `Diagnostic` objects with a stable code such as `L2.dangling`, a file, a record address and a message). Every inherited loader check also runs on the built package. A read-only investigation (see .plans/story-data-schema-contract.md and the reports named below) found that several mistakes the LEGACY loader rejected are now silently accepted by the source route. Authors can ship a broken story. Your job is to close the holes named below with real source checks, written as new files so they never collide with parallel workers. The checks must work for ANY story source tree, not the default story only: never name a fact, scene or entity of the default story in a check; read rules from the data.

For each hole below, the already-ported test (listed) must go from failing to passing WITHOUT editing the test file. Read the test and the legacy loader check it mirrors (storygame/story_package/loader.py, the file:line is given) so your diagnostic fires on the same mistake; where the test matches an error message with a regex, make your diagnostic message contain that text (the compiler wraps diagnostics in `SourceError`; read how the message is assembled). Also write a few focused tests of your own for each check in the new test file named below, using tests/story_source/helpers.py (`compiled_story_copy`, `patch_source`, `load_compiled_copy`): one rejection test per check on a mutated copy of the real default source tree, and one test that the unmutated default source tree still produces NO diagnostic from your new check module. The real default story must keep compiling exactly as before: tests/story_source/test_parity_default.py and every other test in tests/story_source must still pass.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, data/, the contract or any module not named in your ownership list. If a hole needs a contract decision or a change in a module you do not own, write the exact need in NOTES_<key>.txt (worktree root, never committed) and leave that test failing.
"""
)

TASKS = {
    "r6e2-world-checks": {
        "owned": ["storygame/story_source/l2_world.py", "tests/story_source/test_l2_world_checks.py"],
        "spec": COMMON
        + """
YOUR HOLES (all in the world catalog, source/catalog.yaml):
1. Item and NPC state axes. Tests: tests/test_world_seats.py::test_axis_unavailable_must_be_a_pole and ::test_npc_axis_unavailable_must_be_a_pole. A declared state axis is exactly two opposite values (poles) and its `unavailable` value must be one of them; find the legacy check in loader.py / storygame/story_package/world_schema.py / worldkeeper and mirror it. The source schema accepts `unavailable` but nothing validates it.
2. Seat lines. Tests: tests/test_seating.py::test_loader_rejects_a_seat_without_its_lines and ::test_loader_rejects_a_seat_without_its_leave_line. A seat (a prop or item that a character can sit on) must carry its enter line and its leave line; the legacy loader rejects a seat missing either.
3. Blank place description. Test: tests/test_place_scoped_feed.py::test_loader_rejects_blank_location_description.
4. Scoped alias collisions. Test: tests/test_markdown_story_package.py::test_group_scoped_alias_loader_rejects_declared_name (that file also holds other failing tests that are NOT yours; run only this node id). A group's or item's scoped alias must not duplicate any declared entity name or alias (casefolded); legacy check: the pre-parse alias loop in loader.py `_load_story_package_uncached` ("scoped alias ... duplicates a declared entity name or alias").
Put all four checks in the new module storygame/story_source/l2_world.py (layer 2, registered through checks.py's discovery) with codes `L2.axis_pole`, `L2.seat_lines`, `L2.blank_description`, `L2.scoped_alias_collision`; list the exact codes and messages you used in NOTES_r6e2-world-checks.txt.
""",
        "tests": [
            "tests/test_world_seats.py::test_axis_unavailable_must_be_a_pole",
            "tests/test_world_seats.py::test_npc_axis_unavailable_must_be_a_pole",
            "tests/test_seating.py::test_loader_rejects_a_seat_without_its_lines",
            "tests/test_seating.py::test_loader_rejects_a_seat_without_its_leave_line",
            "tests/test_place_scoped_feed.py::test_loader_rejects_blank_location_description",
            "tests/test_markdown_story_package.py::test_group_scoped_alias_loader_rejects_declared_name",
        ],
    },
    "r6e2-story-checks": {
        "owned": ["storygame/story_source/l2_story.py", "tests/story_source/test_l2_story_checks.py"],
        "spec": COMMON
        + """
YOUR HOLES (story logic, source/scenes/*.yaml):
1. A transition trigger that can never fail or never be produced. Test: tests/test_markdown_story_package.py::test_loader_rejects_transition_trigger_that_can_never_fail (that file holds other failing tests that are NOT yours; run only this node id). The scene `exit` (contract 4.13) has trigger facts; legacy loader.py `_validate_transition_trigger_sources` (about line 1351) requires every true-trigger fact to be produced in the transition's source scene by a pacing event effect, an incident outcome, or a bridge/claim commit. Until now the compiler silently invented producers (that repair was removed in the previous round), so a trigger fact with no producer in its own scene can reach the compiled package; the inherited check then raises a LOADER diagnostic only after compilation. Add a layer 2 check that reports the same mistake EARLY with a precise source address (scene file, `exit`, the fact id) in the diagnostics list, using the producer sources the source tree actually has (beats[].sets, reveal variants' commits, incident outcomes, bridge commits, entry claims). Read the legacy check and `c_scene.py` / `c_knowledge.py` to see exactly which source fields compile into producers, and use the same set. Keep the inherited check running as it does.
2. A delivery for a fact the player can never see. The legacy loader (loader.py about lines 1090-1098) rejects a delivery whose fact has no player-visible claim (a world-only fact). The compiler function `_attach_delivery_facts` in c_knowledge.py (about lines 175-203) currently attaches such a delivery fact to an arbitrary player-visible storylet, which hides the mistake. Add a layer 2 check that rejects a fact `delivery` mapping on a fact that no claim or reveal in the story can convey to the player (decide precisely from the contract section 4.5 and the legacy check what 'player-visible' means; mirror the legacy rule), with an address naming the fact. You may NOT edit c_knowledge.py; if the repair there still lets the mutation through after your check runs (it must not, since layer 2 runs before compilation), write why in the notes file.
Put both checks in the new module storygame/story_source/l2_story.py (layer 2), codes `L2.transition_source` and `L2.delivery_unseen`; list the exact codes and messages in NOTES_r6e2-story-checks.txt. For the delivery check there is no ported test yet (the existing one tests the wrong mutation), so your own tests in tests/story_source/test_l2_story_checks.py are its only coverage: write one on a faithful mutation (add a `delivery` to a fact that only world effects use) and make sure the unmutated default tree has no diagnostics.
""",
        "tests": [
            "tests/test_markdown_story_package.py::test_loader_rejects_transition_trigger_that_can_never_fail",
        ],
    },
}


def check(key: str, owned: list[str], tests: list[str]) -> str:
    keep = " ".join(f"-e '^{p}$'" for p in owned)
    node_ids = " ".join(f"'{t}'" for t in tests)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {node_ids} {owned[1]} > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
n=$(grep -cE "^def test_" {owned[1]})
[ "$n" -ge 3 ] || {{ echo "expected at least 3 own tests, found $n"; exit 1; }}
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source tests/test_loader_source_dispatch.py > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check {owned[0]} {owned[1]}
.venv/bin/python -m ruff format --check {owned[0]} {owned[1]}
git add -A -- storygame tests data
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
[ ! -e NOTES_{key}.txt ] || cp NOTES_{key}.txt {WORK}/NOTES_{key}.txt
"""


def build() -> dict:
    tasks = []
    for key, item in TASKS.items():
        tasks.append(
            {
                "key": key,
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 1200,
                "ownership": item["owned"],
                "spec": item["spec"].replace("<key>", key),
                "check": check(key, item["owned"], item["tests"]),
                "expect_files": [],
                "verified": "the named ported tests pass with new source-layer checks written as separate modules; own rejection tests plus a clean-default-tree test; tests/story_source green; ruff clean; only owned files changed.",
            }
        )
    return {
        "run_name": "story-data-round6-checks",
        "workdir": WORK,
        "max_parallel": 2,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6e2-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
