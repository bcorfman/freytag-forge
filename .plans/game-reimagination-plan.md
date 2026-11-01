# Reimagine Freytag Forge around dramatic play

Status: proposed design and delivery plan, 2026-10-22. Planning baseline:
`984767a3e234179f8fbd0ef57844b77f93b311bf`. No implementation, model experiment,
or deployment is part of this change.

## Resume here

Act 2 rebuild (2026-11-01): propagated and green. 2A to 2C are three 1C-style incidents
(`i_2a_real_leak`, `i_2b_audit`, `i_2c_rebecca_corridor`) with recovery storylets `SL-2A-D`,
`SL-2B-D`, `SL-2C-E`, the shift supervisor NPC, and the 2B/3A/3B entry variants (written
into `plot.md` directly, not via ChatGPT). Full suite with the coverage gate: 3,679 passed, 92.74%.
Ringer run `act2-incident-propagation`; the id contract is in
[act2-propagation-contract.md](game-reimagination/act2-propagation-contract.md) (superseded in
places by the decisions below). Nothing is committed yet.

Decisions made while propagating (2026-11-01):

- **Engine:** the incident loader (`storygame/story_package/loader.py`) now lets a recovery
  realization match zero outcomes, or one, if it asserts an extra non-outcome fact. Two or more
  stays rejected. This is what lets a missed window be neutral.
- **2C missed window is neutral:** the purge alarm forces them out before Kristin chooses. No
  commitment fact and no outcome cost; 3A gets its neutral entry.
- **2A outcomes:** `inspection_convincing` has advantage `supervisor_convinced`;
  `inspection_doubted` has advantage `restricted_corridor_access` and cost `cover_suspected`
  (outcome advantages must be disjoint). Both set `restricted_corridor_access` as the exit trigger.
- **Recovery ids** follow the engine pattern `SL-<digit><letter>-<letter>`.
- **Timing assumption (unmeasured):** missed windows at turn 5, nudges at turn 6, copied from 1C.
  Neutral-staller recovery bridges were added for 2A, 2B and 2C so a staller leaves by handoff plus three.
- Scene frames for 2A to 2C, the 2A entry knowledge, and the Act 2 prompts in
  `frontend/e2e/canon-journey.js` were rewritten to the new opening; the canon walk plays the
  keep-name and transmit path.

- **2B stall defect found and fixed (2026-11-01):** `audit_recovery_2b` carried a stray
  `processing_numbers_copied == false` condition, so a player who copied the numbers in 1C and
  then stalled in 2B never left (22 turns, no exit). Removed; `tests/test_stall_exit_audit.py`
  now also stalls 2A and 2B with each carried 1C advantage, and fails on the old condition.
  A matrix over carried facts for 2A to 3B found no other stuck state.
- **Live smokes (2026-11-01):** nine rows ran clean after fixes (eight pass; one stopped on a
  narrator-versus-guard rejection). They found and fixed four defects (2B first-beat `JANUS`
  detail, mis-sourced matchable 2A pacing knowledge, the 2B stall exit, a probe over-activation).
  Open finding: every passing row left by a recovery bridge; a blind player never earned a real
  outcome in 2A, 2B or 2C. Act 2 needs the 1C technique of the narration offering the moves.
  Detail and rows in [act2-live-smoke.md](act2-live-smoke.md).
- Nightly check (2026-11-01): the 145 `nightly` tests had never been run against the rebuild (PR runs
  deselect them). 19 failed; all passed on clean HEAD. Real defects: the 2A `k_sl_2a_c_r6` delivery text
  named "the limited console" and "infrastructure corridors" without listing them in its own
  `must_convey`, so a player who earned the vague-diagnosis outcome had the narration rejected (fixed in
  `knowledge.yaml`); the three `*_route_effects` entries were visible to non-player audiences, so they
  entered NPC knowledge context (now a `characters: [charles]` audience; `world_only` was tried and
  rejected because the engine auto-applies world-only effects at bridges and 2B exited early). Stale
  tests updated to the redesign: filler exits 2A to 3A are `earned` through the neutral recovery;
  the 2B development-record gap is now the cost of the earned erase outcome (the recovery carries none);
  `journey_prefix._blocked_for` blocks the outcomes of any incident whose recovery is preferred, not only
  1C; the carried 3C prefix was rebuilt (scripted, free) and its dry-run baseline regenerated; the 3C
  checker compares each artifact with its own recorded prefix turn instead of a constant. Result: 145
  nightly tests pass. Open: the canonical scripted journey waits six filler turns in 2A, so it passes the
  turn-5 window and ends with `supervisor_convinced` and `cover_suspected` both true.

