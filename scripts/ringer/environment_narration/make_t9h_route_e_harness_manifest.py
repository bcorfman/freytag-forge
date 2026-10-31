"""Write build-t9h-route-e-harness.json: route E plan step 1, the free measurement-gap fixes."""

from __future__ import annotations

import json
from pathlib import Path

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
    "-p no:cacheprovider --no-cov <files>`. No network, no live model call, no billed call, no Worker. Do not git "
    "commit. NEVER print or write any credential. NO regular expressions in new code. Never name a story, a "
    "character, an item or a scene id in engine or harness logic (tests may name the real route E clues). METHOD: "
    "write the new tests FIRST and run them to see them fail for the right reason, then implement until they pass. "
    "Keep the code in the style of the surrounding file (comment density, naming, idiom). "
    "BACKGROUND. The T9h smoke sample for route E (park bench, scene 1B) stopped, and its rows could not show what "
    "happened. The harness tracks only six entity parents (`TRACKED`), so equal `places_before` and `places_after` "
    "do not prove a rejected turn rolled back, and a relation-only change (a clue going from `under` the bench to "
    "`on` it with the same parent) is invisible. It logs verifier reports but not every candidate preview, so a "
    "rejection by the unrelated-move guard (no verifier request) leaves no trace. A call-cap exception inside a "
    "turn records `verifier_requests: 1` although no verifier HTTP call completed. The run manifest also "
    "requires route F files even when the run correctly stopped at route E. This task list fixes the measurement "
    "only: it changes no product code, no acceptance rule, no story data and no prompt. "
)

