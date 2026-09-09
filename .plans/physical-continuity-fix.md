# Physical continuity and pacing fix

Status: Stage A is specified to implementation depth and ready for Ringer.
Stage B is an audit at review depth; each scene becomes its own brief when it is
picked up. Stage C is unblocked: Brandon settled the budget question on
2026-09-08 (see "The budget decision"). This plan fixes the continuity defects
found while reviewing `missed-obligation-escalation.md`; it does not implement
the missed-obligation escalation design itself.

## Objective

Make every scene narratively continuous and mechanically truthful when the
player investigates in different orders:

- Kristin cannot hear a recording before she has the memory card.
- The patrol's scheduled pressure does not occupy the same action as a private
  card/recording investigation, and never changes who holds the card.
- The patrol's search has an authored scope and cannot discover or confiscate an
  unexposed item.
- The story consistently treats the evidence as files on the memory card.
- "Her laptop" unambiguously means Michelle's laptop; Kristin's reading device
  is explicit.
- Each scene gives a slower player a visible pressure cue and a real response
  window when that scene has a timed external threat.
- Every bridge and ending says only what the currently established facts and
  physical items support.

The fix stays story-agnostic in the runtime. Physical custody, authored
placement, knowledge prerequisites, and pressure timing are package data; the
engine only validates and applies them.

## Why this is three stages, not one plan

The original draft mixed three jobs with different risk, different verification,
and different decision-makers. They are separated here so the ready part is not
blocked behind the undecided part.

| Stage | What it is | Blocked on |
|---|---|---|
| **A — Scene 1A physical chain** | The card-before-recording defect, the custody fact, the bounded patrol search, the laptop language, and the generic engine support all of it needs. | Nothing. Ready to specify as Ringer tasks. |
| **B — Bridge-claim audit, 1B–3C** | Bridges and handoffs that narrate facts their activation does not guarantee, plus stale scene item declarations. | Nothing, but authored one scene at a time as problems surface, not in one sweep. |
| **C — Pacing** | Visible pressure events for the scenes that lack them, and the two-turn reaction window. | Nothing. `budget_seconds` rises to 1890; ship after Stage A. |

Stage A is the defect a player hits in the first five minutes. Ship it first.

---

# Stage A — Physical continuity in Scene 1A

## The defect, precisely

`SL-1A-B-R2` (`storylet-routes.yaml:452`) asserts `michelle_warning_known` with
no physical prerequisite, so the recording can be heard while the card is still
taped under the drawer. `SL-1A-D` is titled "The Memory Card Under the Drawer"
and activates only after that recording was already heard, so on the
warning-first path the story finds the card twice. Nothing in the package
distinguishes *card still taped under the drawer* from *card in Kristin's
hands*.

## A1. One custody fact, positively named

Add a single physical fact. Name it for what it gates, not for a location:

    memory_card_in_kristins_custody

Rejected alternative: `memory_card_still_in_house`, used as `equals: false`.
"Not in the house" is not "Kristin has it" — a confiscated card, a dropped card,
and a card left in the truck all satisfy it. It also forces every loss to be
written twice (retract the location fact *and* mark the item unavailable), which
is exactly the two-sources-of-truth desynchronisation the fact was meant to
avoid. One positively-named custody fact is asserted on recovery and retracted
on loss, in one place, by one operation.

This also keeps `missed-obligation-escalation.md` decision 6 intact: the fact
that reaches the narrator names the state that *is* true.

**Why the naming decides whether seeding is needed.** `predicate_matches`
(`storygame/runtime/validation.py:143-150`) treats an absent fact as satisfying
`equals: false`:

```python
present = list(facts.matching(predicate.fact_id))
if not present:
    # Route activation uses an absent fact as the ordinary false state.
    return predicate.equals is False
```

So any guard written as "the card is not yet recovered" passes trivially until
something asserts the fact. With a positively-named custody fact this works in
our favour — absent means *not held*, which is the correct starting state — and
**no story-start seeding mechanism is required at all.** That removes the new
engine bootstrap the earlier draft asked for.

The hazard is worth a loader rule anyway, because it generalises zero-shot to
any package:

- **Loader rule:** a fact used with `equals: false` in a transition trigger must
  be asserted `true` somewhere in the package, or the trigger is dead weight
  that can never fail. Reject with that reason.

## A2. Make the transition require custody

`t_1a_1b` currently declares `required_dependencies: [memory_card]`, but
`transition_dependencies_available` (`validation.py:325-335`) only treats a
dependency as unavailable when its entity is `destroyed` or `incapacitated`. A
dependency is therefore a loss guard, not a possession proof. So:

