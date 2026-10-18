Scene 1A is not blocked on `d_r1`. Its real problems are **thin research content, incorrect movement narration, and a transition that can repeat travel already narrated**. The reveal-selection refusals themselves are mostly correct.

I made no repository changes or billed calls. I checked the recorded turns, prompts, bundles, package conditions, runtime code, and the real offline matcher.

**1. What each flagged turn actually did**

The prompt’s definition of “stuck” needs correcting. [blind-player.js:330](/home/bcorfman/dev/freytag-forge/frontend/e2e/blind-player.js:330) flags a turn only when it mentions no mapped affordance, adds no fired storylet, and adds no grounding ID relative to the preceding turn:

> `if (!mentionsAffordance && !addedStorylet && !addedGrounding) stuckTurns.push(turn);`

It does **not** measure committed reveals or meaningful world changes directly.

| Turn | Engine decision and reason | Assessment |
|---|---|---|
| A4: “go to the truck” | `semantic_refusal`, universe 2, no reveal. Truck movement earns no authored reveal. `patrol_return_pressure` nevertheless commits. | **Real prose defect; correct reveal refusal.** The engine had already seated Kristin, but narration makes her get out, approach the truck, and get in again. |
| A7: search the park | `semantic_refusal`, universe 2, no committed delta. Only patrol reveals remain eligible. The reply locates a bench. | **Fair no-reveal navigation**, rather than a failed reveal. However, the scene remains 1A while narration already places her in the park. This produces a genuine continuity problem on A8. |
| B2: examine Michelle’s phone | `semantic_refusal`, universe 3, no reveal. A1 already established the crime-scene inference. | **Fair dead end for progression.** No extra reveal is needed. The invented passcode and attempted guessing are unsupported embellishments, not evidence of a blocked route. |
| B5: get the laptop | `semantic_refusal`, universe 2, no reveal. Acquisition/navigation is not a research reveal. | **Real prose defect; correct reveal refusal.** The reply picks up the laptop, carries it “out to the truck,” then puts it inside, despite starting beside it in the truck. |
| B7: examine saved files | `semantic_refusal`, universe 2. `d_r1` is already established; the remaining candidates are `c_r1` and `c_r2`. | **Real response defect; correct eligibility decision.** It opens folders without giving requested information and invents “Michelle’s laptop.” |
| B8: read the documents | `no_eligible_action`, universe 0. Patrol availability has expired; other relevant knowledge is established. An earned transition fires. | **Real response defect; correct transition.** Kristin ignores the reading action and enters the house. This is not a failed attempt to earn `d_r1`. |

Evidence: [Run A turns](/home/bcorfman/dev/freytag-forge/bench/results/stage7-blind-raw/attempt-1/e2e-blind-player.json:87), [Run B turns](/home/bcorfman/dev/freytag-forge/bench/results/stage7-2b-entry/attempt-1/e2e-blind-player.json:48).

A6 is **not counted by design**, despite committing no reveal: its `k_sl_1a_d_r1` grounding ID differs from A5’s grounding IDs. A7 repeats that ID and is counted. A8 also escapes the stuck flag through changed grounding. These are attribution changes, not newly earned research.

The common selection path is [cloudflare.py:411](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:411); semantic refusal is recorded at [cloudflare.py:595](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:595).

**2. The five leads**

**Lead 1: substantially correct, but the filter is not merely a semantic-fallback filter.**

The real `_matches_all` check confirms:

| Command | Raw evidence matches, before eligibility |
|---|---|
| B7’s saved-files command | `d_r1` |
| B8’s documents/folder command | None |
| “Open the files on Michelle’s memory card.” | `b_r1`, `d_r1` |
| “Read Michelle’s remaining files.” | `d_r1` |

However, [knowledge.py:416](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:416) excludes ineligible reveals **before exact matching**. [reveal_eligibility.py:51](/home/bcorfman/dev/freytag-forge/storygame/runtime/reveal_eligibility.py:51) says:

> `if _established(item, state):`  
> `return RevealEligibility(False, ALREADY_ESTABLISHED, item.id)`

The semantic filter at [cloudflare.py:670](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:670) repeats that protection.

There is also an explicit package condition. [storylet-routes.yaml:815](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/storylet-routes.yaml:815) requires:

```yaml
- fact_id: continuity_initiative_known
  equals: false
- fact_id: michelle_warning_known
  equals: true
- fact_id: memory_card_recovered
  equals: true
```

Thus `b_r1` deliberately closes D’s route. D’s stated purpose is:

> “Guarantee that the concrete lead away from the house stays earnable when Kristin reads the damaged recording before the remaining research files.”

—[storylets.md:230](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/storylets.md:230)

