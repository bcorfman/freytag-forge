# Complete every authored game path with coherent discoveries and reveals

Design direction update, 2026-10-22: [the game reimagination plan](game-reimagination-plan.md)
now frames the requested content and engine reassessment. Use this completion
plan as evidence and a regression inventory; do not treat its older experiment
queue as parallel work by default. Its unverified results remain unverified.

Status: steps 1 to 4 mostly implemented offline (uncommitted); step 5 audited, awaiting the plot handoff answer; steps 6 and 7 not started. Updated 2026-10-20. Baseline checkout:
`f918c663d67d368645f9a24a47a28ffb29fb77d8` (the adopted pump package).
This is the new plan for whole-game completion. Keep the older 3C plan and its
preregistrations as evidence; do not overwrite their results or reopen failed
arms by silently renaming them. Existing worktree changes are outside this edit.

## Outcome and scope

Finish Continuity Initiative's nine-scene game so every supported authored
branch has a demonstrated route to an earned ending, with its required main
story and storylet material delivered at the right time. An ending flag alone
does not satisfy this goal. The player must see the revelations, retain items
already obtained, and get consequences consistent with their actions.

“Every path” means every declared realization and consequential branch, with
coverage of their differing prerequisites and downstream effects. It does not
mean every possible free-text sentence or every permutation of independent
actions. Build a finite coverage ledger that names what is covered and what is
not. Mutually exclusive alternatives get separate journeys; do not force all
storylets into one playthrough. Optional discoveries may be missed legitimately.
An intentional, confirmed irreparable game break is a separate outcome, not a
successful rescue path and not a reason to fabricate an ending.

The added user requirement is central: discovering an important item must be
registered before later story logic acts on its absence. In particular, finding
Michelle's memory card must not be followed by a gap reveal that sends Kristin
back to find the card she already has. Acquisition, reading its contents, and
learning the next lead are distinct accomplishments.

## Evidence and constraints carried forward

- The reference is [the 3C prompt](chatgpt-3c-stuck-turns-plan-prompt.md), read
  alongside [the updated plan](chatgpt-3c-stuck-turns-plan.md). Later recorded
  outcomes in that plan supersede earlier proposed work.
- The recorded raw whole-game run on the baseline took 79 turns. Scenes 1A–3B
  earned their exits. 3C earned A, B, C1 and C2, then looped and reached the
  deadline ending without D/E. This is one observed failure, not a rate estimate.
- The carried-prefix pump screen's 10/12 earned outcomes do not establish live
  whole-game reliability. Scripted and live histories are different evidence.
- The subsequent C1 screen lost: 3/12 passage finishes versus shipped 6/12.
  The A-R1 broadcast scoping screen also lost: 5/12 versus shipped 7/12.
  Neither is queued again. See the recall-live and broadcast-live preregistrations.
- The free state comparison found both D candidates eligible in the scripted
  comparison, while the recorded movement command matched neither. Location
  differed; SCENE did not. This narrows hypotheses but proves no model cause.
- No-reveal turns are not automatically defects. Movement, dialogue and
  investigation can be successful turns. Repeatedly requesting an already
  completed task, contradictory custody, and missing essential disclosures are
  defects even when a reveal counter or browser test passes.
- Keep the matcher, guards and model budgets intact. Do not revive judge
  calibration, losing aliases, deadline 16, generic extra cues or a new narrator
  rule without new evidence. Preserve ordinary LLM-proposal-first play.

Follow the PRD and contributor, scene-fixing, grounding, player-input and
narrator-writing guides. Facts remain the only mutable truth. Never infer a
commit by scanning narration for words. Package changes use the seven source
files under `data/stories/continuity-initiative/`; generated projections are
regenerated, not hand-edited. Changes to story meaning start in `plot.md`.

## 1. Freeze the evidence and define the coverage ledger

Deliverable: `.plans/game-path-completion-matrix.md`, followed by a small
machine-readable fixture only where tests need it. This is a bounded inventory
for the completion work, not a revival of the parked general reporting project.

Read all seven package sources together. Enumerate every storylet realization,
knowledge item, bridge, resolution event, pacing event and outgoing transition.
Map each to a plot beat and classify it as required, optional, alternative,
observer-only, or deadline fallback. Record:

| Field | Required content |
| --- | --- |
| Identity | Scene, source storylet/realization, knowledge and fact IDs |
| Entry | Actual prerequisites, inherited facts, item custody and location |
| Timing | Earliest/target/latest, required-storylet status, pressure conditions, exit floor and deadline |
| Earned result | Validated action/proposal, committed delta and downstream obligations |
| Visible result | Delivery text and required meaning; permitted speaker/audience |
| Retirement | What makes the cue, candidate or discovery obsolete |
| Coverage | Journey IDs, isolated boundary tests, live evidence and unresolved gaps |

