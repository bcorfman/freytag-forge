# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19q: repair the factory's evidence and probe (diagnosis chatgpt-19q-diagnosis.md). FREE to build and run.

Four disjoint Codex tasks (provider parity, transition cause + probe approval, diagnosis provenance, plan reroute + lint).
Usage: build_round19q_factory_repairs_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-19q"
DIAG = "/home/bcorfman/dev/ringer-work/out/chatgpt-19q-diagnosis.md"

PREAMBLE = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`, never write factory/state/. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`. Tests must be hermetic (no model call, no network) and fast; use fixture stories or fakes, not live providers. Do not add a new test file (add to the existing test files you own). If an OLD test pins behaviour this change deliberately changes, update that test and say so in NOTES.txt; never leave a failing test and never weaken an unrelated one. Read @DIAG@ for the owner's diagnosis; the section named below is your brief, but the spec here is complete. Write NOTES.txt (worktree root, never committed) listing every ambiguity and the choice you made. Edit ONLY the files in your ownership list; anything else you touch fails the check."""

SPEC_A = """TASK: provider parity (diagnosis section 1). Owned files: storygame/runtime/item_facts.py, tests/test_bench_item_facts.py.

PROBLEM. `ItemFactsProvider.from_environment` (storygame/runtime/item_facts.py, near line 344) builds a base `CloudflareTurnProvider.from_environment(...)` and then returns a new `ItemFactsProvider` built from the base's `worker_url`, `token`, `projector` only. It drops the base's `semantic_ask` callback (set in `CloudflareTurnProvider.from_environment`, storygame/runtime/cloudflare.py near line 388). When `semantic_ask` is missing, `_semantic_authored_handoff` (cloudflare.py near line 637) returns without making the semantic reveal decision. So any bench or probe that uses `item_facts.mode: single_call` replays WITHOUT the semantic reveal selection the hosted game runs. Evidence: a saved live game earned a reveal on 'Reach beneath my initials drawer' through the semantic path; every probe replay of the same prefix selects nothing. Read cloudflare.py to see exactly how `semantic_ask` is created and used (and how storygame/web_demo.py near line 267 sets it on the hosted path) so the fix matches the hosted behaviour.

CHANGE. Make `ItemFactsProvider.from_environment` carry over the base provider's `semantic_ask` (and any other base attribute that `from_environment` of the base sets and the subclass constructor does not take — inspect, list them in NOTES.txt, and carry over only those that affect reveal selection). Do not change when the semantic path is eligible or how ambiguity is checked; this is wiring only. Do not enable FREYTAG_CONTRACT_SHADOW behaviour. Do not add aliases or touch story data.

TESTS (tests/test_bench_item_facts.py, hermetic). Add a regression using the real `ItemFactsProvider.from_environment` classmethod with env vars patched (monkeypatch CLOUDFLARE_WORKER_URL etc. and a fake token/asker; no network) proving: (1) the returned provider's `semantic_ask` is not None and is the same callable the base would carry; (2) with a fake asker injected, an exact-evidence miss on an eligible authored claim causes the asker to be called once (go through `_semantic_authored_handoff` with a small fixture package that has one action-evidence claim; reuse existing fixtures in tests/test_bench_item_facts.py or tests/test_cloudflare*.py helpers); (3) the hosted eligibility/ambiguity behaviour is preserved: an ambiguous asker reply does not grant, an ineligible claim is not offered to the asker. Use the fake pattern already used in the repo's tests for semantic_ask (grep tests/ for `semantic_ask`). If CloudflareTurnProvider.from_environment requires env that tests cannot provide hermetically, patch it minimally and say so in NOTES.txt.

HARD LIMITS. Edit only the two owned files. NEVER edit bench/, factory/, story data under data/, or storygame/runtime/cloudflare.py."""