- Add `{fact_id: memory_card_in_kristins_custody, equals: true}` to `t_1a_1b`
  triggers.
- Keep `required_dependencies: [memory_card]` as the generic unavailable-item
  guard. Do not repurpose it.
- Any explicit loss or confiscation uses the generic unavailable-item operation
  *and* retracts the custody fact, in the same accepted operation.

## A3. The placement hazard the earlier draft missed

`item_placements` is a static per-scene mapping (`models.py:194`) rendered into
the narrator prompt on every turn of the scene:

```python
def _placement_rules(self) -> list[str]:
    return [f"{scene_items[item_id].name} is {placement}." for item_id, placement
            in self._current_scene().item_placements.items() ...]
```
(`storygame/runtime/cloudflare.py:365-371`)

Authoring `memory_card: taped beneath the workstation drawer` would keep telling
the model the card is under the drawer after Kristin has pocketed it — the same
object-in-two-places defect commit `6f28f77` just fixed. The card's placement
must stop being stated once custody changes.

**Recommended:** give a placement an optional fact guard, so the engine stops
stating a placement that is no longer true:

```yaml
item_placements:
  michelle_phone: on the kitchen floor
  memory_card:
    placement: taped beneath the workstation drawer
    while_fact_false: memory_card_in_kristins_custody
```

`_placement_rules` filters on the guard; a bare string keeps today's meaning, so
existing packages and `michelle_phone` are untouched. This is generic package
data, not a Scene 1A branch in the engine.

**Fallback if we want zero engine change in this stage:** omit the card from
`item_placements` entirely and let the realization text carry its location. That
is subtractive and safe, but it gives up the grounding that made `6f28f77`
work, so prefer the guard.

The same hazard applies to Stage B's transit card (1B) and portable archive
(3C). Do not author those placements until the guard exists.

## A4. Make every evidence realization physically reachable

- `SL-1A-B-R1`: Kristin finds the card, secures it, then reads its
  recording/files. Add `assert memory_card_in_kristins_custody`.
- `SL-1A-B-R2`: Kristin finds and secures the card *before* playing the warning.
  Add `assert memory_card_in_kristins_custody`.
- Add the custody prerequisite to the recording's knowledge entry, so a
  recording candidate cannot be selected while the card is unrecovered.
- `SL-1A-D`: retitle and rewrite from "the card under the drawer" to "the
  remaining files on the recovered card." Its activation already requires
  `michelle_warning_known == true`, which after A4 implies custody; state the
  custody condition explicitly anyway so the guard does not depend on that
  chain holding.
- Knowledge statements and route operations must agree exactly: a statement
  saying Kristin holds or reads the card must have the operation that makes it
  true.

## A5. Give the patrol an authored, bounded search

- Rewrite Scene 1A.4 prose (`plot.md:126-136`) to distinguish a quick welfare
  check and targeted office inspection from a forensic ransack. State what the
  patrol searches and what it does not open. The drawer stays concealed because
  the officers check the work area and ask about research; they do not search
  every taped underside.
- If Kristin already has the card, the realization creates scrutiny and a
  concealment/departure problem. **It must not retract custody.**
- If the player explicitly hands over or exposes the card, validate that
  normally, including the unavailable-dependency warning. The pressure event
  itself never mutates custody.
- Keep the patrol ignorant of Kristin's knowledge. It reacts to its own
  timetable and to physical state, never to epistemic facts. This is the causal
  rule from `missed-obligation-escalation.md`; do not weaken it.

## A6. Resolve the laptop and file language

- `plot.md:95` reads "Her laptop and work bag are missing." Replace with
  "Michelle's laptop and work bag."
- Kristin's truck laptop already appears in 1A.2 prose ("She plugs the memory
  card into her laptop out in her truck"), but is not a world item and is not in
  the entry text. Add it as an authored item with placement "in Kristin's truck"
  so it exists before any card-reading action, rather than being introduced by
  the action that needs it.
- Replace every reference to packing Michelle's *files* with recovering,
  securing, carrying, or reading the *memory card*.
- Keep `handoffs.yaml`'s required phrases aligned: a handoff may recover the card
  and expose its information, but must not imply loose papers or Michelle's
  laptop.

## A7. Runtime changes Stage A needs

1. Document the turn boundary: pacing activates at the start of a player turn,
   then the provider resolves that turn. A pressure fact at turn *n* describes
   the situation entering turn *n*; it cannot consume Kristin's action or invent
   an already-completed search.
2. Validate physical prerequisites for knowledge candidates and selected
   realizations before applying operations. An unavailable recording/card
   selection fails closed, committing no facts and not advancing the scene.
