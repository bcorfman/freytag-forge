# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6d: read-only scouts that classify the 15 blocked loader tests (6 tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6d-scout"
SCRATCH = "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/ac2494da-eb1b-431b-a8b5-379acfca776d/scratchpad/blocked/tests"
LABELS = "MISSING_CHECK|COMPILER_DROPS_FIELD|UNREPRESENTABLE_BY_DESIGN|MIGRATION_ERROR"

FILES = {
    "world_seats": ("test_world_seats", ["test_axis_unavailable_must_be_a_pole", "test_npc_axis_unavailable_must_be_a_pole"]),
    "seating": ("test_seating", ["test_loader_rejects_a_seat_without_its_lines", "test_loader_rejects_a_seat_without_its_leave_line"]),
    "place_scoped_feed": ("test_place_scoped_feed", ["test_loader_rejects_blank_location_description"]),
    "markdown_story_package": (
        "test_markdown_story_package",
        [
            "test_group_scoped_alias_loader_rejects_declared_name",
            "test_loader_rejects_transition_trigger_that_can_never_fail",
            "test_loader_rejects_ambiguous_knowledge_effect_and_unreachable_prerequisite",
            "test_loader_rejects_invalid_canonical_event_and_scene_entry_sources",
            "test_loader_rejects_invalid_transition_graph[loader_rejects_ambiguous_transition_priority]",
            "test_loader_rejects_duplicate_fact_delivery",
            "test_loader_rejects_delivery_for_world_only_fact",
            "test_loader_rejects_bridge_text_keys_that_do_not_match_transition_ids",
        ],
    ),
    "gap_rules": ("test_gap_rules", ["test_no_strand_seeded_defect_and_clean_variant", "test_single_reveal_strand_seeded_defect_and_clean_variant"]),
    "3c_recall_live": ("test_3c_recall_live", ["test_c1_only_does_not_make_surface_fact_true_and_c_orders_unlock_d"]),
}


def spec(key: str, stem: str, tests: list[str]) -> str:
    listing = "\n".join(f"  - {t}" for t in tests)
    return f"""You are a read-only investigator. Your current working directory is {REPO}. NEVER edit, create or delete any file inside {REPO}; never git commit; never call a billed model or the network; never run `uv`. Write only into {WORK}/{key}/ (create it). Run python as `PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp {REPO}/.venv/bin/python` and pytest with `-p no:cacheprovider -n 0` (never --cov).

BACKGROUND. The default story's data moved from nine legacy files (plot.md, storylets.md, world.yaml, knowledge.yaml, storylet-routes.yaml, handoffs.yaml, incidents.yaml, pacing.yaml, connections.yaml) to a source tree, data/stories/continuity-initiative/source/ (story.yaml, catalog.yaml, scenes/<id>.yaml, scenes/<id>.match.yaml), compiled by `storygame.story_source.compile_source_tree` into the same `StoryPackage`. The format is defined in .plans/story-data-schema-contract.md (read the sections you need; never edit). Tests help: tests/story_source/helpers.py has `compiled_story_copy(tmp_path)` (a copy holding source/ and ownership.yaml only, loadable with `storygame.story_package.loader.load_story_package(root)`), and `patch_source(root, file, address, value)`. The legacy files still exist in data/stories/continuity-initiative for now, so you can read them to understand what the legacy tests mutated.

The legacy test file is {SCRATCH}/{stem}.legacy.py: each test there builds a bad story by rewriting a legacy file and asserts the legacy loader (storygame/story_package/loader.py) rejects it. The file {SCRATCH}/{stem}.py is a first attempt at porting the same tests to the source tree; these tests currently FAIL because the compiled package loads without the error the legacy loader raised. Do not trust that port: its mutation may be wrong.

THE QUESTION. Someone proposes retiring these tests because 'the source format cannot express the mistake'. That claim must be proven or refuted, test by test. For EACH of these failing tests:
{listing}
1. Name the legacy loader check the test exercises (file:line in storygame/story_package/loader.py) and the authoring mistake it guards against, in one sentence.
2. Find the source-tree field(s) that carry the same information (contract section, source file, address). Apply the equivalent mutation to a compiled_story_copy in a repro script `{WORK}/{key}/repro_<n>.py` (n = 1, 2, ...; one script per test, self-contained: it builds its own copy under tempfile, applies the mutation, then loads it and prints exactly one final line `OUTCOME: ACCEPTED` or `OUTCOME: REJECTED <first 120 chars of the error>`; it must exit 0 in both cases, and put the repo root on sys.path itself). The mutation must be the faithful analogue of the legacy one.
3. If it is ACCEPTED, find out WHY with evidence: which stage (layer 1 shape, layer 2 reference checks, compiler, inherited loader checks run on the built package) lacks the check, or which compiler step drops or derives the field so the bad value never reaches the package. Read storygame/story_source/*.py (l1_*.py, l2_*.py, c_*.py, compiler.py) and cite file:line.
4. Classify with exactly one label: MISSING_CHECK (the source can say it, nothing rejects it; a check should be added: say at which layer and what diagnostic), COMPILER_DROPS_FIELD (the source schema accepts the field but the compiler does not carry it, so the runtime ignores the authored value: a defect even if no check fires), UNREPRESENTABLE_BY_DESIGN (the contract makes the mistake impossible to write, because a field is derived or a link is by id; cite the contract section and show that the derived value is always consistent; say what authors can no longer say), or MIGRATION_ERROR (the first port's mutation was not the right analogue: your repro's faithful mutation is REJECTED). Be strict: UNREPRESENTABLE_BY_DESIGN is only for a mistake that truly cannot be written, and you must try at least two different ways to write it in the source before concluding that. If the information the legacy loader checked now has NO source field at all, say what was lost and whether an author could now silently produce a broken story.
5. Give a recommendation: what check, compiler change or test rewrite would keep this class of mistake caught. A rewritten test must still assert the rejection.

OUTPUT: {WORK}/{key}/report.md with one section per test and, for each test, exactly one line of this form (nothing else on the line):
VERDICT: <test name as listed above> = <LABEL> | repro=repro_<n>.py | outcome=<ACCEPTED or REJECTED>
and one line `RISK: <test name> = <HIGH|MEDIUM|LOW> <one sentence on the player or author impact if this goes uncaught>`.
If a test cannot be investigated, say why in the report and write `VERDICT: <test> = UNKNOWN | repro=none | outcome=NONE` (the check will fail that and show the reason, which is fine).
"""


