# Scene 1A story material and observed-recovery outcome (PROPOSAL, not applied)

Written 2026-10-24 by Claude as interactive-fiction writer, at Brandon's direction ("you take on an interactive fiction writer persona and do it yourself"). This overrides the usual ChatGPT Desktop hand-off for this one task. Nothing here is in the package yet. Each line is checked against `docs/world-model-grounding.md` and `docs/narrator-writing-guide.md` (plain words, one idea per sentence). Mechanism notes say which existing technique carries the line; none adds a narrator rule.

## 1. Back door: forced, no gap

Source of the problem: the `scene_frames` situation for 1A (`knowledge.yaml`) says "its back door frame shows recent damage". "Frame" invites a door-and-frame gap, and the narrator filled it with fabric.

Replace the situation with:

> Michelle's home is otherwise untouched, but the back door has been forced. The lock is splintered out of the wood. Michelle is missing, and her tablet and work bag are gone. A drawer on Michelle's workstation has Kristin's initials, KMS, newly carved into it.

Keep the plot Details line "forced back door". Technique: change of source material (scene-fixing guide step 3). No fabric entity is added.

## 2. The drawer gap is the only gap

Existing deliveries stay exactly as authored (`R1_DELIVERY`, `R2_DELIVERY` are pinned by `tests/test_1a_gap_pointer.py`): "A thin gap beneath its lower edge is wide enough for Kristin's fingers."

- **Reference:** once `drawer_gap_pointed_out` is true, "the gap" resolves to the drawer. Technique: scoped alias on `michelle_drawer` (`gap`, `the gap`), the same way `house_gate` carries `front gate`. The resolver then rewrites "feel in the gap" to name the drawer, so the reveal's drawer group is met without weakening it. If the alias cannot be conditioned on the fact, scope it to scene 1A and accept "gap" before the pointer (to be tested; do not assume).
- **Verbs:** add `feel, reach, run, slide` to the first `action_evidence` group of `k_sl_1a_b_r0`. "Feel" is the player's natural word for a hidden thing under a drawer and is missing today.
- **Card delivery** (replaces "She takes it with her. Her laptop is in her truck outside."):

> Kristin's fingers find something taped beneath the drawer. She peels it loose. It is Michelle's memory card, and she pockets it. Her laptop is still out in her truck.

  It keeps every `must_convey` group (memory card, taped, beneath the drawer, Michelle's). "Pockets it" replaces "takes it with her", which read as leaving. "Still out in her truck" fixes where the laptop is without moving Kristin.
- **Retire the cue:** after `memory_card_recovered`, the two pointer lines stop appearing in SCENE. Today they persist on turns 6 to 8 of the baseline.

## 3. Opening, truck and laptop

- **Entry text** (sent once), add after "...turned the drive into an ordeal.": "She pulled up outside Michelle's house and got out of her truck."
- **Placement:** `character_placements: kristin: {parent: outside_house, text: beside her truck outside Michelle's house}` in the 1A front matter, so committed state matches the prose. Going in is then a real move across the house boundary ("Go in the house" ends in the kitchen).
- **Truck lines already exist** (`enter_text`, `leave_text`, laptop `notice_text` "Kristin's laptop sat on the passenger seat."). Nothing new to write; the missing piece is engine behavior (plan step 4).

## 4. Patrol: arrival, presence, departure

The baseline shows the turn-4 timer realization says an officer "comes back" before any visit. Proposed timeline, all facts, no timer-only claims:

| Moment | Committed | Player sees (authored, deterministic) |
| --- | --- | --- |
| Turn 4 event `patrol_arrives_1a` | `patrol_on_scene` true; officer placed outside the front door | "A federal emergency patrol pulls up outside Michelle's house. Two officers get out. One walks to the front door. The other looks over the street." |
| Next turn, patrol still on scene | Officer moved into the kitchen | "The front door opens. An officer walks in and heads straight for Michelle's workstation." |
| Patrol leaves (via `SL-1A-C-R2`) | `patrol_on_scene` false, `patrol_departed` true; officers removed | "The patrol pulls away. Kristin sees a strip of reflective tape on the front gate." (existing R2 content, now truthful) |
| After departure, turn 9 | `patrol_return_pressure` | "The patrol is coming back to the house." The word "back" is allowed only here, gated on `patrol_departed`. |

Open timing question for Brandon: `pressure_1a` today sets `patrol_return_pressure` at turn 4, and `t_1a_1b` lists it as a trigger. Moving that fact to departure and turn 9 delays the timer exit by about five turns. I have not checked whether `triggers` are any-of or all-of in the loader; this is verified before coding, and the delay is a pacing decision, not a given.

## 5. Observed recovery: proposed outcome

**Observation is geometry, not a new flag.** An officer observes the recovery when the officer is in the same area as Kristin (`together()` on the world tree) on the turn the card is recovered. At the truck or outside, nobody saw.

| Case | Result |
| --- | --- |
| Recovered before arrival, or while the officers are elsewhere | No challenge. Patrol does its targeted look at the workstation, does not open the drawer, finds nothing (matches plot 1A.4). |
| Recovered with an officer in the room | Challenge (below). |
| Card already recovered, officer then enters | No retroactive knowledge. The officer does not know about a concealed card. |

**Challenge, committed and visible the same turn** (verbatim authored text, appended after the narration):

> The officer turns at the sound. "What have you got there?" His hand is already out.

Committed facts: `card_challenged` true, `kristin_marked_by_patrol` true. Custody does not change. Nothing is hidden, confiscated or lied for Kristin.

**Response is the player's.** The next turn answers the challenge as an incident with typed outcomes, reusing the `incidents.yaml` contract that 1C uses:

- `deflect` (Kristin answers or lies): cost `kristin_marked_by_patrol`; the officer lets it go for now and the patrol leaves early, via `SL-1A-C-R2`.
- `hand_over` (Kristin gives it up): the card moves to the officer by the player's own act; this is the player's choice, not an engine default. It routes to the existing goal-break go-on/go-back prompt, because `t_1a_1b` requires the card.
- `walk_out` (Kristin leaves with it): the officer follows her to the gate; cost `kristin_marked_by_patrol`, scene exit allowed at once.

**Persistent consequence:** `kristin_marked_by_patrol` is read by 1B. The existing `pursuit_1b` realization gains a gated first line, "The pursuers already have her description." Without the fact, 1B is unchanged. Open question: whether the incident contract can express a three-way free-text response; if not, the missing generic capability is a "challenge" incident kind, to be named in the plan before coding.

## 6. Plot edit for 1A.4

Replace the sentence "They do not open the drawer, so the card remains undiscovered; they discover and confiscate nothing." with:

> They do not open the drawer. If Kristin has not taken the card, or takes it out of their sight, they find nothing. If she takes it while an officer is watching, the officer challenges her, and the patrol's suspicion follows her out of the house.

and delete "Kristin conceals the memory card and pretends to know nothing." (the player decides whether she conceals or pretends). `storylets.md` SL-1A-C Available-when line "Hidden memory card, if currently carried or concealed" stays.

## 7. What this does not do

- No narrator rule is proposed. Observation scoping (plan step 5) is a projection change first; a rule is probed only if the projection alone fails.
- No new fabric or door-gap object.
- Not applied, not live-tested. Every claim above about player-visible behavior is a hypothesis until the replays in the plan.