3. Apply custody changes atomically with the accepted realization. The same
   operation contract is available to the handoff path.
4. Handoff simulation uses the same candidate state and custody rules as ordinary
   realization. The fallback either recovers the card and asserts custody in the
   same accepted operation, or delivers no card-derived information and does not
   transition.
5. Optional placement guard per A3.
6. Preserve the narrator contract: the engine selects one realization, the
   provider sees no alternatives, and no fact changes after narration renders.

Nothing here is Scene 1A-specific in the engine.

## A8. Verification

### Deterministic package tests

- Loader accepts the custody fact, guarded item placement, and custody
  operations.
- Loader rejects a recording knowledge entry with no custody prerequisite.
- Loader rejects a physical statement or operation referencing an unknown
  item/fact.
- Loader rejects a transition trigger using `equals: false` on a fact the package
  never asserts true (A1).
- Loader rejects a handoff whose fallback omits the card phrases its delivery
  contract requires.
- Loader verifies every Scene 1A realization leaves a valid path to `t_1a_1b` or
  to the declared handoff.
- The guarded placement is absent from the rendered prompt once custody is true,
  and present before.

### Runtime sequence tests

Player inputs are imperative commands:

- `Search the kitchen for signs of a struggle.`
- `Search beneath the marked drawer for Michelle's memory card.`
- `Play the damaged recording from the memory card.`
- `Watch the patrol for signs that it knows about Michelle's research.`
- `Read the remaining files from the memory card in the truck.`

Cover these paths:

1. **Fast path** — recover the card and complete B-R1; the scene may exit after
   its minimum, and C/D/handoff do not fire unnecessarily.
2. **Warning-first path** — B-R2 establishes custody and the warning; D later
   reads the remaining files and supplies the park lead. The recording is
   impossible before B-R2.
3. **Slow path** — the card stays under the drawer; the patrol performs only the
   authored bounded search; the handoff recovers and delivers only the
   indispensable information, with its cost. Assert the patrol cannot confiscate
   or reveal the card merely because the player was slow.
4. **Custody path** — once recovered, the patrol event alone cannot retract
   custody or force a confession; only explicit player-caused exposure does.
5. **Laptop path** — files are read from Kristin's established truck laptop,
   never Michelle's missing laptop.

Also: exercise the optional storylets in every valid order; no order may expose
the recording before custody. Assert a transition is rejected when the continuity
facts are present but custody is neither established nor atomically supplied by
the handoff. Update the existing "shadow timeline" test so it no longer offers
`k_sl_1a_b_r2` for a recording search before custody is true.

## A9. Stage A completion criteria

- No valid provider response can commit or narrate access to the recording
  before card custody.
- The patrol pressure has one temporal interpretation and never makes Kristin
  perform an impossible simultaneous action.
- Patrol search outcomes come from authored physical state and search scope, not
  narrator invention.
- Every mention of the evidence identifies the memory card as its source, and
  Kristin's reading device is explicit.
- No prompt states the card's drawer placement after custody changes.
- All Scene 1A paths stay reachable and preserve player agency.

---

# Stage B — Bridge-claim audit, Scenes 1B–3C

These are findings at review depth, not specifications. The recurring defect is
one shape: **a bridge or handoff narrates facts its activation rule does not
guarantee.** Take them one scene at a time, as each surfaces in play, and write
the per-scene brief then — do not author all of them up front.

The second recurring defect is a **stale scene item declaration**: `memory_card`
is listed in 2B, 2C, and 3C (`plot.md:383,469,703`) where the operative evidence
is the JANUS archive. Removing the declaration is subtractive and removes the
mechanism that lets the narrator reach for the wrong evidence.

### Scene 1B — The Lead in the Park

- `bridge_1b_departure` can be satisfied by any two of three facts, but the
  `transport_route_identified` fallback (`handoffs.yaml:20-28`) always claims the
  transit card opened the route. Require the transit-card state and the route
  fact before `t_1b_1c`; make the slow handoff recover the card and route
  together. A Brandon-only clue may establish trust or survival, but cannot make
  the freight route physically available.
- The transit card has no authored placement beneath the bench. Add one once the
  A3 guard exists.

### Scene 1C — Discovery of the Facility

- The bridge requires facility proof and living captives, but its fallback
  mentions national scope and the architects' strategy as though guaranteed.
  **Recommended:** rewrite the fallback to claim only the active facility, living
  captives, and the need for deliberate infiltration. The next scene can discover
  the broader network.
- The entry names the transit card; make sure it does not read as newly found
  here.

### Scene 2A — False Identities