HARNESS_SPEC = (
    "You are the HARNESS worker. "
    + COMMON
    + "You own ONLY scripts/ringer/transcript_1a/live_baseline.py, a NEW test file "
    "tests/test_live_baseline_evidence.py, and tests/test_live_baseline_scene_start.py (extend it). "
    "Never touch storygame/, packages/, data/, any other "
    "script or test (another worker owns the T9h manifest generator and its test). Read first: the whole of "
    "`_replicate` and `_places` in live_baseline.py, tests/test_live_baseline_enforce.py (how it fakes urlopen and "
    "runs `module.main(['--dry-run', ...])`), tests/test_live_baseline_scene_start.py, "
    "storygame/runtime/capture.py (`WorldCapture`, `_moved_unrelated`, the preview build near lines 330-470 and "
    "`last_after`), storygame/runtime/observation_preview.py (`CandidatePreview`), storygame/runtime/state.py "
    "(`snapshot`, `RuntimeSnapshot`) and packages/worldkeeper/src/worldkeeper/model.py (`entity_ids`, `parent`, "
    "`relation`, `is_hidden`, `axis_values`). "
    "CONTRACT. Every legacy field stays exactly as it is (`TRACKED`, `places_before`, `places_after`, `before`, "
    "`after`, `enforce_attempts`, `verifier_requests`, `call_timings`, ...). With `--enforce` OFF every row and "
    "summary must stay byte-identical to today (tests/test_live_baseline_default_output.py runs unchanged and "
    "passes). The additions are only for `--enforce` turn rows and the opening record, and must be JSON "
    "serializable (they are written to rows.json) and must not change any call, counter, budget or exception. "
    "Add: (1) `world_before` and `world_after` on each enforced turn row: a dict mapping EVERY entity id in the "
    "world (not only TRACKED) to {`parent`, `relation` (the value `world.relation(entity)` returns, so `under` "
    "and `on` differ), `hidden` (bool), `axes` (the dict from `world.axis_values`)}. Build both from one helper "
    "that takes the runtime state, taken before the turn starts and after `engine.turn` returns or raises. "
    "(2) `state_digest_before` and `state_digest_after`: sha256 hex of a canonical JSON dump (sorted keys) of the "
    "complete runtime snapshot (`state.snapshot()`: scene id, phase, turn_index, fired event ids, and every fact, "
    "so a newly created entity or a changed fact anywhere shows) and `state_unchanged` = the two digests are "
    "equal. Work out how to serialize the snapshot facts deterministically (read how RuntimeSnapshot and the "
    "facts store expose their content; do not use `repr` of an object that embeds memory addresses). "
    "(3) `previews`: a list with one entry for EVERY CandidatePreview the capture built during the turn, in "
    "order, each {`outcome`, `failure`, `accepted`, `required` (bool), `moved_unrelated` (list of names), "
    "`changed` (list), `relations` (the required relations as [{thing, place, holder}]), `narration`}. Capture "
    "them by wrapping the capture method that returns the preview, on the capture INSTANCE inside `_replicate` "
    "(the same way `counted_verify` wraps the verifier), calling the original unchanged and returning its "
    "result untouched; clear the list at the start of each turn. If the preview is built in more than one "
    "place, wrap the one function they share. Do not edit capture.py. "
    "(4) `turn_outcome`: exactly one of `committed` (narration is not None), `rejected` (narration None, an "
    "ordinary engine error, no stop), `stopped_call_cap` (the call counter's stop reason is MAX_CALLS_EXCEEDED "
    "when the row is built), `stopped_quota` (any other stop reason), classified from the existing "
    "`counter.stop_reason`. (5) `verifier_http_calls`: the number of this turn's `call_timings` entries of kind "
    "`jev` whose keys start with `relation_`, next to the existing `verifier_requests`, which stays the LOGICAL "
    "count; a cap row can then show 1 logical and 0 HTTP. (6) On `record['opening']` when enforcing: "
    "`world_before`, `world_after`, `state_digest_before`, `state_digest_after`, `state_unchanged` (same "
    "helpers, taken around `engine.opening()`), and `proposed_item_facts`: the `item_facts` value parsed from "
    "each narrator provider response in `provider_responses` that parses as a JSON object with that key (else an "
    "empty list), so a reader can see an opening that proposes item facts while its state did not change. "
    "TESTS in tests/test_live_baseline_evidence.py. Drive the real `_replicate` through `module.main` or the "
    "helpers directly, with fakes as the existing tests do; add a small helper-level test with a hand-built "
    "state where the real flow cannot reach a case. Six terminal cases, each asserting the legacy fields are "
    "unchanged AND the new fields are right: (a) a committed turn: `turn_outcome` committed, digests differ when "
    "a fact changed; (b) a turn rejected by the unrelated-move guard: no verifier request, `enforce_attempts` "
    "empty, `previews` holds the rejected preview with `moved_unrelated` non-empty, `state_unchanged` True and "
    "`world_before` equals `world_after`; (c) a verifier-uncertain rejection: one preview with its failure "
    "recorded and `state_unchanged` True; (d) item-facts matching budget exhausted: a rejected outcome with "
    "`state_unchanged` True; (e) a call-cap exception inside the turn: `turn_outcome` stopped_call_cap, "
    "`verifier_requests` 1 while `verifier_http_calls` 0, and `state_unchanged` reported honestly (assert the "
    "value the code really produces, and say in your report whether it was True); (f) the opening: state "
    "unchanged and `proposed_item_facts` listing a response's item facts. If a case cannot be reached with the "
    "real code path, build the nearest honest fixture and say which. Also assert: a relation-only mutation "
    "(same parent, `under` changed to `on`) changes `world_after` and the digest but leaves `places_after` "
    "equal to `places_before`; a newly created entity appears in `world_after` and changes the digest; and a "
    "hidden-flag or axis change shows in `world_after`. Use a second synthetic package or world with different "
    "names for at least one of these. "
    "SCENE-START TEST in tests/test_live_baseline_scene_start.py: for the route that starts at scene 1B "
    "(`observe_park_bench_1b`), build the start state the way the existing tests there do and assert, through "
    "the new world-structure helper, that each of `transit_card`, `number_sequence` and `michelle_photograph` "
    "has parent `park_bench`, relation `under` and `hidden` False, and that the checkpoint index equals the "
    "recorded one. Do NOT assert anything about what the observation context contains (a later change will "
    "alter it on purpose). "
    "Run tests/test_live_baseline_evidence.py tests/test_live_baseline_scene_start.py "
    "tests/test_live_baseline_enforce.py tests/test_live_baseline_default_output.py "
    "tests/test_enforce_stage1_harness.py tests/test_enforce_stage2_harness.py and report counts. Run "
    "`.venv/bin/python -m ruff check --fix` and `ruff format` on your owned files."
)

