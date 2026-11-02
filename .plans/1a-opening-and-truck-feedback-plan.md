# Scene 1A: opening prose, emotional grounding, and truck continuity

Status (corrected): in progress, 2026-11-02; plan revised for Brandon's five rulings.
Step 1 baseline capture is done; targeted diagnosis continues below. Step 2 edits are applied (plot.md,
knowledge.yaml, world.yaml, `7794e4b9`) but only partly effective: the kitchen is
named in 9 of 9 openings; layout, KMS as new and strange, and a specific reaction
are not shown, and emotional responsiveness on later turns is not started. Step 3
has one runtime change (`e41878c3`): seated and parked on the boarding turn, with a
side effect noted in the Completion record; surroundings, repeated boarding and
custody are open. Step 4 replicates ran once (`9abc76fb`) and failed several rows.
Source baseline: `8da801206ca5e1708b0bce72e2c63e449cd3aae4`. This revision changes
the plan only; implementation, new billed calls and deployment have not run.

## Resume here

**Corrected:** Step 4's first live replicates are done (`replicates-prereg.md`, Result; commit `9abc76fb`):
the truck turn is right in 9 of 9, the drawer and gap in 9 of 9, the park transition
in 3 of 3, and the opening names the kitchen in 9 of 9. Still failing the acceptance
table: (1) repeated "get in the truck" while seated writes an exit in 6 of 6 and
committed it in 2; (2) invented glove-compartment handling contradicts where the
card and laptop are on the plug, take and re-board turns (Brandon: picking the laptop
up when she gets in is fine; falsely sourcing either item from the glove compartment
is a custody/parent contradiction and fails); (3) the opening omits the layout
and does not convey the two new situation sentences (layout 0 of 9, KMS new or strange
0 of 9, specific reaction 0 of 9); (4) no reaction to Michelle's warning; (5)
surroundings on the boarding turn (known gap). Next, per the scene-fixing guide
(step 1 first, no new arm sweep): finish tracing the recorded failure through the
current implementation, then prepare the smallest repair for each boundary below.
The representative raw-route opening, boarding, repeat-boarding and plug prompts
have now been read beside the plot: opening layout is absent from the narrator
payload, exterior material is present but omitted in prose, and the plug prompt
requests only a lead-up to the warning. Do not treat those as the same cause.
Already-aboard feedback is now engine-owned (2026-11-02, uncommitted, see Completion record); next address the visible parent-area projection, custody, opening
layout and correctly ordered emotional response. Full suite, save/load
persistence and staging are still to do. Fixes stay generic: no command lists, no
story names in the runtime.

The user's current instruction supersedes the older continuity plan's
approach-only expectation: **“head out to the truck” should seat Kristin in
the driver's seat and describe her surroundings.** It must not start the
engine, drive, cross the gate, or return her to the house. A subsequent
“get in the truck” while seated must preserve that position.

## Scope and decision boundary

**Corrected:** Prefer local story/prompt-material corrections, then narrowly scoped repairs
to existing shared behavior if evidence requires them. Keep environmental
prose LLM-written, following the existing environment-narration direction.
Do not substitute fixed environmental boarding descriptions or hardcode
Kristin/truck commands in the runtime. Facts remain the only mutable truth.
Ruling 1 explicitly requires brief engine/harness feedback for a redundant
boarding action, such as “You're already in the truck.” This reverses the
already-aboard delegation in `289e2575`, not the requirement for LLM-written
kitchen, cab and exterior prose. Interpret intent through the existing proposal
path; resolve the already-aboard result against facts before movement/narration.
Do not implement a literal-command shortcut or globally suppress compound actions.

**New — rulings 2–5:** The truck remains a child of `outside_house`; the seat
remains a child of the truck. Its windows allow a view of that parent area while
Kristin stays seated. Visibility is not reach, and parenthood alone must not make
all containers transparent. A glove compartment and harmless contents may exist;
the card and laptop cannot be retrieved from it unless their actual parents put
them there. Kitchen narration and specific emotional reactions are required,
not optional polish. Do not weaken these requirements to preserve earlier scores.