Do not collapse alternatives just because they share an exit fact. Compare their
information, custody, evidence costs and future eligibility. Separate private
facts such as Rebecca's surveillance from what Kristin may know.

Freeze the baseline SHA, package hash, model settings and available artifacts.
Use the recorded 3C run and its prompts/bundles rather than buying another full
run to reconstruct it. Clearly label partial telemetry, synthetic state and
true saved-state replay. Record missing artifacts rather than inventing history.

Completion of this step: every declared option has a row, a coverage obligation
or an explicit reason it is unreachable. A package contradiction becomes a
named issue, not an assumption embedded in expected test output.

## 2. Fix discovery registration and obsolete cues first

Start with the user's memory-card sequence. Its exact failing transcript has
not yet been identified; the symptom is user-reported, not reproduced here.
Retrieve an existing recording if available, otherwise build the smallest
offline reproducer before a billed scene probe.

Current source already gives `SL-1A-E` and `SL-1A-F` the activation condition
`memory_card_recovered == false`. `k_sl_1a_b_r0` establishes recovery; the two
gap knowledge entries establish `drawer_gap_pointed_out` and have empty
knowledge-level `requires`. This is a concrete boundary to investigate, not
proof that another missing activation condition is the fix.

Compare the accepted discovery turn, its next turn and any save/load boundary:

1. Did only the prose say Kristin found/took the card, with no accepted recovery
   fact or custody change? Diagnose proposal, selection and atomic commit.
2. Did the world tree put the card with Kristin while the story recovery fact
   stayed false? Diagnose the missing validated acquisition consequence. Do not
   add a reverse rule that infers arbitrary story facts from physical movement.
3. Did recovery commit correctly, but an already active storylet, staged cue,
   recall line, handoff or candidate survive? Diagnose invalidation and whether
   current prerequisites are rechecked at selection and delivery time.
4. Did the displayed response or saved state lag the committed engine state?
   Diagnose the adapter/projection boundary separately from story authoring.

Use `plot.md`, `knowledge.yaml`, `storylet-routes.yaml`, `world.yaml` and
`handoffs.yaml` for story-side fixes. Follow existing validated reveal handoffs
and one-way `on_assert` custody effects. Scope or remove stale recall only when
the recording shows it is the source. If current package declarations are
correct and the shared lifecycle violates them, file and fix that engine defect
separately with a second, unrelated synthetic story. Never add a card-specific
runtime condition or scan prose to repair state after rendering.

Add the following regression sequences to the existing discovery/transport and
cue tests, or a focused `tests/test_discovery_continuity.py` if needed:

| Sequence | Required result |
| --- | --- |
| Direct search beneath drawer → acquire → examine drawer | Recovery and custody commit together; no renewed search-for-card obligation |
| Open drawer → gap → acquire → examine initials | Gap may guide the first search; neither gap nor recovery is delivered as a new discovery afterwards |
| Acquire → save/load → read card | Recovery and ownership persist; reading remains eligible and is not mistaken for reacquisition |
| Acquire → recording → remaining files | Warning and actionable lead remain distinct; no lost lead from spending an alternative |
| Acquire → put card down → pick it up | Current custody changes; historical discovery stays true; no replay of first discovery |
| Rejected acquisition | Exact pre-turn facts, custody, counters and cue state survive; the UI does not report a successful acquisition |
| Acquire before pressure/nudge/deadline | Time cannot resurrect the completed search or deliver a contradictory fallback |

Example commands: `Search beneath the drawer.`, `Open the drawer.`, `Examine
the carved initials.`, `Read Michelle's memory card.` Use only objects already
available to that player. Do not put future protected vocabulary into a blind
player prompt.

Extend the same lifecycle checks to the transit token, copied records, gate
authorization and Portable data case where the ledger establishes an acquisition
or custody obligation. Do not assume all information objects require possession.
Pass condition: agreement among committed facts, world state, visible delivery
and next-turn eligibility; both direct and cue-led discoveries remain playable.

## 3. Pin the actual timing contract

The following numbers are read from the baseline sources. Reconcile their
compiled interpretation before changing any of them. Scene-local accepted turns
are not wall-clock seconds, displayed attempt numbers or model-call counts.

