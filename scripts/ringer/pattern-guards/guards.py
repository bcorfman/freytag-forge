# ruff: noqa: E501
"""Pattern guards 1 and 3 from the 3A review: advisory, declared-data checks that catch routine bug patterns before a billed run.

Guard 1 (delivery_names_unbound_item): a delivery that names a character and a movable item, but the entry neither binds the item nor has a world effect that moves it (the 3A stolen-radio hand-off).
Guard 3 (deep-turn budget): the narrator prompt size of each scene once its knowledge is established, so completed events fed back every turn show up before a probe (3A c7 to c9 above 6,500).

Drafted only. Nothing here runs a model; the generator writes the manifest and does not execute it.
"""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/pattern-guards"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src or a worktree edit to worldkeeper is silently ignored). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the failing tests, then the code. Do NOT edit any file under data/stories/ (story text and world data are not yours; if the real package produces findings, those are reported and pinned, never fixed). Do NOT touch tests/shard_durations.json (the orchestrator registers new test files afterwards).

DESIGN RULES (project rules, not optional): a guard reads declared data (ids, facts, effects, placements, aliases) and never narrator output; it is advisory and deterministic; known findings in the real package are listed in an explicit allowlist inside the test so any NEW finding fails; it must work for any story package, so never name continuity-initiative ids in guard code (ids may appear only in tests that use the real package or in synthetic fixtures); the hermetic tests build tiny synthetic packages in tmp_path and need no network or .env.
"""

SPEC_UNBOUND = (
    COMMON
    + """
ROLE: audit engineer. You may edit/create ONLY: storygame/audit.py, tests/test_audit_unbound_item.py (new), and, only if an existing assertion about the real package's full finding set must change because of the new check, tests/test_package_audit.py (change nothing else there).

PATTERN: in Scene 3A the c8 delivery says "Michelle hands Kristin the stolen radio and Kristin gives the signal", but the entry has entity_ids: [], its only effects are `assert` of story facts, and no world.yaml fact_effects entry moves the radio. So the world never learns the hand-off, the radio keeps no holder, and the narrator re-does the hand-off at c9. A static check can see this from declared data.

BUILD one new check in storygame/audit.py, named `delivery_names_unbound_item`, emitted with the existing `_finding(check, scene_id, detail)` helper and included in audit_package's findings and in the markdown report like the sibling checks. Read how `ambiguous_owned_item`, `delivery_restates_scene` and `absent_speaker` load knowledge.yaml, world.yaml and plot.md (the helpers `_read_yaml`, `_plot_scenes`, `_scene_item_ids`, `_words` exist) and follow that style.

Rule, for each knowledge entry that has a `delivery_text`:
1. Collect its texts: `delivery_text` plus the `text` of every `delivery_variants` item.
2. Candidate items: world.yaml items that are NOT `fixed: true`, are listed in `item_ids` of at least one scene named in the entry's `available_in_scenes` (use the plot.md scene front matter via `_scene_item_ids`), and whose `name` or any of `aliases` / `scoped_aliases` appears in a text as a whole phrase (case-insensitive, word boundaries; no stemming).
3. The text must also name at least one character: a world.yaml npc (or the protagonist) `name` or alias as a whole phrase. A delivery that names an item but no character is not a candidate transfer and is skipped. This is the noise filter; keep it.
4. An item is BOUND (no finding) if its id is in the entry's `entity_ids`, `reach_entity_ids` or `relevance.entity_ids`, OR any fact the entry establishes with op `assert` appears in world.yaml `fact_effects` with an effect whose `move` equals the item id (also treat `reveal` equal to the item id as bound).
5. Otherwise emit ONE finding per (entry, item), scene_id = the first scene in `available_in_scenes`, detail: "Delivery of '<entry id>' names the <item name> with <character name> but the entry neither lists the item nor has a fact effect that moves it, so the world never records what the text says happened to it." Order findings deterministically (entry order, then item order).

Say in a comment above the function that it is lexical, like its siblings: it cannot read pronouns, and it cannot tell a handed-over item from a merely observed one; it asks the author to bind the item or add a `fact_effects` move, or to allowlist the entry as a known item.