Preserve the KMS clue, hidden-card recovery, laptop interpretation, patrol
pressure and witnessed-recovery consequences, and the earned park lead.
Keep scene/knowledge/entity IDs, reveal effects, transition prerequisites,
deadlines, and later plot connections intact unless a demonstrated defect
requires a small mechanical correction. Do not solve prose misses by
automatically earning a reveal or advancing a scene.

**Scoring policy (corrected; Brandon, 2026-11-02):** invented details are acceptable
unless they affect the main storyline. In probe criteria, "nothing invented"
fails an arm only for a contradiction of canon or state, a pre-empted or revealed
beat (patrol arrival, hidden card), or a collision with story names (a neighbor
called Jenkins). An open laptop at the workstation while it is in the truck also
fails (Brandon confirmed both examples on 2026-11-02). Atmosphere such as a
passing police car is recorded for information and does not fail an arm. Probes 1
to 3 were scored under the stricter rule; re-scoring under this policy changes no
adoption decision. In particular, harmless glove-compartment scenery passes;
false card/laptop provenance fails even if the final JSON leaves them held.
Picking up the laptop on boarding remains allowed, with its accepted movement
reflected in facts. This permission does not license early card interpretation.

**Permission checkpoint:** if the smallest viable fix requires an engine
redesign or changes to plot connections with cascading consequences, stop
before implementing that change. Present the concrete proposed diff/design,
affected scenes and dependencies, evidence that narrower fixes failed, and
the alternatives; obtain the user's permission. Routine local repairs do
not need this checkpoint. This planning request does not authorize execution
of the implementation or paid experiments.

## Evidence checked and limits

**New — revision evidence:** Read all four probe Result sections and the
replicate preregistration/Result, inspected local replicate rows (including the
smoke), and read representative full raw-route prompts and pre/post parents.
Reviewed `e41878c3`, `7794e4b9`, `9abc76fb`, the earlier continuity/environment
plans and `289e2575`. Opening history includes `d09db551` (removed a recurring
arrival/unsearched frame that caused scene restarts), `35d490fa` (late-night
shift and arrival), `271541dc` (entry sentence) and `7794e4b9` (kitchen start).
The old frame mentioned the kitchen floor, but this does not establish the
exact commit that lost a once-good generated kitchen description. Restore
grounded opening coverage without restoring stale arrival prose on every turn.
The following original evidence table describes the original baseline, not
today's kitchen placement.

Read the PRD; contributor/runtime/interaction boundaries; agent workflow;
scene-fixing, grounding, player-input and narrator-writing guides; testing
runbook and its local/prompt-inspection entries; promotion guide; previous
1A continuity plan; current environment-narration plan's status and evidence;
and historical W1–W14 with amendments in `5ea0119955c62b84699a8dc7878a4af770b55a7e`.
Inspected current 1A/1B plot, relevant world/knowledge/storylet declarations,
and indexed `board_vehicle` implementation. Serena is not available in this
session; code discovery used codebase-memory-mcp. No session trace or deployed
model/configuration accompanied the transcript, so causes below are leads,
not a reproduced diagnosis.

| Finding | Implication |
| --- | --- |
| `plot.md` 1A entry ends with entering the forced back door; 1A has no explicit protagonist placement. The declared kitchen holds the workstation and back door. | Check whether opening state defaults to the whole house and whether the opening receives usable kitchen material. Use the existing kitchen rather than inventing rooms. |
| Beat 1A.1 and `knowledge.yaml` scene frame already say KMS is newly carved. The plot establishes Michelle as Kristin's best friend. | Preserve this meaning; investigate why the opening loses novelty and personal significance. No new backstory or puzzle is necessary. |
| `world.yaml` already declares driver/passenger seats; 1A places the laptop on the passenger seat and truck outside. | Repair projection, interpretation, or reach only where the trace shows a defect. Do not create a separate cab/location subsystem. |
| `board_vehicle` already handles boarding and an already-aboard case through model questions and existing seat movement. | Inspect its answers and command-consumption path before adding any new mechanism. Correct seating facts alone do not prove correct narration. |
| 1A.1 recounts arrival; the park bridge explicitly starts the truck; 1A.2 includes taking the card out to the truck. | Check whether historical arrival, future departure, or preparatory travel is being presented as a current instruction. The exact source of the repeated driving remains unknown. |
| Prior boarding probes lost with extra rules; supplying concrete material helped other scene repairs. Existing environment-narration work has verifier/configuration limits. | Reuse supported projection/observation paths and measure prose. Do not assume an available verifier is enabled or catches invented driving. |