| Scene | Minimum / nudge / handoff | Pressure events: local turn |
| --- | --- | --- |
| 1A | 8 / 10 / 13 | patrol return 4; widening search 8 |
| 1B | 8 / 10 / 13 | pursuit 4; lockdown 8 |
| 1C | 7 / 8 / 11 | security 3; sweep 7 |
| 2A | 7 / 8 / 11 | scrutiny 3; cover review 7; both require perimeter reached |
| 2B | 8 / 10 / 15 | archive sweep 8 |
| 2C | 8 / 9 / 16 | purge clock 3; transfers 8 |
| 3A | 9 / 10 / 13 | detention lockdown 8; override warning 9 |
| 3B | 9 / 10 / 14 | destruction 9 after Charles abandons Rebecca; relay power 9 |
| 3C | 10 / 11 / 14 | collapse 4; routes collapse 10 |

Storylet windows below are earliest/target/latest, using the suffix after each
scene ID. Knowledge IDs do not always share that suffix: 3C C2 comes from F,
and D2 from G. Derive mappings from `source`, never naming conventions.

| Scene | Storylet windows |
| --- | --- |
| 1A | A 0/2/3; E 1/3/12; F 0/3/12; B 2/5/6; C 4/6/7; D 0/8/9 |
| 1B | A 0/2/3; B 0/6/7; C 0/10/11 |
| 1C | A 0/2/3; B 0/5/6; C 0/9/10 |
| 2A | A 0/2/3; B 0/5/6; E 0/7/8; C 0/9/10 |
| 2B | A 0/2/3; B 0/6/7; C 4/7/7 |
| 2C | A 0/2/3; B 0/5/6; C 0/10/11; D 0/13/14 |
| 3A | A 0/2/3; B 0/6/7; E 0/6/7; D 0/8/9; C 0/10/11 |
| 3B | A 0/3/4; E 0/5/6; B 0/7/8; D 0/9/10; C 0/11/12 |
| 3C | A 0/3/4; B 0/7/8; C 0/11/12; F 0/11/12; D 0/13/13; G 0/13/13; E 0/14/14 |

Do not turn target turns into mandatory disclosure times. In
`RuntimeEngine._activate_pacing` (`storygame/runtime/engine.py`), earned-forward
progress can open a storylet before its earliest turn; required storylets do not
expire at latest. `required_storylet_ids` in `story_package/obligations.py`
computes prerequisite closure. `_ranked_cue_fact_ids` orders eligible missing
facts rather than simply delivering each target beat. Tests must preserve those
rules unless a separately documented defect requires a general correction.

For each boundary, test just before, at and after it, with prerequisites both
present and absent. Include late prerequisites, already completed obligations,
two simultaneously due events, rejection/rollback and save/load. Assert the
exact event/fact provenance and player-visible pressure or delivery, not only
the scene number. Check the final accepted turn's ordering explicitly: an earned
reveal on the deadline turn must not be silently counted as an earned whole
chain when the backstop supplies the rest.

Cover both package-clock and ordinary turn progression; retain the authored
120-accepted-turn story budget and the distinction from `budget_seconds: 7200`.
Required knowledge may remain earnable late; optional windows may close. Neither
case licenses protected information before its prerequisites or a repeated
completed discovery. A conditional pressure event becoming eligible late needs
an explicit expected result, not an assumed exact-turn miss.

## 4. Demonstrate every branch and its continuation offline

Build a minimal set of journeys that covers every realization row and every
distinct downstream state. Reuse shared prefixes, but carry real committed
state forward. A synthetic start is useful for a local boundary test and must
not be reported as a completed whole-game path.

| Scene | Completion and branch obligations |
| --- | --- |
| 1A | Direct/cue-led recovery; full-files versus recording-then-files; patrol alternatives; actionable park lead and retained card |
| 1B | Dead-drop route/photo alternatives; identification/trust alternatives; both pursuit escape realizations; usable token and Brandon dependency |
| 1C | Infrastructure/service entry; confirmed captives versus uncertain Michelle sighting; network/architect evidence; earned infiltration need |
| 2A | Preparation and cover alternatives; perimeter entry; supervisor versus infrastructure access; observer-only surveillance stays private |
| 2B | JANUS and Kristin's role; all three Brandon realizations; sabotage/uprising alternatives; crisis understood without losing required knowledge |
| 2C | Both offer and purge realizations; evidence/rescue dilemma, including C-R2; both maintenance-plan realizations lead to the combined plan |
| 3A | Reunion alternatives; conditioned-release/experiment coverage; authorization alternatives; both uprising launches preserve later gates |
| 3B | JANUS disruption; office entry; both Rebecca bargains; both abandonment realizations; confession/relay alternatives supply a valid broadcast |
| 3C | Both A and B alternatives; pumps plus gates in legal orders; D1→D2 and D2→D1; both E alternatives; coherent earned resolution |