MANIFEST_SPEC = (
    "You are the MANIFEST worker. "
    + COMMON
    + "You own ONLY scripts/ringer/environment_narration/make_t9h_run_manifests.py, the two generated files "
    "scripts/ringer/environment_narration/run-t9h-smoke.json and run-t9h-full.json, and "
    "tests/test_t9h_run_manifests.py "
    "(extend it). Never touch live_baseline.py (another worker is editing it) or any other file. Never "
    "hand-edit the two JSON files: change the generator and run `.venv/bin/python "
    "scripts/ringer/environment_narration/make_t9h_run_manifests.py` to regenerate them. "
    "BUILD. In `_manifest`, `expect_files` today lists rows.json and summary.json for routes c, d, e and f plus "
    "spent.json, unconditionally, so a run that correctly stops at route E (its own `_check` already skips the "
    "later routes when an earlier summary has a `stopped_reason`) is reported missing route F files. Make "
    "`expect_files` list only the unconditional artifacts: route c rows.json, route c summary.json and "
    "spent.json. Leave the check's conditional route logic exactly as it is (the later routes are required "
    "only when the earlier summary has no stop reason), the spec text, caps, replicate counts and every other "
    "field unchanged. "
    "TESTS in tests/test_t9h_run_manifests.py: for both generated manifests assert `expect_files` is exactly the "
    "three c/spent paths; assert the check string still contains the conditional structure (an `if` on "
    "`stopped_reason` guarding each of routes d, e and f, in order) and still requires d, e and f rows when the "
    "earlier summary has none; and execute the check's first python heredoc against a temporary directory tree "
    "(copy the heredoc text out of the check, point `base` at the temp tree) in two cases: route c summary with a "
    "stopped_reason and only c/spent present passes; route c clean but route d missing fails with a message "
    "that names the missing file. Keep every existing assertion, including the committed-JSON byte-equality "
    "tests, passing. Run tests/test_t9h_run_manifests.py and report counts. Run "
    "`.venv/bin/python -m ruff check --fix` and `ruff format` on your owned files."
)


def _check(files: str, own: str, ruff_paths: str) -> str:
    return (
        "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp "
        "&& set -o pipefail "
        f"&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
        f"-p no:cacheprovider --no-cov {files} 2>&1 | tee /tmp/t9h-route-e-{own}.out | tail -15 "
        f"&& ! grep -Eq '[0-9]+ failed|FAILED|ERROR' /tmp/t9h-route-e-{own}.out "
        f"&& grep -Eq '[0-9]+ passed' /tmp/t9h-route-e-{own}.out "
        f"&& .venv/bin/python -m ruff check {ruff_paths} && .venv/bin/python -m ruff format --check {ruff_paths}"
    )


MANIFEST = {
    "run_name": "t9h-route-e-measurement",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-route-e-measurement",
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
            "key": "harness-full-state-evidence",
            "ownership": [
                "scripts/ringer/transcript_1a/live_baseline.py",
                "tests/test_live_baseline_evidence.py",
                "tests/test_live_baseline_scene_start.py",
            ],
            "expect_files": ["/home/bcorfman/dev/freytag-forge/tests/test_live_baseline_evidence.py"],
            "verified": (
                "enforced bench rows carry full per-entity parent/relation/hidden/axis evidence, a full-state "
                "digest, every candidate preview and a turn outcome, and rows with enforcement off are unchanged"
            ),
            "spec": HARNESS_SPEC,
            "check": _check(
                "tests/test_live_baseline_evidence.py tests/test_live_baseline_scene_start.py "
                "tests/test_live_baseline_enforce.py tests/test_live_baseline_default_output.py "
                "tests/test_enforce_stage1_harness.py tests/test_enforce_stage2_harness.py",
                "harness",
                "scripts/ringer/transcript_1a/live_baseline.py tests/test_live_baseline_evidence.py "
                "tests/test_live_baseline_scene_start.py",
            )
            + " && grep -q state_digest_after scripts/ringer/transcript_1a/live_baseline.py",
        },
        {
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "key": "manifest-conditional-expect-files",
            "ownership": [
                "scripts/ringer/environment_narration/make_t9h_run_manifests.py",
                "scripts/ringer/environment_narration/run-t9h-smoke.json",
                "scripts/ringer/environment_narration/run-t9h-full.json",
                "tests/test_t9h_run_manifests.py",
            ],
            "expect_files": [
                "/home/bcorfman/dev/freytag-forge/scripts/ringer/environment_narration/run-t9h-smoke.json"
            ],
            "verified": (
                "the T9h run manifests require only route c and the spend file unconditionally, so a run that "
                "stops at an earlier route is not reported as missing later route files"
            ),
            "spec": MANIFEST_SPEC,
            "check": _check(
                "tests/test_t9h_run_manifests.py",
                "manifest",
                "scripts/ringer/environment_narration/make_t9h_run_manifests.py tests/test_t9h_run_manifests.py",
            )
            + " && .venv/bin/python - <<'PY'\n"
            "import json\n"
            "from pathlib import Path\n"
            "base = Path('scripts/ringer/environment_narration')\n"
            "for name in ('run-t9h-smoke.json', 'run-t9h-full.json'):\n"
            "    files = json.loads((base / name).read_text())['tasks'][0]['expect_files']\n"
            "    assert len(files) == 3, (name, files)\n"
            "    assert not any('/f/' in path or '/d/' in path or '/e/' in path for path in files), (name, files)\n"
            "print('expect_files limited to route c and spent')\n"
            "PY",
        },
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("build-t9h-route-e-harness.json")
    out.write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(out)