## Implementation sequence

### 1. Reproduce and separate prose failures from state failures

- [x] (2026-11-02: cause found, see Completion record) **New:** Finish targeted trace of already-aboard handling, early standing,
  observation command consumption and item-fact commit using the saved failures.
  Distinguish the six narrated exits from the two committed exits; preserving
  JSON alone does not satisfy ruling 1. Read the other failing route prompts
  before selecting a repair. **Billed calls: 0**; reuse saved rows and stubs.
- [~] Preserve the supplied opening and responses (the raw inputs were replayed; the pasted responses were not available to this session) as the reported evidence,
  with the exact raw inputs: `open the drawer`, `feel in the gap`,
  `head out to the truck`, `look for the laptop`, `get in the truck`,
  `plug the memory card into the laptop`. Label this a raw-language regression;
  new probes use canonical imperative inputs and `my laptop` where appropriate.
- [x] Reuse the current 1A harness and prompt-capture support. Capture the
  opening and each turn's full system/user prompts, original versus effective
  action, boarding/standing answers, observations, selected reveal, appended
  delivery, fired events, and pre/post facts. Include protagonist/vehicle/item
  parents, custody, hidden state, scene, and package/code/configuration identity.
  Stubbed output diagnoses wiring, not live writing quality.
- [x] Read each prompt beside plot.md. Distinguish missing room/relationship
  material, material present but ignored, wrong movement proposals, and correct
  state contradicted by prose. Trace the opening path separately from turns.
  Inspect saved live evidence first; do not launch a broad benchmark to rediscover
  a failure already captured.
- [x] Record a short causal table and proposed changed lines before editing (table below; changed lines for the boarding fix were in the Ringer spec).

### 2. Repair the opening and its emotional meaning at the source

- [ ] **New:** Compare the historical opening sources with the actual opening
  payload. The saved raw opening THINGS contains only Kristin; neither the
  workstation's “across the kitchen” placement nor the chair is supplied there.
  Repair opening projection/scope before asking the narrator to obey missing
  layout. Keep placement truths fact-derived and story-agnostic in shared code;
  preserve the current kitchen start. Do not simply append more situation rules.
- [x] (kitchen start applied via `character_placements`; effect verified live) Start story edits in `data/stories/continuity-initiative/plot.md`, then
  synchronize only affected world, scene-frame, storylet and knowledge material.
  Give Kristin an explicit kitchen starting placement if the capture confirms
  the current house-level default. Verify scope/reach changes this causes.
- [~] **Corrected:** (kitchen named 9 of 9; layout authored but absent from the
  inspected opening payload; layout shown 0 of 9) Supply a compact, grounded view: name the kitchen, establish where the
  existing workstation/chair and damaged back door are relative to her, and
  show enough layout to orient the player. Use existing objects; any added
  actionable physical detail must be declared and placed. Avoid a decorative
  inventory that creates unnecessary dependencies.
- [~] (sentence supplied; a specific reaction shown 0 of 9) Supply the personal significance of the scene: this is her best friend's
  familiar home, now disturbingly quiet and disrupted. The opening should show
  a concrete reaction to Michelle's absence and the damage, rather than a
  generic “eyes scanning” summary. Do not invent shared-history episodes,
  assert Michelle's fate, or make choices for Kristin.
- [~] ("Kristin did not carve them" supplied; new or strange shown 0 of 9) Keep KMS newly carved. Make recognition and abnormality legible: these
  are Kristin's initials on Michelle's furniture, a fresh deliberate mark
  that draws her attention. Treat its intended recipient as a reasonable
  suspicion, not proof of who carved it or what lies underneath. Preserve the
  search/recovery gate and avoid revealing the hidden card in the opening.
- [x] (only the phrase "into the kitchen" was added) Preserve the first paragraph's established events. Improve the generated
  second paragraph through appropriate opening material, not by padding the
  fixed preamble or making every turn repeat the opening description.
