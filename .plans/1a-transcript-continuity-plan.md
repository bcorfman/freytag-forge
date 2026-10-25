# Correct Scene 1A reference, patrol, and location continuity

Status: in progress, 2026-10-24. Steps 1 to 4 and most of 5 and 6 are implemented
and committed on `fix-1a-transcript-continuity`; the live verification and the final
full-suite gate are not done, so no requirement is claimed corrected yet except where
the Completion record shows live evidence. Planning baseline:
`be14abdf997db10bdfefc47a1e5b60d254fb1963`.

## Resume here

Branch `fix-1a-transcript-continuity` (never merged; commit log has every step).
State as of 2026-10-24 late evening. Read the Completion record at the bottom
for what each step did; this section says only what to do next.

**Standing instructions from Brandon (follow them):**
- Every code change goes through a Ringer task (Luna, `gpt-5.6-luna`, **high
  effort**), tests first, manifests in `scripts/ringer/transcript_1a/`. Review each
  diff; reject worker overreach (a past worker bloated `docs/testing-runbook.md`
  and rewrote a test to hide a bug; both were reverted).
- No billed run without a preregistration he has approved.
- Run the full suite (`TMPDIR=/tmp uv run pytest -q --cov`, plus ruff) **once, at
  the very end**; use focused suites in between. The last full run passed except
  2 failures that were then fixed (stale alias pin and the fail-open bug).
- Read every live narration by hand; report per requirement, not pooled.

**Running when this was written:** Ringer task `step7b-literal-scope-and-referent`
(manifest `scripts/ringer/transcript_1a/step7b-literal-scope-and-referent.json`,
run `1a-continuity-step7`). It edits `storygame/runtime/item_facts.py`,
`cloudflare.py`, `tests/test_place_scoped_feed.py`, `tests/test_recent_cue_reference.py`
(uncommitted until reviewed). To resume: `git status`; if those files are modified
and the Ringer run (`~/.ringer/runs/1a-continuity-step7-*.json`) says PASS, review
`git diff storygame tests`, run the focused suites, and commit; if it failed or was
interrupted, rerun the manifest. It fixes (1) distant objects still listed in the
narrator prompt because the name-matcher's `refers` list kept them (now only things
the command literally names), and (2) passing the engine's resolved “the gap means
the drawer” to the narrator (“feel in the gap (meaning the drawer)”).

**Approved, not yet run (both preregistered and approved by Brandon):**
1. [boarding probe](1a-transcript-continuity/boarding-probe-prereg.md): 3 arms x 3
   prompts x 10 samples (cap 100 narrator calls). Question: can the narrator be made
   to narrate the laptop on the passenger seat after boarding, or must boarding be
   engine-only text? First build `scripts/ringer/transcript_1a/boarding_probe.py`
   (a Ringer task) with `--dry`, build the prompts from the head AFTER 7b is
   committed, 2-sample smoke, then the run. If neither arm wins, the fallback
   (engine-authored text, no narrator call) needs Brandon's separate approval.
2. [postfix2 verification](1a-transcript-continuity/postfix2-live-prereg.md): routes
   A reported n=5, B corrected n=3, C witnessed n=3, D movement n=3, about 530 calls,
   cap 700. Manifests exist (`postfix2-smoke.json`, `postfix2-smoke-b.json`,
   `postfix2-live.json`); the harness already supports `--route movement`. Smokes
   were run twice; run the full `postfix2-live.json` only after 7b is committed and
   the boarding probe has settled boarding behavior.

**Open defects (from the smokes and the postfix run):**
- The laptop notice never reaches the player's text (0 of 10 boarding turns):
  only the boarding probe above can settle this.
- Reported route lead-up invents a door gap for “feel in the gap” (5 of 5 in the
  first post-fix run); 7b passes the referent to the narrator, to be measured live.
- Seated or outside “look around” still described the house (0 of 11 correct in
  the first post-fix run); the place-scoped feed (6b, 7b) is the fix, to be measured.
- Narrator-invented rooms (`n_living_room_1`) and `None` places: fixed by aliases,
  same-root reach and fail-open; to be counted in the verification run.