There was no “other candidate alongside D” on B7. **The two candidates were C-R1 and C-R2.** D was absent.

Do not remove the established-facts filter or invent a new fact solely to make D fire. Neither fixes the missing information in B7’s reply.

**Lead 2: correct about reveal eligibility, incomplete about reply quality.**

The phone and laptop are properly declared and placed. [plot.md:87](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:87) places the phone on the kitchen floor and laptop on the truck’s passenger seat.

The phone also has an authored investigative role:

> “Handling Michelle’s phone makes the missing tablet and work bag stand out.”

—[storylets.md:53](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/storylets.md:53)

But B1 already delivered that inference. B2 does not establish a need for another reveal. B5 should successfully retrieve the laptop without earning research knowledge. Its contradictory prose is the defect.

**Lead 3: confirmed, with an additional upstream issue.**

B8’s actual narrator prompt contains:

> `Kristin. Place: outside the house.`  
> `Just before this: Kristin got out of the truck.`

The previous turn’s captured state places Kristin in the driver’s seat. Therefore the narrator did not invent the entire departure: **an engine preparation step had already moved her outside**.

[seating.py:159](/home/bcorfman/dev/freytag-forge/storygame/runtime/seating.py:159) asks whether standing is needed, moves her to the seat’s area on a positive answer, and inserts the seat’s `leave_text`. That text is:

> `leave_text: Kristin got out of the truck.`

—[world.yaml:214](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:214)

Reading files does not obviously require leaving the truck. The saved evidence establishes the resulting step, but not the standing question’s raw answer or reasoning.

The narrator then independently adds the walk indoors. Competing prompt material includes:

> “What presses on Kristin now: Find evidence of Michelle’s disappearance”  
> “The house is quiet and Michelle is missing.”

These are plausible contributors, **not a proven causal explanation**. The prompt already instructs Kristin to start at PLAYER’s place and perform only the requested action.

**Lead 4: both exits were earned, subject to a pacing floor.**

[t_1a_1b](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/pacing.yaml:213) requires:

- `michelle_lead_actionable`
- `patrol_return_pressure`
- `memory_card_recovered`
- the memory-card dependency to remain available.

`pressure_1a` supplies patrol pressure at turn 4. A5 and B6 supply the remaining lead facts through `b_r1`.

But [pacing.yaml:176](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/pacing.yaml:176) sets:

```yaml
min_turns: 8
nudge_after_turns: 10
handoff_after_turns: 13
```

[engine.py:988](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:988) explicitly waits for that minimum. Both exits occur at the first permitted turn, using already-earned facts. Neither turn-8 command itself earns the exit; neither invokes the turn-13 backstop.

A’s resulting continuity defect is concrete: narration reaches the park on A6, but A8 appends:

> “Kristin starts the truck and heads for the park…”

The transition machinery is working as authored; narration and the fixed bridge disagree about whether travel has already occurred.

**Lead 5: confirmed; not a coverage failure.**

Both patrol alternatives require the warning. Their shared storylet has `latest_turn: 7`, and [engine.py:1022](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:1022) removes expired optional storylets.

Neither run attempts the required officer/research or gate action during that window. These alternatives are optional, and selecting one spends their shared storylet. Do not require both in a single walk or extend their window merely to improve coverage.

**3. Ranked story-side fixes**

**First: probe a subtractive change for B8’s house restart.**

In [knowledge.yaml:2842](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:2842):

Old:

```yaml
statement: The house is quiet and Michelle is missing.
```

New:

```yaml
statement: Michelle is missing.
```

This removes a repeated house-state assertion that is especially questionable while patrol activity is escalating. It preserves the entry fact and introduces no entity or instruction.

Technique: remove competing recall, as in the guide’s 2C stale-1A-recall precedent. I also checked commit `a1be8409`, which removed misleading spatial framing from 3B’s situation.

Risk: less opening atmosphere; possibly no improvement because the standing step, scene frame, and objective remain. **Probe this; do not call it a demonstrated fix.**

**Second: supply the research content B7 actually asks for.**

The selected B reveal names the program and destination but omits the substantive research in [plot.md:135](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:135). Add that existing material to the already-earned knowledge rather than resurrecting D.

In `k_sl_1a_b_r1`, [knowledge.yaml:407](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:407), replace the statement:

Old:

> Kristin reads Michelle's memory card. Its damaged recording warns her not to trust emergency broadcasts, and the Continuity Initiative files point to a dead drop at a bench in the park.

New:

> Michelle's memory card holds a damaged recording warning Kristin not to trust emergency broadcasts. The Continuity Initiative files point to a dead drop at a bench in the park. Private contractors built population stabilization centers before the disappearances. The centers were officially intended as shelters for natural disasters and biological attacks.