SPEC_B = """TASK: record the real exit cause, stop counting missing evidence as success, record probe provenance, and make the billed-run approval single-use (diagnosis sections 2 and execution-order step 5). Owned files: bench/core.py, factory/stations/probe.py, tests/test_factory_probe.py, tests/test_bench_runtime_mode.py.

PROBLEM 1 (exit cause). `bench/core.py` records scene transitions near line 1353 as `{from_scene, to_scene, after_turn, advanced_offline}` and the turn record `left_scene` near line 1309, but NO cause. The runtime engine already knows the cause: `engine.last_attempt.transition_cause` is one of "none", "earned", "forced", "timer" (storygame/runtime/attempt_bundle.py line 98; factory/checks/carry_matrix.py line 469 reads it as `self._engine.last_attempt.transition_cause`). `factory/stations/probe.py` `_transition_cause` therefore returns None and `summarize_arm` counts every exit that is not forced/timer as earned (probe.py near lines 118 and 198): missing evidence counted as success. Real example: in saved probe records, deadline fallback text ended scenes that were reported as 'earned exits'.
CHANGE 1. In bench/core.py persist the engine's `transition_cause` on the turn record (key `transition_cause`) and on the scene_transitions entry (key `cause`) whenever the run is runtime mode and an attempt exists; in non-runtime mode leave the cause absent (do not invent one). Keep every existing key and behaviour. In probe.py `summarize_arm`: an exit whose cause is "earned" is earned; "forced" and "timer" are forced; a missing/unrecognised cause is counted under a NEW summary key `unknown_exits` (initialise to 0, also add it wherever the summary keys are enumerated, validated or compared, e.g. the arm comparison / decision / probe.json writer: find every reader of `earned_exits` and `forced_exits` with grep and keep them consistent). Unknown exits must never be added to `earned_exits`. If the probe's pass/fail decision uses earned exits, compare only proven earned exits and, when either arm has unknown exits, record `exit_evidence: "incomplete"` in the probe result and do not let an unknown exit satisfy an exit criterion (never a silent pass). Old saved turn-records.json files without a cause must still summarise without error (their exits become unknown), because the original probe artifacts are retained and re-analysed.

PROBLEM 2 (provenance). Probe replays cannot be compared to saved games unless the run records what ran. CHANGE 2. In bench/core.py add a run-level record field `provider_features` to each run in turn-records (runtime mode only): `{"item_facts_mode": <mode or null>, "semantic_ask": <bool provider.semantic_ask is not None>, "contract_shadow": <bool FREYTAG_CONTRACT_SHADOW == "1">, "code_head": <git HEAD sha from `git rev-parse HEAD` in the repo root, or null if unavailable, never raising>}`. In probe.py copy these into the per-arm summary and into probe.json under `provider_features` (first run's values, plus `consistent: bool` if runs disagree). Add an arm-level warning field `semantic_ask_missing: true` when any run reports semantic_ask false, and make the probe result carry it so a human sees replay parity is broken. Do NOT fail or block on it (another task fixes the wiring); just record it.

PROBLEM 3 (approval). The handler checks `payload.get("billed_run_approved") is not True` (probe.py near line 433) but nothing consumes it, and rehearse_19.py writes it persistently, so a rejection and replan can schedule another billed run without a new go. CHANGE 3. A billed probe run consumes its approval: when the handler passes the approval check and is about to start a billed run, it must persist `billed_run_approved: False` and `billed_runs_consumed` incremented in the ticket payload (follow how other handlers persist payload changes — read factory/tickets.py, factory/line.py and factory/stations/fun_review.py/live_playtest.py for the convention; if the handler result type carries payload updates use that, e.g. a StationResult field; if no mechanism exists, say so in NOTES.txt and implement the smallest one inside the handler's result, without editing factory/line.py or tickets.py — if that is impossible, write the consumption to the per-ticket probe record file next to probe.json and refuse a second run when that record shows one consumed, unless the payload carries a fresh `billed_run_approved: true` together with `billed_run_approval_id` different from the recorded one). Also add an optional cumulative ceiling: payload `billed_usd_ceiling` (number); the handler refuses to start a run when `spent_so_far + projected > ceiling`, where spent_so_far is read from the guard ledger rows for this ticket if the existing code exposes that cheaply (otherwise from the per-ticket probe records' actual/estimated spend) — document the source in NOTES.txt. Absent ceiling keeps today's behaviour.

TESTS (hermetic, fast; tests/test_factory_probe.py and tests/test_bench_runtime_mode.py). Cover: (1) summarize_arm with turn records whose cause is earned / timer / forced / missing -> earned_exits, forced_exits, unknown_exits counts; the missing case is not earned; (2) an old-format records file (no cause anywhere) still summarises with exits as unknown; (3) the bench runtime-mode test records `transition_cause` and `cause` and the `provider_features` fields with a fake/hermetic provider (follow the existing hermetic runtime-mode tests; assert semantic_ask is False/True correctly and that code_head never raises when git is unavailable); (4) the probe result flags `exit_evidence: incomplete` and `semantic_ask_missing`; (5) second billed run is refused after the first consumed its approval, and a ceiling refuses an over-budget run; the fake runner must prove no bill occurs when refused. Update existing tests that pinned the old `earned_exits` behaviour for cause-less records and say so in NOTES.txt.

HARD LIMITS. Edit only the four owned files. NEVER edit storygame/, factory/line.py, factory/tickets.py, factory/guard.py, factory/config/*, story data under data/, or scripts/."""

