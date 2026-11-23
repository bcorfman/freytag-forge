"""Build the round 21b manifest: keep failing turns in planner evidence (task A) and a per-run spend cap (task B)."""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-21"
REPO = "/home/bcorfman/dev/freytag-forge"

COMMON = (
    "You are a factory engineer. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge "
    "(detached at HEAD). Edit files here directly. NEVER git commit, never touch /home/bcorfman/dev/freytag-forge "
    "itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, never run "
    "`python -m bench run`, never write factory/state/. FIRST run: [ -e .venv ] || ln -s "
    "/home/bcorfman/dev/freytag-forge/.venv .venv . Environment for every command: "
    "`export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): "
    "`.venv/bin/python -m ruff check <files>` / `.venv/bin/python -m ruff format <files>` (line length 120, "
    "Python 3.12). Never pass --cov to pytest. Run tests as "
    "`.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 <files>`. Tests must be hermetic (fake runner, no "
    "network, no real `claude`). Shared code must stay story-agnostic (no story, scene or character names in "
    "production code). If an OLD test pins behaviour this change deliberately changes, update it and say so in "
    "NOTES.txt. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice. Read "
    "first: AGENTS.md and docs/contributor-guide.md. "
)

EVIDENCE_SPEC = COMMON + (
    "You may edit ONLY: factory/stations/fix_plan.py and tests/test_factory_fix_plan.py.\n\n"
    "PROBLEM (reproduced). `factory/stations/fix_plan.py::_bound_evidence` keeps the planner's evidence packet under a "
    "12,000-character limit. It first pops `failing_turns` from the END until the packet fits, then `beats`, then "
    "`exits`, and only then trims `candidates`. On a real 1A case (23 failing turns, about 18.7k characters of turns "
    "inside a 40k packet) it drops EVERY failing turn, so the planner sees no failing turns, answers `unsupported`, "
    "and nobody is told anything was cut. Silent loss of the main evidence is the defect.\n\n"
    "CHANGE. Rewrite `_bound_evidence` (keep its name and a compatible signature; add an optional "
    "`protected_turn_keys: set[str] | None = None` parameter and pass it from `build_evidence`) so that:\n"
    "1. Cut order, cheapest evidence first, stopping the moment the packet fits `limit`: (a) unprotected "
    "`candidates` (sorted order, last first, as today); (b) `fact_readers` entries (entries with no readers first, "
    "then last by sorted id); (c) `beats`, then `exits`, from the end; (d) shrink the text fields of every kept "
    "failing turn in steps (`narration`, `previous_narration`, `rejected_code`, `rejected_message` to 300, then 150, "
    "then 80 characters); (e) only then drop failing turns, from the end, but turns whose `key` is in "
    "`protected_turn_keys` are dropped last, and the packet NEVER ends with zero failing turns when it began with at "
    "least one (keep at least one even if the limit cannot then be met).\n"
    "2. `build_evidence` computes `protected_turn_keys` as the set of diagnosis-row `key` values "
    "(`ticket_payload['diagnosis']['rows'][*]['key']`, strings only) so turns the diagnosis rows describe survive "
    "longest. Existing behaviour that protects diagnosis-referenced candidates stays.\n"
    "3. Record what was cut, never silently: when anything was removed or shortened, the evidence gets a "
    "`truncated` object, e.g. {\"failing_turns\": {\"kept\": 12, \"of\": 23}, \"candidates\": {\"kept\": 4, \"of\": 9}, "
    "\"fact_readers\": ..., \"beats\": ..., \"exits\": ..., \"text_shortened_to\": 150} listing only the parts that "
    "were actually cut (counts kept and original). When nothing was cut, the key is absent. The `truncated` object "
    "itself counts toward the limit and must be JSON-serialisable.\n"
    "4. Find where the planner prompt is built from this evidence (grep for `build_evidence` and the planner prompt "
    "in factory/stations/planner.py; you may NOT edit planner.py, so only check it) and say in NOTES.txt whether the "
    "`truncated` key reaches the model unchanged; if it would be stripped, say where.\n\n"
    "TESTS (extend tests/test_factory_fix_plan.py, hermetic, fast): (a) a REGRESSION test with 25 failing turns "
    "whose total evidence is over the limit because of long narrations and many candidates: after bounding, at least "
    "one failing turn survives, the packet is within the limit (or only the single mandatory turn exceeds it), and "
    "`truncated` reports the counts; (b) turns whose keys the diagnosis rows reference survive when others are "
    "dropped; (c) candidates are cut before any failing turn; (d) a small packet is returned unchanged with no "
    "`truncated` key; (e) zero failing turns in stays zero out with no error. Build the fixtures from the file's "
    "existing helpers; do not assert exact explanatory strings, assert the counts and survival facts. Update any old "
    "test that pinned the old drop-turns-first order and say so in NOTES.txt."
)

