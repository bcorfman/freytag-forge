# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 3 of the nightly repair: the journey harness without hand re-arms, and the fact-index guard.

1. journey-harness: apply the reviewed patch from round 1 but drop `_rearm_next_chain_storylet`,
   which the engine follow-up rule (161145bc) made unnecessary; it edited storylet state by hand.
2. fact-index-guard: the predicate index added in c32f7ad7 is bypassed by in-place edits of
   `FactStore.asserted` (tests/test_incident_engine.py:105 does one). Make that impossible to get wrong.
Timing uses `date +%s` because checks run under sh, where SECONDS is not set.
Usage: build_nightly_round3_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-round3"
OUT = f"{WORK}/out"
OLD_PATCH = "/home/bcorfman/dev/ringer-work/nightly-rest-fix/out/journey-harness.patch"
BASELINE = "/home/bcorfman/dev/ringer-work/persona-speed/baseline/personas.json"
ENV = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp"
PY = f"{ENV} .venv/bin/python -m pytest -q -p no:cacheprovider"
REGEN = f"{ENV} .venv/bin/python scripts/regen_shard_durations.py --missing-only"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at the branch `nightly-suite-repair`). Edit files here directly. NEVER touch {REPO} itself, never git commit, never run `uv`, never call a model or the network, never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PY} -n 16 <test ids>` (add `--run-nightly` for nightly tests). Leave changes uncommitted; the check exports them as a patch. Keep Python ruff-formatted (`.venv/bin/ruff format <file>`, `.venv/bin/ruff check <file>`). Never add skip, xfail or broad try/except. If you create a new `tests/test_*.py` file, run `{REGEN}` so `tests/shard_durations.json` lists it.
"""

JOURNEY_CASES = (
    "k_sl_1a_b_r1",
    "k_sl_1a_f_r2",
    "k_sl_1a_f_r3",
    "k_sl_1a_j_r3",
    "k_sl_1a_k_r1",
    "k_sl_1b_g_r1",
    "k_sl_2a_g_r1",
    "k_sl_2a_h_r1",
    "k_sl_2b_g_r1",
    "k_sl_2c_g_r1",
)
TARGETS = " ".join(
    f"'tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[{k}]'"
    for k in JOURNEY_CASES
)
WAITING = "k_sl_3c_d_r1|k_sl_3c_d_r2|k_sl_3c_e_r1|k_sl_3c_e_r2"

TASKS = {
    "journey-harness": {
        "files": ["tests/test_game_path_journeys.py", "tests/journey_prefix.py"],
        "spec": f"""YOU MAY EDIT ONLY: tests/test_game_path_journeys.py and tests/journey_prefix.py. Any other edited file fails the check.

BACKGROUND. Ten cases of `tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[<id>]` fail (ids: {", ".join(JOURNEY_CASES)}) because the scripted playthrough harness is stale. An earlier worker wrote a reviewed fix, saved at `{OLD_PATCH}`: new `CHAINS` entries, an action-aware replay (`ACTION_COMMANDS`, `_preferred_command`), a legal move to the truck (`_move_to_truck`), and `_rearm_next_chain_storylet`. That last helper edits `state.fired_event_ids` and `state.active_event_ids` by hand to re-arm a storylet, which hid a real engine defect. The engine is now fixed (commit 161145bc): a fired storylet stays offerable for its follow-up realizations (`StoryPackage.follow_up_realization_ids`, which on this story holds SL-1A-F-R2, SL-1A-F-R3 and SL-1A-J-R3).

TASK. Apply the old patch (`git apply {OLD_PATCH}`). Then delete `_rearm_next_chain_storylet` and every call to it, so the harness never edits `fired_event_ids` or `active_event_ids`. Keep the rest of the patch. If a case then fails, find out why from the engine's offer and fix the harness legally (a real player command, a legal `World.move`, or a `CHAINS` order). Never edit storylet state by hand, and never seed a target outcome fact.
All ten cases must pass. Every other test in the guard files must pass, except the four 3C cases `k_sl_3c_d_r1`, `k_sl_3c_d_r2`, `k_sl_3c_e_r1` and `k_sl_3c_e_r2`, which wait on a story decision and must still fail. Do not touch them.""",
        "extra": """if grep -nE "fired_event_ids|active_event_ids" tests/journey_prefix.py tests/test_game_path_journeys.py; then echo "the journey harness still edits or reads storylet state by hand"; exit 1; fi
grep -q "ACTION_COMMANDS" tests/journey_prefix.py || { echo "the action-aware replay from the reviewed patch is missing"; exit 1; }""",
        "tests": f"""rc=0
{PY} -n 16 --run-nightly {TARGETS} > /tmp/r3-jh-targets.out 2>&1 || rc=$?
tail -6 /tmp/r3-jh-targets.out
[ "$rc" = 0 ] || {{ echo "target journey cases fail"; exit 1; }}
grep -qE "^10 passed" /tmp/r3-jh-targets.out || {{ echo "expected exactly 10 target cases to pass"; exit 1; }}
rc=0
{PY} -n 16 --run-nightly -rf tests/test_game_path_journeys.py tests/test_journey_prefix_equivalence.py tests/test_evidence_gap_journeys.py tests/test_three_c_prefix.py tests/test_narration_earned_names.py > /tmp/r3-jh-guards.out 2>&1 || rc=$?
tail -10 /tmp/r3-jh-guards.out
bad=$(grep -E "^(FAILED|ERROR) " /tmp/r3-jh-guards.out | grep -vE "{WAITING}" || true)
[ -z "$bad" ] || {{ echo "guard tests fail:"; echo "$bad"; exit 1; }}
grep -qE "[0-9]+ passed" /tmp/r3-jh-guards.out || {{ echo "guard run passed nothing"; exit 1; }}""",
        "budget": 300,
    },
    "fact-index-guard": {
        "files": [
            "storygame/runtime/facts.py",
            "tests/test_incident_engine.py",
            "tests/test_fact_store_index.py",
        ],
        "spec": f"""YOU MAY EDIT ONLY: storygame/runtime/facts.py, tests/test_incident_engine.py and tests/test_fact_store_index.py. Any other edited file fails the check.

BACKGROUND. Commit c32f7ad7 gave `FactStore` (storygame/runtime/facts.py) a private index by predicate (`_by_predicate`), a `version` counter and a cached `KnowledgeGuards`. It rebuilds them in `assert_fact`, `retract_fact`, on assignment to `asserted`, and on construction. But `asserted` is still a plain mutable `set`, so an in-place edit such as `store.asserted.add(fact)` or `store.asserted.discard(fact)` changes the facts without updating the index, the version or the guard cache. `matching()` and every guard built from it then silently return stale answers. `tests/test_incident_engine.py` line 105 does exactly this (`facts.asserted.add(...)`); it passes only because that code path does not read the index.

TASK. Make it impossible for an in-place edit to desync the index. Choose one of these:
(a) Store `asserted` as an immutable `frozenset`. Callers that build or assign a set still work: validate and convert on construction and on assignment. Then an in-place edit raises `AttributeError`.
(b) A small `set` subclass that tells its owning store to rebuild the index and bump the version on every mutating method.
(a) is preferred if the default suite allows it. Keep `matching()` order, every public signature, pydantic validation and serialization (`model_dump`, `model_dump_json`, `model_validate`, `model_validate_json`), `clone`, `model_copy`, snapshot and restore, and equality behaving exactly as now. Change `tests/test_incident_engine.py` line 105 to use `facts.assert_fact(...)`. Add tests to `tests/test_fact_store_index.py` proving the chosen guard: for (a), `asserted.add` raises and the index stays right; for (b), `asserted.add` and `asserted.discard` update `matching()`, `version` and the guard cache.
Behaviour must not change: the persona harness output (`{ENV} .venv/bin/python -m storygame.personas --out /tmp/p.json`) must stay byte-identical to `{BASELINE}`, and the whole default suite must pass (`{PY} -n 16 tests`, about 3 minutes).""",
        "extra": f"""grep -q "asserted.add" tests/test_incident_engine.py && {{ echo "tests/test_incident_engine.py still edits asserted in place"; exit 1; }} || true
{ENV} .venv/bin/python -m storygame.personas --out /tmp/r3-fig.json
cmp /tmp/r3-fig.json {BASELINE} || {{ echo "persona output changed: behaviour is not identical"; exit 1; }}
{ENV} .venv/bin/python - <<'PYEOF'
from storygame.runtime.facts import Fact, FactStore
s = FactStore()
f = Fact(predicate="probe_fact", subject="story", value="true")
try:
    s.asserted.add(f)
except (AttributeError, TypeError):
    pass
assert s.matching("probe_fact") == ((f,) if f in s.asserted else ()), "in-place add desynced the index"
v = s.version
s.assert_fact(Fact(predicate="probe_two", subject="story", value="true"))
assert s.version != v, "assert_fact did not bump the version"
print("in-place edit guard holds")
PYEOF""",
        "tests": f"""{PY} -n 0 tests/test_fact_store_index.py tests/test_incident_engine.py > /tmp/r3-fig-focus.out 2>&1 || {{ tail -20 /tmp/r3-fig-focus.out; echo "focused tests fail"; exit 1; }}
tail -1 /tmp/r3-fig-focus.out
rc=0
{PY} -n 16 -rf tests > /tmp/r3-fig-full.out 2>&1 || rc=$?
tail -8 /tmp/r3-fig-full.out
[ "$rc" = 0 ] || {{ echo "default suite fails (exit $rc)"; exit 1; }}""",
        "budget": 420,
    },
}


def check(key: str, t: dict) -> str:
    allowed = " ".join(t["files"])
    return f"""set -e
mkdir -p {OUT}
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A
git diff --cached > {OUT}/{key}.patch
changed=$(git diff --cached --name-only)
[ -n "$changed" ] || {{ echo "no changes made"; exit 1; }}
for f in $changed; do
  case " {allowed} " in *" $f "*) ;; *) echo "edited a file outside this task: $f"; exit 1;; esac
done
if git diff --cached -U0 | grep -E '^\\+' | grep -nE 'pytest\\.(skip|xfail)|mark\\.(skip|xfail)|except Exception: *pass'; then echo "added a skip, xfail or swallowed exception"; exit 1; fi
py=$(git diff --cached --name-only --diff-filter=AM | grep -E '\\.py$' || true)
[ -z "$py" ] || {{ .venv/bin/ruff format --check $py && .venv/bin/ruff check $py; }}
{t["extra"]}
start=$(date +%s)
{t["tests"]}
el=$(( $(date +%s) - start ))
echo "tests took $el s (budget {t["budget"]} s)"
[ "$el" -le {t["budget"]} ] || {{ echo "over the time budget: $el s > {t["budget"]} s"; exit 1; }}
echo "PASS {key}"
"""


def build() -> dict:
    return {
        "run_name": "nightly-round3",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 1200,
                "spec": COMMON + "\n" + t["spec"],
                "check": check(key, t),
                "expect_files": [f"{OUT}/{key}.patch"],
                "verified": f"Patch changes only {', '.join(t['files'])}, adds no skip or xfail, is ruff-clean, passes the task's content checks and its tests within {t['budget']} s (timed with date, which works under sh).",
            }
            for key, t in TASKS.items()
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-round3-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
