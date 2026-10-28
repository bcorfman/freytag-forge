# ruff: noqa: E501
"""Generate the Ringer build manifest for T9d round 1: search opens, underside decided first, probe v2, report, run scripts."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
E = "scripts/ringer/environment_narration"
OUT = Path(__file__).resolve().parent / "build-t9d-round1.json"
PREREG = ".plans/grounded-llm-environment-narration/t9d-search-opens-prereg.md"

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call, no billed call, never run a billed script. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "Story-agnostic engine code: no story names, verbs, vocabulary or notice text in non-test code under storygame/. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement until they pass. Run ruff check and ruff format on your files at the end. "
    "Other workers edit OTHER files in this same checkout at the same time; edit only the files you own. "
    "If a test in a file you do not own fails because of your change, do NOT edit that file: say which test and why in your final message. "
    "Any generator script you write must write its output files NEXT TO ITSELF using `Path(__file__).resolve().parent` and never a hardcoded absolute output path (CI runs the generators in a different checkout path); the manifest CONTENTS may contain /home/bcorfman/dev/... paths. "
    f"BACKGROUND. Read {PREREG} fully first; it is the preregistration this build implements. Plain summary: in a Jev-classified turn on a container, the engine asked `opens_container` first (true gives request kind `open`, and the engine opens a closed openable container before narration) and only then, if false, asked `searches_underneath` (true gives kind `under`). Brandon's decision: `search the drawer` now OPENS the drawer (the engine does it), because the narrator opened it itself on 15 of 15 such turns and 4 of those failed; `inspect`, `examine`, `check` and `look at` stay look commands; any verb followed by under, beneath, underneath or below is an underside search and must stay kind `under` (finding the card), so the underside question is now asked FIRST and decides before `opens_container` is asked."
)

CHECK = f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
PYTEST = "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov "


def ruff(files: str) -> str:
    return f".venv/bin/python -m ruff check {files} && .venv/bin/python -m ruff format --check {files}"


def pytest_check(out: str, files: str) -> str:
    return (
        f"{PYTEST}{files} 2>&1 | tee /tmp/{out}.out | tail -6 && ! grep -Eq '[0-9]+ (failed|error)' /tmp/{out}.out && "
    )


ORDER_FILES = (
    "storygame/runtime/jev_questions.py storygame/runtime/capture.py tests/test_jev_questions.py "
    "tests/test_observation_mode.py tests/test_observation_open_step.py tests/test_observation_under_scope.py "
    "tests/test_search_opens_drawer.py"
)

ORDER_SPEC = (
    COMMON
    + "YOUR TASK: (1) reword the Jev question `opens_container` and (2) ask the underside question first. YOU MAY EDIT ONLY: storygame/runtime/jev_questions.py (only the `opens_container` function's question text), storygame/runtime/capture.py (only `WorldCapture._set_observation_request` and tiny helpers it needs), tests/test_jev_questions.py, tests/test_observation_mode.py, tests/test_observation_open_step.py, tests/test_observation_under_scope.py, and the NEW file tests/test_search_opens_drawer.py. "
    "(1) WORDING. Replace the `opens_container` question text with EXACTLY these three strings (keep the function name, signature, return type, the `noul` type, the payload keys and the `_answer` call as they are; do not touch `searches_underneath`): "
    "instructions = 'Decide whether the command has the player open the container. Opening it, pulling it open or out, searching it, or going inside, in, into, or through it counts.' ; "
    "true = 'The command opens the container, pulls it open, pulls it out, searches it, or says inside, in, into, or through the container. The player looks, feels, or reaches there.' ; "
    "false = 'The command does not open the container, does not search it, and does not say inside, in, into, or through. A command that only looks at, inspects, examines, checks, closes, locks, touches, moves, carries, or talks about the container, or goes behind or on top of it, is false.' "
    "(2) ORDER. In `WorldCapture._set_observation_request` (read it first; today it asks `opens_container` for a container focus, makes kind `open` when true, and asks `searches_underneath` only when the kind is still `look`), change the order for a container or supporter focus that is not a boarding (kind `enter`) case: ask `searches_underneath` FIRST; if it is True the kind is `under` and `opens_container` is NOT asked (so `opens` stays None and no engine open happens); otherwise, for a container focus, ask `opens_container` (True gives kind `open`, exactly as today, followed by the existing engine open step); otherwise kind `look`. A supporter focus asks only `searches_underneath`. A `None` answer from either question counts as not True. Everything else (the engine open step conditions via `_should_engine_open`, `engine_opened`, `focus_open_state_after`, rollback, the `enter` and non-container paths where neither question is asked) is unchanged. "
    "TESTS. Existing tests that pin the OLD order or the old wording must be updated to the new behaviour (you own the four existing test files above; read each for assertions about which questions are asked, in which order, with which answers, and about the question text, for example `test_under_question_is_not_asked_for_open_enter_or_non_container` in tests/test_observation_under_scope.py, which must now say: for an open command `searches_underneath` is asked first and `opens_container` second; for an enter command and for a non-container non-supporter focus neither is asked). RULES for updating: change only assertions that pin the old order or text, never delete, loosen or skip a test, and list every assertion you changed in your final message. "
    "NEW tests/test_search_opens_drawer.py (real continuity package as tests/test_observation_under_scope.py does with `_state_at('kitchen')`, `build_capture_provider`, `WorldCapture` and a stubbed ask, no network; also read tests/test_drawer_gap_nudge.py for how a command is matched to a handoff in the real package, and reuse its helper): "
    "a) `search the drawer` with answers searches_underneath False, opens_container True: the ask order is searches_underneath then opens_container; the request kind is `open`; the closed drawer (`michelle_drawer`) is open after `before_turn`, `engine_opened` True; the observation context then requires the four supplies; the authored handoff that command matches in the real package is still the repeatable nudge `k_sl_1a_f_r2`. "
    "b) `search under the drawer` with searches_underneath True: kind `under`, `opens_container` NOT asked, the drawer stays closed, `engine_opened` False, and the matched authored handoff is the card find (`k_sl_1a_b_r0`) and not the nudge. "
    "c) `inspect the drawer` with both answers False: kind `look`, drawer stays closed, no engine open. d) both answers None: kind `look`, closed. e) `open the drawer` (searches_underneath False, opens_container True): kind `open`, engine opens it. f) a synthetic second story (see tests/test_observation_preview.py `_synthetic_package`, or build a minimal one the way tests/test_observation_open_step.py does) with an openable container: under True keeps it closed with kind `under`; under False and opens True opens it. "
    "VERIFY: run all seven files in your ownership list plus tests/test_drawer_gap_nudge.py and tests/test_observation_enforcement.py; report any failure in a file you do not own."
)

ORDER_CHECK = (
    CHECK
    + pytest_check(
        "t9d-r1-order", ORDER_FILES + " tests/test_drawer_gap_nudge.py tests/test_observation_enforcement.py"
    )
    + ruff(ORDER_FILES)
)

PROBE_FILES = f"{E}/opens_container_probe.py {E}/make_t9d_probe_run_manifest.py tests/test_opens_container_probe_v2.py"

PROBE_SPEC = (
    COMMON
    + "YOUR TASK: add the version-2 corpus, gates and runner manifest to the opens_container Jev probe (preregistration 'Stage P: Jev probe v2'). Read scripts/ringer/environment_narration/opens_container_probe.py, tests/test_opens_container_probe.py, the v1 corpus opens_probe/ (cases.jsonl, cases.lock.json), scripts/ringer/environment_narration/under_question_probe.py (it has a `--corpus v2` option; copy that pattern), make_t9c_probe_run_manifest.py and run-t9c-probe-live.json first. "
    f"YOU MAY EDIT ONLY: {E}/opens_container_probe.py, and these NEW files: {E}/opens_probe_v2/cases.jsonl, {E}/opens_probe_v2/cases.lock.json, {E}/make_t9d_probe_run_manifest.py, {E}/run-t9d-probe-live.json, tests/test_opens_container_probe_v2.py. Do NOT change the v1 corpus, its lock, tests/test_opens_container_probe.py or any v1 behaviour: `--corpus v1` is the default and everything that works today must keep working byte for byte. "
    "OPTION: `--corpus {v1,v2}` (default v1) selects the corpus directory (`opens_probe` or `opens_probe_v2`), the build/check/dry-run/run/report behaviour, the default `--max-calls` (v1 344, v2 378) and the default output directory (v2: bench/results/environment-narration/t9d-search/probe/). "
    "V2 CORPUS (`--corpus v2 --build-cases` writes cases.jsonl and the lock from literal lists and the grid rule in the script; `--check-corpus` verifies the lock; copy the lists EXACTLY from the preregistration section 'Stage P: Jev probe v2'): "
    "grid G = 60 commands: verbs [Search, Inspect, Examine, Check, Look at] (index i) x containers [dresser, trunk, suitcase, cupboard] (index j) x forms bare / under / inside. Bare: `<Verb> the <container>.` (`Look at the trunk.`). Under: `<Verb> <w> the <container>.` with w = ['under','beneath','underneath','below'][(i+j) % 4], and the verb `Look at` becomes `Look under` (word fixed 'under' for that verb). Inside: `<Verb> inside the <container>.` with `Look at` becoming `Look inside`. "
    "Question assignment: bare and inside grid cases are asked BOTH questions (`opens_container`, `searches_underneath`); under grid cases are asked ONLY `searches_underneath`. Expected: bare Search -> opens_container True; bare Inspect/Examine/Check/Look at -> opens_container False; every bare -> searches_underneath False; under -> searches_underneath True; inside -> opens_container True and searches_underneath False. "
    "Other lists, `opens_container` only: S (16 fresh search positives, expected True), L (16 fresh bare look-group negatives, expected False), O (20 retained opening positives, expected True), N (22 retained non-opening negatives, expected False), reported X (3 phrases, expected null, printed only), and regression R (12 commands on the container `drawer`): opens_container True for `Open the drawer.`, `Pull out the drawer.`, `Look inside the drawer.`, `Search the drawer.`, `Search inside the drawer.`; opens_container False for `Inspect the drawer.`, `Examine the drawer.`, `Check the drawer.`, `Look at the drawer.`, `Close the drawer.`; searches_underneath True (opens_container NOT asked) for `Search under the drawer.` and `Look under the drawer.`. Each case records the container name given in brackets in the preregistration (for grid cases the container; for R the word `drawer`). "
    "REQUESTS: 2 samples per question-case: G (20 x 2 + 20 x 1 + 20 x 2) x 2 = 200, S 32, L 32, O 40, N 44, X 6, R (10 + 2) x 2 = 24, total 378. `--dry-run --corpus v2` prints `planned requests: 378`. `--run --confirm` refuses without `--confirm`, default `--max-calls 378`, stops on a quota code, HTTP 429, auth failure or the cap and records the stop reason, and writes rows with every raw score, exactly as v1 does. "
    "REPORT (`--report --corpus v2`) prints every score per case and sample and these gates, then a final line `probe gate: PASS` only if K1 to K6 all pass, else `probe gate: FAIL`: "
    "K1 `opens_container` true on at least 7 of the 8 bare-Search grid samples AND at least 29 of the 32 S samples (list every miss by case id); "
    "K2 `opens_container` TRUE answers among the 64 samples of the bare Inspect, Examine, Check and Look at grid commands (32) plus L (32) must be zero (also print the one-sided 95% Wilson upper bound); "
    "K3 `opens_container` true on at least 36 of the 40 inside grid samples (list misses by case id and verb); "
    "K4 `searches_underneath`: at least 36 of 40 false on the bare grid samples, at least 38 of 40 TRUE on the under grid samples, at least 36 of 40 false on the inside grid samples (list misses by case id and verb); "
    "K5 O at least 36 of 40 true AND N zero true of 44; "
    "K6 R: all 10 true-labelled `opens_container` samples true, all 10 false-labelled false, and all 4 `searches_underneath` samples true. A `None` answer counts as not true for every gate that needs true and as not false for every gate that needs false; print the number of None answers. The reported group X is printed with no gate. "
    f"RUNNER MANIFEST: `{E}/make_t9d_probe_run_manifest.py` WRITES `{E}/run-t9d-probe-live.json` next to itself, modelled on make_t9c_probe_run_manifest.py (same runner rules: COMMAND 1 exactly once, foreground, never rerun, edit nothing, no credential, no commit; load .env the way that manifest does) with COMMAND 1 = `opens_container_probe.py --corpus v2 --run --confirm --max-calls 378 --max-usd 0.01 --out bench/results/environment-narration/t9d-search/probe/rows.json`, COMMAND 2 the safe `--report --corpus v2` render into report.md in that directory, workdir `/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9d-probe`, the 378-row-or-stop-reason check and the credential-leak check as in the T9c manifest, and run name `grounded-environment-narration`. "
    "TESTS (tests/test_opens_container_probe_v2.py; stub the client, no network): a) corpus counts: grid 60 (20 bare, 20 under, 20 inside), S 16, L 16, O 20, N 22, X 3, R 12; unique ids; the 378 request count; b) every command of the grid generator output, S, L, O, N, X and R occurs in the preregistration file (the grid commands as generated patterns: check the 16 bare grid commands, and the generated under and inside strings against the rule); c) none of the grid, S and L commands occurs in the T9c probe corpus (opens_probe/cases.jsonl) or in the earlier under_probe and under_probe_v2 lists; d) the report gates: synthetic rows that satisfy everything give `probe gate: PASS`; for each of K1..K6 a synthetic row set that violates exactly that gate gives FAIL and names the miss; None answers are counted; e) `--run` without `--confirm` exits non-zero without a call; f) the generated run manifest matches the committed JSON byte for byte when regenerated into a temp copy of the script's directory. "
    "VERIFY: run tests/test_opens_container_probe_v2.py, tests/test_opens_container_probe.py and tests/test_under_question_probe.py and tests/test_under_question_probe_v2.py (all must pass), then `--corpus v2 --check-corpus` and `--corpus v2 --dry-run`."
)

PROBE_CHECK = (
    CHECK
    + pytest_check(
        "t9d-r1-probe",
        "tests/test_opens_container_probe_v2.py tests/test_opens_container_probe.py tests/test_under_question_probe.py tests/test_under_question_probe_v2.py",
    )
    + f".venv/bin/python {E}/opens_container_probe.py --check-corpus && "
    + f".venv/bin/python {E}/opens_container_probe.py --corpus v2 --check-corpus && "
    + f".venv/bin/python {E}/opens_container_probe.py --corpus v2 --dry-run | grep -q 'planned requests: 378' && "
    + f".venv/bin/python {E}/opens_container_probe.py --dry-run | grep -q 'planned requests: 344' && "
    + f"(cd /home/bcorfman/dev/ringer && ./ringer.py lint {REPO}/{E}/run-t9d-probe-live.json) && "
    + ruff(PROBE_FILES)
)

REPORT_FILES = f"{E}/enforce_report.py tests/test_enforce_report_t9d.py tests/test_enforce_report_t9c.py tests/test_enforce_report_scope.py"

REPORT_SPEC = (
    COMMON
    + "YOUR TASK: update the blind-label report script for the T9d gates (preregistration section 'Stages S and F', 'Gate'). Read scripts/ringer/environment_narration/enforce_report.py (the T9c clauses N1 to N6 are in `_t9c_n1` .. `_t9c_n6` and the `_join` function that prints them), tests/test_enforce_report_t9c.py and tests/test_enforce_report_scope.py first. "
    f"YOU MAY EDIT ONLY: {E}/enforce_report.py, tests/test_enforce_report_t9c.py, tests/test_enforce_report_scope.py (only assertions that pin the T9c rules changed below), and the NEW file tests/test_enforce_report_t9d.py. The report is joined PER ROUTE FILE, so the gates are per route. "
    "CHANGES. (1) Constants: LOOK_GROUP_COMMANDS becomes (`inspect the drawer`, `examine the drawer`, `check the drawer`); add NUDGE_GROUP_COMMANDS = (`inspect the drawer`, `examine the drawer`, `search the drawer`, `check the drawer`) and SEARCH_COMMAND = `search the drawer`. (2) N1 (route C scope only, i.e. when the file has route `observe_look_inside_under`): over the look-group turns (the three verbs), PASS when at least 43 of the 45 turns end with a committed narration (generalise as: at least the total minus 2 for a total of 45; print `N1: PASS|FAIL (X/Y look-group turns committed; failures: ...)` as today with each failing turn id and reason). (3) New N1s (route C scope only): over the `search the drawer` turns, PASS when at least 14 of the 15 turns are committed AND `focus_open_state_committed` is `open` AND the `contents_shown` label is true; print `N1s: PASS|FAIL (X/Y search turns pass; failures: id (reasons))` with reasons `unsuccessful`, `closed after commit`, `contents_shown false`. (4) N2 (route C scope): over the nudge-group turns (four commands) gap restated on at least 58 of the 60 turns (as the current route C part; drop the pooled-72 part); misses listed with handoff_id as today. Add N2a, printed for any file that has route `observe_topup` rows with `inspect the drawer` turns: PASS when at least 9 of the 10 route A `inspect the drawer` turns have the `gap_restated` label true (generalise as: at most 1 miss for 10 turns); print `N2a: PASS|FAIL (X/Y route A inspect turns restated the gap)`. Route B is not part of N2. (5) N3, N4 and N6 unchanged. (6) N5: failures are (a) `engine_opened` true while the `command_opens` label is not true, and (b) `engine_opened` true on a look-group turn (the three verbs only, NOT search). (7) Information lines (printed, never gated): keep the existing ones; make `look-group request kinds` use the three verbs; add `search request kinds: look=a/15, open=b/15, under=c/15` style for the search turns; `narrator-opened look-group and search turns:` listing turn ids where `engine_opened` is not true and `focus_open_state_committed` is `open` while `focus_open_state_after` was `closed` (the narrator, not the engine, set it open; keep the existing narrator-opened line if one exists and extend it to the search turns); `engine opens by command:` counts per command; and `delivered statement text in prose:` the number of committed route C `look under the drawer` turns whose narration contains the sentence `Kristin looks over the drawer and is pointed toward the thin gap beneath its lower edge.` (a bench script may hold this literal). (8) The `command_opens` label guidance in any help text or docstring: true when the command text opens the container, pulls it open or out, SEARCHES it, or says inside, in, into or through it. (9) A file with NO route C rows must still print exactly what it prints today for clauses 1 to 7, S1 to S3 (no new T9c/T9d lines except N2a for route A). "
    "TESTS (tests/test_enforce_report_t9d.py with synthetic rows and labels built the way tests/test_enforce_report_t9c.py builds them): for each of N1, N1s, N2, N2a, N5 one synthetic set that passes exactly at the limit and one that fails just past it (N1 43/45 vs 42/45; N1s 14/15 vs 13/15, and a search turn with the drawer closed after commit fails with that reason; N2 58/60 vs 57/60; N2a 9/10 vs 8/10; N5 an engine open on `search the drawer` with `command_opens` true passes, with `command_opens` false fails, an engine open on `inspect the drawer` fails even if `command_opens` is true); a route A-only file and a route B-only file still print their old clauses; the new information lines appear. Update the T9c report tests only where they pin the changed rules (list every assertion you changed in your final message; never delete, loosen or skip a test). "
    "VERIFY: run tests/test_enforce_report_t9d.py tests/test_enforce_report_t9c.py tests/test_enforce_report_scope.py and every other tests/test_enforce_report*.py file; all must pass."
)

REPORT_CHECK = (
    CHECK
    + pytest_check("t9d-r1-report", "tests/test_enforce_report*.py")
    + ruff(f"{E}/enforce_report.py tests/test_enforce_report_t9d.py")
)

RUN_FILES = f"{E}/make_t9d_run_manifests.py tests/test_t9d_run_manifests.py"

RUN_SPEC = (
    COMMON
    + "YOUR TASK: the T9d stage script and run manifests (preregistration 'Stages S and F'). Read scripts/ringer/environment_narration/enforce_stage3.sh, make_t9c_run_manifests.py, run-t9c-smoke.json and tests/test_t9c_run_manifests.py first and copy them closely. "
    f"YOU MAY EDIT ONLY these NEW files: {E}/enforce_t9d.sh, {E}/make_t9d_run_manifests.py, {E}/run-t9d-smoke.json, {E}/run-t9d-full.json, tests/test_t9d_run_manifests.py. Do not change any T9c file. "
    "(1) enforce_t9d.sh is enforce_stage3.sh with: the usage/comment text saying T9d, OUT=$ROOT/bench/results/environment-narration/t9d-search/$STAGE, everything else identical (port 8797, routes A observe_topup then B observe_under_first then C observe_look_inside_under with the same stop-reason gating between them, same caps: smoke A `--replicates 1 --max-calls 90`, B `--replicates 1 --max-calls 40`, C `--replicates 2 --max-calls 90`, MAX_USD 0.07; full A `--replicates 10 --max-calls 800`, B `--replicates 5 --max-calls 250`, C `--replicates 15 --max-calls 700`, MAX_USD 0.45). Make it executable and `bash -n` clean. "
    "(2) make_t9d_run_manifests.py writes run-t9d-smoke.json and run-t9d-full.json NEXT TO ITSELF using `Path(__file__).resolve().parent` (REPO string constant may stay `/home/bcorfman/dev/freytag-forge` for manifest contents only, never for the output location), modelled on make_t9c_run_manifests.py: workdir `/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9d-{stage}`, COMMAND 1 `cd <repo> && bash scripts/ringer/environment_narration/enforce_t9d.sh {stage}`, the prereg path `.plans/grounded-llm-environment-narration/t9d-search-opens-prereg.md`, the output directories under t9d-search, the same expected row counts and caps (smoke A 1x9, B 1x4, C 2x6, $0.07, 70000 micro-dollars; full A 10x9, B 5x4, C 15x6, $0.45, 450000), the stop-reason or exact-row-count check and the credential-leak check as in the T9c manifests, one task, max_attempts 1, max_parallel 1, run name `grounded-environment-narration`. Generate both JSON files by running the generator. "
    "(3) tests/test_t9d_run_manifests.py mirrors tests/test_t9c_run_manifests.py for T9d (script has routes, port and caps; the manifests have caps, workdirs, checks and no credential values; and the regeneration test copies the generator into a temp directory OUTSIDE the repo, runs it there and compares the two JSON files byte for byte with the committed ones, so it passes in any checkout path). "
    f"VERIFY: run tests/test_t9d_run_manifests.py and tests/test_t9c_run_manifests.py, `bash -n {E}/enforce_t9d.sh`, and `cd /home/bcorfman/dev/ringer && ./ringer.py lint {REPO}/{E}/run-t9d-smoke.json` and the same for run-t9d-full.json."
)

RUN_CHECK = (
    CHECK
    + pytest_check("t9d-r1-run", "tests/test_t9d_run_manifests.py tests/test_t9c_run_manifests.py")
    + f"bash -n {E}/enforce_t9d.sh && test -x {E}/enforce_t9d.sh && "
    + f"(cd /home/bcorfman/dev/ringer && ./ringer.py lint {REPO}/{E}/run-t9d-smoke.json && ./ringer.py lint {REPO}/{E}/run-t9d-full.json) && "
    + ruff(RUN_FILES)
)


def _task(key, spec, check, ownership, expect, verified):
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "ownership": ownership,
        "expect_files": [f"{REPO}/{p}" for p in expect],
        "spec": spec,
        "check": check,
        "verified": verified,
    }


manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9d-round1",
    "max_parallel": 4,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        _task(
            "t9d-order-and-wording",
            ORDER_SPEC,
            ORDER_CHECK,
            [
                "storygame/runtime/jev_questions.py",
                "storygame/runtime/capture.py",
                "tests/test_jev_questions.py",
                "tests/test_observation_mode.py",
                "tests/test_observation_open_step.py",
                "tests/test_observation_under_scope.py",
                "tests/test_search_opens_drawer.py",
            ],
            ["tests/test_search_opens_drawer.py"],
            "search opens the drawer in the engine and the underside question decides first",
        ),
        _task(
            "t9d-probe-v2",
            PROBE_SPEC,
            PROBE_CHECK,
            [
                f"{E}/opens_container_probe.py",
                f"{E}/opens_probe_v2/cases.jsonl",
                f"{E}/opens_probe_v2/cases.lock.json",
                f"{E}/make_t9d_probe_run_manifest.py",
                f"{E}/run-t9d-probe-live.json",
                "tests/test_opens_container_probe_v2.py",
            ],
            [f"{E}/run-t9d-probe-live.json", "tests/test_opens_container_probe_v2.py"],
            "the v2 probe corpus, gates K1 to K6 and runner manifest match the preregistration",
        ),
        _task(
            "t9d-report",
            REPORT_SPEC,
            REPORT_CHECK,
            [
                f"{E}/enforce_report.py",
                "tests/test_enforce_report_t9d.py",
                "tests/test_enforce_report_t9c.py",
                "tests/test_enforce_report_scope.py",
            ],
            ["tests/test_enforce_report_t9d.py"],
            "the report computes N1, N1s, N2, N2a and N5 as preregistered",
        ),
        _task(
            "t9d-run-manifests",
            RUN_SPEC,
            RUN_CHECK,
            [
                f"{E}/enforce_t9d.sh",
                f"{E}/make_t9d_run_manifests.py",
                f"{E}/run-t9d-smoke.json",
                f"{E}/run-t9d-full.json",
                "tests/test_t9d_run_manifests.py",
            ],
            [f"{E}/run-t9d-smoke.json", f"{E}/run-t9d-full.json", "tests/test_t9d_run_manifests.py"],
            "the T9d stage script and smoke/full manifests carry the preregistered caps and checks",
        ),
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