Include every reachable combination of the three authored evidence-gap facts
for processing numbers, development record and marked site list. Establish
reachability through runtime transitions; label impossible combinations. Verify
that costs persist and pressure text reflects the actual gaps. Do not count a
fallback that creates a gap as an earned full-evidence journey.

For each branch record a legal command/proposal sequence, exact reveal order,
scene-local timing and an earned continuation to the ending. Test independent
orders locally instead of multiplying all whole-game permutations. Add a full
journey when a branch changes later prerequisites, knowledge, custody or costs.
Deterministic providers exercise real validation and commit; tests must not
assert goal facts directly and then call that an earned path.

Use and extend `tests/test_canon_journey.py`, `test_scene_relative_pacing.py`,
`test_pacing_handoff.py`, `test_storylet_expiry.py`,
`test_required_storylet_closure.py`, `test_evidence_penalty.py`,
`test_3c_cue_chain.py` and `test_resolution_cascade.py`. A focused new
`tests/test_game_path_completion.py` may hold the coverage-to-journey assertions.
Existing spine expectations do not simulate pacing; `@spine` and `@storylets`
do not prove full branch coverage.

## 5. Close 3C's remaining story and playability gaps

First audit what each alternative actually tells the player. Current E-R2
establishes `phase_one_label_known` and `phase_two_conflict_plan_known`, but its
delivery describes Charles watching unrest and hoping to restore order. It
does not itself explain the Phase One label or the plan to provoke conflict.
Compare the entire composed response and ending against plot 3C.4. If required
meaning is absent, use the proven missing-material handoff technique (3B office
entry and the adopted pump handoff), not a test that merely accepts the facts.
Keep E-R1/E-R2 as separate coverage cases. Do not assume both can be earned in
one playthrough after their common storylet is spent or the ending fires.

Likewise verify that D2's families/community consequence is delivered before
the closing text relies on it. The ending condition in `pacing.yaml` is
`phase_two_conflict_plan_known`; it is not by itself proof that every required
resolution event or visible consequence occurred. Trace A/B/C/F/D/G/E through
`canonical_events.py`, including `resolution_complete`, and require an empty
deadline-event list for earned-completion evidence. Normal canonical cascades
after earned storylets are allowed; deadline backstops are separately labelled.

Then diagnose the live post-gates loop with the discovery-continuity method:
completed evacuation obligations, current parents, stale active/staged material,
the player-visible result, and the available next action. Read the complete
prompt and response beside plot 3C.3–3C.4. Verify whether the intended passage
finished in facts and prose before blaming recognition of an unattempted D act.
Do not teleport Kristin back to the chamber or move Michelle to two places to
make a harness pass. If story geography or delivery location is contradictory,
resolve it in plot and grounded package data first.

The unadopted surface binding only moves captives; earlier evidence did not
establish it as a cure for the loop. C2, pressure text and other recurring lines
remain hypotheses, not a queue of automatic subtraction experiments. Select one
only when a reproduced mismatch identifies it. Preserve the failed C1/A-R1
results. Do not widen D2 recognition unless an eligible, genuine family action
is actually refused in the new evidence.

For each proposed change: name the failing artifact, exact old/new source text,
earlier proven technique, expected fact/prose change and regression risk before
implementation. Screen one variable against shipped control. If the cause is a
shared engine bug, keep its repair separate and cover another story; a package
workaround must not conceal it.

## 6. Verify free-text play with bounded, useful spending

Offline mechanics come first. For an evidenced prompt change, preregister one
mechanics smoke and a 12-row-per-arm screen on the affected scene/context. Freeze
the prompt/history or carried state, alternate arms, name the observable outcome
and read all replies including appended delivery text. Preserve malformed,
rejected and partial rows. No top-ups, replacement failures or pooling across
different starts. A local triage threshold can choose a candidate; it cannot
establish a population success rate.

For prompt-only comparisons, use at most 48 narrator requests for 24 replies
with one shared recovery each, plus the explicitly budgeted smoke. No player or
judge calls are needed unless the hypothesis concerns player response. For a
free-player continuation, derive caps from accepted-turn and attempt limits and
include semantic and item-facts requests separately. Do not describe 48 as a
cap for an entire engine run with those additional calls.

After local wins and source adoption, qualify the exact staged SHA. Run one raw
whole-game journey first. Then spend only on uncovered consequential branches,
using carried histories or dedicated complete journeys as their downstream
differences require. Branch-directed players may receive a roleplay objective,
not reveal IDs, hidden facts or exact matcher commands; label that evidence
separately from raw blind play. Every path has deterministic coverage; live
branch coverage and remaining uncertainty are reported explicitly.