- [ ] **Corrected:** Carry emotional responsiveness into consequential turns, especially
  recovery and hearing Michelle's warning, using only then-available context.
  Keep reactions brief and specific; do not require an emotion sentence on
  every mechanical action or create an emotion-state subsystem. Ruling 5 makes
  this an acceptance requirement. The plug prompt currently says “Write only
  what leads up to it” before an appended warning: do not ask that lead-up to
  react to unheard words. Prefer a brief authored reaction after the warning in
  its earned delivery, using the existing handoff mechanism and prose workflow.
  Preserve its facts, gate and lead. If a generic composition change is needed,
  prove why the existing handoff cannot cover it; do not add a second narration
  call or expose the warning before it is earned.
- [ ] **New — billed calls:** For one supported opening-material correction,
  use 12 unchanged-control + 12 candidate calls = **24**. For one earned-warning
  composition correction, use 12 + 12 = **24**. Step 2's proposed budget is
  **48 narrator calls**, no retries or uncounted smoke; approve exact payloads
  and cost in a preregistration before running. Source inspection is free.

### 3. Separate boarding from driving and preserve seated interaction

- [x] (2026-11-02, uncommitted; Brandon chose: clock untouched) **New — ruling 1:** Check the committed seat/vehicle relation before any
  leave-seat step or narrator request can reinterpret redundant boarding. For
  a pure boarding intent targeting the occupied vehicle, consume that action
  and return generic engine/harness “already aboard” feedback. Do not invoke
  the narrator to decide or rewrite that result; preserve seat, vehicle parent,
  scene and custody. Keep ordinary pacing semantics and independent event
  delivery intact. Compound actions retain their other requested acts; explicit
  exit, seat change or drive must still work. Resolve ambiguous targets through
  the existing intent/reference path. World-only checks belong in `World`;
  storygame owns intent adaptation and feedback rendering. Test the actual
  product observation path, not only a legacy engine-text switch.
- [x] Trace `storygame/runtime/seating.py`, the model questions it uses,
  `CloudflareTurnProvider` prompt construction, observation projection, and
  proposal/commit handling for the exact route. Retain the player's intent
  when preparatory steps are supplied; do not let a consumed boarding command
  become an invitation to improvise travel.
- [ ] **Corrected:** Correct any misleading arrival/departure or stale place material at its
  source/scope. Boarding ends with Kristin seated in the parked truck, the
  laptop visible at its current location, and grounded cab/exterior surroundings.
  It leaves the vehicle's parent and scene unchanged. Driving requires a
  separate explicit driving/departure command; an explicitly compound command
  may still request both actions. Derive the exterior from the truck's actual
  parent and the supported window/view semantics, not from a hardcoded scene.
  Read existing view/projection support first. If declarations cannot express
  it, document that specific gap before proposing a minimal generic extension;
  do not build a separate cab/location subsystem. Describe useful cab context
  and the visible outside area in the same boarding response. The saved prompt
  already contains the house/gate/curb description, so missing exterior prose
  is not evidence that those source facts are absent. Never grant exterior
  reach or visibility through an opaque enclosure just because it has a parent.
- [ ] **Corrected:** For `Look for my laptop.`, show its current place or holder. Finding it does
  not require retrieving it, exiting, or reopening the passenger door.
  Repeated boarding gets the engine-owned result above, rather than another
  narrated attempt; ordinary pacing may still advance according to existing rules.
- [ ] **Corrected:** For card/laptop use while seated, project both seats' shared vehicle
  context and available reach. Permit reaching across from the driver's seat.
  Keep Kristin seated; do not trigger a leave-seat step, move the laptop outside,
  or reset its custody/placement. If she actually moved it earlier, respect
  its current place rather than forcing it back onto the passenger seat.
  Picking it up on boarding is allowed. In the recorded plug failure both items
  are explicitly held in THINGS, yet prose retrieves the card from a glove
  compartment; this is a contradiction of supplied facts, not harmless invention
  or merely missing placement. Diagnose proposal validation and prose separately.
  Do not ban glove compartments, create one as these items' parent to excuse
  bad prose, or add a transcript-specific glove-compartment rule.
- [ ] If a world-state-only defect is proven, implement the smallest generic
  `World` method repair in `packages/worldkeeper`, with tests there; storygame
  adapts and calls it. Use existing proposal validation and atomic rollback.
  Do not implement action keyword tables, a second location store, or a blanket
  rule that all objects in the scene are reachable.