Next: (1) make the Act 2 moves visible to a stranger (the 1C offers technique), then re-smoke; (2) the 3A reunion turn and radio signal beat, which is not confirmed in `plot.md` yet;
(3) Phase 2 (finite 3B to 3C evacuation and aftermath, lighthouse-fixture portability, the 3C
neutral staller); (4) the human gates. Detail in
[game-reimagination/](game-reimagination/whole-story-pacing.md).

Environment narration follow-up (2026-10-25): the
[LLM environment narration plan](grounded-llm-environment-narration.md) defines
the measured replacement for engine-written item/boarding descriptions, model
comparison, and routine implementation coordinator recommendation. It is a
focused workstream, not a restart of the whole-game migration.

Phase 0 status (2026-10-22): complete. The catalogue and accepted revised 1C
incident contract are in [game-reimagination-phase0.md](game-reimagination-phase0.md)
and [1c-contract-result.md](1c-contract-result.md). Phase 1 may begin only
after implementing the typed incident-outcome, outcome-scoped-cost, and
traversal contracts named there.

Phase 1 status (2026-10-24): the build is merged to `main`; the human gate is open. The
incident slice, cue lifecycle fix, handoff guard, Brandon's offers, the loader change and the
stall exit (nudge turn 6, withdrawal turn 8) are in. Seven single-row live smokes ran; smokes
4 to 7 reached 2B on every path (copy numbers, missed window, secure route, stall). Not met:
five fresh human players, which Brandon may waive or replace with his own playthrough. Known
gap for Phase 2: a neutral staller stays in 3C. [game-reimagination-phase1.md](game-reimagination-phase1.md)
holds the step table and each step's result; [phase1-live-smoke.md](phase1-live-smoke.md) holds
the smokes.

Start with Phase 0, then build the observation-shaft slice in Phase 1. The
primary question is whether this becomes a game people want to keep playing,
not whether another scripted journey reaches an ending flag. Prove that before
migrating nine scenes. This document is the new design direction; the older
[implementation plan](implementation_plan.md) and
[completion plan](game-path-completion-plan.md) retain their evidence and
unverified work. Their historical result entries are not fresh measurements.
Do not run their experiment queues alongside this redesign by default.

User priorities incorporated:

- Deliver a finished, engaging game; reconsider engine and story boundaries
  where repeated repairs have not solved the underlying problem.
- The terminals near the observation shaft bog down into boring access and
  typing. Fixing recognition alone would still leave a boring scene.
- Freytag Forge exists to introduce incidents, tension and release at the right
  rate, keeping the story moving.
- Discovery hints still fire after their target has been found. Treat this as
  a first-class continuity defect, not merely a distracting line of prose.

## 1. Product decision: a dramatic adventure with freeform agency

Keep Kristin's search for Michelle, Brandon's compromised allegiance,
Michelle's resistance, the conspiracy and the flood/broadcast climax. Change
how the player experiences them. The game should repeatedly offer a concrete
situation, an understandable opportunity, a meaningful response, and a visible
consequence. Investigation is interesting when it changes a plan or relationship;
accessing one more terminal is not inherently an accomplishment.

Aim initially for a complete 45–75 minute adventure, roughly 35–55 consequential
turns, with room for optional conversation. These are design targets to measure,
not a new forced-ending timer. The current 120-turn ceiling must not become a
content quota. Keep a bounded, mostly reconverging plot; do not build an open
world or an exponentially branching novel to solve pacing.

Define the recurring dramatic rhythm:

