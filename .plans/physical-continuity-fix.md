# Physical continuity and pacing fix

Status: Stage A has shipped. Stage B is an audit at review depth; each scene
becomes its own brief when it is picked up. Stage C is unblocked and not started:
Brandon settled the budget question on 2026-09-08 (see "The budget decision").
This plan fixes continuity defects found while reviewing
`missed-obligation-escalation.md`; it does not implement that design.

## Objective

Make every scene narratively continuous and mechanically truthful when the
player investigates in different orders:

- Every bridge and ending says only what the currently established facts and
  physical items support.
- The patrol's and every other scheduled pressure's search has an authored
  scope and cannot discover or confiscate an unexposed item.
- Each scene gives a slower player a visible pressure cue and a real response
  window when that scene has a timed external threat.

The fix stays story-agnostic in the runtime. Physical custody, authored
placement, knowledge prerequisites, and pressure timing are package data; the
engine only validates and applies them.

| Stage | What it is | State |
|---|---|---|
| **A — Scene 1A physical chain** | Card before recording, custody fact, bounded patrol search, laptop language, generic engine support. | Shipped. |
| **B — Bridge-claim audit, 1B–3C** | Bridges and handoffs that narrate facts their activation does not guarantee, stale scene item declarations, and the 3C resolution cascade. | Open, one scene at a time as problems surface. |
| **C — Pacing** | Visible pressure events for scenes that lack them, and the two-turn reaction window. | Unblocked, not started. |

---

# Stage A — shipped

Scene 1A is physically continuous. For reference, the generic mechanisms Stage B
builds on now exist:

- **Positively named custody fact.** `memory_card_in_kristins_custody` is
  asserted by the recovery realizations and by the handoff fallback's `costs`,
  and is a trigger on `t_1a_1b`. `required_dependencies` stays a loss guard, not
  a possession proof. An absent fact satisfies `equals: false`, so a positively
  named fact needs no story-start seeding.
- **Dead `equals: false` triggers are rejected.** The loader
  (`storygame/story_package/loader.py`) rejects a transition trigger using
  `equals: false` on a fact the package never asserts true.
- **Guarded placements.** An `item_placements` entry may carry
  `while_fact_false: <fact>`, and the engine stops stating it once that fact is
  true. A bare string keeps its old meaning.
- **Bounded pressure search.** The 1A.4 patrol checks the work area and asks
  about research; it does not open drawers and confiscates nothing.

---

# Stage B — Bridge-claim audit, Scenes 1B–3C

Findings at review depth, re-verified against the package on 2026-09-13. The
recurring defect is one shape: **a bridge or handoff narrates facts its
activation rule does not guarantee.** Take them one scene at a time, as each
surfaces in play, and write the per-scene brief then.

Resolved since the first audit, and dropped from this list: the 1C bridge no
longer claims national scope, the 3A bridge no longer claims the experiment
stakes or the expiring-code deadline, and the 3B bridge no longer claims
Brandon's confession or Rebecca's data.

The second recurring defect is a **stale scene item declaration**. `memory_card`
is still declared in 2B, 2C and 3C, where the operative evidence is the JANUS
archive, and `override_codes` is still declared in 3B, which never uses it.
Removing a declaration is subtractive and removes the mechanism that lets the
narrator reach for the wrong object.

### Scene 1B — The Lead in the Park

- `bridge_1b_departure` needs `park_pursuit_resolved` plus any two of
  `transport_route_identified`, `brandon_identified` and `missing_may_be_alive`,
  so it can fire without the route. Yet the `t_1b_1c` bridge text and the
  `transport_route_identified` fallback both say the transit card opened the
  route. Require the transit-card state and the route fact before `t_1b_1c`, or
  make the bridge prose not depend on them. A Brandon-only clue may establish
  trust or survival, but cannot make the freight route physically available.
- The transit card has no authored placement beneath the bench. Add one behind a
  `while_fact_false` custody guard.

### Scene 2A — False Identities

Not re-verified on 2026-09-13; carried from the first audit.

- The false-inspector credentials must be visibly created by `SL-2A-B` before the
  supervisor confrontation; the bridge must not imply access existed earlier.
