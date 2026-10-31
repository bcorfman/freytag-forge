# ruff: noqa: E501
"""Write build-t9h-j1c-wiring-probe.json: the free build of the J1c wiring probe (step 2 of the wiring plan)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = f"{REPO}/scripts/ringer/environment_narration"
PREREG = f"{REPO}/.plans/grounded-llm-environment-narration/t9h-j1c-wiring-probe-prereg.md"
PROBE = f"{ENV}/j1c_wiring_probe.py"
TESTS = f"{REPO}/tests/test_j1c_wiring_probe.py"

SPEC = (
    f"You are the PROBE worker. Working directory: {REPO} (Python 3.12). export PYTHONPATH={REPO} TMPDIR=/tmp; run "
    "`.venv/bin/python` (never uv). Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN "
    ".venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. No network, no live model call, no billed "
    "call, no Worker: you build and test the probe, you NEVER run it with `--run`. Do not git commit. NEVER print or "
    "write any credential. NO regular expressions. Keep the code in the style of the surrounding files (comment "
    "density, naming, idiom). METHOD: write the tests FIRST, watch them fail for the right reason, then implement. "
    f"You own ONLY {PROBE} and a NEW test file {TESTS}. Never touch storygame/, packages/, data/, the plan files, "
    "the corpus, the locked scope cases, or any other script or test. "
    f"BACKGROUND. Read the preregistration FIRST and follow it exactly: {PREREG}. TEMPLATE: {ENV}/j1_scope_probe.py "
    f"(read it fully) and its tests {REPO}/tests/test_j1_scope_probe.py. IMPORT shared helpers from j1_scope_probe "
    "(and through it from j1_screen_probe and verifier_calibration) instead of copying: case loading and the scope "
    "lock check, the client ask path, redaction, stop-reason code, atomic row writing, percentile helpers. Do not "
    "edit those files. The probe builds its two request sets at run time by fixed rules from the LOCKED scope cases "
    f"({ENV}/j1_scope/cases.jsonl, lock {ENV}/j1_scope/lock.json); it authors no new case file and writes no new "
    "lock. Every mode first checks the scope lock (refuses on a mismatch). "
    "PRODUCT FORM. label(place) = place with a leading 'the ' removed (case-insensitive), first letter capitalised, "
    "the rest unchanged ('the mountain observatory' -> 'Mountain observatory'). SET A: for each of the 30 "
    "scene_level scope cases, one request with ONE relation Relation(thing, label(place), None); the V0 arm sends "
    "state {'narration': text} and the product's `_question_for(relation)`; the J1c arm sends state "
    "{'narration': text, 'scene': label(scene_place), 'starting_places': {thing: label(place)}} with the same "
    "question. SET B: 12 mixed batches built by these fixed position rules from the scope cases (n is the story "
    "number 1-6; case ids are f-<n>-<two digits>): m-n-1 for every story: narration = narration of f-n-01 + ' ' + "
    "narration of f-n-06, relations [scene-level Relation(thing of f-n-01, label(scene_place)), specific "
    "Relation(thing of f-n-06, its own place unchanged)] labelled [accept, accept]; m-n-2 for stories 1-3: "
    "narration = narration of f-n-02, relations [scene-level Relation(thing of f-n-02, label(scene_place)) accept, "
    "specific Relation(thing of f-n-10, its own place unchanged) reject]; m-n-3 for stories 4-6: narration = "
    "narration of f-n-07, relations [specific Relation(thing of f-n-07, its own place unchanged) accept, "
    "scene-level Relation(thing of f-n-05, label(scene_place)) reject]. Relations are in that listed order; each "
    "request is ONE batched ask with questions relation_0, relation_1 (the product's question per relation). A "
    "relation is scene-level iff it was built from a scene_level case's place (track a per-relation flag). The "
    "builder fails with a clear error if a reject-labelled thing's name (lowercase) occurs in the narration it is "
    "asked against, or if any referenced case id is missing. V0 arm: state {'narration': text}. J1c arm: if at "
    "least one relation is scene-level, state {'narration': text, 'scene': label(scene_place), 'starting_places': "
    "{thing: label(place) for each scene-level relation only}}, else the V0 state. Put the state construction in "
    "one small function (`j1c_state(narration, relations, scene)` taking (thing, place, scene_level) items) and "
    "test it directly. "
    "MODES: `--validate` (scope lock matches, Set A has 30 cases, Set B has 12 requests with 18 accept-labelled "
    "and 6 reject-labelled relations, prints the counts); `--dry-run` (set sizes, planned requests = (30 + 12) x 2 "
    "arms x --samples (default 5) = 420, token estimate, USD ceiling at 1.5x margin); `--run --confirm` (refuses "
    "without --confirm, without --out, with a bad lock, when planned calls exceed --max-calls (default 440), when "
    "the ceiling exceeds --max-usd (default 0.02), or when either Cloudflare environment variable is missing; "
    "stops after 3 consecutive unusable replies and on HTTP 429/5xx; atomic rows after every call; stop_reason "
    "'incomplete' until the last row is written, then null); `--report --rows F --out F` (markdown; exit 1 on "
    "failure). Rows record set ('A' or 'B'), request id, arm, sample, per-relation thing/label/scene_level/score/"
    "verdict, and whether the J1c state differed from the V0 state. "
    "REPORT and GATES (J1c with V0 beside it; uncertain is never an accept): A1 zero accepts among the 90 "
    "negative samples of Set A; A2 at least 54 of the 60 positive samples of Set A are accept and no fewer than "
    "V0's count; B1 zero accepts among the 30 reject-labelled relation samples of Set B; B2 at least 80 of the 90 "
    "accept-labelled relation samples of Set B are accept; B3 on the accept-labelled specific-place relations of "
    "Set B (9 relations, 45 samples) J1c has at most 2 fewer accepts than V0. Overall PASS only if all five hold. "
    "Also report: every non-reject sample on a reject-labelled relation with its score, per-relation score "
    "ranges, sample-to-sample disagreement, latency p50/p95, model/version, and the number of requests whose J1c "
    "state differed from V0's. "
    "TESTS in tests/test_j1c_wiring_probe.py, hermetic (fake client, tmp fixtures; the real locked cases may be "
    "read for the derivation test): label(); `j1c_state` for scene-level only, specific only and mixed items; "
    "Set A and Set B derivation counts and the exact relation labels of m-1-1, m-2-2 and m-4-3 from the real "
    "cases; the reject-thing-in-narration guard fails on a doctored case; planned-call arithmetic 420 and "
    "deterministic seeded order; run refusals (no --confirm, no --out, bad lock, over --max-calls, over --max-usd, "
    "missing environment); a fake-client run writes all 420 rows with a final null stop_reason, stops on three "
    "unusable replies, and leaves an 'incomplete' document if the client raises; report gates on hand-made rows "
    "for a pass and for a fail of each of A1, A2, B1, B2, B3; no credential value in dry-run output. Add only "
    "tests that cover real behavior; no redundant ones. Finally run the new tests plus "
    "tests/test_j1_scope_probe.py, then `.venv/bin/python -m ruff check --fix` and `ruff format` on your owned "
    "files, and report the test counts and the `--validate` and `--dry-run` output."
)

CHECK = (
    f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail "
    "&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
    "-p no:cacheprovider --no-cov tests/test_j1c_wiring_probe.py tests/test_j1_scope_probe.py "
    "2>&1 | tee /tmp/j1c-wiring-tests.out | tail -15 "
    "&& ! grep -Eq '[0-9]+ failed|FAILED|ERROR' /tmp/j1c-wiring-tests.out "
    "&& grep -Eq '[0-9]+ passed' /tmp/j1c-wiring-tests.out "
    f"&& .venv/bin/python {PROBE} --validate | tee /tmp/j1c-wiring-validate.out "
    f"&& .venv/bin/python {PROBE} --dry-run | tee /tmp/j1c-wiring-dry.out "
    "&& grep -q 'planned requests: .*= 420' /tmp/j1c-wiring-dry.out "
    f"&& .venv/bin/python -m ruff check {PROBE} {TESTS} "
    f"&& .venv/bin/python -m ruff format --check {PROBE} {TESTS} "
    f"&& ! grep -n 'import re$' {PROBE} && grep -q 'os.replace' {PROBE} && grep -q 'def j1c_state' {PROBE}"
)

MANIFEST = {
    "run_name": "t9h-j1c-wiring-probe-build",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-j1c-wiring-probe-build",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "j1c-wiring-probe",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "ownership": [PROBE, TESTS],
            "expect_files": [PROBE, TESTS],
            "verified": "product-form Set A and mixed-batch Set B probe with J1c state function, gates, hermetic tests; nothing billed",
            "spec": SPEC,
            "check": CHECK,
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("build-t9h-j1c-wiring-probe.json")
    out.write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(out)
