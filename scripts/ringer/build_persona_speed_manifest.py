# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Speed up tests/test_persona_escalation.py (Brandon, 2026-11-20).

Its module fixture plays three full persona runs (about 69 s alone, 153 s in a loaded nightly run),
and the default-suite CLI test waits for all of it. Profiling the staller run (83 s under cProfile,
96 turns) found engine-wide waste: `entity_is_protected` builds `KnowledgeGuards(state)` on every
call (15,744 calls, about 31 s), `world_for` rebuilds `WorldSchema.from_data` on every call (7,416
calls, about 22 s), and `FactStore.matching` scans and sorts every fact on each lookup (2.5 million
calls). Task 1 removes that waste with byte-identical behaviour. Task 2 moves the real-run checks
out of the default suite. Sequential, so the timings do not compete.
Usage: build_persona_speed_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/persona-speed"
OUT = f"{WORK}/out"
BASELINE = f"{WORK}/baseline/personas.json"
ENV = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp"
PY = f"{ENV} .venv/bin/python -m pytest -q -p no:cacheprovider"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at the branch `nightly-suite-repair`). Edit files here directly. NEVER touch {REPO} itself, never git commit, never run `uv`, never call a model or the network, never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PY} -n 16 <test ids>` (add `--run-nightly` for nightly tests). Leave changes uncommitted; the check exports them as a patch. Keep Python ruff-formatted (`.venv/bin/ruff format <file>`, `.venv/bin/ruff check <file>`). Never add skip, xfail or broad try/except.
"""

ENGINE_FILES = [
    "storygame/runtime/knowledge.py",
    "storygame/runtime/facts.py",
    "storygame/runtime/world_model.py",
    "storygame/runtime/reference_resolution.py",
    "storygame/runtime/cloudflare.py",
    "storygame/runtime/narration_safety.py",
    "tests/test_fact_store_index.py",
    "tests/shard_durations.json",
]

ENGINE_SPEC = f"""YOU MAY EDIT ONLY: {", ".join(ENGINE_FILES)} (`tests/test_fact_store_index.py` is a NEW file, only needed if you add a fact index). Any other edited file fails the check. Do NOT edit `packages/worldkeeper`, `storygame/runtime/engine.py`, `state.py`, `validation.py`, `reveal_eligibility.py` or `canonical_events.py` (another worker owns those), or any story data.

GOAL. Make the runtime's turn processing faster with EXACTLY the same behaviour. The proof is the persona harness: `{ENV} .venv/bin/python -m storygame.personas --out /tmp/p.json` runs three deterministic personas (thorough, staller, wrong_lead) through the whole real story. Its output must stay byte-identical to the baseline `{BASELINE}` (captured at the starting commit), and it must take at most 40 seconds (it takes about 69 s now: thorough 12, staller 38, wrong_lead 19).

PROFILE (cProfile of the staller run, 96 turns, 83 s under the profiler). Profile again yourself before changing anything (`{ENV} .venv/bin/python -c "import cProfile,pstats; from pathlib import Path; from storygame.story_package.loader import load_story_package; import storygame.personas as p; pkg=load_story_package(Path('data/stories/continuity-initiative')); cProfile.run('p.run_persona(\\"staller\\", pkg)', '/tmp/prof'); pstats.Stats('/tmp/prof').sort_stats('cumulative').print_stats(40)"`):
1. `storygame/runtime/knowledge.py` `entity_is_protected` (about line 152) constructs `KnowledgeGuards(state)` on every call (15,744 calls). Each construction runs `KnowledgeProjector._established` over every knowledge item (about 31 s cumulative). The guards depend only on the current facts and package, so compute them once per state of the facts, not once per entity. For example, let callers pass a prebuilt `KnowledgeGuards`, or cache it on a fact-store version counter. A cache must never return guards built from an older set of facts.
2. `storygame/runtime/world_model.py` `world_for` (line 61) calls `WorldSchema.from_data(world_schema_data(package))` on every call (7,416 calls, about 22 s). The schema depends only on the package, so build it once per package object, for example in a cache keyed by the package object's identity that is safe for many packages and does not leak memory without bound. Keep `World(..., facts, ...)` per call, because facts change.
3. `storygame/runtime/facts.py` `FactStore.matching` scans and sorts all asserted facts on every lookup (2.5 million calls, about 25 s including the scan). If you add an index by predicate, keep it exactly consistent through every way facts change (`assert_fact`, any retract or replace method, `clone`, pydantic construction, validation and serialization, and direct assignment to `asserted` if code does that). Keep the return order identical (sorted by `fact.key`). Add `tests/test_fact_store_index.py` proving consistency through each mutation path and through clone, snapshot and restore. Any new test file must also get an entry in `tests/shard_durations.json`: run `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/regen_shard_durations.py --missing-only` after creating it (`tests/test_regen_shard_durations.py` fails otherwise).
4. `re` compiles are about 12 s (921,000 calls to `re._compile`). If a hot path builds a pattern per call from data that does not change per turn, precompile or cache it.
Do the biggest safe win first and re-measure after each. Stop when the 40 s budget holds; do not micro-optimize further. Do not change any output, ordering, error message, or public function signature that other modules use, except adding optional parameters.

All of the default suite must pass (`{PY} -n 16 tests` takes about 5 minutes here).
"""

ENGINE_CHECK = f"""set -eo pipefail
mkdir -p {OUT}
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A
git diff --cached > {OUT}/engine-speed.patch
changed=$(git diff --cached --name-only)
[ -n "$changed" ] || {{ echo "no changes made"; exit 1; }}
for f in $changed; do
  case " {" ".join(ENGINE_FILES)} " in *" $f "*) ;; *) echo "edited a file outside this task: $f"; exit 1;; esac
done
if git diff --cached -U0 | grep -E '^\\+' | grep -nE 'pytest\\.(skip|xfail)|mark\\.(skip|xfail)|except Exception: *pass'; then echo "added a skip, xfail or swallowed exception"; exit 1; fi
py=$(git diff --cached --name-only --diff-filter=AM | grep -E '\\.py$' || true)
[ -z "$py" ] || {{ .venv/bin/ruff format --check $py && .venv/bin/ruff check $py; }}
s0=$SECONDS
{ENV} .venv/bin/python -m storygame.personas --out /tmp/ps-engine.json
e0=$((SECONDS-s0))
cmp /tmp/ps-engine.json {BASELINE} || {{ python3 -m json.tool {BASELINE} > /tmp/ps-base-pretty.json; python3 -m json.tool /tmp/ps-engine.json > /tmp/ps-new-pretty.json; diff /tmp/ps-base-pretty.json /tmp/ps-new-pretty.json | head -40; echo "persona output changed: behaviour is not identical"; exit 1; }}
echo "three personas: $e0 s (budget 40 s, baseline about 69 s); output byte-identical"
[ "$e0" -le 40 ] || {{ echo "over the 40 s budget"; exit 1; }}
if [ -f tests/test_fact_store_index.py ]; then {PY} -n 0 tests/test_fact_store_index.py > /tmp/ps-idx.out 2>&1 || {{ tail -20 /tmp/ps-idx.out; echo "fact index tests fail"; exit 1; }}; fi
if git diff --cached --name-only | grep -q "storygame/runtime/facts.py"; then [ -f tests/test_fact_store_index.py ] || {{ echo "facts.py changed without tests/test_fact_store_index.py"; exit 1; }}; fi
s1=$SECONDS
rc=0
{PY} -n 16 -rf tests > /tmp/ps-full.out 2>&1 || rc=$?
tail -12 /tmp/ps-full.out
[ "$rc" = 0 ] || {{ echo "default suite fails (exit $rc)"; exit 1; }}
echo "default suite: $((SECONDS-s1)) s"
echo "PASS engine-speed"
"""

TEST_FILES = ["tests/test_persona_escalation.py"]

TEST_SPEC = """YOU MAY EDIT ONLY: tests/test_persona_escalation.py. Any other edited file fails the check. Do not change `storygame/personas.py`.

GOAL. `tests/test_persona_escalation.py` has a module fixture `summaries` that plays all three personas through the whole real story (about 69 s). The default-suite test `test_persona_cli_writes_json` requests that fixture, so the default suite pays the full cost. The project's rule (`docs/test-suite-performance-guide.md`): an end-to-end test that takes more than about 2 seconds is marked `@pytest.mark.nightly`.
1. Make `test_persona_cli_writes_json` test only the CLI: monkeypatch `storygame.personas.run_persona` to return small stand-in summaries built in the test (no real run), call `storygame.personas.main()` with `--out`, and assert that the file holds one entry per name in `PERSONAS`, with the stand-in content, as valid JSON. It must run in the default suite in under 2 seconds and must not request the `summaries` fixture.
2. Move the real-run assertions into a NEW nightly test that uses the `summaries` fixture: every persona has `resolution_complete` and `scenes`, and for `staller` and `wrong_lead` the 1C row has `turns_to_exit == 8` and `costs_applied == []`. Keep `test_persona_summary_is_json_serializable` as it is (nightly). No assertion may be dropped; each moves.
"""

TEST_CHECK = f"""set -eo pipefail
mkdir -p {OUT}
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A
git diff --cached > {OUT}/persona-test.patch
changed=$(git diff --cached --name-only)
[ "$changed" = "tests/test_persona_escalation.py" ] || {{ echo "changed files must be exactly tests/test_persona_escalation.py, got: $changed"; exit 1; }}
if git diff --cached -U0 | grep -E '^\\+' | grep -nE 'pytest\\.(skip|xfail)|mark\\.(skip|xfail)'; then echo "added a skip or xfail"; exit 1; fi
.venv/bin/ruff format --check tests/test_persona_escalation.py && .venv/bin/ruff check tests/test_persona_escalation.py
grep -q 'turns_to_exit"\\] == 8' tests/test_persona_escalation.py || {{ echo "the 1C turns_to_exit == 8 assertion is gone"; exit 1; }}
grep -q 'costs_applied"\\] == \\[\\]' tests/test_persona_escalation.py || {{ echo "the 1C costs_applied assertion is gone"; exit 1; }}
s0=$SECONDS
{PY} -n 0 -rf --durations=5 tests/test_persona_escalation.py > /tmp/pt-default.out 2>&1 || {{ tail -20 /tmp/pt-default.out; echo "default-suite run fails"; exit 1; }}
e0=$((SECONDS-s0)); tail -8 /tmp/pt-default.out
grep -qE "[1-9][0-9]* passed" /tmp/pt-default.out || {{ echo "no default-suite test ran"; exit 1; }}
echo "default-suite file run: $e0 s (budget 8 s including startup)"
[ "$e0" -le 8 ] || {{ echo "default-suite run of the file is over 8 s"; exit 1; }}
rc=0
{PY} -n 4 --run-nightly -rf tests/test_persona_escalation.py > /tmp/pt-nightly.out 2>&1 || rc=$?
tail -4 /tmp/pt-nightly.out
[ "$rc" = 0 ] || {{ echo "nightly run of the file fails"; exit 1; }}
n=$(grep -oE "[0-9]+ passed" /tmp/pt-nightly.out | grep -oE "[0-9]+")
[ "$n" -ge 5 ] || {{ echo "expected at least 5 tests in the nightly run (3 serializable, CLI, real-run checks), got $n"; exit 1; }}
echo "PASS persona-test"
"""


def build() -> dict:
    tasks = [
        (
            "engine-speed",
            ENGINE_SPEC,
            ENGINE_CHECK,
            3600,
            1500,
            "Patch touches only the listed runtime files; persona output is byte-identical to the baseline and the three personas run in at most 40 s; any fact index has its own consistency tests; the whole default suite passes.",
        ),
        (
            "persona-test",
            TEST_SPEC,
            TEST_CHECK,
            1500,
            900,
            "Only the test file changes; every real-run assertion still exists; the default-suite run of the file takes at most 8 s; the nightly run passes with at least 5 tests.",
        ),
    ]
    return {
        "run_name": "persona-speed",
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
                "timeout_s": timeout,
                "check_timeout_s": check_timeout,
                "spec": COMMON + "\n" + spec,
                "check": check,
                "expect_files": [f"{OUT}/{key}.patch"],
                "verified": verified,
            }
            for key, spec, check, timeout, check_timeout, verified in tasks
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("persona-speed-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