- Rebecca's observation is hidden world state. Keep her identity hidden. No
  automatic capture may occur merely because the player explored slowly.
- Preserve the two-part bridge requirement and test both the normal route and
  the slow handoff, including the world-only observation effect.

### Scene 2B — Evidence and Betrayal

- `bridge_2b_archive_crisis` completes from `janus_evidence` plus any two of
  three later facts, but the `t_2b_2c` bridge text claims all of them: Michelle's
  selection, Kristin as bait, Brandon's name, and Michelle's resistance. Use
  conditional-neutral bridge prose plus a test per two-fact combination.
- Remove the stale `memory_card` scene item.
- Keep this a deliberate investigation window; do not invent an arrest.

### Scene 2C — The Trap Closes

- The `t_2c_3a` bridge says Michelle's coded message established the combined
  plan, while `bridge_2c_combined_plan` requires only `purge_clock_started` and
  `evidence_ready_to_transmit`. Require the message fact for that claim, and let
  a handoff deliver the message and its route coherently.
- Introduce Rebecca's secured office and the relay as the concrete route before
  the player is expected to pursue them (not re-verified).
- Remove the stale `memory_card` scene item.

### Scene 3B — The Battle for the Broadcast

- Remove the stale `override_codes` scene item declaration.

### Scene 3C — Exposure and Escape

- **Highest-value item in Stage B.** `_apply_canonical_route_events`
  (`storygame/runtime/canonical_events.py`) commits each event's operations and
  marks it fired before checking the next, and the six resolution events are
  declared in chain order. Once the initial facts hold, exposure, archive
  recovery, escape, network consequences, Phase Two and completion can all
  commit in one pass, before the optional storylets narrate them. Sequence the
  resolution events, or require each one's validated, player-visible realization
  before it commits. Each outcome must be atomic with its physical custody
  change, especially Rebecca's archive and the prisoner-location copies.
- The central portable archive has no world item, and `memory_card` is declared
  instead. Add `portable_archive` with custody beginning at Rebecca, replace the
  stale declaration, and introduce it before Kristin is asked to secure or copy
  it.

### Shared custody rule for Stage B

- One canonical custody fact per item, positively named, as in Stage A. Never use
  an item ID alone as proof of possession.
- A fallback that supplies a fact must also supply the corresponding physical
  item, or use bridge prose that does not require it.
- Every bridge and handoff states only facts established in that candidate.
- Add authored placements per item only as each scene is picked up, and only
  behind a `while_fact_false` guard.

---

# Stage C — Pacing

## The reaction-window rule

- A visible timed threat is announced before it materially constrains the
  player's next action.
- At least two complete player turns follow the threat's arrival or escalation.
- Every authored storylet's `target`/`latest_turn` fits inside the scene's
  handoff window, with a turn after the last one so a scene never ends on the
  turn that delivers its final content.
- Scene windows are sized independently; nothing is compressed to preserve a
  total.

## What the rule costs

Applying the rule arithmetically — handoff = max(last storylet turn + 1, threat
arrival + 2), with authored storylet turns unchanged:

| Scene | Last storylet | Threat arrival | Today | Rule-derived |
|---|---|---|---|---|
| 1A | 4 | 3 (`SL-1A-C`) | 5 | **5** |
| 1B | 3 | 3 (ambush) | 4 | **5** (+1) |
| 1C | 3 | 2 (new) | 4 | **4** |
| 2A | 3 | 2 (new) | 4 | **4** |
| 2B | 3 | none | 4 | **4** |
| 2C | 3 | 2 (`purge_2c`) | 4 | **4** |
| 3A | 3 | 3 (`override_deadline_3a`) | 5 | **5** |
| 3B | 3 | 3 (`destruction_3b`, moved from 4) | 5 | **5** |
| 3C | 5 | 2 (new) | 5 | **6** (+1) |
| | | | **40 = 1800 s** | **42 = 1890 s** |

Seven of nine scenes are already compliant. The real work is that four scenes
have **no visible timed threat at all**, so a slow player gets no warning before
the handoff carries them. `pacing.yaml` still holds only the original four
events. The change:

