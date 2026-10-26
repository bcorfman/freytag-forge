# ruff: noqa: E501
"""Generate the T8 Ringer manifests (candidate preview, engine integration, resume)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration"

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "No story vocabulary (no Kristin, truck, laptop, drawer, Michelle) in non-test code. Tests may use the shipped continuity-initiative package "
    "through the helpers in tests/test_observation_mode.py (`_state_at`) and tests/test_observation_shadow.py, plus a synthetic second story. "
    "Write the tests FIRST, run them and confirm they fail for the right reason, then implement until they pass. "
    "Do not edit any file outside YOU MAY EDIT ONLY. Run ruff check and ruff format on your files at the end. "
)

BACKGROUND = (
    "BACKGROUND. RuntimeEngine._turn_active (storygame/runtime/engine.py) loops up to TURN_NARRATION_ATTEMPTS=2 times: provider call, "
    "reveal resolve, validate_effects, a deepcopy `candidate_state` with `apply_proposal(proposal, apply_world=False)`, then "
    "narration_validator.validate; a ProposalValidationError on the first attempt triggers one retry with provider.note_rejection(code). "
    "Only AFTER the loop does it call state.apply_proposal(proposal) and then WorldCapture.after_commit(command, narration, entered_scene=...), "
    "which calls ItemFactsProvider.apply_item_facts(raw, ...) and that MUTATES state.facts (World over state.facts), provider fields and makes billed "
    "model calls: one item-facts match call via CloudflareTurnProvider._request_item_facts and Jev mapping checks through the `confirm` lambda. "
    "Observation context: ItemFactsProvider._observation_context() and storygame/runtime/observation_verifier.py (ObservationVerifier, relations_from_context, "
    "fail-closed verdicts; `report.accepted` is True only when outcome is 'ok' and every verdict is 'accept'). The verifier is already built and must not change. "
)


def t8a() -> dict:
    spec = (
        COMMON
        + BACKGROUND
        + "YOU MAY EDIT ONLY: storygame/runtime/observation_preview.py (NEW), storygame/runtime/capture.py, storygame/runtime/item_facts.py (ONLY the single place described below), "
        "tests/test_observation_preview.py (NEW). "
        "\n\nGOAL (T8a): a side-effect-free PREVIEW of the item-fact effects on a candidate state, with the observation verifier run against the candidate, and "
        "a replay memo so the later real commit makes no second billed call. Nothing in the engine calls it yet; the product default is unchanged. "
        "\n\nBUILD 1. New module storygame/runtime/observation_preview.py with: "
        "(a) `class CallMemo`: records and replays answers of billed calls. `remember(kind: str, key: object, call: Callable[[], object]) -> object` returns a deepcopy of the stored answer when the same (kind, canonical JSON of key with sort_keys=True and default=str) was seen, otherwise runs `call()`, stores a deepcopy of a successful answer and returns it; an exception propagates and stores nothing (None answers are stored too). `to_json() -> dict` and `@classmethod from_json(data) -> CallMemo` (answers must be JSON-compatible; keys are strings). `hits` and `misses` integer counters. "
        "(b) `@dataclass(frozen=True) class CandidatePreview`: fields `required: bool` (an observation was required), `accepted: bool`, `outcome: str` ('not_required', 'ok', or the verifier report outcome such as 'unavailable', 'partial', 'malformed', 'budget_exhausted', or 'unrelated_move'), `failure: str | None` (generic code only: a verifier failure code or 'unrelated_move'; never narration or model text), `verdicts: tuple[dict, ...]` (thing, verdict, score), `moved_unrelated: tuple[str, ...]`, `changed: tuple[str, ...]` (sorted item names changed by the candidate), `facts_after: object` (JSON value as in the after_commit record), `command: str`, `narration: str`, `memo: CallMemo`. "
        "\n\nBUILD 2. In ItemFactsProvider add a public attribute `item_facts_call_memo: CallMemo | None = None` (set in __init__). In apply_item_facts, the ONE place that calls `CloudflareTurnProvider._request_item_facts(self, self._match_payload(...))` must go through the memo when set: `self.item_facts_call_memo.remember('match', payload, lambda: CloudflareTurnProvider._request_item_facts(self, payload))`; with no memo the behavior is byte-identical to today. Keep the existing except/budget-error handling around it. Build the payload once into a local variable. "
        "\n\nBUILD 3. In WorldCapture add `enforcing_verifier: ObservationVerifier | None = None` (separate from shadow_verifier; default None so the product is unchanged), `self._pending_preview: CandidatePreview | None = None`, and "
        "`preview_commit(self, command: str, narration: str, candidate_state, *, entered_scene: bool) -> CandidatePreview`. Behavior: "
        "if `self.enforcing_verifier is None` or `self.provider.observation_request is None`, return CandidatePreview(required=False, accepted=True, outcome='not_required', ...) without touching anything. "
        "Otherwise: take `raw = self.provider.pending_item_facts()`; remember the provider's original `state`; build a fresh CallMemo; SAVE (deepcopy) every provider turn-output field that apply_item_facts or the scene seeding touches, namely the names in WorldCapture.context() (_pending_item_facts, _pending_item_facts_present, _held_item_facts, _item_facts_issues, _changed_last_turn, _selected_names, _referred_names, _referred_lines, _last_scene_seeded, _match_offered_names, _fact_effect_snapshot, _last_item_facts_unplaced, _last_item_facts_refused, _last_item_facts_match) plus prior_steps, prior_notice_steps, command_consumed, observation_request, item_facts_seed_issues, item_facts_match_calls, item_facts_axis_fixes, item_facts_lifted, item_facts_reply_keys and _schema_cache. DO NOT save or restore the real billing counters `_turn_request_count`, `_turn_item_facts_request_count` and `request_count` (they must keep counting preview calls, because the preview really spends them). "
        "Then inside try/finally: set `provider.state = candidate_state` (a deepcopy the engine made; it is discarded afterward), set provider._schema_cache = {} (the cached schema is built from the old facts), set provider.item_facts_call_memo = memo, run the same item-fact application that after_commit performs (apply_item_facts with the same `confirm` lambda but wrapped in memo.remember('confirm', [c, s, q, st, p, k], ...), then apply_scene_placements when entered_scene, exactly as after_commit does), then build the observation context ON THE CANDIDATE with `self.provider._observation_context()`, call `self.enforcing_verifier.verify(narration, relations_from_context(context))` (do NOT call begin_turn here; before_turn does that), and compute `moved_unrelated`: names of items that existed in the real world before the preview and whose parent differs in the candidate, excluding the protagonist, the observation request's focus entity, and every thing named in the context's visible_things (and anything those contain); creations and unplaced things are not 'moved'. "
        "The finally block ALWAYS restores provider.state, all saved fields, and sets provider.item_facts_call_memo = None, even when apply_item_facts raises (a NarrationProviderError must propagate after restoration). "
        "accepted = report.accepted AND not moved_unrelated; outcome is 'unrelated_move' (failure 'unrelated_move') when the report accepted but something unrelated moved, else the report outcome. If `_observation_context()` returns None or there are no relations, accepted=True, outcome 'not_required'... but still check moved_unrelated. Store the result in `self._pending_preview` and return it. "
        "Add `take_preview(self, command: str, narration: str) -> CandidatePreview | None`: returns and clears `_pending_preview` only when its command and narration equal the arguments, else clears it and returns None. "
        "Change `after_commit` minimally: at its start call `preview = self.take_preview(command, narration)`; when preview is not None and preview.required, set `self.provider.item_facts_call_memo = preview.memo` for the duration of the existing apply (replay, so no second billed match call) and wrap `confirm` in the same memo (kind 'confirm', same key list), restoring the memo to None in a finally. Add `record['observation_preview'] = {'outcome','failure','accepted','changed','verdicts'}` only when a preview was taken and required, and `record['observation_diverged'] = True/False` comparing sorted(provider._changed_last_turn) with preview.changed and the record's facts_after with preview.facts_after (only when a preview was taken and required). With no preview the record is byte-identical to today. Also `before_turn` must call `self.enforcing_verifier.begin_turn()` when set (resets the per-turn verifier budget) and clear `_pending_preview`; `discard()` clears `_pending_preview`; keep shadow behavior unchanged and independent. "
        "\n\nTESTS (tests/test_observation_preview.py, hermetic, fake `ask` returning noul scores like tests/test_observation_shadow.py, real ObservationVerifier, real providers via build_capture_provider; monkeypatch CLOUDFLARE_WORKER_URL in an autouse fixture as that file does). Required cases: "
        "1 off by default: no enforcing_verifier -> preview not required, accepted, provider untouched, ask never called. "
        "2 EXACT RESTORATION: after preview_commit (accepted and rejected alike, and when apply_item_facts raises) `state.facts` equals a clone taken before, `provider.state is state`, and a snapshot of vars(provider) (deepcopy of every plain data attribute, excluding the three billing counters and callables) is equal before and after. This test is the guard against unknown mutated fields: make it generic over vars(provider), not over a hand list. "
        "3 candidate really previewed: with item_facts raw that move an item, the CANDIDATE state's facts show the move (use a spy/instrumented candidate_state or the returned `changed`/`facts_after`) while the real state does not. "
        "4 verdicts: score 1.0 -> accepted; 0.0 -> rejected with a generic failure; ask returns None -> accepted False outcome 'unavailable' (fail closed); uncertain score -> rejected; the narration text never appears in the failure or outcome. "
        "5 unrelated move: raw item_facts that move an item nobody asked about on an observation turn -> accepted False, outcome 'unrelated_move', the unrelated name listed; a move of the protagonist or focus is allowed. "
        "6 replay: with a fake provider network that counts match calls and a counting `ask` for Jev confirm, preview then after_commit(command, same narration) performs the billed match call and the confirm calls exactly ONCE in total (counts from the preview), the committed world equals what an unpreviewed after_commit produces on the same input, and record['observation_diverged'] is False. A different narration or command passed to after_commit drops the preview (take_preview returns None) and calls live. "
        "7 divergence: tamper with the real state between preview and commit so the replayed application differs -> record['observation_diverged'] is True. "
        "8 verifier turn budget: two previews in one turn after one before_turn spend two verifier requests; a third report is 'budget_exhausted' (not accepted). before_turn resets it. "
        "9 synthetic second story: the same accept/restore/unrelated-move behavior on a tiny synthetic observatory package built like tests/test_observation_context.py does (no Kristin vocabulary). "
        "10 shadow unchanged: with only shadow_verifier set, records are identical to before. "
        "\n\nFINISH: report test counts and the exact diff stat; quote preview_commit's finally block."
    )
    focused = (
        "tests/test_observation_preview.py tests/test_observation_shadow.py tests/test_observation_mode.py "
        "tests/test_observation_prompt.py tests/test_observation_context.py tests/test_observation_verifier.py "
        "tests/test_runtime_capture.py tests/test_3c_world_capture_wiring.py tests/test_3c_item_facts_capture.py "
        "tests/test_environment_baseline.py tests/test_narration_retry.py tests/test_guard_retry_flag.py tests/test_narrator_cannot_board.py"
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {focused} 2>&1 | tee /tmp/t8a.out | tail -8 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/t8a.out "
        "&& grep -q 'def preview_commit' storygame/runtime/capture.py && test -f storygame/runtime/observation_preview.py "
        "&& ! grep -nE '^(import re|from re )|\\bre\\.(compile|search|match|sub|findall|fullmatch)' storygame/runtime/observation_preview.py "
        "&& ! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' "
        "&& ! grep -iE '(kristin|laptop|truck|drawer|michelle)' storygame/runtime/observation_preview.py "
        "&& git diff --quiet -- docs worker data storygame/runtime/engine.py storygame/web_demo.py storygame/runtime/observation_verifier.py "
        "&& .venv/bin/python -m ruff check storygame/runtime/capture.py storygame/runtime/item_facts.py storygame/runtime/observation_preview.py tests/test_observation_preview.py "
        "&& .venv/bin/python -m ruff format --check storygame/runtime/capture.py storygame/runtime/item_facts.py storygame/runtime/observation_preview.py tests/test_observation_preview.py"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "key": "t8a-candidate-preview",
        "ownership": [
            "storygame/runtime/observation_preview.py",
            "storygame/runtime/capture.py",
            "storygame/runtime/item_facts.py",
            "tests/test_observation_preview.py",
        ],
        "expect_files": [
            f"{REPO}/storygame/runtime/observation_preview.py",
            f"{REPO}/tests/test_observation_preview.py",
        ],
        "spec": spec,
        "check": check,
        "verified": "a side-effect-free candidate preview with exact restoration and replayed billed calls",
    }


FOCUSED = (
    "tests/test_observation_preview.py tests/test_observation_shadow.py tests/test_observation_mode.py "
    "tests/test_observation_prompt.py tests/test_observation_context.py tests/test_observation_verifier.py "
    "tests/test_runtime_capture.py tests/test_3c_world_capture_wiring.py tests/test_3c_item_facts_capture.py "
    "tests/test_environment_baseline.py tests/test_narration_retry.py tests/test_guard_retry_flag.py tests/test_narrator_cannot_board.py"
)


def _check(extra_files: str, out: str, forbidden_diff_paths: str) -> str:
    return (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {FOCUSED} {extra_files} 2>&1 | tee {out} | tail -8 "
        f"&& ! grep -Eq '[0-9]+ (failed|error)' {out} "
        "&& ! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' "
        f"&& git diff --quiet -- {forbidden_diff_paths} "
        "&& .venv/bin/python -m ruff check storygame tests/test_observation_preview.py "
        "&& .venv/bin/python -m ruff format --check storygame tests/test_observation_preview.py"
    )


def t8a2() -> dict:
    spec = (
        COMMON
        + BACKGROUND
        + "YOU MAY EDIT ONLY: storygame/runtime/capture.py (only WorldCapture.preview_commit and WorldCapture._moved_unrelated) and tests/test_observation_preview.py. "
        "\n\nCONTEXT. T8a already added WorldCapture.preview_commit (read it first, with storygame/runtime/observation_preview.py and tests/test_observation_preview.py; 15 tests pass). A review found two defects and one missing test group. "
        "\n\nDEFECT 1 (wrong baseline). preview_commit builds `real_world` from a deepcopy of the PRE-PROPOSAL real state and `_moved_unrelated` compares that with the candidate AFTER item facts. But the candidate state already carries the proposal's own authored effects (fact operations and world effects can move an item, for example an authored reveal giving an item to the protagonist), so those moves would be flagged as 'unrelated'. Fix: the baseline must be the CANDIDATE world immediately BEFORE apply_item_facts runs. Take it inside the try block after `provider.state = candidate_state` and before apply_item_facts, as a mapping {entity_id: parent} for every thing (use the World API the existing code uses: entity_ids(), is_a(..., 'thing'), parent()), and compare that mapping with the candidate world after application. Delete the throwaway `copy.deepcopy(original_state)` and the `real_world` construction. `_moved_unrelated` then takes (before_parents, candidate_world, context). Keep exclusions (protagonist, focus, visible things and their descendants) and keep ignoring creations and unplaced things. "
        "\nDEFECT 2. When the verifier produces no report (no relations / context is None) the code returns accepted=True even if moved_unrelated is non-empty. Fix: accepted = not moved_unrelated; when something unrelated moved, outcome 'unrelated_move' and failure 'unrelated_move'; otherwise outcome 'not_required' as today. "
        "\n\nTESTS FIRST in tests/test_observation_preview.py (add, do not remove existing ones; existing tests may only change if they encoded the old baseline): "
        "(a) a proposal effect already moved an unrelated item in the candidate state before the preview (move it in candidate_state's facts via the World API before calling preview_commit) while item_facts raw does not touch it: accepted stays True and moved_unrelated is empty. "
        "(b) the same, but item_facts raw then moves a DIFFERENT unrelated item: rejected, only that item named. "
        "(c) no relations case (ask never called) plus an unrelated move: accepted False, outcome 'unrelated_move'; no relations and no move: accepted True, outcome 'not_required'. "
        "(d) SYNTHETIC SECOND STORY: build a tiny synthetic package the way tests/test_observation_context.py builds its observatory/skiff packages (read how; no Kristin vocabulary anywhere) and prove with it that preview accepts at score 1.0, rejects at score 0.0, restores every provider field exactly, and flags an unrelated move. If the existing providers cannot be built over a synthetic package, build the smallest harness that can (reuse tests/test_observation_mode.py helpers if possible) and say so in your report. "
        "\n\nFINISH: ruff check and format; report counts; quote the new baseline code."
    )
    return {
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "key": "t8a2-baseline-fix",
        "ownership": ["storygame/runtime/capture.py", "tests/test_observation_preview.py"],
        "expect_files": [f"{REPO}/tests/test_observation_preview.py"],
        "spec": spec,
        "check": _check(
            "",
            "/tmp/t8a2.out",
            "docs worker data storygame/runtime/engine.py storygame/runtime/observation_verifier.py",
        )
        + " && ! grep -q 'real_world' storygame/runtime/capture.py",
        "verified": "unrelated-move baseline is the candidate before item facts and a synthetic story is covered",
    }


def t8b() -> dict:
    spec = (
        COMMON
        + BACKGROUND
        + "YOU MAY EDIT ONLY: storygame/runtime/engine.py and tests/test_observation_enforcement.py (NEW). "
        "\n\nCONTEXT. T8a/T8a2 are done and tested: read storygame/runtime/observation_preview.py and WorldCapture.preview_commit / take_preview / after_commit / before_turn / context / resume / discard in storygame/runtime/capture.py, and tests/test_observation_preview.py. "
        "`WorldCapture.enforcing_verifier` is None in the product, so enforcement is OFF unless a test sets it; the engine must be byte-identical in behavior when it is None (the existing suites are the proof). `capture.after_commit` records `observation_preview` and `observation_diverged` when it consumed a required preview. "
        "\n\nGOAL (T8b): wire the preview into RuntimeEngine._turn_active as ONE shared recovery path, with exact rollback. Do not add a third narration call: the loop keeps TURN_NARRATION_ATTEMPTS = 2 and the per-turn narration budget. "
        "\n\nBUILD. (1) Inside the existing attempt loop, in the same `try` as `self.narration_validator.validate(...)`, directly after it, call a new private method `_preview_observation(command_text, proposal, candidate_state, before)` that does nothing when `self.capture is None`; otherwise calls `self.capture.preview_commit(command_text, proposal.narration, candidate_state, entered_scene=candidate_state.current_scene_id != before.current_scene_id)` and, when the returned preview is not accepted, raises `ProposalValidationError('The narration did not show the observed things as the world has them.', code='observation_unverified')` (generic message: no thing names, no narration, no model text). That exception flows into the EXISTING `except ProposalValidationError` retry branch (same bookkeeping: guard_rejections, `provider.note_rejection(code)` with NO term, `guard_retry_used`, budget check, last attempt re-raises) so nothing is duplicated. Remember the accepted preview's narration in a local variable `previewed_narration` (None when no required preview). "
        "(2) Before `self.capture.before_turn(...)`, when `self.capture` is set, take `pre_turn_context = self.capture.context()`. In the `except (ProposalValidationError, RuntimeContractError)` block, after the existing `self.capture.discard()` and snapshot restore, when the error code is 'observation_unverified' or 'observation_diverged' also call `self.capture.resume(pre_turn_context)` so no provider field from the rejected turn survives (held item facts, changed names, unplaced lists, prior steps). The same restoration is done on the divergence path below. "
        "(3) At commit: when `previewed_narration` is not None pass `previewed_narration` (not the possibly hand-off-extended proposal.narration) as the `narration` argument of `self.capture.after_commit`, so the preview is consumed and its billed answers replayed. Directly after after_commit, if `capture_record.get('observation_diverged')` is true: `self.capture.discard()`, `self.state.restore_snapshot(before)`, `self.capture.resume(pre_turn_context)`, `self._clear_provider_handoff()`, record the attempt with outcome 'rejected' and `AttemptError(code='observation_diverged', message='The committed effects differ from the previewed effects.')`, and raise `ProposalValidationError(message, code='observation_diverged')`. No success text, segments or facts may remain. "
        "(4) Leave the game-break paths, `_handle_refusal`, pacing and `_complete_accepted_turn` unchanged; the preview must never be taken twice for one attempt, and a preview left over from a rejected attempt must not be consumed by the next attempt (before the second attempt's preview, take_preview semantics already drop mismatches; add a test). "
        "\n\nTESTS FIRST in tests/test_observation_enforcement.py (hermetic; find a working engine+capture fixture in tests/test_narration_retry.py, tests/test_3c_world_capture_wiring.py, tests/test_boarding.py, tests/test_observation_mode.py and tests/test_observation_preview.py; a scripted narration provider that returns proposals with different narrations and item_facts per attempt is expected; fake `ask` returning noul scores; count every provider/narration call, match call and confirm call). Required: "
        "1 enforcement off (default): preview_commit is never called (spy), behavior unchanged. "
        "2 accepted on attempt 1: exactly 1 narration call, world committed equals a run with no enforcing verifier, exactly one match call and one set of confirm calls in total (replay), record has observation_preview accepted and observation_diverged False. "
        "3 rejected then accepted: 2 narration calls, provider.note_rejection received code 'observation_unverified' with no term, guard_retry_used True, the first attempt's item facts are in NO committed fact (assert on facts and on the final record), match calls at most 2 for the whole turn. "
        "4 rejected twice: the turn raises ProposalValidationError with code 'observation_unverified'; narration calls == 2 (never 3); `state.snapshot()` equals the pre-turn snapshot on every field including turn_index and last_turn_delivery; the generic vars(provider) snapshot (same helper idea as tests/test_observation_preview.py, excluding billing counters) equals the pre-turn one; the attempt is recorded 'rejected' with that code; no segments committed. "
        "5 verifier unavailable (ask returns None) and uncertain scores behave as rejection (fail closed), not as acceptance. "
        "6 verifier requests: at most 1 per attempt and 2 per turn; a new turn resets them. "
        "7 divergence at commit: make the real application differ from the preview (for example wrap state.apply_proposal to also move an item, or alter facts the application reads) -> ProposalValidationError code 'observation_diverged', snapshot and provider fields exactly restored, nothing committed. "
        "8 a boarding turn (observation kind 'enter') that is rejected once then accepted seats the protagonist exactly once, increments turn_index once, fires each pacing event once, and consumes prior_steps once (no double seating, no repeated pacing). "
        "9 forced-handoff turn or a complication_verbatim turn (find a fixture; if none exists build the smallest one) with enforcement: the preview is consumed (no live match call at commit), the committed turn succeeds. If you cannot build either, say so and assert via a spy that after_commit receives the previewed narration. "
        "10 a NarrationProviderError raised inside the preview (item-facts budget exhausted) surfaces as the existing operational failure: state and provider fields restored, attempt recorded 'operational_failure'. "
        "11 a turn with no observation request but an enforcing verifier set: no verifier request, no behavior change. "
        "12 a synthetic second-story engine run (tiny package as in tests/test_observation_context.py) shows accept, reject-once and reject-twice behaviors. "
        "\n\nFINISH: run the engine-related suites listed in the check, ruff check and format; report counts and quote the new engine code."
    )
    focused = FOCUSED + (
        " tests/test_observation_enforcement.py tests/test_incident_engine.py tests/test_scene_runtime_phase2.py tests/test_runtime_state_copy.py tests/test_2c_turn_one_copy.py tests/test_engine_error_line.py tests/test_boarding_engine_text.py tests/test_boarding.py tests/test_seating.py "
        "tests/test_incident_handoff_guard.py tests/test_opening_retry.py tests/test_guard_retry_telemetry.py"
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        ""
        f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {focused} 2>&1 | tee /tmp/t8b.out | tail -8 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/t8b.out "
        "&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py > /tmp/t8b-quick.out 2>&1 || { tail -30 /tmp/t8b-quick.out; false; } "
        "&& grep -q 'observation_unverified' storygame/runtime/engine.py && grep -q 'observation_diverged' storygame/runtime/engine.py "
        "&& ! git diff -U0 -- storygame/runtime/engine.py | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' "
        "&& git diff --quiet -- docs worker data storygame/web_demo.py storygame/runtime/observation_verifier.py "
        "&& .venv/bin/python -m ruff check storygame tests/test_observation_enforcement.py "
        "&& .venv/bin/python -m ruff format --check storygame tests/test_observation_enforcement.py"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "key": "t8b-engine-integration",
        "ownership": ["storygame/runtime/engine.py", "tests/test_observation_enforcement.py"],
        "expect_files": [f"{REPO}/tests/test_observation_enforcement.py"],
        "spec": spec,
        "check": check,
        "verified": "the engine rejects, retries and rolls back unverified observation turns through the existing guard path",
    }


def t8c() -> dict:
    spec = (
        COMMON
        + BACKGROUND
        + "YOU MAY EDIT ONLY: storygame/runtime/observation_preview.py, storygame/runtime/capture.py, storygame/runtime/engine.py, tests/test_observation_resume.py (NEW), and tests/test_observation_enforcement.py (only to adjust tests that this task legitimately changes; say which). "
        "\n\nCONTEXT. T8a/T8a2/T8b are done: read observation_preview.py, WorldCapture.preview_commit/take_preview/after_commit/context/resume in capture.py, RuntimeEngine._preview_observation, the changes in _turn_active, and resolve_break in engine.py, plus tests/test_observation_preview.py and tests/test_observation_enforcement.py. Enforcement is OFF in the product (`WorldCapture.enforcing_verifier` is None), and the default product path must stay behaviorally identical. "
        "\n\nBUILD. "
        "(1) GATE T8b's engine additions on enforcement. T8b made every turn call `self.capture.context()` and deep-copy provider fields (pre_turn_context / pre_turn_provider_fields), and made the NarrationProviderError branch call `capture.discard()` and `capture.resume(...)` even when enforcement is off. Gate all of that on `self.capture is not None and self.capture.enforcing_verifier is not None` (a small helper such as `_enforcing()` is fine) so with enforcement off the engine does exactly what it did before T8 (no context() call, no extra discard/resume). Add a test that, with enforcement off, `capture.context` is not called during a turn and a NarrationProviderError leaves the provider exactly as the pre-T8 code did (compare against calling the same sequence with the T8 gate bypassed is not needed: assert context/discard/resume spies were not called). "
        "(2) PREVIEW FAILURE IS FAIL CLOSED. In `_preview_observation`, an unexpected Exception from `preview_commit` that is NOT a NarrationProviderError (and not a ProposalValidationError) must become `ProposalValidationError('The observation check could not complete.', code='observation_preview_failed')` (raised `from error`), so it takes the same retry/reject/rollback path, and `capture.resume(pre_turn_context)` also runs for that code. NarrationProviderError keeps its existing operational-failure path. "
        "(3) GAME-BREAK RESUME. `WorldCapture.context()` must include the pending preview when `_pending_preview` is not None (key 'observation_preview': a JSON-compatible dict built by new `CandidatePreview.to_json()`), and must NOT add the key when there is none (so existing contexts are byte-identical). `CandidatePreview.from_json(data)` rebuilds it, including `CallMemo.from_json`. `WorldCapture.resume(context)` restores `_pending_preview` from the key, or sets it to None when the key is absent. `CandidatePreview.facts_after` and every field must survive a JSON round trip (json.dumps/loads) unchanged; tuples may come back as lists but comparisons in `after_commit` (`observation_diverged`) must still be correct, so normalize in from_json. In `resolve_break('proceed')`, `self.capture.resume(pending_capture)` then `after_commit(command, pending.narration, ...)` must therefore consume the preview and replay the billed answers (no live match or confirm call). "
        "(4) DIVERGENCE ON PROCEED. In `RuntimeEngine.resolve_break`, take `pending_snapshot = self.state.pending_snapshot` before `self.state.resolve_break(decision)`. After `after_commit` in the proceed path, if `capture_record.get('observation_diverged')` is true: `self.capture.discard()`, `self.state.restore_snapshot(pending_snapshot)`, `self._clear_provider_handoff()` and raise `ProposalValidationError('The committed effects differ from the previewed effects.', code='observation_diverged')` so nothing from the proceeded turn remains and the player can re-enter the command. Document in a comment that provider turn-output fields are reset by the next turn's before_turn. "
        "\n\nTESTS FIRST in tests/test_observation_resume.py (hermetic; reuse the fixtures of tests/test_observation_enforcement.py and tests/test_runtime_capture.py game-break tests around lines 155-165 and 319): "
        "a context() has no 'observation_preview' key without a preview, and the whole context equals today's (compare to a copy taken with no verifier). b preview -> context() -> json round trip -> a FRESH capture/provider .resume() -> after_commit consumes the memo: zero live match calls and zero live confirm calls, committed world equals the uncommitted-path result, observation_diverged False. c at-risk game break (future dependency) with enforcement on: the turn returns a game_break, `state.pending_capture` is JSON-serializable (json.dumps works), the whole RuntimeState survives model_dump_json / model_validate_json, and `engine.resolve_break('proceed')` on the restored state commits exactly once with zero extra billed calls, correct item facts, single pacing and single seating; `resolve_break('return_to_scene')` restores the pre-turn snapshot exactly and leaves no pending preview. d post-commit game break (the 'newly unsatisfied' branch after after_commit) with enforcement on: same proceed/return checks. e divergence on proceed (tamper with the restored state before proceeding) -> ProposalValidationError code 'observation_diverged', facts equal the pending snapshot's, no pending break, the next turn runs normally. f FAULT INJECTION: parametrize a fault at each of these points and prove EXACT rollback (state.snapshot() equals the pre-turn snapshot; the generic vars(provider) snapshot excluding billing counters equals the pre-turn one; no segments; attempt recorded) and that the narration provider is called at most 2 times and item-facts match calls at most 2: preview_commit raises RuntimeError on attempt 1 (then succeeds on 2 -> committed once) and on both attempts (rejected, code 'observation_preview_failed'); verifier raises; verifier returns None; the `ask` used for Jev confirm raises inside the preview; after_commit raises inside the real application. Where an unexpected exception from after_commit cannot be made fail closed without widening scope, assert only what the existing engine does and say so in your report. g a verdict from attempt 1 is never consumed by attempt 2 (stale preview dropped). h a synthetic second story passes b and f. "
        "\n\nFINISH: run the check's suites, ruff check and format; report counts, list the test_observation_enforcement.py edits, and quote the resume/context code."
    )
    focused = FOCUSED + (
        " tests/test_observation_enforcement.py tests/test_observation_resume.py tests/test_incident_engine.py "
        "tests/test_scene_runtime_phase2.py tests/test_runtime_state_copy.py tests/test_2c_turn_one_copy.py "
        "tests/test_engine_error_line.py tests/test_boarding_engine_text.py tests/test_boarding.py tests/test_seating.py "
        "tests/test_incident_handoff_guard.py tests/test_opening_retry.py tests/test_guard_retry_telemetry.py"
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {focused} 2>&1 | tee /tmp/t8c.out | tail -8 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/t8c.out "
        "&& { env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py > /tmp/t8c-quick.out 2>&1 || { tail -30 /tmp/t8c-quick.out; false; }; } "
        "&& grep -q 'observation_preview_failed' storygame/runtime/engine.py "
        "&& ! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' "
        "&& git diff --quiet -- docs worker data storygame/web_demo.py storygame/runtime/observation_verifier.py "
        "&& .venv/bin/python -m ruff check storygame tests/test_observation_resume.py tests/test_observation_enforcement.py "
        "&& .venv/bin/python -m ruff format --check storygame tests/test_observation_resume.py tests/test_observation_enforcement.py"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "key": "t8c-resume-and-faults",
        "ownership": [
            "storygame/runtime/observation_preview.py",
            "storygame/runtime/capture.py",
            "storygame/runtime/engine.py",
            "tests/test_observation_resume.py",
            "tests/test_observation_enforcement.py",
        ],
        "expect_files": [f"{REPO}/tests/test_observation_resume.py"],
        "spec": spec,
        "check": check,
        "verified": "game-break resume replays the previewed answers and every failure point rolls back exactly",
    }


def shadow_harness() -> dict:
    spec = (
        COMMON
        + "YOU MAY EDIT ONLY: scripts/ringer/transcript_1a/live_baseline.py and scripts/ringer/transcript_1a/test_live_baseline.py. "
        "\n\nCONTEXT. live_baseline.py replays a route of player commands through the real engine (product wiring: build_capture_provider, WorldCapture, JevClient) against a Worker URL, with a call cap, and writes rows.json and summary.json. Read the whole file and its test file first. The product has an optional SHADOW observation verifier: `WorldCapture.shadow_verifier = ObservationVerifier(ask)` (storygame/runtime/observation_verifier.py); when set and an observation request exists, after_commit adds `record['observation_shadow']` (outcome, requests, elapsed_s, failure, accepted, verdicts [thing, verdict, score]) to `capture.last_after`. It never changes a turn. "
        "\n\nBUILD. (1) A new flag `--shadow` (default off; with it off, rows and summary are byte-identical to today). With it on, `_replicate` sets `capture.shadow_verifier = ObservationVerifier(capture_ask)` before the opening, and every turn row gains: `observation_shadow` (the dict from `capture.last_after` for that turn, or None), `observation_relations` (a list of {thing, place, holder} for the relations the verifier was asked about, in order, or None), and `observation_request` (kind and focus name or None). Record the relations WITHOUT changing product code: wrap `storygame.runtime.capture.relations_from_context` for the duration of the run with a function that calls the original and appends its result to a per-turn list that the replicate loop clears before each turn (restore the original in a finally). The summary gains `shadow: true/false`, `observation_turns` (turns whose observation_relations is not None) and `shadow_verifier_requests` (sum of requests). "
        "(2) A new route `observe` in ROUTES with exactly these 13 inputs in order: 'inspect the drawer', 'pull out the drawer', 'feel under the drawer', 'feel under the drawer', 'go outside', 'inspect the truck', 'enter the truck', 'inspect the passenger seat', 'examine my laptop', 'get out of the truck', 'examine the truck', 'go inside', 'inspect the drawer'. "
        "(3) In dry-run mode the Jev stub raises, so the shadow step records outcome 'unavailable' or 'shadow_error'; that is fine, the dry run only proves wiring and call counts. "
        "\n\nTESTS FIRST in scripts/ringer/transcript_1a/test_live_baseline.py (follow its existing style, hermetic, dry-run only, no network): flag off leaves rows without the three new keys and summary without `shadow`; `--shadow --route observe --replicates 1 --dry-run` writes 13 turn rows each with the three keys present (values may be None), summary shadow true; the `relations_from_context` wrapper is restored after the run even when the run raises; the route has exactly the 13 inputs; --shadow does not change `calls_made` ordering assumptions for existing routes (compare a dry run of 'corrected' with and without --shadow: same narration rows). "
        "\n\nFINISH: ruff check and format both files; report test counts and the dry-run summary of `--route observe --shadow --replicates 1 --dry-run --out /tmp/shadow-dry`."
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov scripts/ringer/transcript_1a/test_live_baseline.py tests/test_observation_shadow.py tests/test_observation_verifier.py 2>&1 | tee /tmp/shadowh.out | tail -6 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/shadowh.out "
        "&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/ringer/transcript_1a/live_baseline.py --route observe --shadow --replicates 1 --dry-run --out /tmp/shadow-dry-check >/dev/null "
        "&& .venv/bin/python -c \"import json;s=json.load(open('/tmp/shadow-dry-check/summary.json'));assert s['shadow'] is True and len(s['inputs'])==13, s\" "
        "&& git diff --quiet -- storygame docs worker data "
        "&& .venv/bin/python -m ruff check scripts/ringer/transcript_1a && .venv/bin/python -m ruff format --check scripts/ringer/transcript_1a"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 900,
        "key": "shadow-sample-harness",
        "ownership": [
            "scripts/ringer/transcript_1a/live_baseline.py",
            "scripts/ringer/transcript_1a/test_live_baseline.py",
        ],
        "expect_files": [f"{REPO}/scripts/ringer/transcript_1a/live_baseline.py"],
        "spec": spec,
        "check": check,
        "verified": "the live harness can run a hand-readable shadow-verifier sample",
    }


def shadow_report() -> dict:
    spec = (
        COMMON
        + "YOU MAY EDIT ONLY: scripts/ringer/environment_narration/shadow_report.py (NEW) and tests/test_shadow_report.py (NEW). "
        "\n\nCONTEXT. scripts/ringer/transcript_1a/live_baseline.py (read it) with `--shadow` writes rows.json: a list of replicate records, each with `turns`, each turn row having `input`, `narration`, `error`, `observation_request` ({kind, focus} or None), `observation_relations` (list of {thing, place, holder} or None) and `observation_shadow` (None or {outcome, requests, elapsed_s, failure, accepted, question_version, verdicts: [{thing, verdict, score}]}). Verdicts are 'accept', 'reject', 'uncertain' or 'unavailable'. A human (the orchestrator) reads the narrations BLIND to the verdicts and writes labels; this script prints the blind sheet and later joins labels to verdicts. "
        "\n\nBUILD a stdlib-only CLI with three subcommands (argparse; no regex). "
        "`sheet ROWS_JSON [--out FILE]`: prints markdown, one block per observation turn (turns whose observation_relations is not None and error is None) with the id `r<replicate>t<turn>` (0-based indexes), the player command, the narration text verbatim, and the relation list as 'thing | place | holder' lines numbered 1..n. It must NOT print verdicts, scores, outcome or any observation_shadow content. Also lists, at the end, the ids of turns that were skipped because they had no relations. "
        '`labels-template ROWS_JSON`: prints a JSON skeleton {id: {"1": null, "2": null, ...}} (one key per relation number) for the human to fill with true (the narration presents the thing as present at that place/holder) or false. '
        "`join ROWS_JSON LABELS_JSON [--out FILE]`: refuses (exit 2, message) if any label is null/missing for an observation turn that has relations. Computes per relation: label x verdict confusion (verdict accept / reject / uncertain / unavailable x label true / false); FALSE ACCEPTS = verdict accept with label false (listed with id, command, thing, score); strict rejections = label true with verdict not accept; per turn: `would_reject` = any relation not accepted OR shadow outcome not 'ok' (fail closed), split by whether all labels on that turn are true ('good turn') or not; verifier latency p50/p95 (elapsed_s) and requests; counts of turns without a shadow record. Prints the GATE: PASS only if false accepts == 0 AND good-turn strict reject rate <= 0.10 AND verifier p95 elapsed_s <= 2.0 AND at least 30 labelled relations; else FAIL with every failing clause named. Always print n for each rate and the exact one-sided 95% upper bound for zero false accepts (1 - 0.05**(1/n) form is fine; document the formula). Exit code 0 for PASS or FAIL (the report is informational), 2 for refusal. "
        "\n\nTESTS FIRST in tests/test_shadow_report.py (hermetic, tmp_path rows files built inline): sheet shows narration and relations and contains none of the strings 'accept', 'reject', 'uncertain', 'score', 'outcome' that came only from the verdict data (use unusual verdict-only markers such as a score 0.8431 and check absence); sheet skips error turns and no-relation turns and lists them; labels-template shape; join refuses on a missing label; join counts a false accept and fails the gate; join passes the gate on a clean synthetic set of 30+ relations with p95 <= 2.0; strict-reject rate and would_reject logic (an 'unavailable' outcome counts as would_reject); upper-bound arithmetic. "
        "\n\nFINISH: ruff check and format; report counts."
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py scripts/ringer/transcript_1a/test_live_baseline.py 2>&1 | tee /tmp/shadowr.out | tail -6 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/shadowr.out "
        "&& ! grep -nE '^(import re|from re )|\\bre\\.(compile|search|match|sub|findall|fullmatch)' scripts/ringer/environment_narration/shadow_report.py "
        "&& git diff --quiet -- storygame docs worker data "
        "&& .venv/bin/python -m ruff check scripts/ringer/environment_narration tests/test_shadow_report.py && .venv/bin/python -m ruff format --check scripts/ringer/environment_narration tests/test_shadow_report.py"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 900,
        "key": "shadow-sample-report",
        "ownership": [
            "scripts/ringer/environment_narration/shadow_report.py",
            "tests/test_shadow_report.py",
        ],
        "expect_files": [f"{REPO}/scripts/ringer/environment_narration/shadow_report.py"],
        "spec": spec,
        "check": check,
        "verified": "a blind reading sheet and a label join with a preregistered gate",
    }


def shadow_report_acceptable() -> dict:
    spec = (
        COMMON
        + "YOU MAY EDIT ONLY: scripts/ringer/environment_narration/shadow_report.py and tests/test_shadow_report.py. "
        "\n\nCONTEXT. Read both files and .plans/grounded-llm-environment-narration/t8-shadow-sample-prereg.md including Addendum A. shadow_report.py has subcommands sheet, labels-template and join (a blind reading sheet and a join of hand labels with shadow verdicts, with a gate). Addendum A adds a per-turn reading `acceptable` and a new gate clause 2b. "
        "\n\nBUILD. (1) `labels-template` adds, for every observation turn, a key \"acceptable\": null next to the numbered relation keys. A turn with zero relations (observation_relations == []) still gets the template entry with only \"acceptable\". (2) `sheet` also prints, for each observation turn, the turn row's `places_before` and `places_after` (compact one-line JSON each, key `places_before`/`places_after`), and the observation request kind and focus name; still NO verdict, score, outcome or shadow content. Zero-relation observation turns are printed too (relations section says 'none'). (3) `join` refuses (exit 2) when any observation turn lacks a boolean `acceptable` label, or when a relation label is missing. It computes clause 2b: among observation turns with acceptable == true, the share that enforcement would reject (any relation verdict not 'accept', or a shadow outcome other than 'ok' when the turn has at least one relation; a turn with zero relations and outcome 'no_relations' is NOT a rejection; a turn with zero relations and a missing shadow record is NOT a rejection), printing n and the share, and adds `2b` to the gate: FAIL when that share is above 0.10 (when n is 0 it is inconclusive and the gate says so). Also print a short table of acceptable == true turns that would be rejected: id, command, and the rejected things with scores. Existing clauses 1, 2, 3, 4 keep their meaning and wording. "
        "\n\nTESTS FIRST in tests/test_shadow_report.py (extend; keep existing tests green): template carries acceptable; sheet shows places and request kind but still no verdict-only markers; join refuses without acceptable; 2b computed correctly on a synthetic set (acceptable turn rejected because of over-demanded relations lowers the 2b pass and is listed; an unacceptable turn that is rejected does not count against 2b; zero-relation turns are not rejections); gate wording lists 2b when it fails. "
        "\n\nFINISH: ruff check and format; report counts."
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py 2>&1 | tee /tmp/shadowr2.out | tail -6 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/shadowr2.out "
        "&& grep -q 'acceptable' scripts/ringer/environment_narration/shadow_report.py "
        "&& ! grep -nE '^(import re|from re )|\\bre\\.(compile|search|match|sub|findall|fullmatch)' scripts/ringer/environment_narration/shadow_report.py "
        "&& git diff --quiet -- storygame docs worker data scripts/ringer/transcript_1a "
        "&& .venv/bin/python -m ruff check scripts/ringer/environment_narration tests/test_shadow_report.py && .venv/bin/python -m ruff format --check scripts/ringer/environment_narration tests/test_shadow_report.py"
    )
    return {
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 900,
        "key": "shadow-report-acceptable",
        "ownership": [
            "scripts/ringer/environment_narration/shadow_report.py",
            "tests/test_shadow_report.py",
        ],
        "expect_files": [f"{REPO}/scripts/ringer/environment_narration/shadow_report.py"],
        "spec": spec,
        "check": check,
        "verified": "the report supports the acceptable reading and gate clause 2b",
    }


def shadow_report_zero_relations() -> dict:
    spec = (
        COMMON
        + "YOU MAY EDIT ONLY: scripts/ringer/environment_narration/shadow_report.py and tests/test_shadow_report.py. "
        "\n\nBUG. In shadow_report.py `_join`, `turn_would_reject` starts as `not isinstance(shadow, dict) or shadow.get('outcome') != 'ok'`. For an observation turn with ZERO relations the shadow outcome is 'no_relations' (or the shadow record may be missing), so the turn is counted as one enforcement would reject, which inflates the original gate clause 2 (good-turn strict reject rate) and the mixed-turn counts. A turn with zero relations is never rejected by enforcement (nothing is asked). Fix: `turn_would_reject` can be True only when the turn has at least one relation (a relation verdict that is not 'accept', or a shadow outcome other than 'ok', or a missing shadow record, all evaluated only when relations is non-empty). Zero-relation turns still count in `good_turns` (all labels true vacuously) but never as rejected; keep the 2b logic as is. Also make sure `turns_without_shadow` still reports them. "
        "\n\nTESTS FIRST in tests/test_shadow_report.py: a synthetic set containing zero-relation turns with outcome 'no_relations' and with a missing shadow record -> clause 2 good-turn reject count excludes them (compute the exact expected counts), and the printed good-turn rejection rate matches; a turn with relations and outcome 'unavailable' is still a rejection. Keep all existing tests green. FINISH: ruff check and format; report counts."
    )
    check = (
        f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail && "
        "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py 2>&1 | tee /tmp/shadowr3.out | tail -6 "
        "&& ! grep -Eq '[0-9]+ (failed|error)' /tmp/shadowr3.out "
        "&& ! grep -nE '^(import re|from re )|\\bre\\.(compile|search|match|sub|findall|fullmatch)' scripts/ringer/environment_narration/shadow_report.py "
        "&& git diff --quiet -- storygame docs worker data "
        "&& .venv/bin/python -m ruff check scripts/ringer/environment_narration tests/test_shadow_report.py && .venv/bin/python -m ruff format --check scripts/ringer/environment_narration tests/test_shadow_report.py"
    )
    return {
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 900,
        "key": "shadow-report-zero-relations",
        "ownership": [
            "scripts/ringer/environment_narration/shadow_report.py",
            "tests/test_shadow_report.py",
        ],
        "expect_files": [f"{REPO}/scripts/ringer/environment_narration/shadow_report.py"],
        "spec": spec,
        "check": check,
        "verified": "zero-relation turns are never counted as enforcement rejections",
    }


def manifest(task: dict, name: str) -> dict:
    return {
        "run_name": "grounded-environment-narration",
        "workdir": f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": REPO,
        "tasks": [task],
    }


if __name__ == "__main__":
    which = sys.argv[1:] or ["t8a"]
    builders = {
        "t8a": t8a,
        "t8a2": t8a2,
        "t8b": t8b,
        "t8c": t8c,
        "shadow": shadow_harness,
        "shadowr": shadow_report,
        "shadowr2": shadow_report_acceptable,
        "shadowr3": shadow_report_zero_relations,
    }
    for key in which:
        path = OUT / f"build-{key}-preview.json"
        path.write_text(json.dumps(manifest(builders[key](), key), indent=1) + "\n", encoding="utf-8")
        print(path)
