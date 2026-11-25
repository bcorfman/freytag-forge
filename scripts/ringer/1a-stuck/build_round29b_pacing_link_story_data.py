# ruff: noqa: E501
"""Round 29b: Step 2 task 2.2b. Declare `delivers` on the 12 pacing beats the validator named, through the story CLI,
and pin the real package as clean. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-29"
PY = ".venv/bin/python"

PAIRS = [
    ("transfer_withdrawal_1c", "k_bridge_1c_infiltration"),
    ("inspection_window_2a", "k_inspection_window_missed"),
    ("inspection_nudge_2a", "k_supervisor_escorting"),
    ("inspection_recovery_2a", "k_inspection_recovery_ready"),
    ("audit_recovery_2b", "k_audit_recovery_ready"),
    ("audit_window_2b", "k_audit_window_missed"),
    ("purge_recovery_2c", "k_purge_recovery_ready"),
    ("purge_nudge_2c", "k_sl_2c_e_route_effects"),
    ("purge_window_2c", "k_purge_window_missed"),
    ("evacuation_nudge_3c", "k_evacuation_recovery_ready"),
    ("evacuation_window_3c", "k_sl_3c_h_route_effects"),
    ("evacuation_recovery_3c", "k_sl_3c_h_route_effects"),
]
pairs_text = "\n".join(f"  {e} -> {k}" for e, k in PAIRS)
pairs_py = json.dumps(PAIRS)

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""

OWNED_RE = r"^(data/stories/continuity-initiative/source/scenes/(1C|2A|2B|2C|3C)\.yaml|tests/test_pacing_links_story\.py|tests/test_pacing_links\.py|tests/shard_durations\.json|data/stories/continuity-initiative/entry/.*)$"

SPEC = b.COMMON + (
    "You may edit ONLY: the scene source files data/stories/continuity-initiative/source/scenes/{1C,2A,2B,2C,3C}.yaml (and ONLY through the story CLI, never by hand), "
    "the scene-entry snapshot files under data/stories/continuity-initiative/entry/ that `python -m storygame.runtime.entry_snapshots write` regenerates, tests/test_pacing_links_story.py (new), tests/test_pacing_links.py (ONLY the one test named below) and tests/shard_durations.json (one entry for the new test file, value 2.0). Nothing else.\n\n"
    "BACKGROUND. Round 29a added an optional pacing-beat key `delivers` (a list of knowledge claim ids) and the validator storygame/story_package/pacing_links.py::pacing_link_problems(package). "
    "On the real story it reports 11 pressure items that no beat declares. Declare them now. The twelve (event id -> knowledge item) declarations, each beat's `delivers` list getting the items shown "
    "(the beat `evacuation_window_3c` and `evacuation_recovery_3c` both get k_sl_3c_h_route_effects):\n"
    + pairs_text
    + "\n\nHOW. Read docs/contributor-guide/runtime-and-authoring-boundaries.md and run `.venv/bin/python -m storygame.story_cli set --help` and `show --help`. Story source is edited ONLY with `python -m storygame.story_cli` "
    "(`set <address> <yaml_value>`, `--add`, `--drop`); find the address form by running `story_cli show` on one beat first (beats are the `beats:` list of each scene file, keyed by beat `id`). "
    "Never edit the YAML by hand. After the edits run `.venv/bin/python -m storygame.story_cli fmt` then `.venv/bin/python -m storygame.story_cli fmt --check` (must pass), and `.venv/bin/python -m storygame.runtime.entry_snapshots write` so the entry snapshots match the source. "
    "If a beat id above does not exist in the scene named by its suffix, or the CLI cannot add the key, stop and say so in NOTES.txt rather than hand-editing.\n\n"
    "TEST, WRITE IT FIRST in tests/test_pacing_links_story.py (hermetic; `load_story_package(default_package_root())`): (1) `pacing_link_problems(package)` returns `[]` on the real package; "
    "(2) the declarations are exactly these (event id, item id) pairs, no others, as a set equality over `[(e.id, item) for e in package.pacing.events for item in e.delivers]`: "
    + pairs_py
    + "; (3) every declared item is a knowledge item whose `earn_when` is None and which has no `action_evidence`. Run it before the edits to see it fail, then make the edits.\n"
    "OLD TEST THAT THIS CHANGE DELIBERATELY BREAKS: tests/test_pacing_links.py::test_real_package_has_exactly_eleven_unlinked_pressure_items asserts the real package has 11 undeclared pressure items. After your edits the real package declares them all, so update that one test to keep its purpose (the validator finds the 11 when the links are missing): derive a package copy whose pacing events have their `delivers` emptied (pydantic `model_copy(update={\"delivers\": ()})` on each event, rebuilding `package.pacing` the same way the other tests in that file derive copies) and run the same assertions against it. Do not change any other test in that file. "
    "Then run the neighbouring tests that load the real package or snapshots: tests/test_pacing_links.py, tests/test_contract_scene.py, tests/test_trailing_pacing_events.py, and `grep -l entry_snapshots tests/*.py` files; if one fails because of this deliberate data change, report it in NOTES.txt and do not edit it (it is outside your ownership)."
)

CHECK = (
    SETUP
    + f"""git add -A -- data tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '{OWNED_RE}' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
{PY} -m storygame.story_cli fmt --check || {{ echo "story_cli fmt --check failed: source was not written by the CLI"; exit 1; }}
{PY} -m storygame.runtime.entry_snapshots check || {{ echo "entry snapshots do not match the source; run entry_snapshots write"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/test_pacing_links_story.py tests/test_pacing_links.py tests/test_contract_scene.py tests/test_trailing_pacing_events.py $(grep -l entry_snapshots tests/*.py | tr '\\n' ' ') 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
grep -q '"tests/test_pacing_links_story.py"' tests/shard_durations.json || {{ echo "tests/shard_durations.json lacks the new test file"; exit 1; }}
{PY} -m json.tool tests/shard_durations.json > /dev/null
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/pacing-link-data.patch"
test -s "$WORK/out/pacing-link-data.patch"
"""
)

manifest = {
    "run_name": "factory-29b-pacing-link-story-data",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "pacing-link-data",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": [
                "data/stories/continuity-initiative/source/scenes/1C.yaml",
                "data/stories/continuity-initiative/source/scenes/2A.yaml",
                "data/stories/continuity-initiative/source/scenes/2B.yaml",
                "data/stories/continuity-initiative/source/scenes/2C.yaml",
                "data/stories/continuity-initiative/source/scenes/3C.yaml",
                "data/stories/continuity-initiative/entry/",
                "tests/test_pacing_links_story.py",
                "tests/test_pacing_links.py",
                "tests/shard_durations.json",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The 12 beats declare their knowledge items through the story CLI, fmt --check passes, snapshots match, and the validator reports no problem on the real package.",
        }
    ],
}
Path(__file__).with_name("round29b-pacing-link-story-data-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
