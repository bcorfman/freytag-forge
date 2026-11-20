# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Read-only diagnosis: why the nightly game-path journeys have failed since 2026-11-02.

coverage nightly was green at 1abb54b008 (2026-11-01) and red from 8da801206c (2026-11-02) on,
with 93 failures in tests/test_game_path_journeys.py and 8 in tests/test_evidence_gap_journeys.py.
One Codex task finds the first bad commit and the cause; the check proves the commit by running
the named test at that commit and at its parent. Usage: build_nightly_journey_diag_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-journey-failures"
GOOD = "1abb54b008"
BAD = "8da801206c"
PYTEST = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 --run-nightly"

SPEC = f"""You are a read-only diagnostic scout. Your current working directory IS a git worktree of {REPO} (detached at HEAD, which is current main). You may `git checkout` other commits INSIDE THIS WORKTREE to bisect, and you may write scratch files under /tmp. You must NEVER edit, stage or commit any tracked file, never touch {REPO} itself, never run `uv`, never call a model or the network, and never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PYTEST} <test ids>`. Your only deliverable is the file {WORK}/report.md (run `mkdir -p {WORK}` first).

THE PROBLEM. The GitHub workflow `coverage nightly` (`.github/workflows/coverage-nightly.yml`, which runs the whole suite with `--run-nightly`) was green on commit {GOOD} (2026-11-01) and has failed every night since, starting with commit {BAD} (2026-11-02, the merge of PR #745). There are 43 commits in `git log {GOOD}..{BAD}`. Every night about 120 tests fail, the same ones each time. The biggest groups:
- `tests/test_game_path_journeys.py`: 93 failures. `test_the_default_policy_earns_the_whole_chain_without_a_deadline` and most cases of `test_every_player_realization_has_an_earned_continuation_to_the_ending[<item_id>]`. The usual assertion: `_resolution_complete(state)` is False, so the scripted journey never reaches the story's ending. Some cases instead assert that a realization id such as `k_sl_3c_e_r2` is in the journey's realized list and it is missing.
- `tests/test_evidence_gap_journeys.py`: 8 failures (`test_every_reachable_evidence_gap_combination[combinationN]`).
Others (not your main target): `tests/test_environment_screen.py` (5, script exits 2 instead of 0), the 3C probe tests `tests/test_3c_*.py` (about 6, errors like "control package did not retain the recorded old C-R1 statement" and "ProposalValidationError: selected knowledge is not eligible for this turn"), `tests/test_drain_details_capture.py` and `tests/test_drain_details_prose_probe.py`, `tests/test_cue_escalation.py`, `tests/test_recent_cue_unit.py`, `tests/test_knowledge_leakage_matrix.py`, `tests/test_bench_item_facts.py`, `tests/test_hidden_bench_1b2_capture.py`.
A separate gate, `factory/checks/carry_matrix.py`, searches every path through the real story on current main and finds an earned exit from every scene, including the ending. So the story can still be finished by SOME sequence of moves; the question is why these scripted journeys no longer finish it.

WHAT TO DO.
1. Reproduce on current main: run `test_the_default_policy_earns_the_whole_chain_without_a_deadline` and two or three failing realization cases, and record the failure.
2. Find the FIRST BAD COMMIT for `tests/test_game_path_journeys.py::test_the_default_policy_earns_the_whole_chain_without_a_deadline` by bisecting `{GOOD}..{BAD}` (use `git bisect` in this worktree or check out commits by hand; walk the first-parent and the merged branch's commits as needed so you land on a single non-merge commit if one exists). Confirm it: the test passes at the commit's parent and fails at the commit. If the test passes at {BAD}, or fails at {GOOD}, say so and find where it actually changes.
3. Explain the CAUSE with evidence: read the failing journey (the policy in `storygame/personas.py`, `tests/journey_prefix.py`, the test file) and what that commit changed (story data under `data/stories/`, runtime code, or tests). Play the journey and say exactly where it now goes wrong: the scene, the turn, what the policy picks, and why the ending (`_resolution_complete`) is never reached (for example a timer or forced exit, a 3C ending that now needs a different realization, a renamed id, or a turn limit). Cite file:line for every claim.
4. Decide, with reasons, which side is wrong: (a) the tests or journey policy are stale after an intended story change (say what the intended change was, citing the plan or commit message), or (b) the commit introduced a real story or engine defect that a player could hit. Say what a fix would touch, without making it.
5. Group the other failures: for `tests/test_evidence_gap_journeys.py` and each other failing file listed above, run one failing test at the first bad commit's parent and at the commit, and at current main, and say whether it shares this cause, has its own first bad commit (find it if cheap; otherwise give the range), or fails for an unrelated reason. Note any failure that is flaky or depends on the environment (for example a missing credential or network).
Leave the worktree checked out at the commit it started on (current main) when you finish.

REPORT ({WORK}/report.md), in plain words, with these sections:
- `## First bad commit`: a line exactly `FIRST_BAD: <full 40-character sha>` and a line exactly `TEST: <one pytest node id that passes at the parent and fails at the commit>`, then the commit subject and what it changed.
- `## Cause`: where the journey goes wrong and why, with file:line.
- `## Stale test or real defect`: your verdict and reasons.
- `## Other failures`: one line per failing file: shares the cause / own cause (commit or range) / unrelated, with the evidence.
- `## Suggested fix`: what to change and where, not done.
"""

