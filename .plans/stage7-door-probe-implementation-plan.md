# Stage 7 door probe: implementation plan

Status: ready for implementation; no implementation or billed runs performed.
Prepared 2026-10-17 from the current working tree and recorded fixtures.

This is a wording screen. It does not reproduce the hosted pre-turn facts,
pacing, transition eligibility, world capture, or full runtime validation.
Do not replay the seven commands from bare 2A entry again.

## 1. Files and interfaces to build

Keep new harness files in `scripts/ringer/stage7/`:

| File | Responsibility |
| --- | --- |
| `door_prompt.py` | Fixture selection, exact replacements, bridge/entry extraction, hashes and byte-diff assertions |
| `door_transport.py` | Raw prompt adapter using the existing provider transport/parser; request budgets and spend events |
| `door_continuation.py` | Fresh 2B bench state, raw-player commands, real matcher and runtime outcomes |
| `door_probe.py` | CLI, rep-major scheduling, incremental artifacts and final ledger append |
| `door_ask_player.mjs` | Existing `askPlayer` adapter with counted attempts and a one-request cap |
| `check_door_probe.py` | Offline artifact, ownership, caps, matching and verdict checks with explicit failure messages |
| `test_door_probe.py` | Offline tests with provider/network and subprocess fakes |
| `door-probe-build.json` | One implementation task |
| `door-probe-dry.json`, `door-probe-smoke.json`, `door-probe-n12.json` | One execution task each |
| `door-probe-read-smoke.json`, `door-probe-read-n12.json` | One reading task each |

Add `bench/variations/stage7-door-bridge.json`. Keep the four existing door
variations unchanged. Update the existing live-bench entry in
`docs/testing-runbook.md` and the Stage 7/Resume here entry in
`.plans/implementation_plan.md` when implementation is verified. No story or
recorded fixture edits. Keep results under `bench/results/stage7-door-*`.

The proposed CLI is:

`door_probe.py --n {1,12} --out DIR [--dry-run] [--confirm]`

`--confirm` is mandatory for live execution. Reject other N values, existing
nonempty output directories, missing fixtures and failed preflight assertions
before creating live clients. There is no automatic resume or rerun.

## 2. Exact prompt selection and patches

Read UTF-8 JSON at
`bench/results/stage7-blind-raw/attempt-1/e2e-blind-player-prompts.json`.
Select exactly one element of `replicates` with `replicate == 1`, exactly one
element of its `scenes` with `scene == "2A"`, and exactly one element of that
scene's `prompts` with `turn == 7`. Its `prompt.system` and `prompt.user` are
the input strings. Require both to be nonempty strings. Do not use list index
7 or assume the final prompt is the target.

I read this fixture. The command is the final bullet in the `PLAYER` section:

```text
PLAYER:
- Kristin. Place: service corridors.
- Look for a concealed route or access panel leading from the service corridors to the detention area.
```

Keep the system string byte-identical in every arm. Split the user text only
at the exact section separators, retaining separators and all whitespace.
Require one each of CHARACTERS, SCENE, THINGS, CONSTRAINTS and PLAYER.
Apply the following replacements to scoped, complete bullet lines, requiring
each old line to occur **exactly once in its stated section** before editing:

| Arm | Section | Old text after bullet prefix | New text |
| --- | --- | --- | --- |
| control | — | — | No edit |
| review | CONSTRAINTS | `This happens now. Show it in the scene: A second credential check threatens their inspector cover.` | `This happens now. Show it in the scene: Their inspector cover faces a second review.` |
| stale-scene | SCENE | `Kristin must plan a way into the facility. False identities are a possible cover.` | `False identities are a possible cover.` |
| stale-scene | SCENE | `Brandon prepares technical credentials while Kristin chooses how much of the real cooling-water and ventilation risk to put in their lie.` | `Brandon prepared their technical credentials for the facility inspection.` |
| stale-scene | CONSTRAINTS | `Brandon Corfman may say this aloud: Brandon prepares technical credentials while Kristin chooses how much of the real cooling-water and ventilation risk to put in their lie.` | `Brandon Corfman may say this aloud: Brandon prepared their technical credentials for the facility inspection.` |
| wording | PLAYER | `Look for a concealed route or access panel leading from the service corridors to the detention area.` | `Search the service corridors for a route to the detention area.` |