A failed journey returns to its recorded cause. Successful passage narration
does not prove the player proceeds to D/E. A successful scripted canon journey
does not prove free-text usability. One to three live successes are regression
evidence only. Do not make three runs an automatic gate or claim 80% reliability
from the historical 10/12 screen.

Before billed execution record the actual Cloudflare dashboard cap, dollar
usage and UTC timestamp, plus a separate player-model budget. The default $5
daily cap is shared by staging traffic, including CI and other tests, and is
not remaining headroom. Stop on `AI_DAILY_BUDGET_EXCEEDED`; retain partial
evidence and do not raise the cap or retry around it. No spend is authorized or
incurred by writing this plan.

## 7. Adoption, staging and completion gates

Adopt only measured fixes. Run the affected tests, regenerate relevant
disclosure/spine projections, and inspect payload diffs. Finish implementation
with Ruff autofix/format and the full deterministic, coverage, frontend-test and
build gates from `docs/testing-runbook.md`. Maintain at least 90% coverage;
collection totals are not a gate. Verify commands against current source/help
before execution and update an existing runbook entry if a procedure changes.

For each completed feature, update this plan with commit, result, remaining
untested work and the next step before starting another. Follow the existing
Ringer manifest patterns for bounded probes; do not reuse old result directories.

Merge the implementation PR, wait for the SHA-bound `main` staging deployment,
and verify both API version and Pages `/dev/deployment.json` identify the same
SHA/channel. Run smoke and the planned earned journeys. Inspect all nine scenes
for acquisition continuity, correct timing, protected disclosures, coherent
movement/custody and readable next opportunities. Existing 1A/2A/2B/2C no-reveal
counts are review targets, not sufficient diagnoses.

The completion record must show:

- Every declared branch accounted for, with a verified earned continuation or
  an explicitly resolved authoring contradiction; no unexplained coverage holes.
- Required main-story meaning visibly delivered on each supported alternative,
  without premature protected knowledge or unearned item acquisition.
- Discovery and cue retirement work across direct, delayed, reordered and
  save/load play; completed actions do not restart as unmet objectives.
- Timing boundary tests pass, optional omissions stay optional, and deadline
  fallback tests remain valid but separate from earned success.
- A reviewed raw whole-game earned ending on the final staged SHA, plus named
  evidence for consequential branch differences and candid live-sampling limits.
- All known story-breaking findings fixed or shown not to be defects. Accepting
  a known limitation may support a release decision, but is not completion of
  this plan's quality goal.

Only then make a production recommendation using
`docs/railway-production-promotion.md`; promotion is a separate action. Release
only the successful staged SHA and verify production identity/E2E. A later
documentation-only result update does not require another deployment or run.

## Progress log

- 2026-10-20, step 2, memory-card cue (branch 3, stale staged cue). Reproduced
  offline with no model spend: in scene 1A with `memory_card_recovered` already
  true, `_activate_pacing` still stages `continuity_initiative_known`, whose
  `cue_text` is the drawer-gap line. Cause: `_cue_reveal_available` ignores
  whether a delivery's assert-cost fact (here `memory_card_recovered`) is already
  true. This is a shared-engine rule, not a card-specific one. Regression tests
  are in `tests/test_discovery_continuity.py` (the gap-cue case on the real
  package plus a story-agnostic case); both failed before the fix. Fix is the
  Ringer run `game-path-completion-memory-card-cue`
  (`scripts/ringer/stage7/game-path-memory-card-cue.json`), engine.py only.
  Result: fix applied (uncommitted, on `main` working tree): an inline guard in
  `_cue_reveal_available` returns False once any assert-cost fact of the
  delivery is true. Two existing tests pinned the old behaviour and were
  updated: `test_cue_spent_reveal.py` (two new 1A rows in the pinned difference
  set, test renamed `..._differ_only_for_spent_rows`) and `test_bench.py`
  `test_run_scene_records_selection_and_offered_candidates` (now asserts no cue
  once the card is held). Fast suite 2352 passed, authoring_quality 90 passed,
  ruff clean. Ringer's own check passed although pytest was piped to `tail`, so
  it could not see failures; the orchestrator's re-run is the evidence.
  Step-2 sequence tests (2026-10-20, in `tests/test_discovery_continuity.py`,
  13 tests): direct search, gap-then-acquire, snapshot round trip then read,
  put down/pick up, rejected acquisition (read card before owning it: engine
  rejects, snapshot byte-identical), acquire then recording then remaining
  files, and acquire at turns 3/8/11/13. Without the engine fix 4 of 13 fail
  (turns 11 and 13, plus the two direct cue tests); the direct-search and
  gap-then-acquire tests pass either way, so they guard custody and
  re-delivery, not the cue. Finding: the engine commits any reveal the
  provider selects, even for an unrelated command ("Look out the window." with
  `k_sl_1a_b_r0` selected commits recovery); command-to-reveal matching lives
  in the provider's reveal selection, so rejection is only tested for unmet
  `requires`. Save/load is a `RuntimeSnapshot` JSON round trip, not the hosted
  store. Provider-level check added (6 tests, hermetic, `urlopen` faked with a
  worst-case narrator that always claims the card): the real
  `CloudflareTurnProvider` commits it for "Search beneath the drawer." and the
  engine rejects it for five misses (window, open drawer, inspect drawer, take
  the note, back door), mostly through the leak guard on "taped beneath the
  drawer" or `semantic_refusal`. This covers the exact-match path only; the
  live semantic ask is not exercised. Put-down/pick-up moves the card with `World.place`, not a narrated
  item_facts turn. Remaining step-2 work: the same checks for the transit
  token, copied records, gate authorization and Portable data case; the
  `fallback_text` wording after recovery. Also not yet done: the ledger (step 1).