SPEC_C = """TASK: give diagnosis (station 11) the pre-turn facts and provenance it lacks, so its labels stop being lexical guesses (diagnosis section 4). Owned files: factory/stations/diagnose.py, factory/stations/live_playtest.py, tests/test_factory_diagnose.py, tests/test_factory_live_playtest.py.

BACKGROUND. `diagnose_turn` in factory/stations/diagnose.py classifies each failing-turn packet by scanning the scene's claims and word lists. Real mistakes seen in a saved run (S = saved live report; each is a distinct failure of the heuristic):
(a) A command 'Ask Officer Reyes about his orders' was labelled `claim_wording_miss` for a claim that is another character's (a neighbour's) account: the input matched the claim's 'ask' group but not the neighbour group. A near-miss whose missing evidence group names a DIFFERENT actor/target than the command names is not a wording miss.
(b) 'Inspect Officer Reyes's badge' was labelled `lead_outside_scene` because the package-wide entity surfaces include another scene's 'badge' alias; the alias is scoped to that later scene and the possessive names Reyes. Surfaces/aliases must be resolved in the scene's context (scoped aliases only count where their scope applies) before a name is declared outside-scene.
(c) 'Open the notebook' was labelled `unknown_object` but the previous narration (the model's own earlier response) had just introduced 'a small notebook'. A word present in the preceding narration of the same run is a referent the narrator created, not an unexplained player request; label it with a NEW cause `follows_prior_narration` (add to the cause constants, summary/count handling and everywhere causes are enumerated; grep).
(d) A claim labelled `claim_not_offered` had ALREADY been delivered earlier in the run; a non-repeatable delivered claim is correctly unavailable. Label such rows with a NEW cause `already_delivered` (same wiring as (c)), carrying the earlier turn number in signals.
(e) Reads of text already delivered ('show Michelle's text' when it was read earlier) are the same case as (d). A claim also has presence/predicate conditions (`requires`, `earn_when`); a claim not offered because its condition is false is `claim_not_offered` with signals recording WHY (`unmet`: the unmet requirement or condition text, from explain_reveal-style reasoning if `storygame/runtime/reveal_eligibility.py` (see its `explain_reveal` or the nearest equivalent; read it) can be called deterministically with the packet's pre-turn facts; otherwise record what you can compute and `unmet: null`).
(f) Sibling alternatives in a shared storylet: when a claim is not offered because a sibling claim of the same storylet already fired (non-follow-up alternatives stay spent; see reveal_eligibility.py near lines 51 and 86), say so: cause `claim_not_offered` with signals `spent_by_sibling: <claim id>`.

WHAT TO BUILD. (1) Extend the failing-turn packet builder in factory/stations/live_playtest.py (`report_to_packets` and what it calls) with bounded provenance fields if the saved report carries them: `previous_narration` (the narration text of the previous turn in the same run, truncated to 600 characters), `delivered_before` (list of claim/knowledge ids delivered earlier in the run, from the report's per-turn selected_knowledge_ids), `rejected_code` and `rejected_message` for rejected turns if the report has them (guard_rejections), and `facts_before` if the report has per-turn pre-turn facts. Missing data -> omit the field; old packets without them must still diagnose exactly as before (keep every existing test green except where a deliberately changed label is pinned: update it and say so in NOTES.txt). (2) Use those fields in `diagnose_turn` for (a)-(f); decisions stay deterministic rules with `decided_by: "rule"` and each new signal key documented in a short comment. (3) Per-row `why` text must state the evidence used (e.g. 'Claim K was delivered at turn 3.'). (4) The classifier (default_classifier / _apply_classifier) may still revise only `unclear` rows; keep that, but pass the new provenance fields in its prompt only if the packet has them (bounded). (5) Keep lexical near-matches as hypotheses: in signals add `hypothesis: true` for claim_wording_miss rows, nothing else changes about them. Look at the real saved report only if you need field names: /home/bcorfman/dev/ringer-work/e2e-blind-player-17c.json (read-only; use `jq`/python to inspect; do not copy it into tests, build small fixtures).

TESTS (hermetic, small fixture package/packets, fast): one test per case (a)-(f) asserting the new cause/signals, plus: a packet without any new fields still gets today's label; counts/summary include the new causes; wording-miss rows carry hypothesis true.

HARD LIMITS. Edit only the four owned files. NEVER edit story data under data/, storygame/, bench/, factory/stations/probe.py, fix_plan.py or planner.py."""