Also append these two sentences to `b_r1.delivery_text`, after its existing final sentence:

> Private contractors built population stabilization centers before the disappearances. The centers were officially intended as shelters for natural disasters and biological attacks.

The complete existing delivery remains intact; only those sentences are added.

Technique: missing plot material goes into a handoff and its reusable statement. Earlier precedent: 3B’s missing office-entry material, implemented through `SL-3B-E` in `90850120` and refined in `a1be8409`.

Risk: longer automatic delivery on insertion; possible model overextension from the official shelter explanation to the protected actual purpose. Do **not** add the “choose who remains” sentence in this patch. The centers are background research subjects, not newly placed visitable destinations.

This fixes an information deficit. It does not guarantee the narrator will answer every follow-up correctly or stop misnaming the laptop.

**For A4/B5’s movement loops: no story patch is justified yet.**

Their placements and engine step text are already explicit. Adding another reveal, duplicating placement prose, or changing seat declarations would mask a narration/preparation problem. The existing start-place rule addresses precisely this behavior. No new narrator rule is warranted by these samples.

**For A’s repeated park journey: no isolated text deletion is worth adopting yet.**

Deleting the bridge’s travel sentence would damage the normal house-to-park transition in B; lowering `min_turns` would change the deliberately authored investigation window. Keep this as a separate scene/physical-location synchronization finding. Do not reopen the already-settled bench declaration or guards.

**4. Cheapest useful probes**

Start with the **free eligibility check**. It already settles the proposed matcher repair: B7 matches D’s words but D is ineligible; B8 matches none. Widening evidence cannot fix either state.

For regression coverage, use two states:

- **After `b_r1`:** recovered card, warning, program, suspicion, and actionable lead established. B7 must not select D.
- **After recording-only `b_r2`:** recovered card and warning established; program and lead false. At an active D turn, `Read Michelle's remaining files.` must uniquely match D.

Score with `_matches_all` **and** `explain_reveal`; a lexical match alone is insufficient. Also retain the raw two-match example above to catch accidental tie introduction.

For the first story hypothesis, use these exact variations:

Control:

```json
{
  "name": "stage7-1a-recall-control",
  "story_package": "data/stories/continuity-initiative",
  "overrides": {}
}
```

Subtraction:

```json
{
  "name": "stage7-1a-drop-quiet-house",
  "story_package": "data/stories/continuity-initiative",
  "overrides": {
    "knowledge.yaml": {
      "replacements": [
        {
          "old": "statement: The house is quiet and Michelle is missing.",
          "new": "statement: Michelle is missing."
        }
      ]
    }
  }
}
```

Replay **B8’s captured narrator prompt**, keeping its actual outside-house place, engine step, command, known facts, and turn-8 complication identical. Use 10 samples per arm through Ringer, following the scene-fixing guide.

Read every reply. A win requires a clear improvement in answering the reading action without re-entering the house, with no invented destination or research revelation. Score narration separately from the appended bridge and entry. Reveal eligibility should remain unchanged; this is not a “more reveals” experiment.

For the material patch, the cheapest initial check is offline package loading, exact replacement validation, unchanged evidence/eligibility results, and prompt inspection. Then replay **B7**, whose actual narrator-start state is:

- scene 1A, seventh turn;
- Kristin in the driver’s seat;
- Kristin’s laptop open and held by Kristin;
- card recovered and held;
- `b_r1` facts already established;
- only patrol reveals eligible.

Compare control against the new B statement, 10 samples each. Success means the reply gives the authored research information, preserves Kristin’s laptop ownership, and does not invent access steps or move her. A new reveal is neither required nor desirable.

**Important artifact issue:** some `*-prompts.json` entries contain the name-matching request rather than the narrator request—B7 is one. Use the bundle’s capture-stage `reply.narration_prompt` for these replays. I checked that field.

**5. Previously settled work**

None of these proposals repeats the drawer fix, laptop cue removal, guard changes, photograph smoke, drawer-avoidance fallback, or cue-wording experiments.

The research proposal changes **earned information**, not a pointer toward information. D remains a recording-first fallback. I am not selecting between the outstanding spine-expectation approaches or treating sibling alternatives as missing content.

**6. What remains unverified**

- Whether removing the quiet-house recall actually improves B8. That requires the paired live replay.
- Whether enriched research content improves B7 rather than merely lengthening its prompt.
- The raw decision that caused B8’s unnecessary standing step.
- Full historical world state reconstruction: bundle summaries list predicates, not every fact value and active-event detail.
- The earlier scripted semantic tie’s reasoning remains unrecoverable.
- A safe package-only solution to travel occurring before the scene transition.

The strongest immediate recommendation is to **keep eligibility unchanged, test the small recall subtraction, and give the already-earned files their missing research content**.