- 2026-10-20, steps 1 and 3 started. Step 1: `.plans/game-path-completion-matrix.md`
  (generated by `.plans/game-path-completion-matrix-gen.py` from the baseline
  package, 239 lines; sections A timing, B storylets/realizations, C knowledge,
  D bridge/resolution events, E transitions, F custody, G issues, H journeys).
  Generator found no package contradictions (every realization has a knowledge
  item and matching operations). Correction recorded in the ledger:
  `required_dependencies` is an availability check (entity not destroyed), not a
  possession check, so `transit_card` and `brandon` need no acquisition test;
  the only acquisition cue is the card. Custody obligations are the
  `fact_effects` moves; all eight land without refusal, apply once, and survive
  a snapshot (parametrized in `tests/test_discovery_continuity.py`, 35 tests).
  Caveat: three deliveries carry penalty costs (`evidence_gap_*`); the step-2
  guard is safe for them today only because those facts are set solely by their
  own fallback. Step 3: the plan's timing tables match the package exactly
  (checked by script for all nine scenes). `tests/test_game_path_completion.py`
  (254 pass, 13 skipped for storylets without a positive condition) tests every
  pressure event, storylet window and exit floor at -1/0/+1; four deliberate
  engine mutations (event `>`, floor `<=`, latest `>=`, earliest ignored) each
  fail it. Not yet covered from step 3: two simultaneously due events, save/load
  mid-window, rollback at a boundary, the deadline-turn ordering, and the
  package-clock versus plain turn progression. Section H of the ledger and step 4
  are not started.

- 2026-10-20, step 4 (offline journeys). `tests/test_game_path_journeys.py`
  (tiered integration, about 80 s on four workers, weight 120 in
  `tests/shard_durations.json`) plays the default policy plus one whole-game
  journey per player-visible realization (70), withholding sibling alternatives.
  All 71 reach the resolution with no deadline backstop event inside 120
  accepted turns. Two branches reach it only through a forced scene exit and
  are pinned as named issues: N-1 `SL-1C-C-R2` (sets `architects_strategy_known`,
  but `bridge_1c_infiltration_needed` needs `national_detention_network_known`)
  and N-2 `SL-2B-B-R3` (sets only `kristin_was_bait`; `bridge_2b_archive_crisis`
  needs two of three facts it cannot supply). Both are authoring decisions for
  plot.md, not engine bugs; they go to the plot-writing handoff, not a code
  fix. `SL-1A-D-R1` is reachable only after the recording alternative (chained
  journey passes; the default policy never plays D). Observer-only rows are not
  journeyed. Full suite without coverage: 2876 passed, 14 skipped, ruff clean.
  Not yet done: the eight evidence-gap combinations, the coverage run
  (`--cov`) and frontend gates, E-R1/E-R2 composed text (step 5), and everything
  in steps 6 and 7. No model spend so far.

- 2026-10-20, N-1 and N-2 handed off. Both are plot decisions, so the ChatGPT
  Desktop prompt is `.plans/chatgpt-n1-n2-bridge-prompt.md` (self-contained:
  engine rules, plot beats, current YAML, three options A bridge accepts the
  alternative, B alternative sets the missing fact, C split into staged
  storylets). Evidence in the package that the alternatives were meant to be
  sufficient: both storylets' `complete_when` accept either fact and both
  realizations list `helps_transition_triggers` for the scene exit. Nothing
  later reads `architects_strategy_known` or `kristin_was_bait`. Waiting on
  Brandon's choice; on return, apply through a Ringer task whose check loads the
  package and updates `KNOWN_FORCED_EXITS` in `tests/test_game_path_journeys.py`
  (the pins must fail first, then be removed).

