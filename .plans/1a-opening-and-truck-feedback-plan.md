# Scene 1A: opening prose, emotional grounding, and truck continuity

Status: in progress, 2026-11-02. Step 1 done. One runtime change (boarding-turn
prompt, `e41878c3`) is implemented and live-checked. The opening (step 2), the
rest of step 3 and all of step 4 are open. No story file has been changed.
Source baseline: `8da801206ca5e1708b0bce72e2c63e449cd3aae4`.

## Resume here

Step 4 live replicates are done (`replicates-prereg.md`, Result; commit `9abc76fb`):
the truck turn is right in 9 of 9, the drawer and gap in 9 of 9, the park transition
in 3 of 3, and the opening names the kitchen in 9 of 9. Still failing the acceptance
table: (1) repeated "get in the truck" while seated writes an exit in 6 of 6 and
committed it in 2; (2) invented glove-compartment handling contradicts card and
laptop custody on the plug, take and re-board turns; (3) the opening ignores the
layout text and both new situation sentences (layout 0 of 9, KMS new or strange
0 of 9, specific reaction 0 of 9); (4) no reaction to Michelle's warning; (5)
surroundings on the boarding turn (known gap). Next, per the scene-fixing guide
(step 1 first, no new arm sweep): read the recorded prompts for the repeated-boarding
turn, the plug turn and the opening beside `plot.md`, name what was checked, then
propose one fix at a time with Brandon's approval. Full suite, save/load
persistence and staging are still to do. Fixes stay generic: no command lists, no
story names in the runtime.

The user's current instruction supersedes the older continuity plan's
approach-only expectation: **“head out to the truck” should seat Kristin in
the driver's seat and describe her surroundings.** It must not start the
engine, drive, cross the gate, or return her to the house. A subsequent
“get in the truck” while seated must preserve that position.

## Scope and decision boundary

Prefer local story/prompt-material corrections, then narrowly scoped repairs
to existing shared behavior if evidence requires them. Keep environmental
prose LLM-written, following the existing environment-narration direction.
Do not substitute fixed boarding descriptions or hardcode Kristin/truck
commands in the runtime. Facts remain the only mutable truth.

Preserve the KMS clue, hidden-card recovery, laptop interpretation, patrol
pressure and witnessed-recovery consequences, and the earned park lead.
Keep scene/knowledge/entity IDs, reveal effects, transition prerequisites,
deadlines, and later plot connections intact unless a demonstrated defect
requires a small mechanical correction. Do not solve prose misses by
automatically earning a reveal or advancing a scene.

**Scoring policy (Brandon, 2026-11-02):** invented details are acceptable
unless they affect the main storyline. In probe criteria, "nothing invented"
fails an arm only for a contradiction of canon or state, a pre-empted or revealed
beat (patrol arrival, hidden card), or a collision with story names (a neighbor
called Jenkins), or an open laptop at the workstation while it is in the truck
(Brandon confirmed both examples on 2026-11-02). Atmosphere such as a passing
police car is recorded for information and does not fail an arm. Probes 1 to 3 were scored under the
stricter rule; re-scoring under this policy changes no adoption decision (the
failing arms also fail the laptop or surroundings criteria).

**Permission checkpoint:** if the smallest viable fix requires an engine
redesign or changes to plot connections with cascading consequences, stop
before implementing that change. Present the concrete proposed diff/design,
affected scenes and dependencies, evidence that narrower fixes failed, and
the alternatives; obtain the user's permission. Routine local repairs do
not need this checkpoint. This planning request does not authorize execution
of the implementation or paid experiments.

## Evidence checked and limits

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

- [ ] Start story edits in `data/stories/continuity-initiative/plot.md`, then
  synchronize only affected world, scene-frame, storylet and knowledge material.
  Give Kristin an explicit kitchen starting placement if the capture confirms
  the current house-level default. Verify scope/reach changes this causes.
- [ ] Supply a compact, grounded view: name the kitchen, establish where the
  existing workstation/chair and damaged back door are relative to her, and
  show enough layout to orient the player. Use existing objects; any added
  actionable physical detail must be declared and placed. Avoid a decorative
  inventory that creates unnecessary dependencies.
- [ ] Supply the personal significance of the scene: this is her best friend's
  familiar home, now disturbingly quiet and disrupted. The opening should show
  a concrete reaction to Michelle's absence and the damage, rather than a
  generic “eyes scanning” summary. Do not invent shared-history episodes,
  assert Michelle's fate, or make choices for Kristin.
- [ ] Keep KMS newly carved. Make recognition and abnormality legible: these
  are Kristin's initials on Michelle's furniture, a fresh deliberate mark
  that draws her attention. Treat its intended recipient as a reasonable
  suspicion, not proof of who carved it or what lies underneath. Preserve the
  search/recovery gate and avoid revealing the hidden card in the opening.
- [ ] Preserve the first paragraph's established events. Improve the generated
  second paragraph through appropriate opening material, not by padding the
  fixed preamble or making every turn repeat the opening description.