Important correction to the prompt's premise: the credential-preparation
sentence occurs **twice globally**, once in SCENE and once in CONSTRAINTS.
Assert that global count is two, then assert each scoped line occurs once.
Replacing both models the proposed knowledge statement override; changing
only SCENE would be a different experiment. The other two package sentences
occur once globally. The bridge sentence occurs zero times in this prompt.
Never silently replace all occurrences or weaken a failed assertion.

Save original/patched prompt files, SHA-256 hashes and unified diffs. Compare
each diff against the exact permitted replacement list. Unchanged sections
must match byte-for-byte. Check variation overrides agree with this table;
YAML `statement:`/`text:` prefixes are not part of the prompt replacements.

## 3. Fixed-output bridge comparison

Load `e2e-blind-player.json` alongside the prompt fixture. Select replicate 1,
scene 2A, turn 7 uniquely; require its input to equal the original command,
`rejected == false`, `scene_id == "2B"`, and `transition_cause == "earned"`.

Its `text` already includes all three components: narrator prose, the bridge,
and the 2B entry. Load the package with the existing loader; obtain 2A's
`bridge_text["t_2a_2b"]` and 2B's `entry_text` from scene metadata. Use the
runtime's `join_narration` separator behavior to verify and remove the exact
terminal bridge-plus-entry suffix. Require one suffix, a nonempty prefix,
and exact reconstruction of the recorded text. Do not split on invented-door
keywords. Fail if the package's current authored suffix no longer matches.

The extracted fixed narrator output ends:
`As she searches, she notices a small, unmarked door with a keycard reader and a ventilation grille.`

Add a paired baseline `stage7-door-fixed-control`, using that prefix plus
the normal bridge and entry. `stage7-door-bridge` uses the identical prefix
and entry with only this bridge sentence removed:

`Beyond those corridors, the records archive waited behind another layer of security.`

Create the bridge variation with name `stage7-door-bridge`, story package
`data/stories/continuity-initiative`, and this exact `plot.md` override:

```text
old: "    won them access to restricted infrastructure corridors. Beyond those corridors, the records archive waited behind\n    another layer of security."
new: "    won them access to restricted infrastructure corridors."
```

Require the old source span once before materialization, and the removed
sentence once in the loaded bridge. The fixed-control can use the existing
control variation with a distinct experiment label; no extra package needed.
Neither fixed-output arm makes a 2A narrator call. Comparing bridge deletion
only against newly generated control prose would confound the bridge effect.

## 4. Narrator transport and the validation boundary

Verified source path:

- `bench.core.load_variation`, `package_and_state`, `provider_for` construct
  the bench's provider.
- `CloudflareTurnProvider._dispatch` builds a 1024-token JSON-object request,
  calls `_request_allowing_one_transient_retry`, and parses through
  `_parse_eligible_proposal`; it also handles recovery and fallback.
- `_request` owns the existing Worker HTTP/auth/envelope normalization path.
- `storygame.runtime.contracts.parse_turn_proposal` supplies the typed segment
  contract; `proposal.narration` uses `join_narration`.
- `worker/src/index.js` chooses the deployed `CF_AI_MODEL` (default
  `@cf/meta/llama-3.1-8b-instruct-fast`) and sets temperature zero with
  `response_format`. Do not choose a new model or temperature in this probe.

There is **no ready-made raw-pair entry point with full hosted validation**.
`_dispatch` takes structured user data and reassembles it; its eligibility
parser requires `last_projection`. A bare state's projection is not the lost
hosted projection. Calling `_dispatch` with a string, setting a fake empty
projection, or declaring bare-state validation equivalent would be wrong.

