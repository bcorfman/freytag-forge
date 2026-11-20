# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 2 of the nightly repair: the 2A supervisor impatience line and the drain experiment deletion.

Both were approved by Brandon on 2026-11-20. The impatience beat's text is authored here, word
for word; the worker applies it and adds one focused test. The drain task deletes a retired
capture experiment and keeps the shared engine helper. Disjoint files, isolated worktrees.
Usage: build_nightly_round2_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-round2"
OUT = f"{WORK}/out"
PYTEST = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider --run-nightly -n 16"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at the branch `nightly-suite-repair`). Edit files here directly. NEVER touch {REPO} itself, never git commit, never run `uv`, never call a model or the network, never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PYTEST} <test ids>`. Leave your changes uncommitted; the check exports them as a patch. Keep Python ruff-formatted (`.venv/bin/ruff format <file>`, `.venv/bin/ruff check <file>`). Never add skip, xfail or broad try/except. Player commands you write must be short imperative sentences, like "Feel the cooling lines at the manifold."
"""

IMPATIENCE_GUARDS = "tests/test_2a_spine_prompts.py tests/test_affordance_map.py tests/test_canon_journey.py tests/test_entry_variants.py tests/test_disclosure_guards.py tests/test_candidate_matcher.py tests/test_guard_vocabulary.py tests/test_richer_overprojection.py tests/test_late_scene_repro.py tests/test_stall_exit_audit.py tests/test_act2_knowledge_sources.py tests/test_gap_rules.py tests/test_richer_2a.py tests/test_scene_2a_grounding.py tests/test_incident_characterization.py tests/test_exit_backstop_invariant.py tests/test_spine_expected_reveals.py tests/test_incident_handoff_guard.py tests/test_narration_safety.py tests/test_knowledge_projection.py tests/test_narration_safety_false_positives.py tests/test_journey_prefix_equivalence.py tests/test_audit_budget.py tests/test_frozen_prompts.py tests/test_markdown_story_package.py"

LINE = "The shift supervisor checks the time on his tablet. He is waiting for an answer."

TASKS = {
    "supervisor-impatience": {
        "files": [
            "data/stories/continuity-initiative/source/scenes/2A.yaml",
            "tests/test_2a_supervisor_impatience.py",
        ],
        "deleted": [],
        "targets": "tests/test_2a_supervisor_impatience.py",
        "guards": IMPATIENCE_GUARDS,
        "budget": 170,
        "new_test_budget": 15,
        "extra": f"""grep -qF "{LINE}" data/stories/continuity-initiative/source/scenes/2A.yaml || {{ echo "the authored line is not in 2A.yaml word for word"; exit 1; }}
grep -qE "^- id: supervisor_impatience_2a$" data/stories/continuity-initiative/source/scenes/2A.yaml || {{ echo "beat supervisor_impatience_2a missing"; exit 1; }}
grep -qE "^  supervisor_impatient:$" data/stories/continuity-initiative/source/scenes/2A.yaml || {{ echo "fact supervisor_impatient not declared under facts"; exit 1; }}
n=$(git diff --cached --numstat -- data/stories/continuity-initiative/source/scenes/2A.yaml | awk '{{print $1+$2}}')
[ "$n" -le 14 ] || {{ echo "2A.yaml diff is $n lines; only the beat and the fact should change"; exit 1; }}""",
        "spec": f"""BACKGROUND. In scene 2A (the facility gate) the shift supervisor waits while Kristin diagnoses the cooling fault. His patience ends at scene turn 5 (beat `inspection_window_2a`), when he escorts Kristin and Brandon in under watch. Four optional details (badges, alarm log, return line, camera) can be explored before that, but the player gets no warning that time is running out. The project owner approved one authored warning line at scene turn 3.

YOU MAY EDIT ONLY: data/stories/continuity-initiative/source/scenes/2A.yaml and the NEW file tests/test_2a_supervisor_impatience.py. Any other edited file fails the check. Do not change any other story text, window, beat or test.

TASK 1. In `data/stories/continuity-initiative/source/scenes/2A.yaml`, add this fact as the first entry under the top-level `facts:` mapping, exactly:
```
  supervisor_impatient:
    purpose: The shift supervisor has shown at the gate that his patience is running out.
```
and add this beat as the first entry under the top-level `beats:` list (before `inspection_window_2a`), exactly:
```
- id: supervisor_impatience_2a
  at_turn: 3
  sets:
    supervisor_impatient: true
  say:
  - text: {LINE}
    verbatim: true
  when:
    inspection_window_missed: false
    restricted_corridor_access: false
```
The text is authored by the project owner's writer: copy it word for word. The package must still load (`load_story_package(Path("data/stories/continuity-initiative"))`).

