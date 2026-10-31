#!/usr/bin/env bash
# Checks for the PR #729 CI-green round. Usage: check_ci_green.sh TASK
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
W=/home/bcorfman/dev/ringer-work/t9h-ci-green
PY="$ROOT/.venv/bin/python"
TASK="${1:?task}"
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp

fix_task() {  # $1 report, rest: failing test ids
  local report="$1"; shift
  local files; files=$(printf '%s\n' "$@" | sed 's/::.*//' | sort -u)
  [ -s "$report" ] || { echo "FAIL: report $report missing" >&2; exit 1; }
  for id in "$@"; do
    name="${id##*::}"; name="${name%%\[*}"
    [ "$name" = "_" ] && continue
    grep -qF -- "$name" "$report" || { echo "FAIL: report does not account for $name" >&2; exit 1; }
  done
  local existing=""; for f in $files; do [ -f "$f" ] && existing="$existing $f"; done
  if [ -n "$existing" ]; then
    # CI view: gitignored artifacts absent, different checkout path.
    bash scripts/ringer/ci_sim_pytest.sh $existing > /tmp/ci-green-$TASK-sim.out 2>&1; rc=$?
    grep -E "^(FAILED|ERROR)|passed|failed|skipped" /tmp/ci-green-$TASK-sim.out | tail -15
    [ $rc -eq 0 ] || { echo "FAIL: tests fail in the CI simulation" >&2; exit 1; }
    if grep -Eq '[0-9]+ skipped' /tmp/ci-green-$TASK-sim.out; then echo "FAIL: tests skip in the CI simulation (a missing artifact must not become a skip)" >&2; exit 1; fi
    # Local view too.
    env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN "$PY" -m pytest -q -p no:cacheprovider --no-cov $existing > /tmp/ci-green-$TASK-local.out 2>&1 || { tail -15 /tmp/ci-green-$TASK-local.out; echo "FAIL: tests fail locally" >&2; exit 1; }
    "$PY" -m ruff check $existing || exit 1
    "$PY" -m ruff format --check $existing || exit 1
  fi
  local fixture_kb; fixture_kb=$(du -sk tests/fixtures/t9h_ci 2>/dev/null | cut -f1); fixture_kb=${fixture_kb:-0}
  [ "$fixture_kb" -le 400 ] || { echo "FAIL: tests/fixtures/t9h_ci is ${fixture_kb} KB (cap 400)" >&2; exit 1; }
  echo PASS
}

scout_task() {  # $1 report
  local report="$1"
  [ -s "$report" ] || { echo "FAIL: report $report missing" >&2; exit 1; }
  for section in "cause" "evidence" "fix" "files"; do
    grep -qi "^#* *$section" "$report" || { echo "FAIL: report lacks a '$section' section heading" >&2; exit 1; }
  done
  if ! git diff --quiet -- storygame tests scripts data docs 2>/dev/null; then
    : # the tree may hold other lanes' edits; scouts are checked by not owning files
  fi
  "$PY" - "$report" <<'PY' || exit 1
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
paths = [w.strip("`*,.:;()") for w in text.split() if ("storygame/" in w or "tests/" in w or "scripts/" in w) and ".py" in w]
paths = [p.split("::")[0].split(":")[0] for p in paths]
missing = sorted({p for p in paths if p and not Path(p).exists()})
if not paths:
    print("FAIL: report names no source file"); sys.exit(1)
if missing:
    print(f"FAIL: report names files that do not exist: {missing}"); sys.exit(1)
print(f"report names {len(set(paths))} existing files")
PY
  echo PASS
}