- [ ] Carry emotional responsiveness into consequential turns, especially
  recovery and hearing Michelle's warning, using only then-available context.
  Keep reactions brief and specific; do not require an emotion sentence on
  every mechanical action or create an emotion-state subsystem.

### 3. Separate boarding from driving and preserve seated interaction

- [x] Trace `storygame/runtime/seating.py`, the model questions it uses,
  `CloudflareTurnProvider` prompt construction, observation projection, and
  proposal/commit handling for the exact route. Retain the player's intent
  when preparatory steps are supplied; do not let a consumed boarding command
  become an invitation to improvise travel.
- [ ] Correct any misleading arrival/departure or stale place material at its
  source/scope. Boarding ends with Kristin seated in the parked truck, the
  laptop visible at its current location, and grounded cab/exterior surroundings.
  It leaves the vehicle's parent and scene unchanged. Driving requires a
  separate explicit driving/departure command; an explicitly compound command
  may still request both actions.
- [ ] For `look for the laptop`, show the laptop beside her. Finding it does
  not require retrieving it, exiting, or reopening the passenger door.
  Repeated `get in the truck` is spatially idempotent; ordinary pacing may
  still advance according to existing rules.
- [ ] For card/laptop use while seated, project both seats' shared vehicle
  context and available reach. Permit reaching across from the driver's seat.
  Keep Kristin seated; do not trigger a leave-seat step, move the laptop outside,
  or reset its custody/placement. If she actually moved it earlier, respect
  its current place rather than forcing it back onto the passenger seat.
- [ ] If a world-state-only defect is proven, implement the smallest generic
  `World` method repair in `packages/worldkeeper`, with tests there; storygame
  adapts and calls it. Use existing proposal validation and atomic rollback.
  Do not implement action keyword tables, a second location store, or a blanket
  rule that all objects in the scene are reachable.
- [ ] Add a narrator instruction only if a controlled prompt probe shows it
  improves the relevant failure. Follow narrator-writing guidance and apply
  shared behavior consistently across opening, turn, section and recovery paths.

### 4. Verify narrowly, then check the plot connections

- [ ] Add meaningful failing deterministic tests for any repaired state,
  projection or selection boundary; reuse existing suites. Do not encode
  subjective writing quality as exact wording or a paragraph word count.
- [ ] Diff stubbed narrator payloads before/after. Keep unrelated scene
  payloads byte-identical unless a shared fix necessarily changes them; list
  and justify each difference. Check no protected reveal becomes visible early.
- [ ] Prepare one small preregistration using captured prompts: unchanged
  control plus one arm per supported causal hypothesis, 10–15 samples per arm
  per the scene-fixing guide. Do not sweep models or stack unmeasured rules.
  Existing plans require approval before billed runs: prepare harness, counts,
  rubric and estimated cost first, then request approval if implementing.
- [ ] Read every final composed response, including appended handoffs. After
  selecting the smallest winning fix, run three full live replicates of the
  transcript route and a compact countercase route. Score each requirement
  independently; a state-only pass or successful reveal is insufficient.

| Acceptance case | Required result |
| --- | --- |
| Opening | Names the kitchen; makes its immediate layout understandable; shows familiarity and a specific reaction to Michelle's absence; identifies KMS as new and strange; no hidden-card leak or unasked search. |
| Drawer then gap | Existing opening/search/recovery order still works; card recovered once, with the correct witnessed or unwitnessed consequence. |
| Head out to truck | Ends in driver's seat; truck remains parked outside; useful surroundings and laptop placement are narrated; no engine start, driving, gate crossing or return to house. |
| Look for laptop; repeat boarding | Laptop is seen at its current place; Kristin stays seated; no automatic pickup or exit/re-entry. |
| Plug card into laptop | Reaches across and uses it from driver's seat; preserves custody and existing earned delivery; reacts plausibly to Michelle's warning. |
| Explicit departure after the lead | Existing park transition remains playable and places the truck correctly in 1B; boarding alone never substitutes for this action. |
| Countercases | Laptop carried/left elsewhere, explicit exit, explicit drive, and observation outside all follow actual state; no global forced seating or remote reach. |
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

## Completion record

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

Done after the free half: live probe 1 (74 calls) answered the boarding question and the opening/boarding prose; see the preregistration Result. Still not read: narrator prompts for turns 4 to 6. No story or runtime
file has been changed.

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
diff has 12 changed lines, all on the approved wording. Not yet done: the live
replicates that show whether the prose now meets the opening acceptance row; full
suite not yet run.

Open: the remaining step 3 items (surroundings on the boarding turn, the unboarded
"gets in" prose mismatch) and step 4. Record each
step's commit, changed paths, deterministic checks, live artifacts, individual
acceptance results, unresolved limits and next action here; refresh Resume here
before proceeding to the next step. Do not declare the five issues fixed until
the final player-visible prose and committed facts both satisfy them.