1. **Disruption:** something changes that matters to Kristin now.
2. **Opportunity:** the player can see what can be attempted and what is at risk.
3. **Response:** accept freeform action, including a plausible unexpected approach.
4. **Consequence:** resolve the attempt, change facts, and show what changed.
5. **Release or reversal:** close the immediate uncertainty; allow reaction or
   introduce a new complication with a different demand.

A tense scene need not be relentless. The reunion needs emotional room. A
successful escape needs a clear arrival. Constant warnings, withheld reveals,
and repeated requests to finish a completed task destroy both tension and release.

## 2. Evidence and diagnosis

Read together: the [PRD](../docs/PRD.md), contributor, grounding, scene-fixing,
player-input, narrator-writing and workflow guides; the seven current package
sources; the completion matrix; and the recent 3C experiment record.

| Evidence | What it supports | What it does not prove |
| --- | --- | --- |
| Older Stage 7 run: 84 turns, 30 harness-labelled stuck turns; 2B forced after an invented access obstacle | Ended is an inadequate quality metric; preceding narration can poison the next scene | A current failure rate; later package repairs exist |
| Completion plan: discovery cue defect reproduced offline; reported original transcript unavailable | Cue lifecycle needs regression coverage independent of reveal matching | Every reported stale cue has the same cause |
| Completion matrix and N-1/N-2 repairs | Alternative revelations can complete a storylet yet fail downstream bridge assumptions | All current alternatives are broken |
| October 22 post-C screen: control 1/12 earned exits, families cue 5/12; persistent tunnel loops and late E delivery | A useful wording improvement still leaves structural completion and pacing problems | Whole-game success rates; starts were synthetic |
| Same screen: undeclared phone used for calls/documents | An offered activity can lack the physical support needed to perform it | A phone-specific narrator prohibition would fix grounding |
| Current 1C/2A/2B content repeatedly uses records, credentials, terminals and files | There is a repetitive interaction-design problem even when state works | More dramatic prose alone will make it fun |

Source inspection: `RuntimeEngine._turn_active` coordinates proposal validation,
world capture, repeated pacing activation, canonical events, transitions, cues
and deadline resolution. `_apply_authored_transition` checks triggers, minimum
turns and dependency availability, then appends bridge and entry text.
`CanonicalEventMixin._apply_canonical_route_events` iterates eligible events and
applies world effects. These are useful existing mechanisms, but their combined
ordering deserves an explicit transaction contract. This is a design hypothesis,
not a claim that the entire engine is defective.

The central mismatch is responsibility: the model is asked to make prose feel
continuous while several mechanisms independently decide what is complete,
where people are, what is offered next, and when the scene must end. Improve the
contracts before adding more negative prompt rules.

## 3. Keep, revise, and deliberately leave out

| Decision | Rationale |
| --- | --- |
| Keep facts as sole mutable truth, immutable packages, typed proposals, knowledge/speaker guards, rollback and package-bound saves | These make failures diagnosable and prevent narration from becoming a second reality |
| Keep Python 3.12, FastAPI, React, Cloudflare narration and a thin hosted adapter | Hosting replacement does not solve dramatic design |
| Keep freeform LLM interpretation with bounded, validated consequences | Preserve creative approaches; do not turn the game into a fixed verb parser |
| Keep worldkeeper's containment tree for custody and nesting | A useful foundation; replacing it wholesale adds migration risk |
| Add explicit traversable connections alongside containment | Being inside the same facility does not establish a route, access, or arrival |
| Revise scene, storylet, cue and transition lifecycle | Completion and retirement must be machine-checkable, not implied by wording |
| Revise pacing around dramatic events and consequences | Turn ceilings alone cannot distinguish suspense from repetition |
| Consolidate authored intent before generating runtime projections | Seven co-equal files currently make one dramatic change expensive to coordinate |
| Preserve tested reveal handoffs during migration | They deliver essential meaning reliably; do not discard working protection mechanisms |
| Defer a universal planner, autonomous NPC simulation, full map UI and model replacement | None is required to demonstrate a fun, resilient first game |

This user request authorizes reconsidering the design. Earlier plans' parked
redesign proposals are evidence, not a prohibition on planning. Implementation
must explicitly update any changed PRD/authoring contracts; it must not quietly
relax guards, expand model budgets, or change production defaults.