case "$TASK" in
  artifacts-drain-condition)
    fix_task "$W/artifacts-drain-condition.md" \
      tests/test_drain_condition_corpus.py::test_real_build_is_deterministic_and_carries_the_known_labels \
      tests/test_drain_condition_heldout.py::test_authored_rows_inherit_declared_state_from_their_source \
      tests/test_drain_condition_heldout.py::test_blind_sheet_is_deterministic_and_does_not_expose_metadata \
      tests/test_drain_condition_heldout.py::test_build_is_deterministic_and_balanced \
      tests/test_drain_condition_heldout.py::test_declared_state_is_well_formed_and_missing_state_has_a_reason \
      tests/test_drain_condition_judge_probe.py::test_case_build_reproduces_frozen_counts \
      tests/test_x1_condition_count.py::test_real_corpus_reproduces_known_x1_counts ;;
  artifacts-probes)
    fix_task "$W/artifacts-probes.md" \
      tests/test_drain_details_prose_probe.py::test_capture_finds_recorded_prompt_and_validates_offline_arms \
      tests/test_drain_details_prose_probe.py::test_control_and_candidate_differ_only_by_suffix \
      tests/test_drain_details_prose_probe.py::test_dry_run_counts_twenty_and_refuses_caps \
      tests/test_drain_details_prose_probe.py::test_recorded_prompt_without_details_fails \
      tests/test_hidden_bench_matcher_probe.py::test_429_stops_after_the_failing_row \
      tests/test_hidden_bench_matcher_probe.py::test_dry_run_refuses_an_over_budget_plan \
      tests/test_hidden_bench_matcher_probe.py::test_shortlists_use_projection_and_head_package_has_no_new_candidates \
      tests/test_hidden_bench_prose_probe.py::test_blind_key_is_a_bijection_for_synthetic_and_frozen_rows \
      tests/test_t9h_run_manifests.py::test_t9h_expect_files_and_conditional_check_behavior ;;
  capture-1b2)
    fix_task "$W/capture-1b2.md" tests/test_hidden_bench_1b2_capture.py::test_tampered_1b2_details_are_reported_as_exposure ;;
  capture-race)
    fix_task "$W/capture-race.md" \
      tests/test_fixed_refusal.py::test_capture_real_scene_1a_fixed_refusal_precedes_other_questions \
      tests/test_fixed_refusal.py::test_names_other_action_question_joins_refused_names \
      tests/test_observation_open_step.py::test_open_step_is_inert_when_the_container_is_not_openable \
      tests/test_observation_open_step.py::test_open_step_works_for_a_second_synthetic_story \
      "tests/test_search_opens_drawer.py::test_synthetic_openable_container_obeys_under_first" \
      tests/test_observation_resume.py::test_preview_faults_fail_closed_with_exact_rollback \
      tests/test_jev_batching.py::_ tests/test_narration_hedge.py::_ tests/test_hedged_request.py::_ tests/test_runtime_capture.py::_
    "$PY" -m ruff check storygame/runtime/capture.py && "$PY" -m ruff format --check storygame/runtime/capture.py || exit 1
    # Stress the race: 80 separate pytest processes, 8 at a time; the old code failed about 4% of runs.
    ID='tests/test_observation_resume.py::test_preview_faults_fail_closed_with_exact_rollback[True-none_verifier]'
    STRESS=$(mktemp -d /tmp/ci-green-race.XXXXXX)
    seq 1 80 | xargs -P8 -I{} sh -c 'env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN "$0" -m pytest -q -p no:cacheprovider --no-cov "$1" > "$2/run-{}.out" 2>&1; echo $? > "$2/run-{}.rc"' "$PY" "$ID" "$STRESS"
    passed=$(grep -l '^0$' "$STRESS"/run-*.rc | wc -l)
    echo "race stress: $passed of 80 runs passed"
    if [ "$passed" -ne 80 ]; then grep -h -m2 -E "RuntimeError|Error" "$STRESS"/run-*.out | head -4; echo "FAIL: race stress" >&2; exit 1; fi
    echo PASS ;;
  scout-fixed-refusal) scout_task "$W/scout-fixed-refusal.md" ;;
  scout-open-step) scout_task "$W/scout-open-step.md" ;;
  scout-race) scout_task "$W/scout-race.md" ;;
  *) echo "unknown task $TASK" >&2; exit 2 ;;
esac