- [ ] Add a narrator instruction only if a controlled prompt probe shows it
  improves the relevant failure. Follow narrator-writing guidance and apply
  shared behavior consistently across opening, turn, section and recovery paths.
- [ ] **New — billed calls:** Already-aboard routing and state tests require
  **0 billed calls**; any live intent calls are counted in step 4's route budget.
  One supported exterior-view candidate costs 12 control + 12 candidate = **24
  narrator calls**; one custody candidate costs another **24**. Step 3's proposed
  prompt budget is **48 calls**. Do not repeat the losing neutral-action arms
  or classifier rewording without new causal evidence. Any additional arm needs
  its own count and approved preregistration.

### 4. Verify narrowly, then check the plot connections

- [ ] Add meaningful failing deterministic tests for any repaired state,
  projection or selection boundary; reuse existing suites. Do not encode
  subjective writing quality as exact wording or a paragraph word count.
- [ ] Diff stubbed narrator payloads before/after. Keep unrelated scene
  payloads byte-identical unless a shared fix necessarily changes them; list
  and justify each difference. Check no protected reveal becomes visible early.
- [ ] **Corrected:** Prepare separate small preregistrations using captured
  prompts for the supported corrections in steps 2 and 3: unchanged control
  plus one candidate, 12 samples each. These are **96 calls total** if all four
  candidates are justified, not an instruction to launch four arms immediately.
  No paid repeat-boarding prose experiment is needed for the engine-owned result.
  Do not sweep models or stack unmeasured rules.
  Existing plans require approval before billed runs: prepare harness, counts,
  rubric and estimated cost first, then request approval if implementing.
- [ ] **Corrected:** Read every final composed response, including appended handoffs. After
  selecting the smallest winning fix, run three full live replicates of the
  transcript route and a compact countercase route. Score each requirement
  independently; a state-only pass or successful reveal is insufficient.
  Reuse all three existing routes (raw, canonical, counter), three replicates
  each: **9 openings and 63 action turns**. Budget from the measured run, not
  the old 216-call estimate: raw **86**, canonical **89**, counter **129**,
  **304 expected full-run calls**; actual calls vary with routing and recovery.
  Hard caps remain **120/120/160 = 400**. Separate three-turn smoke: **12
  expected calls, cap 25**. Total expected **316**, cap **425**, including
  narrator, matching, intent and recovery calls. Count saved calls from the
  already-aboard bypass rather than promising an exact new total.
  Refresh rubric L before running: remove its obsolete blanket “no automatic
  pickup” clause and require engine-owned repeat-boarding feedback. Score false
  parents independently from allowed pickup; preserve historical raw results.

| Acceptance case | Required result |
| --- | --- |
| Opening — corrected | Narrates the kitchen and understandable workstation/chair/back-door layout, not just its name; shows familiarity and a specific reaction to Michelle's absence or damage; identifies KMS as new and strange; no hidden-card leak, unasked search or repeated arrival. |
| Drawer then gap | Existing opening/search/recovery order still works; card recovered once, with the correct witnessed or unwitnessed consequence. |
| Head out to truck — corrected | Facts place Kristin in the driver's seat and the parked truck under outside_house. LLM prose shows cab/laptop context and the parent exterior visible through the windows while she stays seated; no engine start, driving, gate crossing or return to house. |
| Look for laptop — corrected | Laptop is shown at its actual place or held by Kristin; she stays seated. Picking it up on boarding is permitted and reflected in facts. No invented source container or reset to the passenger seat. |
| Repeat boarding — new | Engine/harness recognizes the occupied vehicle before movement/narration, gives brief “already aboard” feedback and consumes the redundant boarding action. No narrator call for that result, exit/re-entry, seat change or custody change; normal independent pacing events still apply. |
| Plug card into laptop — corrected | Uses the actual available laptop from the driver's seat, reaching across only if needed; preserves actual custody/parents and earned delivery; a specific reaction follows the warning. No retrieval from a glove compartment unless facts actually placed the item there. |
| Harmless invention versus custody — new | A glove compartment and harmless contents are allowed; false provenance of the card/laptop fails even with unchanged final facts. Allowed pickup does not excuse wrong provenance or early reveals. |
| Explicit departure after the lead | Existing park transition remains playable and places the truck correctly in 1B; boarding alone never substitutes for this action. |
| Countercases — corrected | Laptop carried/left elsewhere, compound actions, explicit exit, explicit drive, and observation outside follow actual state. Exit lands at the vehicle's actual exterior parent, not the house. Opaque-enclosure visibility is not implied by parenthood; no global forced seating or remote reach. |
| Persistence and generic behavior | Save/load preserves seat, truck location and custody; a synthetic second vehicle/package exercises any shared repair without story names. |