- add `pursuit_1b` (turn 2) announcing that patrols are closing in, before the
  `SL-1B-C` ambush; the event must not resolve the pursuit;
- add a security escalation in 1C (turn 2) — access alarm or guard sweep — that
  does not reveal the facility's later national purpose;
- add visible security scrutiny in 2A (turn 2), keeping Rebecca hidden;
- add a collapse escalation in 3C (turn 2);
- move `destruction_3b` from turn 4 to turn 3; it announces worsening danger and
  does not complete the destruction or sacrifice Brandon.

1A keeps `2 / 4 / 5` with `pressure_1a` at turn 2.

## The budget decision — settled

The loader enforces `sum(handoff_after_turns) * 45 <= budget_seconds`, and the
package sits at exactly 1800 s. The rule-derived schedule needs **1890 s
(31.5 minutes)**.

Do **not** remove `budget_seconds`. It is the only guard on total playtime and a
standing design constraint; the loader enforces a ceiling, so scene-local sizing
does not require removing it.

**Decision (Brandon, 2026-09-08): raise the budget to 1890.** This buys the
reaction window in 1B and the sequenced ending in 3C for 90 seconds of
worst-case playtime. The rejected alternative, holding 1800 and trimming two
turns, would have compressed 3C's five authored storylets into four and worked
against the 3C resolution sequencing that Stage B calls its highest-value fix.
As of 2026-09-13 `pacing.yaml` still reads `budget_seconds: 1800`.

### The raise cannot land on its own

`tests/test_scene_relative_pacing.py:98` asserts the handoff sum **equals** the
budget, so `budget_seconds: 1890` with windows still summing to 40 turns fails.
The budget line, the 1B window (`2/3/4` → `2/4/5`) and the 3C window (`2/4/5` →
`2/4/6`) are one atomic change, landing together with:

- the hard-coded `expected_windows` dict in `tests/test_scene_relative_pacing.py`;
- the over-budget probe at `tests/test_scene_relative_pacing.py:177`, which
  replaces the literal `"budget_seconds: 1800"` with `1799` and must become
  `1890` → `1889`.

While that test is open, change the equality at line 98 to `<=`. The budget is a
ceiling on the worst case, not a target; the per-scene `expected_windows` dict is
already the real assertion about intended timing.

## Stage C verification

- Assert each scene's schedule, and that each threat is visible before the
  player's next response, leaving two complete turns.
- Assert a pressure event can coexist with a same-turn recovery, because it
  represents approaching external pressure, not a completed search.
- Assert pacing validation is scene-local: changing one scene's window requires
  no compensating change elsewhere, and the package still loads against
  `budget_seconds`.
- Keep the full canonical journey and scene-relative pacing tests green.

---

## Inherited open questions

From `missed-obligation-escalation.md`:

- **Closed by Stage A:** Q5 (retraction discipline).
- **Assumed settled, per that plan's own answers:** Q11 (one player input plus
  its resolution is one turn) and Q12 (a cue or complication rides on the
  ordinary turn and does not reset the counter). Stage C's arithmetic depends on
  both.
- **Not required by this plan, and not assumed:** Q2 (`latest_turn` expiry
  semantics) and Q6 (early exit for a scheduled complication). If Stage C later
  adopts expiry, revisit the table above.

## Files expected to change

**Stage B** — per scene, as picked up: `plot.md` (bridge text, item
declarations, placements), `world.yaml` (`portable_archive`), `handoffs.yaml`,
`storylet-routes.yaml`, `storylets.md`, the 3C sequencing in
`storygame/runtime/canonical_events.py` if it is fixed in the engine rather than
in route data, and the matching tests.

**Stage C** — `pacing.yaml` (four new events, `destruction_3b` retimed, 1B and 3C
windows, `budget_seconds: 1890`) and `tests/test_scene_relative_pacing.py`
(window dict, the budget probe, and `==` relaxed to `<=`), as one atomic change.

Record each stage's verification outcome here. Touch `docs/testing-runbook.md`
only if a stage changes how verification is run.