TASK 2. Create `tests/test_2a_supervisor_impatience.py` that plays the real engine offline (no network: monkeypatch the provider transport the way `tests/test_recent_cue_unit.py` does, and start in scene 2A the way an existing 2A test does, for example `tests/test_richer_2a.py` or `tests/test_scene_2a_grounding.py`). Use real player commands, and do not edit `fired_event_ids` or `active_event_ids` by hand. Assert:
(a) The beat's line appears word for word in the turn output exactly once, on the turn when the scene clock reaches 3, and `supervisor_impatient` becomes true then. It is absent on scene turns 1 and 2. Use plain commands that do not end the scene, such as "Read the alarm log." and "Ask Brandon about the badges.".
(b) The line does not appear again on later turns of the scene before the window closes.
(c) A player who explains the fault quickly ("Feel the cooling lines at the manifold." then "Explain the pressure fault and the ventilation problem to the supervisor.") leaves the scene before turn 3 and never sees the line.
Mark nothing nightly; the new file must run in the default suite and take under 15 seconds.""",
    },
    "drain-retire": {
        "files": [
            "scripts/ringer/environment_narration/drain_details_capture.py",
            "tests/shard_durations.json",
        ],
        "deleted": [
            "tests/test_drain_details_capture.py",
            "scripts/ringer/environment_narration/make_t9h_drain_rejection_free_manifest.py",
            "scripts/ringer/environment_narration/run-t9h-drain-rejection-free.json",
        ],
        "targets": "tests/test_opening_condition_v2.py",
        "guards": "tests/test_hidden_bench_1b2_capture.py",
        "budget": 90,
        "new_test_budget": 0,
        "extra": """! grep -nE "DETAILS_LINE|CANDIDATE_SUFFIX|CANDIDATE_PHRASE|_candidate_package_root|capture_arms" scripts/ringer/environment_narration/drain_details_capture.py || { echo "candidate-only code is still in drain_details_capture.py"; exit 1; }
grep -q "def _run_engine" scripts/ringer/environment_narration/drain_details_capture.py || { echo "the shared _run_engine helper was removed"; exit 1; }
! grep -q "test_drain_details_capture.py" tests/shard_durations.json || { echo "shard_durations.json still lists the deleted test"; exit 1; }
.venv/bin/python -c "import json; json.load(open('tests/shard_durations.json'))" || { echo "shard_durations.json is not valid JSON"; exit 1; }
if grep -rnE "make_t9h_drain_rejection_free_manifest|run-t9h-drain-rejection-free|test_drain_details_capture" --include=*.py --include=*.json --include=*.yml --include=*.yaml --include=*.toml . | grep -v "^./tests/shard_durations.json" | grep -vE "^./scripts/ringer/(build_)?nightly"; then echo "a reference to a deleted file remains"; exit 1; fi
PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/environment_narration/drain_details_capture.py --help > /dev/null 2>&1 || PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python -c "import importlib.util as u; s=u.spec_from_file_location('m','scripts/ringer/environment_narration/drain_details_capture.py'); m=u.module_from_spec(s); s.loader.exec_module(m); assert hasattr(m, '_run_engine')" || { echo "drain_details_capture.py no longer imports"; exit 1; }""",
        "spec": """BACKGROUND. `scripts/ringer/environment_narration/drain_details_capture.py` and its test `tests/test_drain_details_capture.py` belong to a conditional experiment: adding a storm-drain detail to scene 1B.1. That edit was never adopted, the tests read the removed legacy `plot.md`, and the 1B.1 Details list is already full. The project owner approved deleting the experiment. But `scripts/ringer/environment_narration/opening_condition_v2.py` loads `drain_details_capture.py` and calls its `_run_engine` helper, so the shared engine-capture helpers must stay.

YOU MAY CHANGE ONLY: delete `tests/test_drain_details_capture.py`, `scripts/ringer/environment_narration/make_t9h_drain_rejection_free_manifest.py` and `scripts/ringer/environment_narration/run-t9h-drain-rejection-free.json`; edit `scripts/ringer/environment_narration/drain_details_capture.py` and `tests/shard_durations.json`. Any other change fails the check.

