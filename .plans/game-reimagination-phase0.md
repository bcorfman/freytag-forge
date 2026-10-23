# Phase 0 design baseline: catalogue

Status: complete, 2026-10-22, baseline `984767a3`. The catalogue and revised
1C incident contract are complete. The accepted contract is in
[`1c-contract-result.md`](1c-contract-result.md). No code, package, or model
run was touched. Everything below was read from the files named; "not verified"
marks what was not.

Plan: [game-reimagination-plan.md](game-reimagination-plan.md). Package:
`data/stories/continuity-initiative/`.

## 1. Scene 1C as it plays today

Entry: `freight_terminal`, Brandon is a companion. Items: `transit_card`,
`kristin_truck`, `logistics_terminal` (fixed), `service_entrance` (fixed). The
area `observation_shaft` (parent `service_level`) exists. The group `captives`
(scoped aliases prisoners, captives) exists. Not declared as entities: tire
tracks, vents, the service schematic, the processing line, the prisoner
numbers, the recorded conference.

### Opportunities (reveals a player can earn in 1C)

| Reveal | Earned by (`earn_when`) | Requires | Establishes |
| --- | --- | --- | --- |
| `k_sl_1c_a_r1` | inspect docks, power, vents, tire tracks | none | `facility_proof` |
| `k_sl_1c_a_r2` | use the transit token at the service entrance | none | `facility_proof`, `service_level_access_known` |
| `k_sl_1c_b_r1` | compare/read/copy the prisoner numbers | `facility_proof` | `captives_confirmed_alive` |
| `k_sl_1c_b_r2` | search the processing line for Michelle | `facility_proof` | `captives_confirmed_alive`, `michelle_possible_sighting` |
| `k_sl_1c_c_r1` | read/use the logistics computer | proof + captives | `national_detention_network_known` |
| `k_sl_1c_c_r2` | play the Charles/Rebecca recording | proof + captives | `architects_strategy_known` |
| `k_bridge_1c_infiltration` | (bridge, no player action) | event below | `facility_infiltration_needed` |

Bridge event `bridge_1c_infiltration_needed` needs `facility_proof` and
`captives_confirmed_alive` and one of the two C facts. `t_1c_2a` fires on
`facility_infiltration_needed`.

### The terminal chain, measured from the files

- The shortest way out of 1C is three reveals in a fixed order: A (inspect or
  token), then B (read the numbers or search the line), then one of C (computer
  or recording). B requires A. C requires A and B. So at least three
  successful, ordered "access" actions are mandatory.
- Delivery text points the player at the next chore. A's two delivery texts
  end with the observation-shaft line, B's three end with "The logistics
  computer waits beside the service entrance." The cue for C1 is "may be worth
  reading".
- Pacing: `min_turns` 7, nudge 8, handoff 11. Pacing event `security_1c`
  (turn 3) and `terminal_sweep_1c` (turn 7) fire on the clock, not on any
  player action, and have no authored consequence beyond a line of prose.
- `captives_confirmed_alive` always asserts `evidence_gap_processing_numbers`
  as a cost (handoffs.yaml:83). The player is never offered a real chance to
  copy the numbers: plot 1C.2 says there is one, the delivery text says time
  ran out, and the gap is applied unconditionally. The gap is later read by a
  3C pacing line (pacing.yaml:58) and the completion matrix.
- C2 (the Charles/Rebecca recording) has no declared physical source in the
  scene. Plot 1C.4 gives it an offscreen origin only.

This is the exact "access and typing" shape the plan describes. It is
measured from the package; no player transcript of 1C was recovered, so how
boring it feels is not verified here.

### Techniques the repo already has for the plan's 1C fix

Per the recommend-only-proven-techniques rule, these exist and are tested:
`costs` on a delivery (the evidence-gap mechanism above), `companions`,
`character_placements`, `fixed` things, `scoped_aliases`, `on_assert` effects
(`move`, `reveal`, `accompany`, `set_axis`), alternative realizations that
establish the same fact (A-R1/A-R2, B-R1/B-R2). The plan's "copy the numbers
versus follow the lead" choice is close to the existing evidence-gap cost, but
the cost is currently automatic, not chosen. Whether a chosen cost needs new
engine support is not verified.

New declarations the plan's three example actions would need (grounding guide:
declare before offering): a copyable prisoner-number record or the processing
line as a thing/area, the transfer route as something Brandon can be asked
about, and a physical support for any terminal that is kept. None exist now.

## 2. Cue emitters (all stories' deliveries)