- The false-inspector credentials must be visibly created by `SL-2A-B` before the
  supervisor confrontation; the bridge must not imply access existed earlier.
- Rebecca's observation is hidden world state. Keep her identity hidden. No
  automatic capture may occur merely because the player explored slowly.
- Preserve the two-part bridge requirement: false identities plus authored
  observation pressure produce restricted corridor access. Test both the normal
  route and the slow handoff, including the world-only observation effect.

### Scene 2B — Evidence and Betrayal

- `bridge_2b_archive_crisis` completes from JANUS evidence plus any two of three
  later facts, but its text claims all of Michelle's selection, Kristin's bait
  status, Brandon's name, and Michelle's resistance. **Recommended:**
  conditional-neutral bridge prose plus a test per two-fact combination.
- Remove the stale `memory_card` scene item.
- Keep this a deliberate investigation window; do not invent an arrest. Make the
  archive's security and the need to move on visible in the entry and handoff
  text instead.

### Scene 2C — The Trap Closes

- The bridge says Michelle's coded message established the combined plan, while
  activation requires only the purge and evidence facts. **Recommended:** require
  the message fact for the authored claim, and let a handoff deliver that message
  and its route coherently.
- Introduce Rebecca's secured office and the relay as the concrete route before
  the player is expected to pursue them.
- Remove the stale `memory_card` scene item; the operative evidence is the 2B
  archive.

### Scene 3A — Reaching Michelle

- The bridge claims the experiment stakes and the expiring-code deadline though
  activation requires only Michelle's arrival and the uprising. Rewrite to the
  guaranteed facts. Keep the optional-code route from blocking the transition.
- The senior official and expiring override codes appear only after actions could
  use them. Introduce that resource in the first medical-level investigation, and
  model the codes as optional leverage.

### Scene 3B — The Battle for the Broadcast

- `override_codes` is a declared scene item that this scene never uses
  (`plot.md:631`). Remove the declaration.
- Tie the relay-opening fact to Brandon physically and narratively. The broadcast
  bridge may mention only the subset of human control, Rebecca's data, Charles's
  abandonment, and Brandon's confession that is actually present. Add a slow-path
  test that cannot invent Brandon's confession merely because the relay is open.

### Scene 3C — Exposure and Escape

- **Highest-value item in Stage B.** The resolution pass can fire all six
  resolution events in one turn once the initial facts are present, crediting
  exposure, archive recovery, escape, network consequences, and Phase Two before
  the optional storylets narrate them. The ending is where player satisfaction is
  decided. Sequence the resolution events, or require each one's validated,
  player-visible realization before it commits. Each outcome is atomic with its
  physical custody change, especially Rebecca's archive and the prisoner-location
  copies.
- The central portable archive has no world item and `memory_card` is declared
  instead. Add `portable_archive` with custody beginning at Rebecca, replace the
  stale declaration, and introduce it before Kristin is asked to secure or copy
  it.

### Shared custody rule for Stage B

- One canonical custody fact per item, positively named, per A1. Never use an
  item ID alone as proof of possession.
- A fallback that supplies a fact must also supply the corresponding physical
  item, or use bridge prose that does not require it.
- Every bridge and handoff states only facts established in that candidate.
- Add authored placements per item only as each scene is picked up, and only
  behind the A3 guard.

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

## What the rule actually costs

The earlier draft proposed windows summing to 62 turns. Applying the rule
arithmetically — handoff = max(last storylet turn + 1, threat arrival + 2), with
authored storylet turns unchanged — gives this:

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

Seven of nine scenes are already compliant. The real work is not retiming — it
is that four scenes have **no visible timed threat at all**, so a slow player
gets no warning before the handoff carries them:

- add `pursuit_1b` (turn 2) announcing that patrols are closing in, before the
  `SL-1B-C` ambush; the event must not resolve the pursuit;
- add a security escalation in 1C (turn 2) — access alarm or guard sweep — that
  does not reveal the facility's later national purpose;
- add visible security scrutiny in 2A (turn 2), keeping Rebecca hidden;
- add a collapse escalation in 3C (turn 2);
- move `destruction_3b` from turn 4 to turn 3; it announces worsening danger and
  does not complete the destruction or sacrifice Brandon.

1A therefore keeps `2 / 4 / 5` with `pressure_1a` at turn 2. The earlier draft
described `4 / 8 / 10` as "the already chosen schedule"; nothing in the
repository had chosen it, and the rule does not require it.

## The budget decision — settled