CHECK_PY = '''
import re, subprocess, sys
from pathlib import Path
work = Path("__WORK__/__KEY__")
report = work / "report.md"
assert report.is_file(), "no report.md"
text = report.read_text()
tests = __TESTS__
labels = "__LABELS__".split("|")
bad = []
for t in tests:
    m = re.findall(r"^VERDICT: " + re.escape(t) + r" = (\\w+) \\| repro=(\\S+) \\| outcome=(\\w+)\\s*$", text, re.M)
    if len(m) != 1:
        bad.append(f"{t}: need exactly one VERDICT line, found {len(m)}")
        continue
    label, repro, outcome = m[0]
    if label not in labels:
        bad.append(f"{t}: label {label} not one of {labels}")
        continue
    if not re.search(r"^RISK: " + re.escape(t) + r" = (HIGH|MEDIUM|LOW) .+", text, re.M):
        bad.append(f"{t}: missing RISK line")
    script = work / repro
    if not script.is_file():
        bad.append(f"{t}: repro {repro} missing")
        continue
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=300)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    if r.returncode != 0:
        bad.append(f"{t}: repro exit {r.returncode}: {r.stderr[-300:]}")
        continue
    got = "ACCEPTED" if last.startswith("OUTCOME: ACCEPTED") else "REJECTED" if last.startswith("OUTCOME: REJECTED") else "NONE"
    if got != outcome:
        bad.append(f"{t}: report says {outcome} but repro printed {last[:100]!r}")
    if label == "MIGRATION_ERROR" and got != "REJECTED":
        bad.append(f"{t}: MIGRATION_ERROR requires the faithful repro to be REJECTED")
    if label in ("MISSING_CHECK", "COMPILER_DROPS_FIELD", "UNREPRESENTABLE_BY_DESIGN") and got != "ACCEPTED":
        bad.append(f"{t}: {label} requires the repro to be ACCEPTED")
    if label == "UNREPRESENTABLE_BY_DESIGN" and len(text) < 1500:
        bad.append("report too thin to support UNREPRESENTABLE_BY_DESIGN")
if bad:
    print("\\n".join(bad))
    sys.exit(1)
print("report verified:", len(tests), "tests")
'''


def check(key: str, tests: list[str]) -> str:
    script = CHECK_PY.replace("__WORK__", WORK).replace("__KEY__", key).replace("__TESTS__", json.dumps(tests)).replace("__LABELS__", LABELS)
    return (
        "set -eo pipefail\n"
        f"cd {REPO}\n"
        f"export PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp\n"
        f"{REPO}/.venv/bin/python - <<'PYEOF'\n{script}\nPYEOF\n"
        f"cd {REPO}\n"
        "dirty=$(git status --porcelain -- storygame tests data bench scripts docs .plans | grep -v 'build_round6d_scout_manifest.py\\|round6d-scout-manifest.json' || true)\n"
        '[ -z "$dirty" ] || { echo "scout modified the repo:"; echo "$dirty"; exit 1; }\n'
    )


def build() -> dict:
    tasks = []
    for key, (stem, tests) in FILES.items():
        tasks.append(
            {
                "key": "scout-" + key,
                "task_type": "research",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 900,
                "ownership": [f"{WORK}/{key}"],
                "spec": spec(key, stem, tests),
                "check": check(key, tests),
                "expect_files": [f"{WORK}/{key}/report.md"],
                "verified": "each blocked test has one verdict with an executed repro whose outcome matches the report; the repo was not modified.",
            }
        )
    return {
        "run_name": "story-data-round6-scout",
        "workdir": WORK,
        "max_parallel": 6,
        "worktrees": False,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6d-scout-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