TASK. (1) Delete the three files. (2) In drain_details_capture.py, remove everything that exists only for the candidate experiment: `DETAILS_LINE`, `CANDIDATE_SUFFIX`, `CANDIDATE_PHRASE`, `_candidate_package_root`, `capture_arms`, and the `_document`, `_print_summary`, `main` CLI and `if __name__` block, plus `_diff`, `_capture_path`, `_capture_scene_prompt`, `PATHS` and `ESCAPE_COMMAND` if nothing left in the file or in opening_condition_v2.py uses them. Keep `_run_engine` and every helper it or opening_condition_v2.py needs (read opening_condition_v2.py to see exactly which names it uses). Update the module docstring to say it now holds shared offline engine-capture helpers. Remove imports that become unused. (3) Remove the `tests/test_drain_details_capture.py` entry from tests/shard_durations.json, keeping the file valid JSON with the same formatting. `tests/test_opening_condition_v2.py` and `tests/test_hidden_bench_1b2_capture.py` must still pass.""",
    },
}


def check(key: str, t: dict) -> str:
    allowed = " ".join(t["files"] + t["deleted"])
    deleted_checks = "\n".join(
        f'[ ! -e "{path}" ] || {{ echo "{path} was not deleted"; exit 1; }}' for path in t["deleted"]
    )
    timing = ""
    if t["new_test_budget"]:
        timing = f"""s0=$SECONDS
{PYTEST.replace("-n 16", "-n 0")} {t["targets"]} > /tmp/nr2-{key}-solo.out 2>&1 || {{ tail -20 /tmp/nr2-{key}-solo.out; echo "new test fails when run alone"; exit 1; }}
e0=$((SECONDS-s0)); echo "new test alone: $e0 s (budget {t["new_test_budget"]} s)"
[ "$e0" -le {t["new_test_budget"]} ] || {{ echo "new test over its time budget"; exit 1; }}
! grep -qE "mark\\.nightly" {t["targets"]} || {{ echo "new test must run in the default suite, not nightly"; exit 1; }}"""
    return f"""set -eo pipefail
mkdir -p {OUT}
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A
git diff --cached > {OUT}/{key}.patch
changed=$(git diff --cached --name-only)
[ -n "$changed" ] || {{ echo "no changes made"; exit 1; }}
for f in $changed; do
  case " {allowed} " in *" $f "*) ;; *) echo "changed a file outside this task: $f"; exit 1;; esac
done
{deleted_checks}
if git diff --cached -U0 | grep -E '^\\+' | grep -nE 'pytest\\.(skip|xfail)|mark\\.(skip|xfail)|except Exception: *pass|fired_event_ids\\.(discard|remove)|active_event_ids\\.add'; then echo "added a skip, xfail, swallowed exception or a hand edit of storylet state"; exit 1; fi
py=$(git diff --cached --name-only --diff-filter=AM | grep -E '\\.py$' || true)
if [ -n "$py" ]; then .venv/bin/ruff format --check $py && .venv/bin/ruff check $py; fi
{t["extra"]}
{timing}
start=$SECONDS
rc=0
{PYTEST} -rf {t["targets"]} {t["guards"]} > /tmp/nr2-{key}.out 2>&1 || rc=$?
tail -12 /tmp/nr2-{key}.out
[ "$rc" = 0 ] || {{ echo "tests fail (exit $rc)"; exit 1; }}
grep -qE "[0-9]+ passed" /tmp/nr2-{key}.out || {{ echo "no test ran"; exit 1; }}
el=$((SECONDS-start))
echo "tests took $el s (budget {t["budget"]} s)"
[ "$el" -le {t["budget"]} ] || {{ echo "over the time budget: $el s > {t["budget"]} s"; exit 1; }}
echo "PASS {key}: patch at {OUT}/{key}.patch"
"""


def build() -> dict:
    tasks = []
    for key, t in TASKS.items():
        tasks.append(
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 900,
                "spec": COMMON + "\n" + t["spec"],
                "check": check(key, t),
                "expect_files": [f"{OUT}/{key}.patch"],
                "verified": "Patch changes only the task's files, deletes what it must, adds no skip, xfail or hand edit of storylet state, is ruff-clean, passes the target and guard tests within the time budget, and passes the task's content assertions.",
            }
        )
    return {
        "run_name": "nightly-round2",
        "workdir": WORK,
        "max_parallel": 2,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-round2-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