SPEC_D = """TASK: let the planner decline an unsupported repair, make the evidence packet causally sufficient, and make lint reject plans their own evidence contradicts (diagnosis sections 3, 6, 7). Owned files: factory/stations/planner.py, factory/stations/fix_plan.py, factory/line.py, tests/test_factory_planner.py, tests/test_factory_fix_plan.py, tests/test_factory_line.py.

BACKGROUND. The planner (factory/stations/planner.py, brief near line 30) must choose exactly one of three fix kinds (`add_pacing_beat`, `set_text`, `edit_claim_evidence`; factory/stations/fix_plan.py `_KINDS`, lint_plan near line 389, build_evidence near line 596). When the real cause is a harness defect, a provider-wiring defect, a diagnosis defect, or a story restructuring (e.g. splitting a reward out of a shared storylet), none of the three fits, so the planner is pushed to force an unsupported cause into a permitted beat. A real rejected plan: a pacing beat `reyes_orders_1a` (trailing, guarded by patrol presence and `card_challenged: false`) set `card_challenged: true`. In the story, `card_challenged` means the officer SAW Kristin take the card and CHALLENGED her; the beat required neither. Readers of that fact (the 'officer presses' storylet and the departure variant) then fabricated suspicion. The saved plan is at /home/bcorfman/dev/ringer-work/rehearse-19f/work/factory-19-1A-story_data/plan.json (read-only; read it and the sibling wire.patch to build a faithful fixture; do not rely on that path in tests).

CHANGE 1 (reroute). Add a fourth plan kind `unsupported` with fields: version, ticket_id, scene, kind, reason (<=400 chars, must begin with 'Precedent:' like the others? NO: for this kind it must begin with 'Reroute:'), evidence_keys (non-empty subset of failing-turn packet keys), and `reroute` one of "station_code" (harness/diagnosis/provider defect), "story_edit" (needs a bounded story restructure the three kinds cannot express), "adaptive_probe" (the hypothesis needs a responding player, not a fixed replay). Update the planner brief: tell the model it may return `unsupported` when no menu fix matches the evidence's real cause, and must not force a cause into a beat; document the three reroute values; keep the brief's other rules. Add `unsupported` to the evidence packet's `fix_menu` as a fourth entry. Lint for `unsupported` checks shape, scene, evidence_keys and reason only. In the planner handler and in factory/line.py: an `unsupported` plan never reaches wiring; the ticket is parked as an owner-wait/escalated state with the `reroute` value and reason recorded in the ticket payload (follow how the line already escalates, e.g. `owner_wait`; read factory/line.py and factory/tickets.py; do not invent a new ticket Status; reuse the existing mechanism so existing escalation tests still pass) and it must not consume a replan cycle as a failed attempt. Do not edit tickets.py (not owned); if a field is needed that tickets.py forbids, put it in `payload`.

CHANGE 2 (evidence sufficiency). In `build_evidence`/`_candidate_ids`: also collect the claim ids the diagnosis rows name (`signals.claim_ids` in ticket_payload['diagnosis']['rows'] if present) so their full definitions (`_candidate_evidence`) are in `candidates` even when they were not offered. Add to each failing turn's bounded evidence, when present in the packet: `previous_narration` (truncated 600), `rejected_code`, `rejected_message` (these may be added to packets by another task; absent -> omit; do not fail). Add `diagnosis` signals compactly to each diagnosis row (bounded as today: keep the 6000-character cap behaviour). Add `fact_readers`: for every fact a pacing beat could set (declared story facts), the list of ids of storylets/pacing events/claims/transitions that READ it, plus its writers (use the existing `producers()` helper and whichever reader index exists; grep for how `_shared_effect_problems` finds readers; if only writers are indexed, build readers by scanning the package's predicates deterministically). Bound the whole `fact_readers` entry to 2500 characters, dropping facts with no readers first.

CHANGE 3 (lint on meaning). Add lint rule `plan.skipped_preconditions`: for an `add_pacing_beat`, for each fact the beat sets (to a given value) that already has existing writers (`producers(package, fact_id, value)`), if ANY existing writer carries preconditions (when/requires/earn_when predicates on facts) that the beat's own `when` does not also pin to the same values, the lint rejects the plan with a message naming the fact, the writer and the missing predicates: a beat may not set a story-meaning fact while skipping the conditions its established writers require, and that fact's readers would act on a state that never happened. Keep the existing `plan.redundant_effect` rule; both may fire. Write the rule so that setting a fact NOTHING else writes (no existing writers) is unaffected. Also add `plan.contradicted_cause`: if the plan's `reason` names a diagnosis cause label (e.g. 'no_authored_outcome') for a failing-turn key in `evidence_keys` whose diagnosis row carries a DIFFERENT cause, the lint rejects it (text-level: any cause label from the diagnosis cause constants appearing in reason that matches none of the causes of the cited keys' rows). If the ticket has no diagnosis, the rule does not fire.

CHANGE 4 (measurable test named). Add a required plan field for `add_pacing_beat` only: `test` with value "fixed_replay" or "adaptive_player" (`fixed_replay` valid only when the hypothesis concerns the same typed action; `adaptive_player` when the beat is a cue meant to change the player's NEXT choice). Update the brief with that rule. Lint rejects a missing or other value (`plan.test`). Everything that constructs or validates plans in the repo (grep: wiring.py, manifests, tests) must still work: for existing stored plans without `test`, `_shape_problems` must accept the old shape ONLY when called through a `legacy=True` path used by readers of saved plans (wiring.py reads saved plans; read it and add the keyword without editing wiring.py: i.e. put the new requirement in lint_plan only, not in the shared shape validator that wiring uses). Do not edit wiring.py (not owned).

TESTS (hermetic, fixture mini-package; extend the existing fixtures in tests/test_factory_fix_plan.py; if loading the real continuity-initiative package takes under 5 s per test you may build one regression with a faithful `reyes_orders_1a`-style plan against the real package, otherwise use a fixture with the same predicate structure): (1) unsupported plan passes lint with Reroute:/reroute, fails with wrong reroute or bad reason prefix; (2) the handler/line parks it without wiring and without consuming a replan; (3) evidence includes diagnosis-named claims not offered, previous_narration and rejected fields only when present, fact_readers bounded; (4) the card_challenged-style beat is rejected with plan.skipped_preconditions naming the writer and missing predicate; a beat that pins the same predicates passes; a fact with no writers is unaffected; (5) plan.contradicted_cause fires/doesn't; (6) test field required and validated in lint only, old plans still readable by wiring (run tests/test_factory_wiring.py unchanged to prove it). Update old tests that pin the old three-kind menu or plans without `test`, and say so in NOTES.txt.

HARD LIMITS. Edit only the six owned files. NEVER edit factory/tickets.py, wiring.py, diagnose.py, probe.py, guard.py, factory/config/*, story data under data/, or storygame/."""