- [ ] Verify adjacent dependencies: patrol arrival and challenge branches,
  card reveal and warning gates, 1A exit eligibility/deadline fallback, 1B truck
  placement and park lead. If shared prompt/movement code changes, include
  affected non-1A journey tests and another vehicle/seat context. Do not revise
  the later story merely to fit a new opening.
- [ ] Follow `docs/testing-runbook.md`: focused package, projection, seating/
  worldkeeper, narration, pacing and journey checks as applicable; quick tier
  between changes; Ruff and final suite/coverage gates at the end. Confirm
  current test paths and CLI flags before execution. Update runbook entries
  only if procedures change, using the testing-runbook-creator skill then.
- [ ] Preserve the existing implementation workflow (Ringer code tasks,
  tests first and review; existing authored-prose workflow). At release time,
  follow CI and exact-SHA staging requirements, inspect the actual staged
  opening and route, and record limitations. No production promotion is
  included in this plan.
- [ ] **New — billed release verification:** Deterministic dependency and
  save/load checks use **0 calls**. After exact-SHA staging succeeds, the same
  three routes at three replicates require **304 expected calls**, cap **400**,
  plus the smoke (**12**, cap **25**): **316 expected, cap 425**. Recount from
  the final local run and verify hosted instrumentation before approval. Broader
  required staged suites need separate concrete counts in their preregistration;
  they are not silently included in this allowance. No billed call or deployment
  is authorized by this planning revision.

## Completion record

### Step 3 code change 2 (2026-11-02): engine-owned already-aboard reply