33 deliveries in `handoffs.yaml`; 32 have a `cue_text`; none has an
`escalation_text`. Per scene: 1A 1, 1B 4 (one without cue), 1C 4, 2A 1, 2B 5,
2C 3, 3A 3, 3B 5, 3C 7.

How retirement works now (read in `storygame/runtime/engine.py`):

- A cue is staged at the end of `_activate_pacing` for the first ranked
  missing bridge fact not yet in `delivered_cue_ids`, and only if
  `_cue_reveal_available` holds.
- `_cue_reveal_available` returns False when any `assert` cost of the delivery
  is already true, or when every reveal that establishes the fact is spent or
  already established. This is the 2026-10-20 memory-card fix; it is in the
  current source. It is keyed to the delivery's fact, not to the cue's target
  thing.
- A staged cue is dropped on a scene change (engine.py ~503-516). Whether
  queued cues, handoffs and recall are re-checked against final state just
  before the visible response is built is NOT verified; the plan lists that as
  a design target, not a finding.
- Only 1A (`memory_card_recovered`), 1C (`evidence_gap_processing_numbers`),
  2B (`evidence_gap_development_record`) and 3B (`evidence_gap_marked_site_list`)
  deliveries carry `assert` costs, so only those four have the "discovery done"
  guard. The other 28 retire only through reveal state.
- Evidence of the stale-cue defect: reproduced offline for 1A (completion plan,
  2026-10-20), fixed there. The user's original transcript was never found.
  No other scene's stale-cue case was reproduced.

## 3. Keep / merge / cut across the nine scenes (provisional)

Basis: plan section 4 and storylet titles. Only 1C was read in full; the other
scenes were not read beyond titles in this pass. ChatGPT should confirm or
overturn each tag against the files.

| Scene | Keep | Merge | Cut or make optional |
| --- | --- | --- | --- |
| 1A | A, B, C | E + F (one drawer discovery) | D (research files) |
| 1B | A, B, C | | |
| 1C | B (rewrite as the incident) | A into the entry situation | C: the national-network reveal and the recording become outcomes or move later; the mandatory chain goes |
| 2A | A, C | B + E into one inspection confrontation | |
| 2B | A, B | | C optional |
| 2C | A, B, C, D | | |
| 3A | A, C, D | B into A | E (exposition) |
| 3B | A, B, C, D | E (travel) into B | |
| 3C | A, C, G | F into C (evacuation completion event); B into A; D into aftermath | E (Phase Two hook, optional sequel) |