`loader.py:420-425` enforces `sum(handoff_after_turns) * 45 <= budget_seconds`,
and the package sat at exactly 1800 s. The rule-derived schedule needs **1890 s
(31.5 minutes)** — two turns more than the previous 30-minute ceiling.

Do **not** remove `budget_seconds`. It is the only guard on total playtime, the
ceiling is a standing design constraint, and the loader enforces a ceiling
rather than forcing the windows to sum to a total, so scene-local sizing does
not require its removal. The earlier draft's removal proposal is withdrawn.

**Decision (Brandon, 2026-09-08): raise the budget.** `budget_seconds` becomes
**1890** (31.5 minutes), buying the reaction window in 1B and the sequenced
ending in 3C for 90 seconds of worst-case playtime. The rejected alternative was
holding 1800 and trimming two turns, which would have compressed 3C's five
authored storylets into four and worked against the 3C resolution sequencing
that Stage B calls its highest-value fix.

Stage C is unblocked.

### The raise cannot land on its own

`tests/test_scene_relative_pacing.py:97` asserts the sum **equals** the budget
exactly:

```python
assert sum(window.handoff_after_turns for window in windows.values()) * 45 == PACKAGE.pacing.budget_seconds
```

So `budget_seconds: 1890` with the handoffs still summing to 40 turns fails that
assertion. The budget line, the 1B window (`2/3/4` → `2/4/5`), and the 3C window
(`2/4/5` → `2/4/6`) are one atomic change, landing together with:

- the hard-coded `expected_windows` dict at `tests/test_scene_relative_pacing.py:78-90`;
- the literal `"budget_seconds: 1800"` substitution at
  `tests/test_scene_relative_pacing.py:176`, which must become `1890` (and its
  over-budget probe `1889`).

### Relax the equality assertion to a ceiling

While that test is open, change line 97 from `==` to `<=`. The budget is a
ceiling that bounds the worst case, not a target the package must sit exactly
on; asserting equality means any future scene that needs one more turn is a
budget change by construction, which is what pushed the earlier draft toward
deleting the field. The per-scene `expected_windows` dict is already the real
assertion about intended timing, so nothing is lost.

## Stage C verification

- Assert each scene's schedule, and that each threat is visible before the
  player's next response, leaving two complete turns.
- Assert the turn-4 style pressure event can coexist with a same-turn recovery,
  because it represents approaching external pressure, not a completed search.
- Assert pacing validation is scene-local: changing one scene's window requires
  no compensating change elsewhere, and the package still loads against
  `budget_seconds`.
- Keep the full canonical journey and scene-relative pacing tests green.

---

## Inherited open questions

From `missed-obligation-escalation.md`:

- **Closed by this plan:** Q5 (retraction discipline — A1/A2 answer who retracts
  custody and what validates it).
- **Assumed settled, per that plan's own answers:** Q11 (one player input plus
  its resolution is one turn) and Q12 (a cue or complication rides on the
  ordinary turn and does not reset the counter). Stage C's arithmetic depends on
  both.
- **Not required by this plan, and not assumed:** Q2 (`latest_turn` expiry
  semantics) and Q6 (early exit for a scheduled complication). Stage A and B work
  without them; if Stage C later adopts expiry, revisit the table above.

## Files expected to change

**Stage A** — `plot.md` (card, patrol, and laptop chronology; guarded card
placement; truck laptop), `world.yaml` (custody fact, truck laptop item),
`knowledge.yaml` (custody prerequisites and unambiguous statements),
`storylet-routes.yaml` (B-R1/B-R2/C/D guards, realizations, custody operations),
`storylets.md` (kept in sync), `pacing.yaml` (custody trigger on `t_1a_1b`),
`handoffs.yaml` (physically coherent fallback), `storygame/story_package/models.py`
and `loader.py` (guarded placement, `equals: false` loader rule),
`storygame/runtime/cloudflare.py` (placement filter),
`storygame/runtime/validation.py` (physical prerequisites), plus
`tests/test_knowledge_projection.py`, `tests/test_scene_progression_phase4.py`,
`tests/test_canon_journey.py`, and focused loader tests.

**Stage B** — per scene, as picked up: `plot.md`, `handoffs.yaml`,
`storylet-routes.yaml`, `storylets.md`, and the matching tests.

**Stage C** — `pacing.yaml` (four new events, `destruction_3b` retimed, 1B and 3C
windows, `budget_seconds: 1890`), `tests/test_scene_relative_pacing.py` (window
dict, the two budget literals, and `==` relaxed to `<=`). These land as one
atomic change; see "The raise cannot land on its own".

`docs/testing-runbook.md` records the verification command, outcome, setup, and
any remaining limitation around subjective pacing feel, once per stage.