## 4. Reimagine the playable content

The following are proposed story changes, not current canon. Make changes in
`plot.md` first, then update the affected declarations together. Retain scene IDs
through the first slice; merge scenes only after the revised structure proves
useful. Do not require every existing storylet to survive.

**Whole-story evaluation (2026-10-31).** The canon is strong; the delivery is not.
Six of the first seven scenes climax on reading a document, every scene opens at
rest, the antagonists stay offstage until 3B, Michelle is only a rumour until 3A,
choices barely carry, and the climax is crowded while Act 2 is flat. The fix
follows five rules for every scene: open in motion, one hands-on set piece, a
person in the way, one carried choice per act, and release before the next blow.
Detail: [whole-story-pacing.md](game-reimagination/whole-story-pacing.md).

**Speed constraint.** The game must ship quickly. The redesign reuses only tested
mechanisms (the 1C incident contract, `entry_variants`, bridge text, declared
items), mostly cuts and reorders, adds one NPC, and leaves 1A and 1B untouched.

| Scene | Revised player experience | Size of change |
| --- | --- | --- |
| 1A, 1B | Unchanged; they work | None |
| 1C | Shipped Phase 1 incident | Close the neutral-staller gap |
| 2A: The Real Leak | Open at the gate; the supervisor says "Show me" and the cooling fault is real, so Kristin's expertise, not credentials, gets them in; a camera turns toward Brandon | One incident; cut hideout, cover-building and travel storylets |
| 2B: The Audit | Kristin's own file says RETAINED to lead them to Corfman, and the build record names Brandon; she confronts him in whispers in the stacks as an audit passes; he asks to erase his name; then Michelle answers through the medical terminal | One incident; three storylets merge into one discovery, one choice, one live reply |
| 2C: Rebecca | Rebecca corners them in person; the purge order lands on her own tablet; Brandon's "yes" frees them; Kristin commits to transmit or rescue by acting, then Michelle's route widens the options without erasing that commitment | One incident; drop the open-ended argument storylet |
| 3A | Unhurried reunion turn, then Kristin gives the uprising signal on the radio | Entry text plus one variant |
| 3B | Brandon's goodbye reflects the 2B name choice | One entry variant |
| 3C | Finite broadcast, archive and barrier episodes; aftermath arrives at dawn | Phase 2 scope, unchanged |

Three ledger facts carry choices forward: the 1C outcome (existing), 2B
`brandon_name_kept`/`brandon_name_erased`, and 2C
`committed_to_transmit`/`committed_to_rescue`. Act 2 detail, outcomes and cuts:
[act2-redesign.md](game-reimagination/act2-redesign.md). Approve the direction
first; then one ChatGPT Desktop prompt writes 2A to 2C into `plot.md` and the
change propagates from there.

### First slice: replace terminal administration with an incident

Use the existing freight-terminal/observation-shaft material. Before adding any
physical affordance, declare its entity, placement, access and visibility under
the grounding guide. The following actions are design examples, not claims that
all are currently supported:

- `Study the prisoners moving beneath the observation shaft.` gives the essential
  confirmation that the missing are alive. Do not hide this obvious observation
  behind credentials, a particular file name, or several successful queries.
- `Copy the prisoner numbers.` secures stronger corroboration while transfers
  continue. A successful action resolves in one consequence, not a sequence of
  login, search, access and download turns.
- `Ask Brandon about the transfer route.` can exploit his knowledge, reveal his
  evasiveness and affect the approach to infiltration.

Offer a bounded choice between stronger evidence and a more immediate lead
under the moving-transfer pressure. Exact costs and routes are authored during
Phase 0. Both supported choices must reach the next dramatic situation; neither
may secretly require the other's information. Watching an ambiguous figure who
resembles Michelle can provide a personal reversal without declaring her identity.

A terminal may remain as a tool if it serves an interesting decision. Collapse
routine access into the resolved action. A denial must introduce a credible new
situation or alternative; it cannot invite endless retries. Let Brandon handle
routine technical work when the story establishes he can, with completion
represented by a validated event rather than repeated narrated typing.