Counts: 40 storylets (1A 6, 1B 3, 1C 3, 2A 4, 2B 3, 2C 4, 3A 5, 3B 5, 3C 7).
The reveal in 1C.4 (Charles and Rebecca's plan) is plot canon, so cutting it
from 1C means relocating it, which is a decision for Brandon.

## 4. Unknowns carried forward

- The player-visible 1C transcripts (terminal boredom) were not recovered.
- Whether `escalation_text` being absent for all 33 deliveries makes stage-2
  cues emit nothing: not verified.
- Display-time cue recheck: not verified.
- Everything in section 3 beyond 1C is title-level.

## 5. Prompt for ChatGPT Desktop (1C contract)

Follows the rule that ChatGPT establishes the evidence and the causes. Paste
as is:

> Read `AGENTS.md`, then `.plans/game-reimagination-plan.md` (sections 1, 4 and
> the Phase 0 row of section 8), then `.plans/game-reimagination-phase0.md`.
> The catalogue in the second file is a set of unverified leads. Check it
> against the 1C material in `data/stories/continuity-initiative/` yourself,
> and correct it where it is wrong.
>
> Then produce the Phase 0 deliverable for scene 1C: the revised 1C incident
> contract the plan describes (entry situation, objective, opportunities, two
> supported outcomes with their costs, successors into 2A, and the payoff).
> Follow `docs/world-model-grounding.md` and `docs/narrator-writing-guide.md`.
> List every declaration that would be new. Return text only; do not edit
> files.

## 5b. Review of ChatGPT's contract (`1c-contract-result.md`, 2026-10-22)

Checked against the package and `engine.py`. "Verified" means I read the line
cited; the rest are open questions for ChatGPT's next round.

Accepted: the catalogue corrections (captives group has no 1C placement; the
recording has no physical source; the gap is automatic) match what I found.
The two-outcome shape and the "converge on `t_1c_2a`" decision fit plan section 4.

Gaps, verified:

1. **`min_turns` floor.** `_apply_authored_transition` skips any transition
   until `turns_since_entry >= min_turns` (engine.py:994). 1C's floor is 7, so
   "withdraw once the choice is made" still waits for turn 7. Lowering it is
   blocked by `loader.py:819`, which rejects a pacing event whose `at_turn` is
   above `min_turns`; `terminal_sweep_1c` is at turn 7. The contract lists no
   pacing change.
2. **Existing automatic gap cost.** `captives_confirmed_alive` carries the
   `evidence_gap_processing_numbers` cost on the delivery (handoffs.yaml:83).
   Outcome 1 also asserts `captives_confirmed_alive`, so it would also take the
   gap unless that cost is removed or made outcome-specific. The contract adds
   "a new cost binding" but never removes the old one.
3. **Bridge rule.** `bridge_1c_infiltration_needed` still requires
   `national_detention_network_known` or `architects_strategy_known`
   (storylet-routes.yaml:2698-2712). The contract says to revise it but does not
   say what the new activation facts are.
4. **Downstream use of the two dropped facts.** Neither fact is read outside 1C
   (only world/knowledge definitions, the 1C storylet and the bridge), so
   removing them from the path breaks no later scene. The story content they
   carry (national network, Charles/Rebecca strategy) is restated in plot.md for
   3C (lines 849-909) and 3B (790-794), so relocation is likely cheap, but the
   contract leaves the destination open.

Gaps, from reading the contract (not engine-verified):

5. **Redundant facts.** `service_route_unresolved` restates "not
   `service_level_access_known`", and `processing_numbers_copied` restates
   "not `evidence_gap_processing_numbers`". Two facts for one state can both be
   true or both false. Facts are the sole mutable truth.
6. **No default when the player does neither.** No pressure fact or deadline
   outcome is declared. Pacing events `security_1c`/`terminal_sweep_1c` are
   clock-driven and not tied to the choice, and the plan says deadlines must
   resolve with an honest cost, not a granted outcome.
7. **Free observation vs choice.** Both outcomes assert
   `captives_confirmed_alive`, but plan section 4 makes studying the prisoners a
   free, unconditioned observation. Outcome 2 also has Kristin follow the
   route through the service entrance while the payoff says they withdraw.
8. **Why can't both be done?** Outcome 1's cost says the route stays unresolved,
   yet Kristin still holds the transit token that opens the entrance. The
   fiction for that is not stated.
9. **No consumer for the earned advantage.** Nothing in 2A-3C reads
   `processing_numbers_copied`; 3C only has a line for the gap (pacing.yaml:58).
   A choice with no later effect fails plan section 4's "carry the choice".
10. **Dropped existing effects.** `michelle_possible_sighting` and the
    `trust_brandon` change in SL-1C-B are not in either outcome.
11. **Needs features that do not exist yet.** The traversable-route
    declaration and a per-outcome cost need engine support (plan sections 6-7);
    whether the current delivery `costs` can carry per-outcome costs is not
    verified. 2A's entry variants need 2A read first (not read).

## 5c. Historical prompt for ChatGPT Desktop (second round, revise the 1C contract)

Pointers only; ChatGPT establishes the causes itself. Paste as is:

> Read `AGENTS.md`, `.plans/game-reimagination-plan.md`, and your own draft
> `.plans/1c-contract-result.md`. Check the draft against the package in
> `data/stories/continuity-initiative/`, `storygame/runtime/engine.py` and
> `storygame/story_package/loader.py`. Establish for yourself whether it can be
> implemented as written and whether it meets the plan's acceptance criteria.
> Then return a revised contract. Text only; do not edit files.

## 6. Phase 0 exit check

- Catalogue of 1C opportunities and all cue emitters: done (sections 1 and 2).
- Keep/merge/cut tagging: done, provisional (section 3).
- Terminal repetition and stale-cue cases from available evidence: done from
  package and plan records; no transcripts exist (section 4).
- Revised 1C incident, two outcomes, successors, payoff: accepted in
  [`1c-contract-result.md`](1c-contract-result.md). It resolves the minimum
  turn floor, makes the evidence-gap cost outcome-scoped, replaces redundant
  negative facts with positive state, defines an honest missed-window outcome,
  preserves the existing sighting/trust effects, and names the 2A consumers of
  both advantages.
- Phase 1 is explicitly blocked on typed incident outcomes, outcome-scoped
  costs, and the minimum traversal contract. Those are implementation
  requirements, not unresolved Phase 0 design questions.