Smallest safe wrapper: in `door_transport.py`, construct the provider through
`provider_for`, then call its existing `_request` with precisely
`{system, user, max_tokens: 1024, response_format: {type: "json_object"}}`.
Parse the normalized reply with `parse_turn_proposal`, reject nonempty
`selected_knowledge_ids` (the fixture explicitly offers no candidates), and
retain all segments and provider-cleanup telemetry. Preserve the request
and returned normalized response. Retain item-facts telemetry when available,
but never use it as the prose verdict or apply it as recovered hosted state.

For this exact-prompt stage allow **one physical request per trial**; invalid
JSON, invalid schema or a transport failure is a failed trial. No salvage,
fallback or correction prompt. This deliberately measures first-response
wording with the shared transport/schema, not hosted recovery effectiveness.
Do not claim complete semantic, grounding, speaker, or fact-store validation:
those require the unavailable snapshot. Any unexpected grounding IDs are
flagged for review, not assumed valid from a fabricated state. If complete
hosted validation is required as a hard condition, this experiment cannot
satisfy it from these fixtures; obtain a new saved-state run first.

For actual 2B turns below, use `RuntimeEngine.turn` and its normal validation,
with the provider's normal maximum of two narration requests per turn.
Wrap the existing provider `_request` in a narrowly scoped counting adapter
that debits a shared budget **before** forwarding; retain and restore the
original method. Cover every provider instance in the run, not just raw 2A.
Do not add another HTTP client or copy the provider's request implementation.

Provider construction alone does not append a bench ledger row; that happens
in `bench.cli._run`. Use `bench.core.append_ledger_row` explicitly at the end
and on failure. Give each experiment a UUID and append one spend-only row per
arm with `scenes_scored: 0`, `max_score: 0`, `scores: []`, a distinct
`score_metric: "door_prompt_screen"`, provenance/hashes, status, exact request
attempt counts, player counts and the request-based neuron estimate. Do not
manufacture seven-criterion bench scores or put player calls in judge counts.
Store detailed spend events locally first so a process crash remains auditable.

## 5. 2B continuation and matching

Reuse the pattern and helpers in `2b_cue_probe.py`, loaded with importlib
because its module name begins with a digit. Reuse `read_fixture_transcript`
as a cross-check of the selected final 2A text and `action_groups` for the
control package's evidence groups. Reuse the existing bench
`package_and_state` → `provider_for` → `RuntimeEngine` path, but do not call
the old `narration_for`: it hard-codes the contaminated door command.

The old probe/check is insufficient: it counts any match as success, omits
prerequisites, counts after successful calls, and uses keyword flags. None of
those behaviors becomes an acceptance rule in this harness.

For each trial:

1. Compose generated 2A narration + normal bridge + 2B entry, or the fixed
   bridge pair above. No opening narration call. Save components separately.
2. Give exactly that composed screen to the existing JS `askPlayer` with
   `profile: "raw"`, empty status, and cap 1. Preserve raw command bytes.
   `door_ask_player.mjs` follows `2b_ask_player.mjs`, reports its counter in
   success/error JSON, and supports an offline prompt-only mode using
   `playerPrompt`. The existing helper's cap 1 actually prevents its optional
   validation retry; keep that behavior explicit. No player retry loop.
3. Create a fresh bare 2B package/state with normal placements for that arm.
   Never infer facts or create a door from the composed prose. Save the
   initial facts and package hash. This is a standardized continuation,
   not reconstruction of the hosted world.
4. Before each action, use the current package knowledge definitions and
   `explain_reveal(state, "player", entry).eligible` to filter scene-2B
   action-evidence entries. Run the real `_matches_all` over every evidence
   group. Save all eligible IDs, evidence and matches. Exactly one is a
   matcher hit; zero or multiple is not.
5. Execute command 1 through `RuntimeEngine.turn`, preserving segments,
   authored delivery/cue, rejected-turn reason, selected/committed reveal
   and before/after facts. A hit counts as **earned** only if the turn
   commits that eligible reveal. Check state deltas, not just model selection.
6. If command 1 earns no reveal, append the command and exact player-visible
   response, ask for command 2, and score and execute it in the same state.
   Use the existing visible recovery response for a runtime rejection, with
   the rollback state; a provider outage ends the run. Stop after command 2
   or an earlier earned reveal. Never request a third command.

