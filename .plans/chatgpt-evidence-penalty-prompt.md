# Brief for ChatGPT Desktop: a timer penalty paid in evidence

You are writing story text and structure for freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A player types free text and a small model narrates. The engine owns the facts. You have the earlier briefs. Read this whole brief, then do the task at the end. Every claim you make must tie to the material below. You write the text and the fact names; I will build them with a Ringer worker and score them with the real engine.

## The design intent (the author's words)

> The whole point of storylets was to increase the story pressure if the user was taking too long to move onto the next scene. They were intended to reveal more information and/or create tension at the same time. Regardless, they were never meant to be blocking ... the idea was that eventually the timer would end a scene with an explanation and a story "penalty" of some sort.

Today a timer ending gives the player the missing information for free and moves on. Of the 17 pressure facts, 14 are read by nothing. So there is no penalty. The author wants one that **feels like a penalty but never derails the player from finishing**. The author chose the currency: **evidence**. A scene that the timer ends leaves the evidence Kristin carries to the final broadcast weaker, and the final scene shows it.

## What the engine already does (verified in the code and data)

- **Timer.** Each scene has a handoff turn (`handoff_after_turns`, 11 to 16). If the scene's required facts are not all earned by then, the engine delivers the missing ones from `handoffs.yaml` (`fallback_text`) and the bridge event or transition follows. The delivered text replaces the narrator's prose only when the narrator's prose lacks the delivery's `must_convey` terms; otherwise the narrator's prose stands. **So a sentence you add to a delivery's fallback_text is best-effort, not guaranteed to appear.**
- **Delivery costs.** A delivery in `handoffs.yaml` may carry `costs`: a list of `{op: assert|retract, fact_id, value}`. They are applied only when the engine forces that delivery at the handoff, never when the player earns the reveal. Three of 31 deliveries use them today (for example the forced `brandon_identified` delivery retracts `trust_brandon`). **This is the existing way to make only a slow player pay.**
- **Conditional pressure lines.** Each pacing event in `pacing.yaml` has `realizations`: a list of `{when: [fact predicates], text}`. The engine shows the FIRST realization whose `when` all hold (a realization with no `when` is the default). A pacing event also has its own `when`, `at_turn` and required `effects` (one or more facts it asserts). The event fires once, on the first turn at or after `at_turn` when its `when` holds, and its text is shown on that turn unless another complication text already occupies the turn (then that turn shows the other one and this line is lost, because the event is spent). So it is reliable but not guaranteed. **This is the reliable place to make a penalty visible, and it needs no engine change.**
- **Not conditional.** Resolution events' `fallback_text` and reveals' `delivery_text` have no `when`; they cannot vary by fact. Do not propose conditions there.
- **Contract for pacing text:** pacing events "must create observable pressure, not unearned knowledge". A pacing line may show what is happening; it may not reveal protected knowledge.
- 3C today has exactly two pacing events: `collapse_3c` (turn 4: "Water seeps under the outer doors. Charles's emergency deluge is becoming real.") and `routes_collapse_3c` (turn 10: "Rising water closes a maintenance passage behind the fleeing captives. The remaining routes are narrowing fast."). Both have one default line.

## The rules a penalty must obey (so it never derails)

1. **Paid in evidence, never in access.** The player always keeps every route to the ending.
2. **No progress gate may read a penalty fact.** No transition trigger, bridge or resolution activation, reveal `requires`, or storylet activation may mention it. Only text reads it. I will add an offline check for this.
3. **No counters, no stacking mechanic, no hidden obligation list.** One fact per gap. A gap is named, not counted.
4. **Bounded.** At most two gap lines can show in 3C (one per 3C pacing event, first match wins), so a very slow player is not buried.
5. **Do not shorten later clocks** (it spirals into more timer endings).
6. **Facts are the only truth; no prose canon.** The penalty is a fact the timer path sets and a line that reads it.
7. **Observable.** Each line shows something that is happening or visible, not something Kristin has not learned.
8. **Payloads byte-identical except the lines you approve.** Existing fallback_text, delivery_text, cue_text and plot lines stay exactly as they are; you may only append to a fallback_text or add `costs`, and add `when` realizations before the existing default line.

## Where evidence is gathered (delivery, scene, forced text, current costs)

1C: `facility_proof` (tire tracks, vents, power prove an active facility) / `captives_confirmed_alive` (sedated prisoners seen through the shaft) / `national_detention_network_known` (the logistics computer shows the hub and a national network).
2B: `janus_evidence` (the JANUS files: every American ranked for detention, leverage or control) / `brandon_janus_role_known` (Brandon admits he helped write JANUS; costs: retract trust_brandon) / `brandon_claimed_reform_motive` / `michelle_resistance_known` (coded messages and notes).
2C: `evidence_ready_to_transmit` ("enough evidence to expose the conspiracy… sending proof will reveal their position").
3B: `detention_locations_secured` (Rebecca gives the locations of every detention site) / `brandon_confession_available` (Brandon transmits a confession before the relay locks down).
Bridge events that need these: 1C needs facility_proof + captives_confirmed_alive + national_detention_network_known; 2B needs janus_evidence and two of three Brandon/Michelle facts; 2C needs purge_clock_started + evidence_ready_to_transmit + rebecca_office_required_for_broadcast; 3B needs relay_open + brandon_confession_available + detention_locations_secured and one of human_security_control / charles_abandoned_rebecca.
3C (the broadcast scene) reveals include: send the evidence package to networks; answer Charles's terrorist claim; broadcast the detention site list; Brandon's confession; the transfer records. Its resolution text says Michelle's broadcast "carries the evidence, detention locations, and Brandon's confession across the country. Charles can no longer contain" the truth. The full 3C plot is in `plot.md`; read it before writing.

## Your task

1. **Choose the gaps.** Pick at most one delivery per scene in 1C, 2B, 2C and 3B (four gaps at most) to carry a new cost: a fact `evidence_gap_<something>` that the forced delivery asserts. Say which delivery, why that one is the natural place for evidence to go missing, and give the fact name. Use plain snake_case. Do not reuse an existing fact name.
2. **Write the forced-delivery addition.** For each, one short sentence to append to that delivery's existing `fallback_text`, in the existing voice, that names what Kristin did not get to see, keep or copy because time ran out. Remember it is best-effort.
3. **Write the 3C payoff.** For `collapse_3c` and/or `routes_collapse_3c`, give ordered conditional realizations (first match wins; the existing default line stays last and byte-identical). Each variant is gated on ONE gap fact and shows something observable on the broadcast scene (for example what Charles or his people can now say, or a gap the network anchors point at). It must fit the water-pressure scene tone and must not state anything Kristin has not learned. If you think a third 3C pacing event with a `when` and one required effect is better than editing the two, say so and write it (give its id, `at_turn` inside the existing 3C window, its `when`, an `effects` fact name, and its text).
4. **Check yourself against plot.md.** Say how the ending stays reachable with all four gaps true, which 3C reveals the player can still earn, and that nothing in 3C requires a gap fact.
5. **Give me a scoring table** I can run offline with the real engine: for each new line, the state (which gaps true), the scene, and what the engine should show. Include the all-gaps-true case and the no-gaps case (must be byte-identical to today).
6. **Say what you could not check** (for example the exact turn when the player is in 3C versus the pacing windows, or how the narrator will treat a pressure line), and what you would measure live.

Keep it concrete. Write the lines at the level of the existing story text. Do not propose a new engine mechanism: everything above uses fields that exist. If you believe a real engine change is needed, say exactly why and propose the smallest one.