TESTS (tests/test_audit_unbound_item.py, offline, synthetic packages in tmp_path built like tests/test_package_audit.py's `_package` helper; read that file first): (a) a delivery naming a character and a movable item with empty entity_ids and no fact_effects -> one finding with the entry id, item name and character name in the detail; (b) the same entry with the item in entity_ids -> none; (c) the same entry with a fact_effects move of the item on an asserted fact -> none; (d) the item `fixed: true` -> none; (e) the delivery names the item but no character -> none; (f) item listed only in another scene's item_ids -> none; (g) a delivery_variants text naming the pair is checked too; (h) the check appears in the markdown report; (i) REAL PACKAGE: run audit_package on data/stories/continuity-initiative, collect the `delivery_names_unbound_item` findings as (entry id, item id) pairs, and compare to a module-level KNOWN_UNBOUND frozenset in the test: the assertion fails with the exact new and missing pairs printed. Fill KNOWN_UNBOUND by running the real audit once. It MUST contain the 3A signal entries (the stolen radio on k_sl_3a_c_r1 and k_sl_3a_c_r2, if the rule flags them; if it does not flag them, STOP and explain why in the final message instead of bending the rule). Add a comment above KNOWN_UNBOUND that the stolen-radio pairs are a real authored-versus-world mismatch awaiting an author decision, and the rest are to be reviewed.

Run tests/test_audit_unbound_item.py tests/test_package_audit.py tests/test_prompt_budget.py.

FINAL MESSAGE: the rule as built, the total number of real-package findings with the full KNOWN_UNBOUND list (entry id, item id, character name) so a human can judge noise, and anything you were unsure about. If the real package yields more than 40 findings, still pin them but say so prominently.
"""
)

SPEC_BUDGET = (
    COMMON
    + """
ROLE: audit engineer. You may edit/create ONLY: storygame/audit_budget.py (new), tests/test_audit_budget.py (new), tests/fixtures/deep_turn_budget.json (new, written by your own tool).

PATTERN: tests/test_prompt_budget.py measures each scene's narrator prompt only at turn one ("Look around."), with no knowledge established. In Scene 3A the real prompt grows to 9,443 characters by c9 because every established statement is projected into SCENE and into every present speaker's "may say this aloud" lines, and both alternate realizations of one event are projected together. The entry test passes while the deep turns blow the 6,500-character worst-case target. Measure the deep turn statically so this is visible before any billed probe.

BUILD storygame/audit_budget.py (importable plus `python -m storygame.audit_budget [--package DIR] [--write] [--fixture PATH]`):
1. `deep_turn_budget(package, scene_id)` returns a dict with: `narration_chars` (system + user prompt of the narrator for the "Look around." turn, measured exactly as tests/test_prompt_budget.py `_prompts` does: bootstrap RuntimeState, set current_scene_id and phase, call `state._assert_scene_entry_fact`, `apply_scene_placements`, build an ItemFactsProvider with worker_url "https://worker.example/turn", prepare_turn and assemble_turn_prompt) but measured AFTER establishing knowledge as described next; `established_entries` (count of in-scene knowledge entries in the knowledge projection state); `alternate_pairs` (sorted list of storylet ids whose `source.storylet_id` has two or more realizations established at once); `narration_chars_all_alternates`.
2. Two states per scene. STATE ONE-PER-STORYLET ("realistic upper bound"): for every knowledge entry with this scene in `available_in_scenes`, assert every `establishes` effect with op `assert` (as `state.facts` assertions with the entry's fact_id and value, mirroring how `RuntimeState` asserts facts; read `KnowledgeProjector._established` in storygame/runtime/knowledge.py to see what "established" means: every one of the entry's establishes effects must hold), but for entries that share a `source.storylet_id` keep only the first realization in file order. STATE ALL-ALTERNATES: the same without that restriction. `narration_chars` is measured in the first state and `narration_chars_all_alternates` in the second. Do not touch retract-op effects (leave those facts absent). If some entries' establishes facts conflict, the later assertion simply wins; do not raise.
3. `report(package)` builds a row for every scene and `--write` writes tests/fixtures/deep_turn_budget.json: {"schema": 1, "scenes": {scene_id: {"narration_chars": n, "narration_chars_all_alternates": n}}}. Without --write the CLI prints a table (scene, entry chars, deep chars, all-alternates chars, a mark for over 6,500) and exits 0. It must never call the network.
4. The measurement must not mutate the loaded package; build a fresh state per scene.

TESTS (tests/test_audit_budget.py, offline): (a) a tiny synthetic package in tmp_path (copy the construction style of tests/test_package_audit.py `_package`, or load a small package fixture from tests/fixtures/stories if one fits; read them first) whose knowledge adds a statement shows a deep prompt longer than the same package with no knowledge; (b) two realizations of one storylet make `alternate_pairs` list it and make the all-alternates figure larger than the one-per-storylet figure; (c) `report` is deterministic (call twice, equal); (d) REAL PACKAGE RATCHET: for each of the nine scenes of data/stories/continuity-initiative, the current `narration_chars` and `narration_chars_all_alternates` must be <= the values pinned in tests/fixtures/deep_turn_budget.json (a scene absent from the fixture fails with a message to run `python -m storygame.audit_budget --write`). Failure messages name the scene, the old pin and the new value. Shrinking is allowed (the pin is a ceiling). The test must NOT assert the 6,500 target (3A is known to exceed it; that is a reported known item, tracked as O8 in .plans/richer-3a-open-issues-plan.md); instead assert the set of scenes over 6,500 in the one-per-storylet state is a subset of a KNOWN_OVER_BUDGET frozenset in the test that you fill from the first real run, with a comment pointing at O8. Generate the fixture by running the CLI with --write inside your worktree.

Run tests/test_audit_budget.py tests/test_prompt_budget.py tests/test_knowledge_projection.py.

FINAL MESSAGE: the per-scene table printed by the CLI (entry-turn chars are in tests/test_prompt_budget.py's constants for comparison), which scenes exceed 6,500 in each state, and anything you were unsure about.
"""
)

CHECK_COMMON = r"""set -o pipefail
[ -e .venv ] || ln -s REPO/.venv .venv
WT=$PWD
export PYTHONPATH=$WT:$WT/packages/worldkeeper/src TMPDIR=/tmp
PY=$WT/.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in ALLOWED) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git status --porcelain data/ | grep . && { echo "WHY: story data was edited"; exit 1; }
$PY -m pytest -q -p no:cacheprovider TESTS > /tmp/tg-KEY.out 2>&1; rc=$?; tail -15 /tmp/tg-KEY.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$')
$PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
$PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
EXTRA
git add $CH && git diff --cached > OUTDIR/KEY.patch && wc -l OUTDIR/KEY.patch && git diff --cached --stat | tail -6
"""

EXTRA_UNBOUND = r"""$PY - <<'E' || { echo "WHY: real-package audit does not flag the stolen radio signal entries"; exit 1; }
from pathlib import Path
from storygame.audit import audit_package
r = audit_package(Path("data/stories/continuity-initiative"))
fs = r["findings"]
hits = [f for f in fs if f["check"] == "delivery_names_unbound_item"]
print("delivery_names_unbound_item findings:", len(hits))
assert any("stolen radio" in f["detail"] for f in hits), "stolen radio not flagged"
E
"""

EXTRA_BUDGET = r"""$PY -m storygame.audit_budget > /tmp/tg-budget-table.txt 2>&1 || { cat /tmp/tg-budget-table.txt; echo "WHY: audit_budget CLI failed"; exit 1; }
cat /tmp/tg-budget-table.txt
for s in 1A 1B 1C 2A 2B 2C 3A 3B 3C; do grep -q "$s" /tmp/tg-budget-table.txt || { echo "WHY: scene $s missing from the table"; exit 1; }; done
python3 -c "import json;d=json.load(open('tests/fixtures/deep_turn_budget.json'));assert len(d['scenes'])==9, d" || { echo "WHY: fixture lacks nine scenes"; exit 1; }
"""


def check(key: str, allowed: str, tests: str, extra: str) -> str:
    return (
        CHECK_COMMON.replace("EXTRA", extra)
        .replace("ALLOWED", allowed)
        .replace("TESTS", tests)
        .replace("KEY", key)
        .replace("OUTDIR", OUT)
        .replace("REPO", REPO)
    )


manifest = {
    "run_name": "pattern-guards-1-and-3",
    "workdir": OUT,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "guard1-unbound-item",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 1,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": ["storygame/audit.py", "tests/test_audit_unbound_item.py", "tests/test_package_audit.py"],
            "spec": SPEC_UNBOUND,
            "check": check(
                "guard1",
                "storygame/audit.py|tests/test_audit_unbound_item.py|tests/test_package_audit.py",
                "tests/test_audit_unbound_item.py tests/test_package_audit.py tests/test_prompt_budget.py",
                EXTRA_UNBOUND,
            ),
            "expect_files": [],
            "verified": "new audit check built tests-first; flags the 3A stolen-radio hand-off; known real-package findings pinned in an allowlist",
        },
        {
            "key": "guard3-deep-turn-budget",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 1,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/audit_budget.py",
                "tests/test_audit_budget.py",
                "tests/fixtures/deep_turn_budget.json",
            ],
            "spec": SPEC_BUDGET,
            "check": check(
                "guard3",
                "storygame/audit_budget.py|tests/test_audit_budget.py|tests/fixtures/deep_turn_budget.json",
                "tests/test_audit_budget.py tests/test_prompt_budget.py tests/test_knowledge_projection.py",
                EXTRA_BUDGET,
            ),
            "expect_files": [],
            "verified": "deep-turn prompt size measured per scene with a ratchet fixture; scenes over 6,500 reported as known items",
        },
    ],
}
Path(__file__).with_name("guards-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