- Not built: 1B marked-pursuit line verified live; the three-way response to the
  officer's challenge is free text only; hosted staging verification after merge.

**After all of that:** full suite once, update the Completion record, then merge
through CI and the staging gate per the testing runbook (Brandon merges per PR).
Original step-1 note kept below for history. This is a focused correction plan alongside
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

### Step 2 — drawer gap (2026-10-24, commits b9dde6ed and after)

Done through Ringer (Luna, manifests in `scripts/ringer/transcript_1a/`, tests
first):
- 2a: 1A situation now says the back door “has been forced. The lock is
  splintered out of the wood” (no “frame”, no “gap”). Card reveal
  `k_sl_1a_b_r0`: delivery “…pockets it. Her laptop is still out in her truck.”,
  statement “…pockets it.”, and `the gap`/`that gap` added to its third
  evidence group. Tests: `tests/test_1a_back_door_gap.py`.
- 2b: new generic `reach_entity_ids` on a reveal (loader-validated,
  `explain_reveal` returns `not_reachable` unless the protagonist is `together`
  with each id). Applied to `k_sl_1a_b_r0`, `k_sl_1a_f_r1`, `k_sl_1a_f_r2` with
  `michelle_drawer`, so the card cannot be recovered from the truck. Tests:
  `tests/test_reveal_reach.py` (1A plus a synthetic story, loader rejection).
  Deviation: I used evidence phrases rather than the scoped alias in the story
  material, because aliases only resolve nouns and do not rewrite the command
  the matcher reads; the plan's “no weakening” rule holds because only this one
  reveal gained two phrases and reach now blocks the remote case.
- 2c/2d: the pointer reveals now require `memory_card_recovered` false, so
  “Pull out the drawer” after recovery no longer re-points a finished cue;
  `test_knowledge_projection` expectations updated to the new behavior.
- Worker overreach caught in review and reverted: a 44-line
  `docs/testing-runbook.md` section with pinned counts, an unrelated rewrap of
  the authoring guide, and a regenerated 1C spine JSON.

Deterministic check (dry harness, product wiring): “feel in the gap” on turn 2
now earns `k_sl_1a_b_r0` with the new delivery; nothing remains of the door gap
in authored text. NOT yet verified live: the narrator's lead-up prose, the
fabric and invented-object behavior (“look at the fabric”), and the stale
pointer lines in SCENE on later turns. That needs a billed run, which is not
preregistered. Open: stale SCENE statement lines are left to step 5.

### Step 3 — patrol arrival, presence and consequence (2026-10-24)

Done through Ringer (Luna, high effort, tests first). Capability finding:
`incidents.yaml` models a scene-exit decision window (`completes_scene`,
successor transition) and would block leaving 1A, so it does not fit a witnessed
recovery. No new engine capability was needed: the existing techniques cover it
(exclusive reveals gated on a presence fact, a second storylet realization,
fact-driven npc moves, pacing events).
- 3a: `pressure_1a` replaced by `patrol_arrives_1a` (turn 4),
  `patrol_enters_1a` (5), `patrol_leaves_1a` (7), `patrol_returns_1a` (9, “coming
  back” only when `patrol_departed`). New npc `patrol_officer` is moved by
  `patrol_on_scene` / `patrol_in_house` / `patrol_departed`; unplaced before
  arrival. 1A `min_turns` 8→9 (the exit trigger now arrives at turn 9). Old
  `pressure_1a` pins in six test files updated.
- 3b: `k_sl_1a_b_r0w` (SL-1A-E-R2) fires instead of `k_sl_1a_b_r0` while
  `patrol_in_house` is true: the delivery ends with the officer's challenge, and
  `card_challenged` plus `kristin_marked_by_patrol` commit; custody does not
  change. `pursuit_1b` has a first line gated on `kristin_marked_by_patrol`.
  Plot 1A.4 and SL-1A-E text updated; the “Kristin conceals the card” sentence
  is gone.
- Known by design: THINGS lists a character only when the command names them
  (context bound), so the officer reaches the narrator through the authored
  lines and the committed statement, not a standing roster line. Whether that
  suffices is a live question.
