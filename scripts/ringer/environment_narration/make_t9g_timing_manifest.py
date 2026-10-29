"""Write build-t9g-timing.json: per-call timing split in the enforced bench rows and report."""

from __future__ import annotations

import json
from pathlib import Path

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
    "-p no:cacheprovider --no-cov <files>`. No network, no live model call, no billed call. Do not git commit. "
    "NEVER print or write any credential. NO regular expressions in new code. Never name a story, a character, an "
    "item or a scene id in engine code. METHOD: write the new tests FIRST and run them to see them fail for the right "
    "reason, then implement until they pass. Keep the code in the style of the surrounding file (comment density, "
    "naming, idiom). "
    "BACKGROUND. T9e stage F failed its latency clause 6 on route A (p95 27.10 s) and route C (p95 16.43 s) and the "
    "rows could not say why: they hold one wall-clock number per turn (`turn_elapsed_s`) and no per-call timing. "
    "The worker log showed Jev calls slow (p50 839 ms against 154 ms the run before) but the split was inferred "
    "afterwards from a worker log that does not know which turn a call belonged to. A turn makes about 3.5 Jev calls "
    "and about 2 narration calls, one after another. The goal is that the NEXT enforced run explains its own "
    "latency. This is two small tasks that share one row schema, defined here. "
    "SCHEMA (the contract between the two tasks). When `--enforce` is on, each turn row gets a new key "
    '`call_timings`: a list, in call order, of objects {"kind": "jev" | "narration" | "worker", '
    '"elapsed_s": float, "status": int or null, "keys": list of str}. `kind` is `jev` when the request URL ends '
    "with `/jev` (then `keys` is the list of question keys in the request body's `input.questions`, in order, "
    "else []); `narration` when the request body is a JSON object whose `system` string starts with "
    "'You are the narrator'; otherwise `worker` (item-facts and other worker calls). `elapsed_s` is wall seconds "
    "from just before the real `urlopen` to the moment the response body has been read (the first `read()` of the "
    "response, or the exception if the call raises), measured with time.monotonic(); `status` is the HTTP status "
    "when known else null. The list covers exactly the calls of that turn (cleared at the start of each turn like "
    "`prompts`). A call that raises still gets an entry. With `--enforce` off the rows and summary must stay "
    "byte-identical to today. `turn_elapsed_s` is unchanged. "
)

HARNESS_SPEC = (
    "You are the HARNESS worker. "
    + COMMON
    + "You own ONLY scripts/ringer/transcript_1a/live_baseline.py and tests/test_live_baseline_enforce.py (extend it; "
    "do not create a test file). Never touch enforce_report.py or any other file. "
    "BUILD. In `CallCounter` (scripts/ringer/transcript_1a/live_baseline.py) add a `timings` list that is cleared "
    "wherever `prompts` is cleared for a turn. In `live_urlopen` measure the call as the SCHEMA says: classify the "
    "request, record the start time before the real `urlopen`, and finish the entry when the wrapped response's "
    "body has been read (`_LiveResponse.read`) or when `urlopen` raises (HTTPError, URLError, timeout). Do not change "
    "what is returned, raised, counted (`calls_made`, `real_calls`) or inspected for quota codes. The dry-run path "
    "(`dry_urlopen`) records nothing. In `_replicate`, where the other enforce-only row keys are set, add "
    '`row["call_timings"] = list(counter.timings)` under the same `if enforce:`; the opening record is untouched. '
    "TESTS in tests/test_live_baseline_enforce.py, following how the existing tests there fake urlopen and the "
    "worker (read them first): (1) with `--enforce` on, every turn row has `call_timings`, each entry has the four "
    "keys with the right types, a `/jev` call has `kind` jev and its question keys, a narrator prompt has kind "
    "narration, and the number of narration entries equals the row's `narration_attempts`; (2) `elapsed_s` is "
    "non-negative and at least the time a fake urlopen sleeps or advances a patched monotonic clock (patch "
    "time.monotonic, never sleep for real); (3) a call whose urlopen raises still appears with status null or the "
    "HTTP status; (4) calls from turn 2 are not repeated in turn 3's list; (5) with `--enforce` off no row has "
    "`call_timings` and the rows equal what the current code writes (reuse the existing default-output test "
    "tests/test_live_baseline_default_output.py as the reference and run it unchanged). "
    "Also run tests/test_live_baseline_enforce.py tests/test_live_baseline_default_output.py "
    "tests/test_enforce_stage1_harness.py tests/test_enforce_stage2_harness.py and report counts."
)