Explicitly disable the provider's semantic fallback (`semantic_ask = None`)
and contract-shadow opt-in for this **exact-matcher screen**. Record this
mode in every run. Otherwise `provider_for` can attach a billed Jev client
and the claimed two-budget experiment would be false. Do not enable
ItemFactsProvider, world-capture enrichment, name-matching calls or judges.
The raw player's natural wording remains untouched. Live confirmation must
restore the hosted semantic/world paths; exact-screen misses can be semantic
successes in real play, and vice versa.

## 6. Arms, ordering and hard caps

For every rep, run this order, serially:

`control, review, stale-scene, wording, fixed-control, bridge`.

Use the `stage7-door-` prefix in artifacts. Run 12 trials per arm; the extra
fixed-control makes 72 full-run rows. Smoke uses one per arm, six rows, and
is not pooled into the 12-trial result. Do not run an entire arm before its
control or split arms into concurrent tasks.

| Phase | Raw 2A requests | 2B request maximum | Total Cloudflare cap | Raw-player cap |
| --- | ---: | ---: | ---: | ---: |
| dry | 0 | 0 | 0 | 0 |
| smoke, N=1 | 4 | 6 × 2 turns × 2 requests = 24 | 28 | 12 |
| full, N=12 | 48 | 72 × 2 × 2 = 288 | 336 | 144 |
| entire planned live experiment | 52 | 312 | 364 | 156 |

No separately billed judge calls. Approximate neuron ceiling using the bench's
11/request heuristic is 4,004 for smoke plus full, not actual billing.
Ringer worker inference costs are separate from these experiment API caps.

Validate N and derive caps internally; do not accept a flag to raise them.
Persist an attempt reservation before every network send. Count failures,
timeouts and recovery requests. Reserve one player attempt before subprocess
launch so a killed child cannot erase possible spend. Keep acknowledged
counts separately if an attempt's delivery is unknown. Stop on quota/budget
errors, transport outages, exhausted budgets or malformed player output;
write partial artifacts and the error, exit nonzero, never restart to fill N.
An invalid raw narrator proposal is retained as a failed trial; do not replace
it with another sample. A completed screen with failed trials cannot pass the
quality gate. These caps are maxima, not targets.

## 7. Reading and artifacts

Each output directory contains `run.json`, `prompts/`, `results.json`,
`spend.jsonl`, `summary.json`, `source-before.json`, `source-after.json`,
`verdicts/`, and `notes.md`; add `run-failure.txt` on failure.
Write results atomically after each stage, including an in-progress row
before its first request. Record rep/arm order and monotonic request sequence.

Each row has a stable ID, hashes, input prompt path, raw proposal, parsed
segments, narrator-only text, bridge/entry/composed screen, continuation
commands/responses, eligible and matched IDs, commit/rejection records,
request counts, status and error. Hash the complete row before review.

A reader (Claude Code or a human) reads **every** narration, composed exit,
command and continuation against the prompt, declared scene things and
available knowledge. Write one `verdicts/<row-id>.json` with row hash,
reviewer identity, these booleans, and evidence quotes plus a short rationale:

- new unsupported access obstacle;
- new unsupported credential requirement;
- respects starting place;
- responds to attempted action;
- stays within declared actionable things;
- player pursues an unsupported access requirement;
- premature disclosure or unauthorized action;
- continuation rejection and earned reveal by command 1/2.

Separate new inventions from the fixed bridge pair's inherited door. The
fixed pair has `upstream_invention: inherited`; its comparison measures
continued pursuit/new obstacles, not prevention of that recorded invention.
For generated arms, the obstacle count is the union of upstream invention,
downstream invention and player pursuit, at most once per row.

Missing/uncertain readings remain `needs_review`, never false. Automated
checks validate verdict completeness and recompute matching/counts, but do
not decide prose meaning. Do not copy `mentions_invention` from the old probe.
No keyword/regex acceptance gate; omit even triage counts unless explicitly
labelled as non-scoring. Blind the prose reader to arm labels where practical.

## 8. Offline tests and dry-run contract

