# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6e-1: bring the converted default story back to real parity (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6e1"
KEY = "r6e1-real-parity"

OWNED = [
    "storygame/story_source/convert.py",
    "storygame/story_source/convert_reveals.py",
    "storygame/story_source/convert_scene.py",
    "storygame/story_source/convert_facts.py",
    "storygame/story_source/convert_catalog.py",
    "storygame/story_source/c_knowledge.py",
    "storygame/story_source/c_scene.py",
    "storygame/story_source/compiler.py",
    "storygame/story_source/l1_scene.py",
]
OWNED_PREFIXES = [
    "data/stories/continuity-initiative/source/",
    "tests/fixtures/story_source/",
    "tests/story_source/",
]

SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The default story's legacy files (data/stories/continuity-initiative/*.yaml and *.md) are converted by `storygame.story_source.convert.write_source_tree` into a source tree, committed at data/stories/continuity-initiative/source/, which `storygame.story_source.compile_source_tree` compiles back into a StoryPackage. The parity gate `tests/story_source/test_parity_default.py` compares the compiled package with the legacy-loaded one. The format is fixed by .plans/story-data-schema-contract.md (read sections 4.8, 5, 9, 10 and the Q3/Q4 decisions; never edit it). The parity checker used to hide content differences whenever a keyed list was reordered; that is fixed, and the gate now FAILS with 627 unreviewed differences. See the list: run the gate logic yourself (copy the steps of test_parity_default.py into a script; do not edit that test) and group the differences. They are:
(1) 617 `storylets.<id>.sections[...]` differences: the legacy storylets.md section texts (Dramatic purpose, Available when, Participants / items, Possible realizations, Effects, Completion, Abort, Protected boundary, Non-coercion note:, Allowed scene:, and the rendered Pacing window / Source beats texts) are not in the converted source tree at all. The contract (Q3, decided) keeps them verbatim as reveal `notes` so no author text is lost; c_knowledge.py `_sections` already renders `notes` into the compiled sections, but the converter never writes them. Make the converter write every section's legacy text into the matching reveal's `notes` (keys as `_sections` expects, add any missing key to `_sections` and to the layer 1 key list in l1_scene.py), and make the compiler reproduce each section byte for byte. Where a section is derived from source fields (Pacing window from the window, Source beats from from_outline, Allowed scene), the derived text must equal the legacy text exactly; if the legacy text differs from what the derivation renders for any storylet, store the legacy text as a `notes` override for that storylet rather than changing the derivation, and say how many overrides you needed in NOTES_r6e1.txt.
(2) 3 `storylets.<id>.title` differences and `storylets.SL-3C-E.target_turn` / `latest_turn`: find out why (converter or compiler) and fix at the source so compiled equals legacy.
(3) 5 `pacing.events.<id>.effects` differences (audit_nudge_2b, destruction_3b, kristin_steadies_1a, override_deadline_3a, pursuit_1b): the compiler function `_supply_transition_sources` in compiler.py adds effects to the first pacing event of a scene so that a transition trigger has a producer. It is documented as being for reduced test fixtures, but it also runs on the real story and injects effects the legacy story does not have (for example kristin_steadies_1a gains michelle_lead_actionable and memory_card_recovered, which would mark the memory card recovered when a timed event fires, with no player action). The real story compiles and passes the inherited loader checks without it. Remove the silent repair from the compile path. Do not replace it with another silent repair. A full story whose transition trigger has no producer must fail with an error that names the transition and the fact (the inherited loader check `_validate_transition_trigger_sources` already says so; keep that message). Reduced fixtures under tests/fixtures/story_source/ that relied on the repair must now declare the producer explicitly in their own source (for example a beat or bridge that sets the trigger fact); edit those fixtures minimally and list every fixture you touched in NOTES_r6e1.txt. tests/test_exit_backstop_invariant.py monkeypatches the repair; do not edit it (another worker owns it): if removing the function breaks that monkeypatch, keep a no-op `_supply_transition_sources(pacing, incidents, routes)` that returns `pacing` unchanged, with a comment saying why.

DONE MEANS: `tests/story_source/test_parity_default.py` passes with the only reviewed difference being the existing `world.facts` entry (do NOT add reviewed entries; do not edit any *.reviewed.yaml); the committed source tree is regenerated so `tests/story_source/test_source_tree_drift.py` passes (regenerate with: `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python - <<'X'\\nfrom pathlib import Path\\nfrom storygame.story_package.loader import load_legacy_story_package\\nfrom storygame.story_source.convert import write_source_tree\\nimport shutil\\nr=Path('data/stories/continuity-initiative/source'); shutil.rmtree(r); write_source_tree(load_legacy_story_package(Path('data/stories/continuity-initiative')), r)\\nX` using a heredoc terminator other than E); all of tests/story_source passes; and the compiled default package behaves as legacy: also run tests/test_loader_source_dispatch.py.

HARD LIMITS. Edit only the owned storygame/story_source modules, files under data/stories/continuity-initiative/source/ (by regeneration only), and files under tests/fixtures/story_source/ and tests/story_source/ (existing tests there may be edited ONLY where they encode the removed repair or the old converter output; never weaken an assertion; list each in NOTES_r6e1.txt). Never edit the contract, docs/, the legacy story files, *.reviewed.yaml files, tests/shard_durations.json, or any test outside tests/story_source/. If a difference needs a contract decision, write it in NOTES_r6e1.txt with the exact paths and leave it failing.
"""
)


def check() -> str:
    exact = " ".join(f"-e '^{p}$'" for p in OWNED)
    prefixes = " ".join(f"-e '^{p}'" for p in OWNED_PREFIXES)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_parity_default.py tests/story_source/test_source_tree_drift.py > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source tests/test_loader_source_dispatch.py > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
reviewed=$(cat tests/fixtures/parity/continuity-initiative/*.reviewed.yaml | grep -c "path:" || true)
[ "$reviewed" -le 1 ] || {{ echo "more than the one world.facts review entry: $reviewed"; exit 1; }}
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame tests data
bad=$(git diff --cached --name-only | grep -v {exact} {prefixes} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
[ ! -e NOTES_r6e1.txt ] || cp NOTES_r6e1.txt {WORK}/NOTES_r6e1.txt
"""


manifest = {
    "run_name": "story-data-round6",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": KEY,
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 5400,
            "check_timeout_s": 1800,
            "ownership": OWNED + OWNED_PREFIXES,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "with the order-hiding bug fixed, the default story compiles to the legacy package with only the world.facts review; sections kept as notes; no silent producer repair; source tree regenerated and drift test green; tests/story_source green; ruff clean.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round6e1-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
