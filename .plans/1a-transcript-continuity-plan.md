# Correct Scene 1A reference, patrol, and location continuity

Status: in progress (step 1 deterministic baseline done), 2026-10-24. Planning baseline:
`be14abdf997db10bdfefc47a1e5b60d254fb1963`. This change is a plan only;
no runtime changes, model calls, or deployment have been performed.

## Resume here

Step 1's free, stubbed baseline is recorded below. Drafted 2026-10-24 and
awaiting Brandon's approval, nothing applied or billed:
[story material and observed-recovery outcome](1a-transcript-continuity/story-material.md)
(steps 2 to 4 wording, written by Claude as IF writer at Brandon's direction)
and the [live baseline preregistration](1a-transcript-continuity/baseline-live-prereg.md)
(step 1, billed part; needs his approval and engine pick). Original step-1 note: capture the reported sequence through the current runtime,
including prompts and committed facts. The user supplied prose, but no session
ID, deployed SHA, model payloads, or save. Do not claim that this checkout
produced the transcript or that the causes below have been reproduced.

This is a focused correction plan alongside
[the active redesign](game-reimagination-plan.md). Reuse its implemented
incident and traversal contracts where applicable; do not restart historical
experiment queues or expand this repair into a whole-game migration.

## Required behavior

1. The back door has no described gap between door and frame. Keep evidence
   of forced entry, but remove competing gap language and the invented fabric
   diversion. Once the drawer gap is presented, a player's reference to
   “the gap” identifies that gap in the current context.
2. A patrol must visibly arrive before an officer from it appears or returns.
   Finding the card under an officer's observation must produce a committed,
   visible consequence. The officer cannot simply watch and then cease to matter.
3. Getting into the truck shows the laptop at its actual location, initially
   on the passenger seat. Finding the card must not imply that Kristin has
   already traveled to the truck or read its files.
4. Observation follows Kristin's actual location and posture. Looking around
   outside describes the exterior; looking around from the driver's seat
   describes the cab and what can be seen from there. Neither puts Kristin
   inside the house or implicitly moves her there.

## Evidence and implementation leads

Checked the PRD, contributor and agent-workflow guides, world-model grounding,
player-input, narrator-writing and scene-fixing guides, testing runbook, and
production-promotion guide. Also checked the historical W1–W14 decisions at
`5ea0119955c62b84699a8dc7878a4af770b55a7e` and the prior
[1A diagnosis](astra-1a-plan.md), which already records contradictory truck
movement despite engine seating. Existing supported techniques are authored
placements, scoped names, fact effects, reveal handoffs, seating steps and
item notices. Prefer these over extra narrator rules.

Relevant sources under `data/stories/continuity-initiative/`:

| Source | Observed evidence / investigation target |
| --- | --- |
| `plot.md`, Scene 1A | Drawer-gap cue, forced back door, house scene location, truck outside, laptop on passenger seat. Patrol arrival is described in beat 1A.4. No explicit protagonist starting placement appears in 1A front matter. |
| `knowledge.yaml`, `k_sl_1a_b_r0` | Card recovery handoff already points to the laptop outside. Exact evidence includes look/search/inspect/check, but not feel, and requires drawer/KMS/workstation wording. Bare “feel in the gap” does not satisfy those groups; bounded semantic selection still needs inspection. |
| `pacing.yaml`, `pressure_1a` | Turn 4 can say an officer “comes back” and lingers at the drawer while the card remains unrecovered. This is a concrete source of unsupported prior-patrol wording; confirm the actual fired event in a reproduction. |
| `world.yaml` | Laptop already has `notice_text`; driver seat has enter/leave text. House and outside are separate root areas, while kitchen is under the house. Audit scope and movement across that boundary. |
| `storylets.md`, `storylet-routes.yaml`, `handoffs.yaml` | Audit patrol prerequisites, card recovery, cue retirement, and fallback paths together so an alternate route cannot restore the defect. |

Runtime leads: `storygame/runtime/seating.py::board_vehicle` already appends
notices for visible items within the boarded vehicle. It requires the command
to name that vehicle, so contextual “get in” needs tracing through the other
reference/movement paths. `CloudflareTurnProvider._scene_setting` in
`storygame/runtime/cloudflare.py` projects eligible beat prose; inspect that
alongside PLAYER, THINGS, scene location, recalled material and engine steps.
These are leads, not a proven explanation of the omitted notice or wrong room.
Serena was unavailable during planning; discovery used the indexed code graph.

## Implementation sequence

### 1. Establish a reproducible baseline

- [ ] Preserve the supplied transcript as a raw-language regression fixture.
  Replay its exact inputs in order: “go in the house”, “feel in the gap”,
  “look at the fabric”, “pull out the drawer”, “feel under the drawer”,
  “go out to the truck”, “get in”, “look around”. The fabric command belongs
  only to this historical regression, not the intended corrected route.
- [ ] Record opening state and each turn's pre/post parents, seat, card
  custody, revealed knowledge, patrol state, fired events, reference matches,
  engine steps, prompts, provider response, and final composed narration.
  Include `item_facts_unplaced`, model/package identity and code SHA.
- [ ] Read failing prompts beside the plot. Identify separately incorrect
  committed state, missing material, misleading material, and prose that
  contradicts correct state. Inspect the opening too: narration starts at the
  driveway while the package defaults the protagonist to the house.
- [ ] Capture current package payloads with the network stubbed. Retain a
  before/after diff and name every intended prompt change.

### 2. Make the drawer the sole local gap referent

- [ ] Audit all 1A opening, beat, cue, delivery, recall and fallback material.
  Describe forced-entry damage without a door/frame opening or gap affordance.
  Do not add a torn-fabric object to accommodate the bad output.
- [ ] Ground the drawer's underside/gap using the existing entity and scoped
  reference mechanisms. Keep this association local to the drawer's scene and
  availability, not a global keyword rule or a second mutable location model.
- [ ] Exercise the real reference and reveal-selection paths for tactile
  search. Add author-reviewed evidence only for demonstrated misses. Do not
  weaken every reveal's object requirement to make bare “gap” pass.
- [ ] A search reaches and recovers the hidden card once; opening the drawer
  alone does not reveal it. Retire discovery cues after recovery. Remote or
  ambiguous references must not recover a card through walls.

### 3. Give the patrol a coherent arrival and consequence

- [ ] Replace unconditional return language with fact-gated arrival, presence,
  departure and return behavior. A timer alone does not establish a previous
  visit. Place the patrol/officer when present and remove or move it on departure.
- [ ] Make the first arrival legible on the turn it commits, including when
  it coincides with a drawer action. Do not introduce an unannounced observer
  halfway through an otherwise private action.
- [ ] Author an explicit observed-recovery outcome. Proposed default: an
  officer who sees Kristin retrieve the card challenges her about it and
  escalates scrutiny, creating a concrete response opportunity and persistent
  consequence. Define the exact fact/outcome and follow-up before coding.
  Simply adding a line of alarm is insufficient. Reuse the typed incident
  contracts if they fit; otherwise identify the missing generic capability.
- [ ] Distinguish recovery before arrival, recovery while observed, and a
  previously concealed card. Presence alone must not grant knowledge of a
  concealed item. Do not auto-conceal the card, auto-confiscate it, or silently
  assert a successful deception on the player's behalf.
- [ ] Align plot, storylets, pacing and handoffs: current 1A.4 says the patrol
  discovers/confiscates nothing and Kristin conceals the card. Make that
  conditional on the actual outcome instead of overriding witnessed recovery.
  Preserve a playable onward route and existing goal-break handling.

### 4. Correct travel, seating and laptop presentation

- [ ] Align authored opening placement and opening prose. Trace house →
  exterior → vehicle → seat through the real movement pipeline, including
  preparatory seating and provider-proposed movement.
- [ ] Define approach versus boarding coherently. “Go out to the truck” must
  leave Kristin beside it unless boarding was clearly requested; “get in” in
  that context boards it. If this changes the current broad boarding helper,
  record the generic behavior change and cover other vehicles too.
- [ ] An entry turn emits the existing laptop notice once when it is visible
  in the cab, including contextual entry. Repeated entry or observation must
  not generate a false exit/re-entry loop. Show current custody if the laptop
  has moved; never repeat the passenger-seat notice after it is carried away.
- [ ] Inspect the full composed response: correct engine steps or JSON alone
  are insufficient when prose says Kristin gets out after she just got in.

### 5. Scope observation to place and posture

- [ ] Project Kristin's committed parent and the relevant area/vehicle context
  for observation, even when the input names no object. Separate scene identity
  from current physical location; scene 1A can continue while Kristin is outside.
- [ ] Scope stale interior descriptions and recalled cues so they do not
  masquerade as the present view. Preserve earned knowledge as knowledge,
  without presenting distant objects as reachable or locally visible.
- [ ] Keep interior standing, exterior standing, driver's seat, and passenger
  seat distinct. Observation must not change parent, posture or item custody.
  Use the existing tree and typed projection; do not infer location from prose
  with regex or build a hardcoded “look around” command handler.
- [ ] If a new narrator instruction proves necessary, probe it against the
  captured prompt first and apply the winning story-neutral rule to all
  narration paths per the narrator-writing guide.

## Acceptance and verification

Write failing deterministic tests before each implementation change. Use
canonical imperative inputs for new tests, with the exact transcript commands
explicitly designated raw-language cases. Minimum coverage:

| Case | Required result |
| --- | --- |
| Drawer cue → “Feel in the gap.” | Drawer resolved, no door gap/fabric diversion, card recovery earned once when reachable. |
| “Pull out the drawer.” only | Ordinary contents and underside cue; hidden card remains hidden. |
| Patrol timer fires before any visit | First arrival shown; no “back”, “return”, or implied previous patrol. |
| Recovery with officer watching | Visible challenge and committed consequence; next turn responds to that state. |
| Recovery before arrival / concealed card | No retroactive witness knowledge; consequence depends on actual observation. |
| “Go out to the truck.” → raw “get in” | Exterior then seat; no unexplained exit; laptop shown at its current place. |
| Raw “look around” outside / seated | Exterior / cab respectively; no return to the kitchen and no movement. |
| Laptop carried or left elsewhere | Accurate notice/view; no stale passenger-seat placement. |
| Save/load at exterior, seat, patrol challenge | Same parents, custody, knowledge, incident outcome and next-turn behavior. |
| Synthetic second story | Generic reference, seating, observation and consequence behavior works without Kristin-specific runtime logic. |

Verify package loading, reveal selection, pacing/incident order, world-model
projection, narration composition, atomic rollback and save/load with the
focused suites in `docs/testing-runbook.md`. Confirm current commands and test
locations in source/help when implementing. Run affected tests after Ruff
autofix/format, then the required full-suite/coverage gates (at least 90%).
Update existing runbook entries only if procedures change.

For model-dependent behavior, follow the scene-fixing guide: replay captured
prompts through Ringer with 10–15 samples per causal arm, including the
unchanged control; read every final narration, including appended delivery
text. Then run three complete live replicates of the corrected scene route
and the observed-recovery branch. Report failures per case, not just pooled
scores or reveal counts. All three final replicates must satisfy the four
user-facing requirements; a failure keeps that requirement open. Billed work
needs a concrete preregistration and budget under the project's existing flow;
this planning change runs none.

After implementation, merge through required CI, wait for the exact main SHA's
staging deployment, and verify the transcript cases on staged gameplay. Check
the current adapter capability first: if only deployment identity is exposed,
record hosted gameplay verification as unavailable rather than calling an
identity check a gameplay pass. Follow the production-promotion guide for any
later release; this plan does not deploy or promote.

## Completion record

For each completed step record its commit, deterministic result, live evidence,
and remaining limits here, then refresh “Resume here”. Completion requires all
four requirements to pass in final prose and committed state, with no story
names in shared runtime, no protected-card leak, and no untested behavior
reported as corrected. Planning itself does not establish any gameplay pass.

### Step 1 — stubbed baseline (2026-10-24, code SHA 206de861, branch fix-1a-transcript-continuity)

Replay: `uv run python .plans/1a-transcript-continuity/baseline_replay.py OUT.json`
(network stubbed; narrator always answers "The scene continues."; semantic
reveal off). Output kept in `.plans/1a-transcript-continuity/baseline-stubbed.json`.
This is the user's eight raw inputs through the real engine and provider
prompt builder, not the user's session: prose below is the engine's, model
behavior is still unmeasured.

Observed in committed state and prompts:

- Opening: Kristin's committed parent is `mcgehee_home` (the house) while the
  opening prose has her driving up. Requirement 4's location defect has a
  deterministic source here.
- “feel in the gap” earns no reveal (`selected_knowledge_ids` empty), as the
  plan predicted. “feel under the drawer” earns `k_sl_1a_b_r0`, delivery text
  ends “Her laptop is in her truck outside.”
- “pull out the drawer” fires `SL-1A-F` and `pressure_1a` on turn 4; that
  turn's prompt carries “An officer from the patrol comes back and lingers at
  the drawer…” with no earlier arrival (requirement 2 source confirmed). The
  card is not yet recovered, so this is the unconditional realization.
- Every prompt's SCENE says “its back door frame shows recent damage” beside
  the “forced back door” detail; the pointer lines (“pointed toward the thin
  gap beneath its lower edge”) stay in SCENE on turns 6–8 after the card is
  recovered, so the cue is not retired (requirement 1 and 4 sources).
- “go out to the truck” resolves `truck` → `kristin_truck` but commits no
  move; “get in” names no vehicle and emits no notice; Kristin's parent stays
  `mcgehee_home` through all eight turns. Boarding needs the semantic ask,
  which this stub does not run, so boarding behavior is untested here.
- CORRECTION (2026-10-24): that stubbed replay used the plain provider. The
  product wiring (world capture on, `build_capture_provider`) does put
  “Kristin. Place: Michelle's house.” in THINGS and PLAYER, so requirement 4
  is not a missing projection but a wrong committed place (house, not outside)
  plus a plain-provider path. The plain provider's PLAYER block holds only the
  command. THINGS in the plain provider says the laptop is on the passenger
  seat even after the card line says it is “in her truck outside”.
- Product-wired dry run (`bench/results/transcript-1a-dry`, harness
  `scripts/ringer/transcript_1a/live_baseline.py`): with Jev stubbed off the
  boarding question for “go out to the truck” is “unanswered”, so the live
  run is what shows whether boarding fires.
- `home_search_narrows_1a` fires on turn 8 (“look around”).

Live capture done (below). Not yet done: the before/after payload diff (taken when step 2 lands). Steps 2–5 not started.

### Approvals and verified facts (2026-10-24)

Brandon approved the live baseline preregistration, the Luna worker, the
patrol retiming (delay of about five turns accepted) and the three-way
response proposal ("ok"; capability gap to be named before coding if the
incident contract cannot express it). Transition `triggers` are all-of
(`storygame/runtime/validation.py:422`, `engine.py:961`), so `t_1a_1b` needs
`michelle_lead_actionable`, `patrol_return_pressure` and
`memory_card_recovered` together; moving `patrol_return_pressure` to departure
cannot fire the exit early.
Harness build: Ringer run `transcript-1a-live-baseline`, manifest
`scripts/ringer/transcript_1a/build-live-baseline.json`. The billed run
follows its dry run and a 2-turn smoke.

### Step 1 — live baseline (2026-10-24, git ae0d7a34)

Ringer runs `transcript-1a-baseline-smoke` and `transcript-1a-baseline-live`
(5 replicates, 40 turns, 145 calls, 0 errors, Luna worker). All four
requirements fail in every replicate at the sequence level; counts, causes and
the fixture are in
[the preregistration result](1a-transcript-continuity/baseline-live-prereg.md#result-2026-10-24-git-ae0d7a34-5-replicates-40-turns-145-calls-0-errors-no-quota-stop)
and `1a-transcript-continuity/baseline-live-narrations.json`. Headline:
“feel in the gap” becomes a door gap with an invented object 5/5; an unannounced
officer lingers at the drawer 5/5 and nothing happens when the card is taken
5/5; the engine seats Kristin on “go out to the truck” but the narration says she
gets out 5/5; “get in” ends correctly 1/5; seated “look around” describes the
house 1/1.
Step 1 is complete. Next: step 2 (package edits through Ringer, tests first).