- 2026-10-20, step 4 evidence-gap combinations (uncommitted). `tests/test_evidence_gap_journeys.py`
  (16 tests, about 15 s on workers, 67 s serial; weight in `tests/shard_durations.json` not yet
  updated) plays all eight subsets of the three gap facts as whole-game journeys through the real
  engine. A subset is built by withholding every knowledge item that establishes the scene's
  delivery fact, so the deadline backstop supplies it. All eight reach `resolution_complete`
  inside 120 turns, set exactly the chosen gap facts, keep the 1C/2B gaps on arrival in 3C, show
  the unchosen scenes' deliveries as earned (delivery set, gap unset), and show the `collapse_3c`
  text that pacing.yaml selects for the subset. These are fallback journeys, never earned
  full-evidence evidence. Ringer run `game-path-completion-evidence-gaps`: round 1 failed only on
  my check's relative `notes.md` path, and its claim that the 2B gap was unreachable was wrong
  (only the B realizations were withheld; the bridge was met by the other three any_of facts).
  Round 2 withheld all four 2B sources and passed. Findings: the backstop records nothing in
  `TurnRecord.deadline_event_ids` for handoff deliveries, so the gap fact is the provenance;
  `routes_collapse_3c` never fires in the thorough journeys (3C resolves before local turn 10),
  so its text per subset stays covered only by the synthetic `test_evidence_penalty.py` test.
  Remaining: a journey that reaches `routes_collapse_3c` with a marked-site-list gap; coverage
  and frontend gates; then step 5.