Carry the choice into 2A/2B and the ending: corroboration can strengthen the
public case; route knowledge can improve the approach. Avoid an arbitrary
points meter. Use a small number of named, observable consequences.

### Make the ending an ending

Conclude the rescue from rescue facts, location and an explicit evacuation
completion event. Stop inviting another trip down the same tunnel. Then enter a
short aftermath whose communications source and participants are physically
established. Reports and the families' response should arrive because the
broadcast and rescue happened, not because the player guessed another command.

Make the Phase Two reveal an optional sequel hook or an earned aftermath
revelation, not the latch that decides whether this rescue counts as finished.
Resolve Michelle's survival, the captives, the evidence, Rebecca and Brandon's
known status before teasing Charles's future threat. Where Brandon's fate is
intentionally unknown, say so clearly rather than implying a rescue never made.
Support a small set of authored outcome variants based on rescue and evidence;
never award the best outcome through a deadline backstop.

## 5. A small dramatic director, not a second storyteller

The director selects eligible authored incidents and opportunities. It does not
invent goals, secretly choose player actions, or mutate a parallel narrative
state. All persistent lifecycle and pressure values are facts; projections are
rebuildable views.

Each dramatic unit declares:

- entry situation and objective;
- the uncertainty at stake and available opportunities;
- permitted outcomes, costs and protected information;
- completion, failure and retirement predicates;
- pressure events, release opportunity and valid successors;
- what the player must visibly learn when an outcome occurs.

Select incidents using transparent rules: causal eligibility first, then
unresolved scene purpose, then authored priority. Preserve optional exploration;
finish a fulfilled scene without waiting for a minimum-turn quota. A quiet
reaction need not earn a reveal to be worthwhile.

Advance pressure on relevant accepted actions or declared world events.
Clarification, rejected proposals and transport retries do not burn the player's
window. After a major reversal, allow an authored release before another
nonessential escalation. Deadlines resolve a threat with an honest cost, escape
or failure variant; they do not silently supply unearned achievements.

If two consecutive substantive attempts leave the same objective and obstacle
unchanged, inspect outcome provenance. Offer a grounded clarification, an
established alternative, or a changed incident. Never automatically grant the
missing fact. This threshold is a diagnostic/design starting point, to calibrate
with human play, not a universal definition of boredom.

## 6. Continuity contracts

### Discovery and cues: one lifecycle, checked at display time

Give every cue a typed purpose and target, with `eligible_when` and
`obsolete_when` predicates. Distinguish finding an item, possessing it, reading
it, and learning its contents. A discovery cue retires on discovery even if the
player subsequently drops the item. A retrieval opportunity may then exist,
but must describe the actual current custody.

Use an explicit acquisition outcome that atomically records discovery and the
physical move. Do not infer arbitrary story facts backwards from all world
moves. Preserve the current one-way fact effects, with a validated binding for
supported acquisition outcomes. Model-only claims of finding something remain
uncommitted and cannot justify downstream progress.

Check eligibility when selecting a cue **and again against the final projected
state immediately before assembling visible segments**. Apply this to queued
cues, escalation text, active storylets, handoffs, scene details and recall—not
only the next selection. A stale cue is omitted by its identity and predicates,
never by scanning prose for the item's name. Completion and cancellation are
idempotent and survive save/load. Event identity prevents duplicate deliveries.

Acceptance sequences include find → inspect → move → save/load → revisit;
find via an alternative realization; find and leave on the same turn; acquire
then drop; a rejected discovery; and a deadline coinciding with acquisition.
After finding the card, no output may imply it still needs to be found. A later
invitation to read it must acknowledge its known location and discovery.

### Topology and travel

Keep containment and add package-declared connections between places, including
access predicates, destination, traversal consequence and arrival text. Store
mutable access as facts. A route is not a new mutable graph service.

Resolve a legal short traversal to a definite arrival in one action. A longer
journey needs a finite authored obstacle or montage, never an indefinitely
regenerated corridor. Prevent unrelated known entities from resolving as local
destinations. Unknown consequential doors, devices and routes cannot silently
become progression requirements; require grounded resolution or clarification.
Permit harmless descriptive invention without letting it alter topology.