CHECK_TEMPLATE = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- bench factory storygame tests
bad=$(git diff --cached --name-only | grep -vE '^(@OWNED_RE@)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
PYFILES=$(git diff --cached --name-only | grep '\\.py$' || true)
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 @TESTS@
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget @BUDGET@ s)"
[ "$took" -le @BUDGET@ ] || { echo "over the @BUDGET@ s budget"; exit 1; }
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/@KEY@.patch"
test -s "$WORK/out/@KEY@.patch"
"""

TASKS = [
    {
        "key": "provider-parity",
        "spec": SPEC_A,
        "owned": ["storygame/runtime/item_facts.py", "tests/test_bench_item_facts.py"],
        "tests": "tests/test_bench_item_facts.py tests/test_3c_item_facts_arm.py tests/test_item_facts_null_place.py tests/test_bench_runtime_mode.py",
        "budget": 120,
        "verified": "The item-facts provider carries the semantic reveal callback, so probe replays use the hosted reveal selection.",
    },
    {
        "key": "exit-cause-and-approval",
        "spec": SPEC_B,
        "owned": [
            "bench/core.py",
            "factory/stations/probe.py",
            "tests/test_factory_probe.py",
            "tests/test_bench_runtime_mode.py",
        ],
        "tests": "tests/test_factory_probe.py tests/test_factory_probe_routing.py tests/test_bench_runtime_mode.py tests/test_bench.py tests/test_factory_line.py",
        "budget": 150,
        "verified": "Exit causes are recorded, missing evidence is never counted as earned, probe runs record provenance, and a billed approval is single-use.",
    },
    {
        "key": "diagnosis-provenance",
        "spec": SPEC_C,
        "owned": [
            "factory/stations/diagnose.py",
            "factory/stations/live_playtest.py",
            "tests/test_factory_diagnose.py",
            "tests/test_factory_live_playtest.py",
        ],
        "tests": "tests/test_factory_diagnose.py tests/test_factory_live_playtest.py tests/test_factory_stations.py tests/test_factory_triage.py",
        "budget": 120,
        "verified": "Diagnosis labels use prior delivery, prior narration, scoped aliases and eligibility instead of lexical guesses alone.",
    },
    {
        "key": "plan-reroute-and-lint",
        "spec": SPEC_D,
        "owned": [
            "factory/stations/planner.py",
            "factory/stations/fix_plan.py",
            "factory/line.py",
            "tests/test_factory_planner.py",
            "tests/test_factory_fix_plan.py",
            "tests/test_factory_line.py",
        ],
        "tests": "tests/test_factory_planner.py tests/test_factory_fix_plan.py tests/test_factory_line.py tests/test_factory_wiring.py tests/test_factory_escalation.py",
        "budget": 150,
        "verified": "The planner can decline an unsupported repair, evidence names the diagnosed claims, and lint rejects beats that skip a fact's preconditions.",
    },
]


def build() -> dict:
    def fill(text: str, **extra: str) -> str:
        out = text.replace("@REPO@", REPO).replace("@WORK@", WORK).replace("@DIAG@", DIAG)
        for key, value in extra.items():
            out = out.replace(f"@{key}@", value)
        return out

    tasks = []
    for item in TASKS:
        owned_re = "|".join(path.replace(".", "\\.") for path in item["owned"])
        tasks.append(
            {
                "key": item["key"],
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": item["owned"],
                "spec": fill(PREAMBLE) + "\n\n" + fill(item["spec"]),
                "check": fill(
                    CHECK_TEMPLATE,
                    OWNED_RE=owned_re,
                    TESTS=item["tests"],
                    BUDGET=str(item["budget"]),
                    KEY=item["key"],
                ),
                "expect_files": [],
                "verified": item["verified"],
            }
        )
    return {
        "run_name": "factory-19q-repairs",
        "workdir": WORK,
        "max_parallel": 4,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19q-factory-repairs-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