Tests cover unique fixture selection; missing/duplicate anchors; the two
credential occurrences; exact section preservation; bridge extraction and
reconstruction; all variation loads; rep-major order; and prompt hashes.
Test malformed/valid provider envelopes with the real typed parser; failure
and recovery spend accounting; child failure accounting; quota stops;
pre-send caps; and incremental failure artifacts.

Test zero/one/multiple `_matches_all` results with current prerequisites,
unearned later reveals, rejection rollback and command-2 state continuity.
Use imperative commands in synthetic tests, e.g. `Read the selection files.`
Keep intentionally raw fixture/player text unchanged. Test the actual
network boundary is forbidden in unit/dry modes, including subprocess fetch.

Dry-run loads all six arms, produces full original/patched prompts, diffs,
bridge compositions, eligible 2B IDs, player prompts and the 72-row planned
order. It uses explicit dummy provider configuration and no `.env`; it must
work with credentials absent. Outputs are labelled dry, never fake live rows.

`check_door_probe.py DIR N --mode dry|artifacts|reviewed` prints each failing
row/path/invariant, then exits nonzero. It verifies fixture/source hashes,
allowed diffs, expected unique rows/order, cap arithmetic and spend events,
recomputes matcher results from saved state/evidence, and reconciles summary
and ledger experiment IDs. `reviewed` also requires every verdict and checks
its row hash. Scientific arm failure is reported separately from invalid
experiment execution; losing arms must not trigger billed retries.

Use a before/after content inventory of tracked files **and pre-existing
untracked inputs**. The current tree is dirty; the existing
`bench/checks/no_source_drift.py` judges git status, not changes from task
start, and broad allowances would hide edits. The new checker must compare
content/deletions/new files to the baseline with exact task-owned paths.
Exclude only the run output, allowed ledger appends, `.git` and known build
caches. Never revert the user's pre-existing changes to make a check pass.

## 9. Ringer manifests and self-contained task briefs

All manifests: repo `/home/bcorfman/dev/freytag-forge`, `max_parallel: 1`,
`worktrees: false`, distinct workdir
`/home/bcorfman/dev/ringer-work/<run_name>`. All tasks have `max_attempts: 1`.
For consistency with `2b-cue-n12.json`, use engine `codex`, model
`gpt-5.6-luna`, and engine args `-c model_reasoning_effort=medium`.
Use `full_access: true` only for billed probe tasks. No task may run git
add/commit/reset/clean/checkout/stash/push, print credentials, edit story data
or fixtures, or run another task. The build coordinator copies each brief
below plus this document's complete technical contract into that task's
`spec`; do not leave a worker with an unexplained reference to earlier chat.

Every command below runs from `/home/bcorfman/dev/freytag-forge` with
`PYTHONPATH=/home/bcorfman/dev/freytag-forge` and `TMPDIR=/tmp` exported.
Use `.venv/bin/python`, never `uv` inside workers. Live commands first run
`set -a; source .env; set +a` without echoing values. Put these environment
steps and `cd` directly in each spec/check command. Shell separators here
express required setup, not a chain of independent probe units.

**Build — `door-probe-build.json`, key `door-build`, task_type `implementation`.**
Own the seven new Python/JS harness files above, all five execution/reading
manifests, the bridge variation, the testing-runbook edit and active-plan
update. No execution task may later edit these files. Implement the full
contract in this document test-first, using the existing transport/parser
and no billed calls. Preserve all pre-existing untracked files. Create the
five manifests with the following briefs expanded and literal paths. Keep
new modules under roughly 500 lines. Commands:

```sh
.venv/bin/python -m pytest -q scripts/ringer/stage7/test_door_probe.py
.venv/bin/python -m ruff check --fix scripts/ringer/stage7/door_*.py scripts/ringer/stage7/check_door_probe.py scripts/ringer/stage7/test_door_probe.py
.venv/bin/python -m ruff format scripts/ringer/stage7/door_*.py scripts/ringer/stage7/check_door_probe.py scripts/ringer/stage7/test_door_probe.py
.venv/bin/python -m pytest -q scripts/ringer/stage7/test_door_probe.py tests/test_bench.py tests/test_cloudflare_transport.py tests/test_candidate_matcher.py
node --check scripts/ringer/stage7/door_ask_player.mjs
```