Cause of the six narrated exits: `WorldCapture.before_turn` ran `stand_before_leave`
before `board_vehicle`, so a "stand first" answer could move her out of the seat;
`289e2575` also delegated the already-aboard result to the narrator. Brandon ruled
the redundant command leaves the clock untouched, so the reply reuses the
`EngineRefusalTurn` path (snapshot restored, no narrator call, no pacing).
Ringer task `already-aboard-engine-reply` (Luna, high effort; manifest
`scripts/ringer/opening_truck/step3-already-aboard.json`). Changes (uncommitted):
`storygame/runtime/capture.py` (already-aboard pre-check before standing, taking and
seating when `engine_refusal` is on; reply "You're already in <the vehicle>.";
reuses the pre-check answer when facts are unchanged), `storygame/runtime/seating.py`
(`already_aboard_only` keyword on `board_vehicle`), new
`tests/test_already_aboard_engine_reply.py` (includes a synthetic second package),
two existing pins updated (`tests/test_observation_mode.py`,
`tests/test_boarding_already_seated.py`). `engine.py` unchanged. Worker run: 24
scoped tests and Ruff pass. Ringer marked it FAIL only because my check ran two tests
that also fail on the untouched baseline (`tests/test_fixed_refusal.py::
test_real_scene_1a_same_area_is_the_legacy_fixed_scope`, `tests/test_web_demo.py::
test_hosted_adapter_reports_identity_and_serves_a_story_session`: stale kitchen
pins from `7794e4b9`). The worker's full suite showed 3,841 passed and 34 failures,
all stale story/data/prompt pins; they need their own pin-update task. Not yet done:
live confirmation of repeat boarding (counted in step 4's route budget) and the
pin cleanup.

### Step 1, free half (2026-11-02, base `8da80120`): stubbed, product-wired capture

Script and outputs: `.plans/1a-opening-and-truck-feedback/capture.py`,
`capture-boards-yes.json`, `capture-boards-no.json`. It attaches `WorldCapture`
as `web_demo.engine_for` does, with a scripted answerer in place of the model
questions and a stub narrator, so it diagnoses wiring, not writing quality.
A first replay without `WorldCapture` never exercised boarding and is discarded.

| # | Finding (verified in the capture) | Status |
| --- | --- | --- |
| 1 | Opening: Kristin starts at `mcgehee_home` (whole house). The opening prompt has no kitchen, no workstation/back-door layout and no material about Michelle's home beyond the bios. SCENE does say KMS is "newly carved". CONSTRAINTS tell the narrator to show only the opening beat and not to invent. | Cause of missing layout confirmed; lost novelty/emotion needs live prose |
| 2 | If the boarding question answers **no** for the command, nothing moves and the narrator gets the bare command with no truck location in SCENE or THINGS. That is an open invitation to improvise travel. | Wiring confirmed; which answer the live model gives is unknown |
| 3 | `boards_vehicle` instructions contradict themselves: "only says go to the vehicle means the player gets in" versus "not boarding if it only walks over to or approaches". A phrase like "head out to X" sits in the gap. | Lead; needs live answers |
| 4 | If boarding answers **yes**, Kristin is in the driver's seat, the truck stays at `outside_house`, SCENE says she is in the driver's seat outside, and THINGS lists the laptop on the passenger seat. State is right. | Confirmed |
| 5 | In that same turn the PLAYER block still carries the raw movement phrase next to "Already done: Kristin sat down in the driver's seat." A narrator can read "head out" as departing from the seat. | Candidate cause of the driving; needs live probe |
| 6 | Once seated, later turns keep her in the driver's seat (state only; their narrator prompts were not read yet). | State confirmed |
| 7 | Using the laptop from the driver's seat picks it up from the passenger seat (`seat_before_use`, authored `take_text`: "Kristin picked up her laptop."). Four tests in `tests/test_seating.py` pin this. | **Not a defect** (first recorded as one in error, corrected the same day). No change. |

**Corrected historical scope:** At the end of this free half no story or runtime
file had changed and turns 4 to 6 had not been read. Live probe 1 subsequently
used 74 calls plus 5 smoke calls. The later commits and this revision's prompt
inspection supersede those pending statements; see the records below.

### Step 3 code change 1 (2026-11-02): boarding-turn prompt

Ringer task `boarding-turn-prompt` (Luna, high effort, PASS on attempt 1).
`storygame/runtime/item_facts.py` `_player_lines`: a committed boarding turn
(`kind == "enter"` with a completed boarding step) no longer carries the raw
movement phrase. `storygame/runtime/cloudflare.py` `_where_line`: a seated
protagonist whose vehicle holds something else gets a second SCENE bullet
"<name> can reach anything inside <vehicle> from the <seat>." (pronoun-free;
probe 2 used "where she sits"). Tests: `tests/test_boarding_turn_prompt.py` (new,
includes a synthetic second vehicle); two existing pins updated
(`tests/test_boarding.py`, `tests/test_observation_prompt.py`). Stubbed non-boarding
payloads are byte-identical to the baseline `payload-base.json`. Known looseness:
something the protagonist merely holds also counts as "inside the vehicle", so
the bullet can appear when nothing else is on the seats. Live-checked in the
product-wired path by probe 4 arm A: seated, parked, laptop shown, no story-affecting
invention in 20 of 20 (commands 'head out to the truck' and 'go to the truck');
full suite not yet run. Surroundings on that turn remain open (probe 4 arm B: 6 of 10).

### Step 2 (2026-11-02): kitchen start, layout text and opening situation

Approved line by line by Brandon, applied through three Ringer tasks
(`opening-kitchen-start`, `opening-kitchen-start-pins`, `opening-kitchen-name`;
Luna, high effort; the first two reported FAIL on attempt 2 for stale pins and a
check flaw, the third PASS, 620 focused tests). Changes: `plot.md` (a
`character_placements` kitchen start for the protagonist, workstation placement
text "across the kitchen from the back door", entry text ends "let herself into the
kitchen.", scene 1A.1 gains "Kristin knows Michelle would not leave her kitchen like
this." and "Kristin did not carve them."), `knowledge.yaml` (1A situation with the
same two sentences), `world.yaml` (the kitchen's display name is now "Michelle's
kitchen" with aliases "kitchen" and "the kitchen"; a mechanical correction found
by the payload check, because the opening line is built from the start place's name
and read "The scene takes place at kitchen."). Tests: new
`tests/test_1a_kitchen_start.py`; pins updated in eight existing tests and one
recorded-prompt fixture (display name, text, schema hash). The 1A stubbed payload
diff has 12 changed lines, all on the approved wording. **Corrected:** the live
replicates have since run (`9abc76fb`); only kitchen naming passes the opening's
positive criteria. Layout, novelty and specific reaction remain 0 of 9. Full
suite not yet run. Authored layout text was added, but is absent from the
representative saved opening narrator payload inspected for this revision.

### Scoring correction withdrawn (2026-11-02)

An earlier note here scored the narrator's "reaches for the laptop, pulls it out
and opens it" on the turn where Kristin gets into the truck as an automatic
pickup that fails the plan. Brandon ruled that this is fine: when she found the
card the narration already said her laptop was in the truck, so picking it up when
she gets in and plugging the card in is natural progression. The note is withdrawn,
the acceptance row above now says so, and the committed prompt change (`e41878c3`)
stands as a good result for the seated, parked and laptop criteria. Still open on
that turn: surroundings (0 of 9). **Corrected by ruling 3:** the previous “small
remaining oddity” classification is withdrawn. Retrieving the card or laptop
from a glove compartment that is not its actual parent is bad narration and an
acceptance failure. The compartment's existence or harmless contents alone are
not failures. The allowed-pickup ruling remains unchanged.

**Corrected open work:** step 2's layout/novelty/reactions; step 3's engine-owned
repeat-boarding result, exterior view, custody, unboarded prose/state mismatch
and explicit-exit error; step 4's post-repair verification, persistence and
staging. Record each
step's commit, changed paths, deterministic checks, live artifacts, individual
acceptance results, unresolved limits and next action here; refresh Resume here
before proceeding to the next step. Do not declare the five issues fixed until
the final player-visible prose and committed facts both satisfy them.

### New — ruling revision and first replicate outcome (2026-11-02)

Only this plan was edited. Step numbering and completed implementation records
are retained. No new implementation, test suite, paid probe or deployment ran.
The existing local rows support `9abc76fb`'s results: kitchen naming, initial
boarding and drawer recovery 9/9; layout, KMS novelty, opening reaction and
boarding surroundings 0/9; repeated boarding 0/6, with two committed exits;
earned warning 9/9 but reaction 0/9; park transition 3/3. Explicit exit and
outside observation pass only 2/3; those defects remain in scope.

| Ruling / artifact | Correction and next verification |
| --- | --- |
| 1; `289e2575`; six repeat-boarding exits | Restore generic engine-owned already-aboard handling in the product path. Deterministic checks must show that no standing or narrator-written exit can precede or replace that response. |
| 2; probe 4 A outside 0/20; replicates outside 0/9 | Make the parent-area view through the truck windows mandatory, alongside cab context. Existing exterior text is present in the saved prompt; measure coverage and retain visibility/reach boundaries. |
| 3; raw plug and counter-route rows | Card/laptop glove-compartment provenance is a failure, not an oddity. Raw plug THINGS already says both are held; a projection-only fix cannot be presumed sufficient. Harmless invented contents and approved boarding pickup stay allowed. |
| 4; `7794e4b9`; opening prompt; `d09db551` history | Kitchen naming is insufficient. Repair the missing layout projection, retain the kitchen start and avoid reintroducing stale scene-arrival text. Exact history of lost good generated prose is not established. |
| 5; opening and plug prompts | Require specific reactions to absence/damage and the earned warning. Opening significance is supplied but not expressed; the warning's lead-up-only contract needs an after-warning reaction in the earned composition. |
| Probes 1–4 | Keep `e41878c3`'s measured boarding improvement; do not adopt the losing classifier, neutral-action or phone-focused opening arms. No new broad arm sweep. |

**New — call ledger:** Historical probes used 74+5, 94+5, 70+5 and 40+2 calls
(295 total). Replicates used 12 smoke + 86 raw + 89 canonical + 129 counter =
316 including smoke; the Result's “304 in all” is the full runs only, not all
four numbers. Proposed remaining calls: step 1 **0**; step 2 **48**; step 3
**48**; step 4 local **316 expected / 425 cap**, staged **316 expected / 425
cap**. Thus the specified future work budgets **728 expected calls**, with
**946** as the combined fixed probe count plus route caps; additional arms or
broader staged suites are excluded and require a separately counted approved
preregistration. These are budgets, not spend authorization or guaranteed counts.