### Scene handoff

Represent each handoff as a validated transaction: source completion, route,
party/custody changes, destination entry conditions, retired opportunities,
newly eligible opportunities and visible bridge/arrival. Preserve carried items
and existing NPC state; entry placements are explicit initializations or
intentional moves, not unconditional resets on every visit.

Validate all of this before exposing the response. A turn cannot leave the
player in the destination while its final cue still asks for a source-scene
activity. Backtracking must have a declared route and visit behavior; otherwise
make the boundary clear in fiction.

### One accepted outcome and one commit

Converge on: current facts → grounded opportunities → untrusted proposal →
validated outcome and effects → projected events/travel/retirement → validated
visible response → atomic commit and response publication.

First unify transaction ordering using the existing proposal/reveal mechanisms.
Do not immediately add a separate planning model or narration request. Keep the
current call budgets. If a one-reply proposal and prose disagree, use the
existing bounded recovery or an explicitly authored outcome segment; never
silently accept contradictory prose or fabricate model success.

An outcome-first provider split remains a bounded experiment only if the slice
shows the existing protocol cannot meet the contract. Measure latency, spend,
prose consistency and held-out play before adopting it. Preserve under-ten-second
normal-path target; record tail latency separately.

## 7. Authoring that can be finished

Prototype a co-located dramatic-unit declaration containing prerequisites,
opportunities, outcomes, delivery, retirement and successor rules. Keep reusable
world entities separate. Compile into the current immutable package initially;
do not hand-maintain old and new declarations as competing authorities.

Start with a mapping document for the slice, then add schema only for fields the
slice needs. Do not replace all seven source formats in the first change. Retain
`plot.md` as narrative canon during migration, explicitly identifying which
fields the compiler owns. If co-location increases duplication, stop and improve
validation instead.

Compiler checks should reject dangling targets, contradictory completion and
exit conditions, an alternative that strands progress, incompatible placements,
required but unobservable information, cues lacking retirement, and missing
physical support for mandatory interactions. Bounded graph exploration can show
reachability of declared outcomes; it cannot prove that freeform play is fun.

Optional storylets must be genuinely optional. Required dramatic outcomes get
explicit ownership instead of hiding inside a pool labelled optional. Cut a
storylet if it only repeats information, adds administration, or exists to make a
counter advance. Keep ones that change trust, tactics, risk or emotional meaning.

## 8. Delivery phases and stopping rules

| Phase | Work and output | Exit criterion |
| --- | --- | --- |
| 0. Design baseline | Catalogue current 1C opportunities and all cue emitters; tag keep/merge/cut across nine scenes; draft revised 1C incident, two outcomes, successors and payoff | One reviewable scene contract; exact terminal repetition and stale-cue cases captured from available evidence; unknowns labelled |
| 1. Playable slice | Implement 1C plus its 1B arrival and 2A handoff; cue lifecycle fix; minimum outcome/travel contracts; preserve old package version | Both approaches finish coherently, costs persist, discovery cues retire, and strangers can play without being coached through terminal syntax |
| 2. Prove portability and finale | Exercise same contracts in the unrelated lighthouse fixture; implement finite 3B→3C evacuation→aftermath crossing | No story-specific engine branches; an earned rescue ends visibly; no return-to-chamber exposition scavenger hunt |
| 3. Migrate the adventure | Rewrite remaining content in dramatic order, remove redundant storylets and superseded cue paths, audit all declared alternatives | Complete game with every supported outcome reachable and its downstream consequences visible |
| 4. Qualify and deliver | Whole-game human and raw-language runs, staging verification, release notes and rollback artifact | Gameplay gates below pass on the intended package/model configuration; staged SHA is eligible for production promotion |

### Test-suite consolidation: where it fits

The [test-suite consolidation plan](test-suite-consolidation-plan.md) is a separate effort that
only touches this one at the frozen set (its section 2f: 21 files owned by Phase 1, including
the slowest journeys). Schedule, decided 2026-10-24:

- **Now to Phase 2:** its Phases 0 to 3 continue on everything outside the frozen set. Phase 1
  step 7 is done, so the freeze is technically lifted, but Phase 1 changed several frozen files,
  so redo its evidence for them before deleting anything.
- **Leave the frozen journeys until Phase 3 lands.** Phase 3 rewrites the remaining content and
  removes superseded cue paths, which changes those journeys again. Consolidation Phase 4
  (frozen set) runs right after Phase 3.
- **Consolidation Phase 5 (regenerate `tests/shard_durations.json`, shard balance, two green CI
  runs on `main`) runs before Phase 4 here,** so staging qualification starts from a balanced,
  faster suite.
- New tests added by this plan follow the consolidation rule: add one only when it gives complete,
  useful coverage; the suite is already too big.

Use one bounded implementation cycle per phase with a recorded result before
expanding scope. If Phase 1 needs repeated wording patches for the same symptom,
stop after two unsuccessful iterations and revisit the contract or cut the
interaction. Do not rename an unsuccessful experiment and restart it.

If engine work threatens delivery, reduce mandatory interactions and branches
first, using authored transitions and consequences within the same contracts.
Do not maintain two permanent runtimes. Do not defer the ending until every
optional storylet is polished. Delete obsolete machinery only after equivalent
boundaries are covered and the replacement slice passes.

## 9. Evidence that counts as success

Keep deterministic correctness, model reliability and human enjoyment separate.
Follow the existing [testing runbook](../docs/testing-runbook.md); update its
procedures only when implementation introduces a new verification boundary.

- **Deterministic:** atomic rollback and save/load; topology and custody;
  discovery/cue lifecycle sequences; alternative paths and downstream effects;
  disclosure audiences; duplicate submission; deadlines versus earned outcomes.
  Run on the real package and an unrelated synthetic package. Preserve the
  project coverage gate and appropriate frontend/build checks.
- **Model:** matched starts followed by carried histories through actual scene
  crossings. Include raw language, unusual valid approaches and clarification.
  Score the complete player-visible response and committed state. Preserve
  malformed and failed attempts; never pool synthetic starts into whole-game
  results. Freeze budgets, model settings and stopping rules before billed runs.
- **Human:** five fresh players for the slice, then five for the full adventure.
  Seek at least four of five able to explain their goal, consequence and next
  opportunity without coaching; at least four of five wanting to continue the
  slice and judging the ending satisfying. These are small product gates, not
  statistical reliability claims. Record where attention drops, not just ratings.

Release targets: no known stale discovery cues, impossible handoffs, silent
custody resets, missing mandatory disclosures or false successful endings in
the qualification set; at least 90% earned completion in a preregistered batch
of 20 full-game raw-player runs; no repeated mandatory terminal-access chain;
no unresolved three-turn movement loop in an otherwise successful run. Track
meaningful consequences, voluntary exploration, tension/release beats, latency
and cost. Do not optimize reveal count or interpret all non-reveal turns as waste.

The numerical targets are proposed acceptance gates, not existing results. If
they fail, inspect failures and narrow scope; do not lower them to bless the
current build. Human enjoyment remains necessary even with perfect completion.

## 10. Migration, release and current limits

Version new package semantics. Keep old saves pinned to their original package
or explicitly reject incompatible loads with a restart explanation; never
reinterpret an old snapshot under new scene rules. Keep an immutable baseline
and a reversible feature/package selection during the slice, with no default
switch until it qualifies. Remove the temporary compatibility path when the
migration is complete.

Use [the production promotion guide](../docs/railway-production-promotion.md):
implementation merges, SHA-bound staging deployment, staged E2E and review,
then production promotion. Keep deployment identity and hosting boundaries;
this plan does not require an infrastructure migration.

Current work completed: repository and evidence review, recommended design,
content direction, phased implementation and proposed acceptance gates.
Unverified: the proposed contracts, player enjoyment, model reliability, timing
and cost. No tests or live model runs were performed for this documentation-only
plan. The present user reports of terminal boredom and stale hints are product
requirements; the full set of their triggering transcripts is not yet captured.