REPORT_SPEC = (
    "You are the REPORT worker. "
    + COMMON
    + "You own ONLY scripts/ringer/environment_narration/enforce_report.py and a NEW test file "
    "tests/test_enforce_report_timing.py. Never touch live_baseline.py (another worker is editing it at the same "
    "time) or any other file. Build synthetic rows in the test as plain dicts following the SCHEMA; no real "
    "artifacts, no network. Read tests/test_enforce_report_t9d.py first for how the report is built from rows. "
    "BUILD. Add to the report text, for every route, a block printed just before the two final lines "
    "`enforcement screen: ...` and `t9b screen: ...`. It is INFORMATION ONLY: it must not change any clause, N gate, "
    "S gate, overall status or exit code. Use the report's existing percentile helper (`_nearest_rank`) and number "
    "formatter. The block, in this order: a header line `call timing (turns with call_timings: N of M):`; one line "
    "per kind in the order jev, narration, worker: `  <kind> calls: n=<count>, per turn mean <x>, call p50 <s>, "
    "p95 <s>, max <s>; per turn sum mean <s>` (omit a kind with zero calls); a line `  turn time outside calls "
    "(engine and waiting): mean <s>` computed as `turn_elapsed_s` minus the sum of that turn's `elapsed_s` entries, "
    "over turns that have both; a line `  slowest 5 turns:` followed by up to five lines `    <turn id> | <command> | "
    "total <s> | jev <s> | narration <s> | worker <s> | narration attempts <n>`, slowest by `turn_elapsed_s` first; "
    "a line `  slowest 5 jev calls:` followed by up to five lines `    <turn id> | <keys joined by +> | <s>`. When no "
    "turn in the route has `call_timings` (every row written before this change), print exactly one line "
    "`call timing: n/a (rows have no call_timings)` instead of the block. A turn whose `call_timings` is missing or "
    "not a list is skipped and counted only in M. Turn ids and commands come from the same fields the report's "
    "existing per-turn table uses. "
    "TESTS in tests/test_enforce_report_timing.py: (1) a route with rows that carry `call_timings` prints the block "
    "with the right counts, means, percentiles and the five slowest in the right order (work the expected numbers "
    "out by hand in the test); (2) rows without `call_timings` print the single n/a line and the report text "
    "otherwise equals what the existing tests expect (run the existing report test files unchanged); (3) the "
    "overall and clause statuses are identical with and without `call_timings` on otherwise identical rows; "
    "(4) a malformed `call_timings` (not a list, entries missing keys) does not raise. "
    "Also run tests/test_enforce_report.py tests/test_enforce_report_scope.py tests/test_enforce_report_t9c.py "
    "tests/test_enforce_report_t9d.py and report counts. If an existing report test pins the exact tail of the "
    "report text and now fails only because of the added block, update that assertion and say so in your report."
)


def _check(files: str, own: str, extra_ruff: str) -> str:
    return (
        "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp "
        "&& set -o pipefail "
        f"&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
        f"-p no:cacheprovider --no-cov {files} 2>&1 | tee /tmp/t9g-{own}.out | tail -15 "
        f"&& ! grep -Eq '[0-9]+ failed|FAILED|ERROR' /tmp/t9g-{own}.out && grep -Eq '[0-9]+ passed' /tmp/t9g-{own}.out "
        f"&& .venv/bin/python -m ruff check {extra_ruff} && .venv/bin/python -m ruff format --check {extra_ruff}"
    )


MANIFEST = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9g-timing",
    "max_parallel": 2,
    "worktrees": False,
    "repo": "/home/bcorfman/dev/freytag-forge",
    "tasks": [
        {
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "key": "harness-call-timings",
            "ownership": [
                "scripts/ringer/transcript_1a/live_baseline.py",
                "tests/test_live_baseline_enforce.py",
            ],
            "expect_files": ["/home/bcorfman/dev/freytag-forge/tests/test_live_baseline_enforce.py"],
            "verified": (
                "enforced bench rows carry a per-call timing list (kind, seconds, status, question keys) "
                "per turn, and rows with enforcement off are unchanged"
            ),
            "spec": HARNESS_SPEC,
            "check": _check(
                "tests/test_live_baseline_enforce.py tests/test_live_baseline_default_output.py "
                "tests/test_enforce_stage1_harness.py tests/test_enforce_stage2_harness.py",
                "harness",
                "scripts/ringer/transcript_1a/live_baseline.py tests/test_live_baseline_enforce.py",
            )
            + " && grep -q call_timings scripts/ringer/transcript_1a/live_baseline.py",
        },
        {
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "key": "report-call-timing-block",
            "ownership": [
                "scripts/ringer/environment_narration/enforce_report.py",
                "tests/test_enforce_report_timing.py",
            ],
            "expect_files": ["/home/bcorfman/dev/freytag-forge/tests/test_enforce_report_timing.py"],
            "verified": (
                "the enforcement report prints an information-only call timing block per route and "
                "changes no gate result"
            ),
            "spec": REPORT_SPEC,
            "check": _check(
                "tests/test_enforce_report_timing.py tests/test_enforce_report.py "
                "tests/test_enforce_report_scope.py tests/test_enforce_report_t9c.py "
                "tests/test_enforce_report_t9d.py",
                "report",
                "scripts/ringer/environment_narration/enforce_report.py tests/test_enforce_report_timing.py",
            )
            + " && grep -q 'call timing' scripts/ringer/environment_narration/enforce_report.py",
        },
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("build-t9g-timing.json")
    out.write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(out)