CHECK = f"""set -eo pipefail
R={WORK}/report.md
[ -s "$R" ] || {{ echo "missing $R"; exit 1; }}
for h in "first bad commit" "cause" "stale test or real defect" "other failures" "suggested fix"; do
  grep -qi "^## *$h" "$R" || {{ echo "report lacks section: $h"; exit 1; }}
done
grep -qE "[a-z_/]+\\.(py|yaml|yml|md|json):[0-9]+" "$R" || {{ echo "report cites no file:line"; exit 1; }}
sha=$(grep -oE "^FIRST_BAD: *[0-9a-f]{{40}}" "$R" | head -1 | grep -oE "[0-9a-f]{{40}}" || true)
test_id=$(grep -oE "^TEST: *tests/[^ ]+" "$R" | head -1 | sed -E 's/^TEST: *//' || true)
[ -n "$sha" ] || {{ echo "no FIRST_BAD: <40-char sha> line"; exit 1; }}
[ -n "$test_id" ] || {{ echo "no TEST: tests/... line"; exit 1; }}
cd {REPO}
git cat-file -e "$sha^{{commit}}" || {{ echo "FIRST_BAD $sha is not a commit"; exit 1; }}
git merge-base --is-ancestor {GOOD} "$sha" && git merge-base --is-ancestor "$sha" HEAD || {{ echo "$sha is not between {GOOD} and main"; exit 1; }}
[ "$sha" != "$(git rev-parse {GOOD})" ] || {{ echo "FIRST_BAD is the green commit"; exit 1; }}
# executed proof: the named test passes at the parent and fails at the commit
T=$(mktemp -d /tmp/nightly-diag-XXXX)
trap 'cd {REPO}; git worktree remove --force "$T/parent" 2>/dev/null; git worktree remove --force "$T/bad" 2>/dev/null; git worktree prune; rm -rf "$T"' EXIT
git worktree add -q --detach "$T/parent" "$sha^"
git worktree add -q --detach "$T/bad" "$sha"
for side in parent bad; do
  ln -s {REPO}/.venv "$T/$side/.venv"
  rc=0
  (cd "$T/$side" && timeout 900 {PYTEST} "$test_id" > "$T/$side.out" 2>&1) || rc=$?
  tail -5 "$T/$side.out"
  echo "$side ($(git rev-parse --short "$sha$([ $side = parent ] && echo '^')")): exit $rc"
  if [ "$side" = parent ]; then [ "$rc" = 0 ] || {{ echo "TEST does not pass at the parent of FIRST_BAD"; exit 1; }}; fi
  if [ "$side" = bad ]; then [ "$rc" = 1 ] || {{ echo "TEST does not fail (exit 1) at FIRST_BAD"; exit 1; }}; fi
done
grep -q "passed" "$T/parent.out" || {{ echo "parent run collected no passing test (wrong node id?)"; exit 1; }}
echo "first bad commit proved: $sha"
"""


def build() -> dict:
    return {
        "run_name": "nightly-journey-failures",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "journey-diag",
                "task_type": "probe",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 5400,
                "check_timeout_s": 2000,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [f"{WORK}/report.md"],
                "verified": "Report has all five sections with file:line citations; its FIRST_BAD commit lies between the last green nightly and main; the named test passes at that commit's parent and fails at the commit, run fresh by the check.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-journey-diag-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