- 2026-10-20, step 5 audit (read-only, no code changed, no model spend). Findings:
  1. **E-R2 delivers no Phase One meaning.** Both E realizations assert
     `phase_one_label_known` and `phase_two_conflict_plan_known`. E-R1's delivery
     names Phase One and the conflict plan. E-R2's ("From an unknown location,
     Charles watches the unrest...") names neither, and the default scripted
     journey takes E-R2. The ending text states the conflict plan but never says
     "Phase One" or a JANUS file. This is a fact asserted without its meaning shown.
  2. **D2 is not on the ending's path.** `SL-3C-E` and the ending need D1's
     `national_network_fragmenting` and `charles_at_large`, not
     `community_rescue_efforts_begun`; `resolution_complete` omits it too. The ending
     text does not lean on the families, so this is a coverage choice, not a defect.
     Only the plot's "families learn many may be alive" beat is optional in play.
  3. **Canonical trace is clean.** The default earned journey plays A/B/F/C/G/D/E in
     3C with an empty deadline list (rerun this session); it picks D2 before D1 and E-R2.
  4. **Recorded loop (raw run `f918c663`, 3C turns 5 to 14).** Gates opened at turn 5.
     Turns 6 to 13 are eight near-identical "lead the captives through the gates" and
     "watch them emerge" commands; the narrator re-describes the tunnel each time and
     never closes the passage. The D1/D2 cues ("...reach the broadcast chamber",
     "...ask the broadcast chamber for word") were appended twice each (turns 6/11 and
     7/12) while Kristin was in the tunnel or outside, and the player never acted on
     them. Turn 14 is the deadline backstop supplying D1, D2, E and the ending, so it
     is not an earned ending. Plot 3C.3 gives the evacuation to Michelle; Kristin's
     task was the pumps and barrier. The mismatch is the cue location plus a passage
     that never reads as finished, not a failed D recognition (no D act was attempted).
  Handoff: `.plans/chatgpt-e-r2-d-cue-prompt.md` (E-R2 delivery text; cue wording for
  the player's position; whether a closing evacuation line is needed). Waiting on
  Brandon's choice. On return: apply through one Ringer task per variable, screening
  one against the shipped control (12 rows per arm, preregistered), with a package
  load check, `authoring_quality`, and a pinned regression test for E-R2's delivery.

- 2026-10-20, step 5 Issue 1 applied (uncommitted). ChatGPT answer in `.plans/astra-replace-text.md`.
  Ringer run `game-path-completion-e-r2-delivery` (manifest `scripts/ringer/stage7/game-path-e-r2-delivery.json`),
  PASS on attempt 1: E-R2 `delivery_text` and `dramatic_intent` replaced, new `tests/test_3c_phase_one_delivery.py`
  (2 tests), `authoring_quality` passed. Issue 2 (D1/D2 cue wording, closing evacuation line) awaits Brandon's
  option choice: ChatGPT's Option 1 needs Kristin to be able to hear the broadcast, which the plot does not establish.

- 2026-10-20, step 5 Issue 2 Option 3 wording applied (uncommitted; Brandon chose Option 1, then switched to
  Option 3; Option 1 was stopped mid-run and its wording, test and manifest removed). Handoffs
  `national_network_fragmenting` and `community_rescue_efforts_begun` now carry the chamber-based cue and fallback
  text; `tests/test_3c_cue_wording.py` pins them. Ringer `game-path-completion-option3-cues` failed twice on two
  stale pins (not the wording): the adopted-package test hashed knowledge.yaml and compared handoffs bytes, and
  the cue-spent test lacked three N-1/N-2 spent rows. Fixed in `game-path-option3-adopted-test.json` (PASS, attempt 1;
  the adopted-package test now names the later intended edits). Remaining Option 3 items need plot decisions:
  how Kristin learns of the reports and calls, the route back to the chamber, and where the closing evacuation line
  goes. Handoff: `.plans/chatgpt-3c-option3-route-prompt.md`. Note for that prompt: `captives_reaching_surface` is set
  by the canonical `resolution_escape` event, not by the gate delivery itself. Option 3's loop effect is untested
  and must be screened (12 rows per arm against shipped) only after those items land.

## Resume here and unverified work

Status at 2026-10-20 (all uncommitted on `main`; no model spend, no remote checks):

- Done and verified locally (full suite 2876 passed, 14 skipped, ruff clean; the
  `--cov`, frontend and build gates were not run): step 2 cue fix in
  `storygame/runtime/engine.py` with its tests; the step-1 ledger; step-3 timing
  boundaries; step-4 per-realization journeys. Files: `tests/test_discovery_continuity.py`,
  `tests/test_game_path_completion.py`, `tests/test_game_path_journeys.py`,
  edits to `tests/test_bench.py`, `tests/test_cue_spent_reveal.py`,
  `tests/conftest.py`, `tests/shard_durations.json`, and
  `.plans/game-path-completion-matrix.md` with its generator.
- N-1 and N-2 resolved (2026-10-20, uncommitted): Brandon chose Option A for both. The loader
  (`storygame/story_package/loader.py` ~975) also requires a `FactDelivery` for every player-visible
  `any_of` bridge fact, so two deliveries were added to `handoffs.yaml` (`architects_strategy_known`
  1C, `kristin_was_bait` 2B; ChatGPT answer in `.plans/astra-delivery-answer.md`). Both are
  unreachable by the backstop under the any_of order (N-1: network fact first; N-2: the other
  three suffice), which is intended. B-only at 2B gets Brandon's role by backstop. The
  `KNOWN_FORCED_EXITS` pins were removed and all 71 journeys now reach the ending with no forced
  exit. Ringer run `game-path-completion-n1-n2-bridges` (round 2): the worker's tests passed
  but my check had a shell bug (process substitution under sh), so I applied its diff by hand
  and verified in main: 610 passed/13 skipped, `authoring_quality` 90 passed, ruff clean.
  Still to check: the 2B `bridge_text`/Brandon deadline text do not imply his reform motive
  when only his role is supplied; the `kristin_was_bait` cue repeats the fallback's last sentence.
- Next, offline: step 5 remainder (audit done, see the 2026-10-20 step 5 entry; E-R2
  composed text against plot 3C.4, D2 families consequence, canonical-event trace
  with an empty deadline list, the post-gates loop from the recorded prompt).
  Only then pick one 3C live experiment, and only for a reproduced mismatch.
  Do not restart the losing C1 or A-R1 statement screens.
- Before committing: run `uv run pytest -q --cov` and the frontend gates from
  the testing runbook; update `tests/shard_durations.json` weights from a real
  timing run (the journey file is an estimate of 120).
- Known caveats: the cue guard treats any assert-cost as an earlier step (safe
  today only because `evidence_gap_*` facts are set solely by their own
  fallback); the fallback_text of `continuity_initiative_known` still says
  Kristin "recovers the card" and is only a deadline fallback; the provider-level
  reveal tests cover the exact-match path, not the live semantic ask.
- Steps 6 and 7 (billed live runs, staging identity, production recommendation)
  need the Cloudflare cap, dollar usage with a UTC timestamp, a player-model
  budget, and Brandon's go-ahead. Not authorized.

Unverified: the memory-card bug report was reproduced offline as a stale cue;
the exact transcript the user saw was not recovered. Reachability of the
evidence-gap combinations, composed E-R2 disclosure, a fresh earned staged run
and current dollar headroom remain unverified deliverables above.