SPEND_SPEC = COMMON + (
    "You may edit ONLY: factory/stations/live_playtest.py and tests/test_factory_live_playtest.py.\n\n"
    "BACKGROUND. The live playtest station runs the blind player against staging; its narrator spend (Cloudflare) "
    "and player spend (OpenAI) are billed. On 2026-11-22 a 5-scene run cost 2.1x the owner's go because nothing "
    "capped one run. Measured rate: 0.0074 USD per counted player turn (scripted-prefix narration turns are billed "
    "but not counted, so this rate already absorbs them). The blind player's turn cap per run is 20 counted turns "
    "unless the payload says otherwise.\n\n"
    "CHANGE (live path only; the `report_path` grading path is untouched and needs no cap). After the existing "
    "`expected_sha` and `billed_run_approved` checks and BEFORE the staging-identity fetch, the handler:\n"
    "1. Fails with `missing payload key: max_usd` (turns=None, no runner call, no network) unless the payload has "
    "`max_usd` as a positive real number (bool and non-numbers are rejected with `max_usd must be a positive number`). "
    "This applies whether or not a `runner` was injected, so update old tests to pass `max_usd` where they run the "
    "live path.\n"
    "2. Computes `estimate_usd = replicates * turn_cap * 0.0074` using the already-clamped `replicates` and "
    "`turn_cap = payload.get('turn_cap', 20)` (positive int, else fail `turn_cap must be a positive integer`). Put "
    "0.0074 and 20 in clearly named module constants (`_USD_PER_COUNTED_TURN`, `_DEFAULT_TURN_CAP`). When "
    "`estimate_usd > max_usd` fail with a line naming both numbers and call nothing.\n"
    "3. Records `estimate_usd` on the Cloudflare ledger row this station already writes for a run (look at "
    "`_record_cloudflare_spend` and the ledger row type in factory/guard.py; READ guard.py, never edit it or "
    "factory/config/**). If the row type has no field for it, do NOT change guard.py: include the estimate in the "
    "row's existing free-text/detail field if one exists, otherwise keep it in the StationResult output line and "
    "say so in NOTES.txt.\n"
    "4. After the run, when the measured Cloudflare spend (micro_usd / 1e6) or the OpenAI player spend, taken "
    "separately, exceeds `max_usd`, the station result stays as today (do not turn a finished run into a failure "
    "and never discard its report or packets) but the output line says `cap_exceeded` with the measured and "
    "allowed amounts, and `payload_updates` gains `cap_exceeded: true` (merge it with the `runs` update when both "
    "apply; a result that otherwise had no payload_updates gets just that key).\n"
    "Everything else (spend recording, quota detection, lock handling, the failure-output tail already present) "
    "stays exactly as is.\n\n"
    "TESTS (extend tests/test_factory_live_playtest.py, hermetic, with the file's existing fake runner/fetch/"
    "budget readers): missing `max_usd` fails and the fake runner is never called; non-positive, bool and string "
    "`max_usd` fail; an estimate above `max_usd` fails with the runner never called (e.g. 3 replicates, turn_cap 20, "
    "max_usd 0.10); an estimate within the cap proceeds; `turn_cap` default and override change the estimate; "
    "a fake budget reader whose after-minus-before exceeds `max_usd` yields a result whose output contains "
    "`cap_exceeded`, whose payload_updates has `cap_exceeded` true, and whose report/packets are still returned; "
    "the grading path with `report_path` still works with no `max_usd`. Do not assert exact full sentences beyond "
    "those facts."
)


def check(owned_re: str, tests: str, budget: int, extra: str, patch: str) -> str:
    return f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^({owned_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 {tests}
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget {budget} s)"
[ "$took" -le {budget} ] || {{ echo "over the {budget} s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only | grep '\\.py$' || true)
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
{extra}
git diff --cached > "$WORK/out/{patch}.patch"
test -s "$WORK/out/{patch}.patch"
"""


EVIDENCE_EXTRA = """grep -q 'truncated' factory/stations/fix_plan.py || { echo 'no truncated marker in fix_plan.py'; exit 1; }
.venv/bin/python - <<'PYV'
from factory.stations.fix_plan import _bound_evidence

def packet(n):
    return {
        "failing_turns": [
            {"key": f"k{i}", "player_input": "x", "narration": "n" * 500, "previous_narration": "p" * 600,
             "candidates_offered": [], "matched_candidate": None, "outcome": None}
            for i in range(n)
        ],
        "candidates": {f"c{i}": {"text": "t" * 400} for i in range(10)},
        "beats": [], "exits": [], "fact_readers": {},
    }

out = _bound_evidence(packet(25))
assert out["failing_turns"], "all failing turns were dropped"
assert "truncated" in out, "cut with no truncated marker"
print("kept", len(out["failing_turns"]), "of 25;", out["truncated"])
PYV"""

SPEND_EXTRA = """grep -q 'max_usd' factory/stations/live_playtest.py || { echo 'no max_usd handling'; exit 1; }
grep -q 'cap_exceeded' factory/stations/live_playtest.py || { echo 'no cap_exceeded flag'; exit 1; }"""

manifest = {
    "run_name": "factory-21b-evidence-and-spend-cap",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "evidence-cap",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": ["factory/stations/fix_plan.py", "tests/test_factory_fix_plan.py"],
            "spec": EVIDENCE_SPEC,
            "check": check(
                r"factory/stations/fix_plan\.py|tests/test_factory_fix_plan\.py",
                "tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_qualification_run_case.py",
                300,
                EVIDENCE_EXTRA,
                "evidence-cap",
            ),
            "expect_files": [],
            "verified": "Failing turns survive evidence bounding and any cut is reported in a truncated marker.",
        },
        {
            "key": "spend-cap",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": ["factory/stations/live_playtest.py", "tests/test_factory_live_playtest.py"],
            "spec": SPEND_SPEC,
            "check": check(
                r"factory/stations/live_playtest\.py|tests/test_factory_live_playtest\.py",
                "tests/test_factory_live_playtest.py tests/test_factory_probe.py tests/test_factory_line.py",
                300,
                SPEND_EXTRA,
                "spend-cap",
            ),
            "expect_files": [],
            "verified": "A billed live playtest run needs max_usd, is refused when its estimate exceeds it, and flags cap_exceeded.",
        },
    ],
}
Path(__file__).with_name("round21b-evidence-and-spend-cap-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