Check executes those focused tests plus Ruff check/format-check and node
syntax check (no autofix in the check). Finish the feature with the runbook's
full Python coverage gate: `.venv/bin/python -m pytest -q --cov`.
Set `timeout_s: 7200`, `check_timeout_s: 1800`. Record verification and remaining
live work in the active plan before marking implementation complete.

**Dry — `door-probe-dry.json`, key `door-dry`, task_type `probe`.**
Own only `bench/results/stage7-door-dry/`. Read this contract; execute the
free command once, with no credentials/network. Inspect every diff and the
fixed-control reconstruction; record exact caps and deviations in notes.
Command:

```sh
.venv/bin/python scripts/ringer/stage7/door_probe.py --n 12 --dry-run --out bench/results/stage7-door-dry
```

Check: `.venv/bin/python scripts/ringer/stage7/check_door_probe.py bench/results/stage7-door-dry 12 --mode dry`.
Set `timeout_s: 900`, `check_timeout_s: 180`.

**Smoke — `door-probe-smoke.json`, key `door-smoke`, task_type `probe`.**
Own `bench/results/stage7-door-smoke/` except its `verdicts/` and
`review-summary.json`; append-only shared exception `bench/results/ledger.jsonl`.
Require dry check success and matching input/harness hashes. Source `.env`,
execute once, six arms in rep-major order, at most 28 Cloudflare and 12
player attempts. No edits, retries or other live commands. Preserve partial
failures and write factual notes. Command:

```sh
.venv/bin/python scripts/ringer/stage7/door_probe.py --n 1 --confirm --out bench/results/stage7-door-smoke
```

Check: `.venv/bin/python scripts/ringer/stage7/check_door_probe.py bench/results/stage7-door-smoke 1 --mode artifacts`.
Set `timeout_s: 1800`, `check_timeout_s: 180`.

**Read smoke — `door-probe-read-smoke.json`, key `door-read-smoke`, task_type `review`.**
Own only `bench/results/stage7-door-smoke/verdicts/` and
`bench/results/stage7-door-smoke/review-summary.json`. Make no experiment API
calls. Read all six rows and their complete continuations against the saved
prompts/package, fill the per-row rubric above with quotes and hashes, and
record whether execution is sound enough for N=12. A losing arm does not
invalidate the harness. Missing output, invalid transport/schema behavior,
wrong composition or unexplained spend blocks full execution. Never alter
raw rows or infer a verdict from words present/absent. Execute the smoke
artifact check before reading and the reviewed check after writing:

`.venv/bin/python scripts/ringer/stage7/check_door_probe.py bench/results/stage7-door-smoke 1 --mode reviewed`

That last command is the Ringer check. Set `timeout_s: 1800`,
`check_timeout_s: 180`.

**Full — `door-probe-n12.json`, key `door-n12`, task_type `probe`.**
Own `bench/results/stage7-door-n12/` except `verdicts/` and
`review-summary.json`; same append-only ledger exception. Require successful
dry and reviewed-smoke checks, a smoke review that approves experiment
integrity, and unchanged inputs/harness. Source `.env`, execute once with
12 trials per arm, 72 rows, at most 336 Cloudflare and 144 player attempts.
Do not pool smoke, replace failed samples, change arms or retry the run.
Write complete or partial evidence and factual notes. Command:

```sh
.venv/bin/python scripts/ringer/stage7/door_probe.py --n 12 --confirm --out bench/results/stage7-door-n12
```

Check: `.venv/bin/python scripts/ringer/stage7/check_door_probe.py bench/results/stage7-door-n12 12 --mode artifacts`.
Set `timeout_s: 7200`, `check_timeout_s: 300`.

