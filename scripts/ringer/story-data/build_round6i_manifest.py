# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6i: fix the tests the flip of the default story broke (4 parallel tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6i"

COMMON = (
    "You are a Python test engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12).

BACKGROUND. The default story data/stories/continuity-initiative/ was just FLIPPED: it now holds only `ownership.yaml` and `source/` (a compiled source tree; format in .plans/story-data-schema-contract.md, read-only to you). Its nine legacy files (plot.md, world.yaml, knowledge.yaml, pacing.yaml, storylets.md, storylet-routes.yaml, handoffs.yaml, incidents.yaml, connections.yaml) were MOVED to tests/fixtures/parity/continuity-initiative/legacy/, a frozen parity reference loadable only with `storygame.story_package.loader.load_legacy_story_package(root)`. `load_story_package(root)` loads compiled stories (ownership.yaml present) and legacy ones (fixture and bench/frozen packages with their own plot.md etc.; they stay legacy forever). Test helpers: tests/story_source/helpers.py (`compiled_story_copy(tmp_path)` copies the default story's source tree with ownership.yaml; `patch_source(root, "source/<file>", "<dotted.address>", value)` edits a copy by record id; `load_compiled_copy`). Variations (bench/variations/*.json) patch files of a story package by exact text replacement (bench/core.py `materialize_package` copies the whole package dir and then patches relative file names, so a variation for the compiled story must name source files like `source/scenes/3C.yaml`). A SourceError (storygame.story_source.diagnostics) message starts with a diagnostic code like `L2.seat_lines`; read storygame/story_source/l1_*.py and l2_*.py for the codes.

Your tests currently fail because they read legacy files by name from the default story, patch variation files that no longer exist there, or catch only `StoryPackageError` while the compiled route raises `SourceError`. Fix each so it tests the same thing it tested before. DECISION RULES (already made, do not reopen):
1. A test about a FROZEN or HISTORICAL experiment (a bench/frozen/* package, an old variation that patches legacy files, a past probe's recorded cases) keeps meaning "the legacy story": point it at the frozen legacy copy with `load_legacy_story_package(Path("tests/fixtures/parity/continuity-initiative/legacy"))` or at its own frozen package. Do not recompile history.
2. A test about the LIVE story's content or behaviour reads the compiled story via `load_story_package(Path("data/stories/continuity-initiative"))` or a `compiled_story_copy`. If it patches the story, express each patch with `patch_source` or, for a variation JSON, as text replacements on the real source file (`source/...yaml`); verify each replacement matches exactly once by loading the result.
3. NEVER delete a test, skip or xfail one, or weaken an assertion (no `Exception` catch-alls, no dropped asserts, no looser equality). The one allowed loosening: the compiled story's cross-scene order of `knowledge.knowledge`, `storylets` and `deliveries` differs from the legacy file order (the parity gate treats this as `collection_order`; within a scene order is kept). If a test asserts the exact legacy LIST ORDER of such a collection and nothing else about order, compare as a set or sorted list instead and say which tests you did this to in NOTES_<key>.txt (worktree root, never committed). If an assertion about CONTENT (not order) differs between legacy and compiled, that is a real parity gap: do not change the test, write the exact difference into NOTES_<key>.txt and leave that test failing.
4. Edit only files in your ownership list. Never edit storygame/, docs/, data/, the contract, tests/shard_durations.json.
"""
)

TASKS = {
    "r6i-source-error": {
        "owned": ["tests/test_seating.py", "tests/test_world_seats.py", "tests/test_place_scoped_feed.py"],
        "tests": ["tests/test_seating.py", "tests/test_world_seats.py", "tests/test_place_scoped_feed.py"],
        "spec": COMMON
        + """
YOUR TESTS: tests/test_seating.py, tests/test_world_seats.py, tests/test_place_scoped_feed.py. Five tests fail only because they catch `StoryPackageError` while the compiled route raises `SourceError` (the new source checks `L2.seat_lines`, `L2.axis_pole`, `L2.blank_description` do fire). Widen each failing test to `pytest.raises((StoryPackageError, SourceError), match=...)` like the already-ported tests, keeping the `match` text satisfied by the real message (read the SourceError message the test now gets and adjust the regex only if it is wrong because of the diagnostic's wording, never to something looser than the code plus the offending record). The tests that currently pass stay as they are.
""",
    },
    "r6i-probes": {
        "owned": [
            "tests/test_act2_guard_probe.py",
            "tests/test_hidden_bench_arm_probe.py",
            "tests/test_holder_wording_probe.py",
            "tests/test_opening_condition_v2.py",
            "scripts/ringer/**",
        ],
        "tests": [
            "tests/test_act2_guard_probe.py",
            "tests/test_hidden_bench_arm_probe.py",
            "tests/test_holder_wording_probe.py",
            "tests/test_opening_condition_v2.py",
        ],
        "spec": COMMON
        + """
YOUR TESTS: tests/test_act2_guard_probe.py, tests/test_hidden_bench_arm_probe.py, tests/test_holder_wording_probe.py, tests/test_opening_condition_v2.py, and the probe scripts they drive (you own `scripts/ringer/**` for this task; find them by reading the tests' imports; the probes copy the default story package and read or patch its legacy files by name, for example `knowledge.yaml`, `plot.md`, `world.yaml`, which are gone). Failures to fix: FileNotFoundError on `<arm>/knowledge.yaml` and `<arm>/plot.md`, and holder-wording cases that rely on the legacy package. For probes that are historical experiments with recorded, locked cases (hidden-bench arms, holder wording lock files) keep their legacy meaning (rule 1) by building the probe's package from the frozen legacy copy; for probes that run against the live story (opening condition v2, act2 guard arms) read the source tree (rule 2) and change the probe script only as far as needed (it should read the loaded package or the source files). Keep each probe's recorded/locked outputs unchanged (lock files must not change).
""",
    },
    "r6i-3c-variations": {
        "owned": [
            "tests/test_3c_families_offer_arm.py",
            "tests/test_3c_families_offer_probe.py",
            "tests/test_3c_surface_binding.py",
            "tests/test_3c_recall_live.py",
            "bench/variations/stage7-3c-*.json",
        ],
        "tests": [
            "tests/test_3c_families_offer_arm.py",
            "tests/test_3c_families_offer_probe.py",
            "tests/test_3c_surface_binding.py",
            "tests/test_3c_recall_live.py",
        ],
        "spec": COMMON
        + """
YOUR TESTS: tests/test_3c_families_offer_arm.py, tests/test_3c_families_offer_probe.py, tests/test_3c_surface_binding.py, tests/test_3c_recall_live.py and the variation files bench/variations/stage7-3c-*.json they load. The variations patch `world.yaml`/`handoffs.yaml` by text replacement ("override file does not exist in story package"). `test_3c_recall_live::test_broadcast_cli_guard_and_request_cap_with_stubbed_network` and `test_3c_families_offer_probe::test_score_uses_real_post_c_selector` may fail for other reasons (a missing recorded file, or a stale test skipped on main): check with `git stash`-free reasoning, i.e. read the error, and if a test is skipped or fails on `main` for reasons unrelated to the flip, say so in NOTES and leave it. For each variation that targets the live story, rewrite its `overrides` so every replacement targets the equivalent text in the real source file (find where the legacy text now lives: the converter maps world.yaml to source/catalog.yaml and scene files; handoffs to the scene file's reveal/entry handoff fields), with the `old` string appearing exactly once in that file. Apply rule 2; the effective package a variation yields must behave as before (its tests assert that).
""",
    },
    "r6i-live-content": {
        "owned": [
            "tests/test_1c_closeout.py",
            "tests/test_2b_delivery_repeat.py",
            "tests/test_delivery_restatement.py",
            "tests/test_voiceable_knowledge.py",
        ],
        "tests": [
            "tests/test_1c_closeout.py",
            "tests/test_2b_delivery_repeat.py",
            "tests/test_delivery_restatement.py",
            "tests/test_voiceable_knowledge.py",
        ],
        "spec": COMMON
        + """
YOUR TESTS: tests/test_1c_closeout.py (`_routes()` now returns StoryletRoute objects, the test indexes it like a dict), tests/test_2b_delivery_repeat.py::test_the_gating_of_the_two_entries_is_unchanged (live compiled entry vs the frozen pre-richer package `bench/frozen/continuity-pre-richer-2b`: first find out whether the differing `establishes` operations are only operation ORDER (legacy `op_order`, allowed by the contract for `k_sl_1a_b_r1`, `k_sl_2b_b_r4`, `k_sl_2b_b_r5`) or real; if only order, compare the operation lists as sets and say so in NOTES; if real, write the exact difference in NOTES and leave the test failing), tests/test_delivery_restatement.py::test_the_check_finds_the_known_restatements_in_the_frozen_pre_1c_story (this fails even before the flip: its helper `_restatement_findings` has a compiled branch that reads `root / "source"` for the FROZEN legacy package `bench/frozen/continuity-pre-richer-1c`; find the real cause), and tests/test_voiceable_knowledge.py::test_real_package_has_exactly_the_non_voiceable_knowledge_items (an exact-list-order assertion; rule 3 order allowance applies, but check that the SET of non-voiceable ids equals the legacy set exactly).
""",
    },
}


def check(key: str, item: dict) -> str:
    owned = item["owned"]
    tests = " ".join(item["tests"])
    py_owned = [p for p in owned if p.endswith(".py")]
    pat = " ".join(f"-e '^{p.replace('**', '.*').replace('*', '[^/]*')}$'" for p in owned)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {tests} > "$out" 2>&1 || rc=$?
tail -30 "$out"
if [ "$rc" -ne 0 ]; then
  if [ -e NOTES_{key}.txt ] && grep -qiE "real parity gap|unrelated to the flip|stale" NOTES_{key}.txt; then echo "failures excused in NOTES: review them"; else exit "$rc"; fi
fi
if git diff -U0 -- tests | grep -E "^\\+.*(pytest\\.(skip|xfail)|raises\\(Exception)"; then echo "forbidden skip/xfail"; exit 1; fi
before=0; for f in {tests}; do n=$(git show HEAD:$f | grep -cE "^def test_|^    def test_" || true); before=$((before+n)); done
after=$(cat {tests} | grep -cE "^def test_|^    def test_" || true)
[ "$after" -ge "$before" ] || {{ echo "tests deleted: $before -> $after"; exit 1; }}
.venv/bin/python -m ruff check {" ".join(py_owned)}
.venv/bin/python -m ruff format --check {" ".join(py_owned)}
git add -A -- tests scripts bench
bad=$(git diff --cached --name-only | grep -v {pat} || true)
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
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 1200,
                "ownership": item["owned"],
                "spec": item["spec"].replace("<key>", key),
                "check": check(key, item),
                "expect_files": [],
                "verified": "the listed tests pass against the flipped story (or are excused in NOTES with a stated cause); none deleted, skipped or weakened; only owned files changed; ruff clean.",
            }
        )
    return {
        "run_name": "story-data-round6-checks",
        "workdir": WORK,
        "max_parallel": 4,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6i-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
