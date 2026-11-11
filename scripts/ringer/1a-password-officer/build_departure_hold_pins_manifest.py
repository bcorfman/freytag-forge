# ruff: noqa: E501
"""One Ringer task: update the old pins that count the new 1A departure-hold storylet and record."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
T = f"{R}/tests"
FILES = [
    f"{T}/{n}"
    for n in (
        "test_scene_relative_pacing.py",
        "test_drawer_avoidance_repro.py",
        "test_drawer_gap_nudge.py",
        "test_richer_1c.py",
        "test_design_review_fixtures.py",
        "shard_durations.json",
    )
]
RUN = "tests/test_scene_relative_pacing.py tests/test_drawer_avoidance_repro.py tests/test_drawer_gap_nudge.py tests/test_richer_1c.py tests/test_design_review_fixtures.py tests/test_regen_shard_durations.py tests/test_1a_departure_hold.py tests/test_markdown_story_package.py"

spec = f"""You are a test-repair worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, do NOT edit story data ({R}/data), engine code (storygame/) or any file other than the ones you own: {", ".join(FILES)}.

CONTEXT. A new optional scene-1A storylet SL-1A-K and a new repeatable knowledge record k_sl_1a_k_r1 (requires michelle_lead_actionable; establishes departure_held; storylet window earliest 4, target 10, latest 12) were just added to data/stories/continuity-initiative. The full suite shows six pin failures, all caused by them, and you fix exactly these:
1. tests/test_scene_relative_pacing.py::test_scene_windows_and_storylet_targets_leave_room_for_every_beat: expected 1A target list [2, 3, 3, 4, 5, 5, 5, 6, 8, 8] gains the new target 10 -> [2, 3, 3, 4, 5, 5, 5, 6, 8, 8, 10].
2. tests/test_drawer_avoidance_repro.py::test_static_drawer_dependencies_have_no_later_scene_dependents: the expected dependent id set gains 'k_sl_1a_k_r1' (it requires michelle_lead_actionable, which only drawer-dependent records establish). Confirm that is the reason by reading _drawer_dependency_graph before editing; the record is a scene-1A record, so the 'no later scene dependents' purpose still holds.
3. tests/test_drawer_gap_nudge.py::test_real_package_repeatable_flags_are_only_on_the_gap_nudges: the repeatable set gains 'k_sl_1a_k_r1'. Add a module constant for it, and rename the test to test_real_package_repeatable_flags_are_only_on_the_nudges_and_the_departure_hold (update any reference to the old name).
4. tests/test_richer_1c.py::test_michelle_glimpse_contract_is_uncertain_and_preserves_its_metadata: the two counts 121 become 122.
5. tests/test_design_review_fixtures.py: a previous worker wrongly changed the eligible count from 9 to 10 (and the reveal_universe count from 9 to 10). Restore the file to the committed version with `cd {R} && git checkout HEAD -- tests/test_design_review_fixtures.py`. Then run its test: if test_more_than_four_eligible passes, leave the file exactly as committed. If it fails, find out why by printing the eligible ids on a scratch copy, update only the number the printout proves, and say why in a comment.
6. tests/test_regen_shard_durations.py::test_real_manifest_covers_test_files: tests/test_1a_departure_hold.py is missing from tests/shard_durations.json. Fix with the repo script: `cd {R} && {ENV} && {PY} scripts/regen_shard_durations.py --missing-only`, and check the diff of tests/shard_durations.json is only the added entry.
Never delete a test; never weaken an assertion that still holds. tests/test_1a_departure_hold.py is NOT yours: do not edit it.

HOW TO RUN (from {R}; never bare python, never uv): `{ENV} && {PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider 2>&1 | tail -30`. Never use --cov. Then `{PY} -m ruff check tests && {PY} -m ruff format --check tests`. All must pass."""

check = f"""set -e
set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider > /tmp/departure-pins.txt 2>&1 || (tail -40 /tmp/departure-pins.txt; exit 1)
tail -3 /tmp/departure-pins.txt
{PY} -m ruff check tests
{PY} -m ruff format --check tests
git diff --stat -- tests/shard_durations.json tests/test_design_review_fixtures.py
"""

m = {
    "run_name": "1a-departure-hold-pins",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-departure-hold-pins",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [
        {
            "key": "repair-departure-hold-pins",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 1800,
            "ownership": FILES,
            "expect_files": FILES[:4],
            "spec": spec,
            "check": check,
            "verified": "the six pin failures pass and the departure-hold tests stay green",
        }
    ],
}
path = Path(D) / "departure-hold-pins-manifest.json"
path.write_text(json.dumps(m, indent=2) + "\n")
print(path)