**Read full — `door-probe-read-n12.json`, key `door-read-n12`, task_type `review`.**
Own only `bench/results/stage7-door-n12/verdicts/` and
`bench/results/stage7-door-n12/review-summary.json`. Make no experiment API
calls. Read every one of the 72 rows, including errors and both commands when
present. Use the complete rubric with evidence and row hashes. Compare
generated arms only to generated control, and bridge to fixed-control.
Record counts, denominators, failures, ambiguity and the decision rules below.
Never declare hosted adoption from this screen. Execute artifact check first;
Ringer check after reading is:

`.venv/bin/python scripts/ringer/stage7/check_door_probe.py bench/results/stage7-door-n12 12 --mode reviewed`

Set `timeout_s: 5400`, `check_timeout_s: 300`.

Launch each manifest in this order, only after its predecessor's check passes:
build → dry → smoke → read-smoke → n12 → read-n12. Each launch is:

```sh
cd /home/bcorfman/dev/ringer
./ringer.py run /home/bcorfman/dev/freytag-forge/scripts/ringer/stage7/door-probe-build.json
```

Substitute respectively `door-probe-dry.json`, `door-probe-smoke.json`,
`door-probe-read-smoke.json`, `door-probe-n12.json`, and
`door-probe-read-n12.json` for the manifest basename. The installed Ringer
source has `check_timeout_for`; `timeout_s` alone does not extend a check.
The shared ledger is the sole intentional ownership overlap, append-only
and serial. No Ringer check itself makes a live call.

## 10. Decision rule and limitations

Restate the earlier answer's **screening**, not project-standard, threshold:
at least 10/12 continuations earn exactly one eligible 2B reveal by command 2;
at most 2/12 invent or pursue unsupported access requirements; no weakened
guard, premature reveal or changed transition eligibility; and a clear
improvement over a newly sampled, matched control.

For the fixed bridge pair report inherited upstream invention separately;
applying the upstream-invention threshold literally would make both arms
12/12 failures by construction. Its downstream pursuit/new-invention bar
remains 2/12. A bridge-only win is mitigation of a contaminated start, not
a complete fix for the invented door.

Report absolute counts and control differences. Do not call a one-row change
clear evidence; N=12 is a small screen, especially with temperature zero and
potentially identical responses. Mixed or marginal differences are
inconclusive, not victories. Do not silently add more trials.

- **Run three live scene replicates:** a package arm passes the screen,
  meaningfully improves its matched control, and survives prose review.
  Validate the real transition, earned facts, placements, semantic path and
  player continuation in those replicates. Allocate their budget separately;
  they are outside the caps/manifests above.
- **Adopt:** only after those three live scene replicates and applicable
  deterministic/staging checks pass. Bridge deletion also needs the author's
  decision that the security layer is dispensable. The wording arm is causal
  evidence, never a restriction on player language.
- **Drop as a proposed fix:** no benefit, worse narration, leakage, weakened
  pressure, or players still stalled. Reduced invention alone remains useful
  diagnosis. An invalid/incomplete experiment is inconclusive, not an arm loss.

Full hosted guard/transition invariance cannot be established by this
prompt-only screen. Static override checks establish that authored mechanics
were not edited; they do not prove the same runtime facts would be reached.

Verified here: repository guides, bench core/CLI, probe/helper/check/manifest,
four variations, complete saved 2A turn-7 prompt and transcript, current
2A bridge and 2B entry, provider request/parsing boundaries, raw-player caps,
real matcher eligibility path, Ringer check timeout support, and the earlier
answer at `/home/bcorfman/astra-solution.md`. The scene-fixing precedents are
the existing removal/narrowing of competing prose and stale recall, not a
new narrator rule or an invented door declaration; the world-model guide
and its historical record were consulted.

Not verified: future harness execution or variation-load tests; deployed
Worker model/revision/configuration versus the historical run; available
quota; exact provider billing; the lost pre-turn snapshot; whether a raw
player with full earlier history behaves like this bounded screen; authorial
intent for the bridge's security layer; and whether any arm wins. Current
provider cleanup/schema and package changes may differ from the recorded
deployment. Preserve hashes/revisions and disclose those differences.

No code, story data, fixtures, runtime settings, deployment or existing active
plan content was changed while preparing this plan. This document is the
only new deliverable of the planning task.