- Not done: the three-way response (deflect, hand over, walk out) is free text
  with no engine-resolved outcome; hand-over is the player's own act.
  Not verified live: narrator behavior after the challenge.

### Steps 4 and 5 (partial) — truck, laptop, cue referent (2026-10-24)

- 4a (generic, Ringer, high effort): the Jev question `goes_to_vehicle` became
  `boards_vehicle` (“get into, sit in, or drive”; approaching, looking, touching
  are false), so “Go out to the truck” no longer seats the player. `board_vehicle`
  also acts with no vehicle named when exactly one boardable vehicle is in the
  protagonist's own area, so a bare “Get in” seats her and emits the enter text
  plus the existing laptop notice (only for items she does not hold). Tests
  include a second, differently named vehicle. This is a generic behavior
  change for every vehicle (plan step 4 required recording it).
- 4b: instead of moving Kristin's committed start outside (which would stall the
  persona and journey tests, because reach now blocks the drawer reveals until
  she is in the house), the 1A entry text ends “She found the back door forced
  and let herself in.” so prose and committed place agree. Deviation from the
  story-material proposal, which suggested starting outside.
- 5a (Ringer, high): reverted the `the gap`/`that gap` evidence phrases I added
  in step 2 (they broke the pinned rule that a bare “Search the gap.” with no
  prior cue earns nothing). `recent_cue_referent_text` now also treats a cue
  delivered on the previous turn as a one-turn referent, so the staged drawer
  cue makes “Feel in the gap.” refer to the drawer. It uses a reveal's
  `reach_entity_ids` as the owner when present.
- Pin repairs: nine tests that pinned the old 1A pacing, reveal rows or turn
  counts were updated to the new intended behavior. One worker edit was
  rejected: it rewrote `test_invitation_report` to assert the drawer cue has no
  response; the cause was a report helper that never placed the protagonist, so
  `sibling_reachability._state` now seeds the world and the original assertion
  passes unchanged.
- Step 5 observation scoping (stale interior description while outside or
  seated) is NOT done. Product wiring already puts Kristin's place in THINGS and
  PLAYER; what remains is whether the narrator honors it, which needs the live
  routes. If they show the cab or exterior still described from the house, a
  probe (one arm per cause, 10 to 15 samples) is next, per the scene-fixing
  guide.
- Next: [post-fix live prereg](1a-transcript-continuity/postfix-live-prereg.md),
  awaiting Brandon's approval.

### Step 6 — engine-owned places and a place-scoped feed (2026-10-24)

Brandon's direction after the post-fix live result: inside the house, outside,
and the truck are three distinct places (outside contains the truck; the truck
contains the seats); “go out to the truck” seats her, “go outside” does not,
“go inside” puts her in the house, getting out of the truck leaves her outside,
and from the truck she sees outside. The data already had that tree; the
failures were that no movement was engine-owned and the narrator prompt ignored
where she is. Reverses 4a's rule that approaching a vehicle is not boarding.
Done through Ringer (Luna, high effort, tests first), all committed:
- 6a: aliases on `outside_house` and `mcgehee_home`; `connections.yaml` with
  `house_to_outside` and `outside_to_house` (authored arrival text, no narrator
  call); `tests/test_1a_movement.py`.
- 6b: optional `description` on locations; the narrator prompt is place-scoped
  (scene situation, committed statements with `reach_entity_ids`, and object
  lists follow the tree; a WHERE bullet and the area description replace the
  house text while she is outside or seated); in-scene prompts are byte-identical
  to before (goldens in `tests/fixtures/place_feed/`); synthetic second story.
- 6c: `boards_vehicle` counts going to the vehicle again; a second Jev question
  `only_boards_vehicle` drops a pure boarding command from the narrator's view
  (it had read “go out to the truck” as leaving the vehicle); a reply that places
  the protagonist at a vehicle lands her in its first visible seat; the
  kitchen-evidence reveal is reach-limited to the back door.
- Withdrawn: the five-arm observation probe prereg. Next:
  [postfix2 verification prereg](1a-transcript-continuity/postfix2-live-prereg.md),
  awaiting Brandon's approval; it needs a `--route movement` added to the
  harness first (free).
