# 1C: Brandon offers the moves

2026-10-24. Proposed story changes only. The package has not been edited or played with these changes. This is the response to Brandon's decision that Brandon, the character, should offer the moves. No new engine capability is needed for this proposal.

The player needs three things in the response they actually see: a reason to study the shaft, a choice after observing the captives, and a new invitation when that choice expires. Put those invitations in existing authored delivery paths. Preserve the difference between offering a move and committing its result.

## Evidence and causes

Evidence references below use one-based turn numbers. In each `results.json`, the row is `rows[0]`; response T3 is `responses[2]`. The per-turn records in smokes 2 and 3 also contain their explicit `turn` number.

Transcripts: [smoke 1](../bench/results/phase1-slice-smoke-1/results.json), [smoke 2](../bench/results/phase1-slice-smoke-2/results.json), [smoke 3](../bench/results/phase1-slice-smoke-3/results.json). The latter two are local, gitignored artifacts. Design references: [accepted contract](1c-contract-result.md), [phase-1 decisions and results](game-reimagination-phase1.md), and [live-smoke record](phase1-live-smoke.md).

| Finding | Evidence | Consequence for the proposal |
| --- | --- | --- |
| The entry invites an entrance hunt, not observation followed by a choice. | `plot.md`, 1C `entry_text`, ends with “looking for a way into whatever lay below.” Smoke 1 T1 searches for a way inside; smoke 2 T1 searches for a hidden entrance. Smoke 3 T4 seeks a way down. | Brandon should point to the existing loading docks and observation shaft before a generic entrance search becomes the apparent objective. |
| The visible text teaches reading numbers, but copying is the consequential move. | `k_sl_1c_a_r1.delivery_text` says Kristin “can read the identification numbers.” Smoke 3 T2 earns `captives_confirmed_alive`; T3 reads numbers and the narrator says she commits them to memory. T3 records `semantic_refusal`, no committed reveal, no advantage. Smoke 1 similarly reads numbers at T5. `k_sl_1c_c_copy_numbers.action_evidence` calls for copy/write down/record/photograph. | Offer copying explicitly. Do not make reading retroactively count as copying. Narrated memory is not the committed `processing_numbers_copied` fact. |
| Neither observation delivery offers the actual choice or explains its cost. | `plot.md` 1C.2 describes both choices, but `k_sl_1c_b_r1.delivery_text` ends “They are alive.” R2 ends “Then the view vanishes.” Neither offers Brandon's help. In smoke 3, no response gives either invitation; no command attempts copying or asks Brandon about the route. | Put Brandon's choice in both observation deliveries. Preserve an uncertain face in R2 while leaving the transfer briefly visible. A plot-only edit would miss the demonstrated delivery gap. |
| The missed window has no visible recovery invitation. Its closing sentence is not reliably displayed. | All runs stay in 1C for 30 commands. Smokes 2 and 3 assert `transfer_window_missed` on T5, but their T5 responses omit the closing sentence. Smoke 1 T5 displays it, still with no next move. `transfer_window_1c` has one non-verbatim realization. Recovery `k_sl_1c_d_r1` describes following Brandon through the service entrance, but no response offers that action. | Make the existing pressure realization verbatim. Have Brandon invite the existing recovery in that same text. Keep the event's sole fact effect. |
| There is stale scene material even though the cue metric is clean. | The 1C `situation` permanently says identification numbers are visible on uniforms below. Smoke 3 T28 presents prisoners and matching numbers again, 23 turns after the window closed. Smoke 2 even earns B-R1 at T8, after the T5 closure. The A/B knowledge prerequisites and A/B storylet activation do not check the missed-window fact. | Remove transient visibility from the permanent frame. Gate the live-view observations and their invitations with the existing false predicate. This is package lifecycle data, not prose scanning. |
| Unauthored leads consume the remaining play. | Smoke 1: stairs at T1, keypad at T6. Smoke 2: hidden compartment/notebook at T2, map at T3. Smoke 3: stairs at T4, clipboard at T5, console at T6, Nightshade at T9, kitchen at T12, Michelle riding with them at T20, keycard at T22, elevator at T29. Subsequent commands repeatedly follow those leads. | Supply grounded positive material early. Do not canonize these inventions by adding props, places, access puzzles, or a phone. This proposal removes a plausible source of drift; it does not prove that all narration drift is cured. |
| Smokes 1 and 2 also contain a distinct, already-fixed failure. | Both repeat the copy fallback at T11–30. Smoke 2 stages `processing_numbers_copied` on those turns, records semantic refusal and no reveal, and has one recovery per turn. Its total is **21** recoveries, including T4; smoke 1 totals 20. `.plans/phase1-live-smoke.md` identifies the legacy handoff guard fix. Smoke 3 has no staged handoff, 30 requests, zero recoveries, and a longest repeated-response streak of two. | Do not describe the fallback loop as the current cause or try to repair it with story wording. Smoke 3 isolates the still-unresolved opportunity problem. |

Smokes 2 and 3 finish with `facility_proof`, `captives_confirmed_alive`, and `transfer_window_missed`, but neither advantage nor `facility_infiltration_needed`. `t_1c_2a` needs `facility_infiltration_needed`. That is the immediate reason no transition occurs. The player has not earned an outcome; the deadline correctly supplies none. Smoke 1 lacks per-turn fact provenance, so its similar visible symptom is not independent proof of the same internal cause.

There is also a timing mismatch in the material: SL-1C-B targets T5, and SL-1C-C targets T9, after the window closes at T5. These are preferences, not hard earliest-turn gates; smoke 3 earns B at T2. Align them, but do not claim they caused a rejection. Likewise, `nudge_after_turns: 8` is not proof that cues cannot appear earlier: the transcripts show early cues.

The accepted phase-1 recovery decision supersedes the older contract's automatic withdrawal language: the scene stays open after the miss. Following Brandon earns the route at higher cost. The proposal follows that decision and the actual SL-1C-D operations.

## Exact proposed changes

Paths below are relative to `data/stories/continuity-initiative/`. Apply the plot changes first. Each YAML block replaces the named fields or entry; unlisted fields retain their current values and order. No action matcher, fact operation, advantage, cost, source ID, or transition changes are proposed, except the explicitly listed eligibility predicates.

### `plot.md`

In the interactive pacing table, replace the 1C row with:

```markdown
| 1C | Choice closes at 5; recovery remains open | Inspect the terminal; observe the captives; choose copying the numbers or asking Brandon about the route; follow Brandon at greater risk if the window closes. |
```

In 1C frontmatter, replace `objective` and `entry_text` in their existing positions. Model: 2C's existing `entry_text`, which offers an immediate action; 1B's Brandon-led delivery provides the dialogue pattern.

```yaml
objective: Observe the transfer and choose what to secure
entry_text: >-
  Michelle's lead brought Kristin and Brandon to the freight terminal.
  It was supposed to be abandoned. Fresh tire tracks crossed the loading docks.
  The air vents hummed. Brandon said, "Check the loading docks for signs of activity.
  The observation shaft gives us a view below. Let's find out what is happening
  before we try to get inside."
```

Replace the 1C Setting, Characters, and Plot block before 1C.1 with:

```markdown
**Setting:** The freight terminal, its loading docks, and the observation shaft above the processing line

**Characters:**

* Kristin Schweitzer
* Brandon Corfman

**Plot:** Kristin and Brandon investigate an active freight terminal. Brandon points Kristin toward the observation shaft. Once she has studied the captives, he offers a choice: copy their numbers or ask him about the transfer route. If the transfer leaves first, he offers a riskier attempt through the service entrance.
```

This removes the obsolete nationwide-network summary and the absent Charles/Rebecca surveillance appearance. Michelle stays narratively relevant in `participant_ids`; this does not place her or confirm the sighting.

Replace the final sentence of 1C.1, “Kristin and Brandon search for a route into the service level without triggering security.”, with:

```markdown
Brandon points Kristin toward the observation shaft. He asks her to study the people on the processing line before they try to enter.
```

Replace all content under the existing 1C.2 heading, stopping before 1C.3, with:

```markdown
**Details:** observation shaft; sedated prisoners; processing line; identification numbers; woman resembling Michelle; service entrance

Through the observation shaft, Kristin can study the sedated prisoners moving along the processing line. Studying them confirms that they are alive. If she looks for Michelle, she glimpses a woman who could be her. The woman's face slips from sight before Kristin can be certain. The transfer is still moving.

Brandon offers two ways to use the remaining time. Kristin can copy the prisoner numbers for stronger proof. She can instead ask him about the transfer route. His help gives them a service approach, but costs Kristin the chance to copy the full number set. There is time for one choice.

Copying the numbers produces the prisoner number record. Asking Brandon earns the service approach. Either choice gives them a reason to pull back and prepare their entry into the facility.

If the window closes first, the view down the observation shaft goes dark. Brandon offers to lead Kristin through the service entrance at greater risk. His offer does not open the entrance, establish the route, or move Kristin. Following him earns the service approach. Kristin loses the number set. The sweep closes in. They then withdraw to prepare their entry.

The closure alone grants no proof, confirmed sighting, copied numbers, route, or decision to infiltrate. Michelle's identity remains uncertain. Brandon says nothing about his past work or the wider conspiracy.
```

Keep the 1C.3 relocation note. No later-scene material returns to 1C.

### `knowledge.yaml`

Replace the 1C scene frame, retaining the order `scene_id`, `situation`, `pressure`:

```yaml
- scene_id: 1C
  situation: >-
    The freight terminal has loading docks above a service level.
    The observation shaft overlooks the processing line.
    The service entrance is at the freight terminal.
  pressure: Observe the transfer and choose what to secure
```

Model: the existing 1C frame, with only lasting geography in `situation`. It assigns no character position. The earned delivery and timed event now own the changing view.

For `k_sl_1c_a_r1`, replace `requires: []` in place with:

```yaml
  requires:
  - fact_id: transfer_window_missed
    equals: false
```

Replace its `delivery_text` in place with:

```yaml
  delivery_text: >-
    Kristin finds electrical load, fresh air from the vents, and signs of recent work.
    The freight terminal is still running. Brandon says, "Study the people through
    the observation shaft. We need to know what is happening on the processing line."
```

Model: `k_sl_1b_b_r1.delivery_text`: earned information followed by Brandon offering a grounded next action. This delivery earns only the existing facility proof. It does not confirm living captives or award either advantage.

For both `k_sl_1c_b_r1` and `k_sl_1c_b_r2`, replace their `requires` blocks with:

```yaml
  requires:
  - fact_id: facility_proof
    equals: true
  - fact_id: transfer_window_missed
    equals: false
```

For B-R1, replace `statement` and `delivery_text` in their current positions:

```yaml
  statement: Kristin studies the sedated prisoners through the observation shaft and confirms that they are alive.
```

```yaml
  delivery_text: >-
    Kristin studies the sedated prisoners through the observation shaft. They are alive.
    Brandon says, "Copy the prisoner numbers if you want stronger proof.
    Or ask me about the transfer route. I can help with the service entrance.
    That will cost us the chance to copy the full set of numbers.
    There is time for one choice before the transfer leaves."
```

The statement correction removes its current claim of matching records during a free observation. That work belongs to the copy outcome.

For B-R2, replace `statement` and `delivery_text` in their current positions:

```yaml
  statement: Kristin sees living captives in the processing line. She glimpses a woman who could be Michelle before the woman's face slips from sight.
```

```yaml
  delivery_text: >-
    Kristin watches the sedated captives in the processing line. They are alive.
    She glimpses a woman who could be Michelle. The woman's face slips from sight.
    The transfer is still moving. Brandon says, "Copy the prisoner numbers if you
    want stronger proof. Or ask me about the transfer route.
    I can help with the service entrance. That will cost us the chance to copy
    the full set of numbers. There is time for one choice before the transfer leaves."
```

Model for both: `k_sl_1b_b_r1` and `k_sl_1b_b_r2`, which both append the same actionable Brandon offer to different earned revelations. R2 must not say the entire view vanishes just before inviting use of that view.

Keep both outcome entries' evidence phrases, requirements, operations, and empty `leak_terms` lists. Replace only these deliveries:

`k_sl_1c_c_copy_numbers`:

```yaml
  delivery_text: >-
    Kristin copies the visible prisoner numbers and matches them to missing-person records.
    Brandon says, "That gives us stronger proof. We still need a way inside."
```

`k_sl_1c_c_secure_route`:

```yaml
  delivery_text: >-
    Brandon explains the transfer route and opens the service entrance with the transit token.
    Kristin loses the chance to copy the full set of prisoner numbers.
    Brandon says, "We have an approach. Now we need to prepare."
```

`k_sl_1c_d_r1`:

```yaml
  delivery_text: >-
    Brandon leads Kristin through the service entrance. He shows her the service approach.
    The full set of prisoner numbers is lost. The sweep closes in.
    Brandon says, "We have to pull back. We can prepare now that we know the approach."
```

Model: these entries' existing deliveries, retaining each `must_convey` requirement. The added sentences make the already-declared loss and next step visible. The bridge still performs the withdrawal into 2A; this does not offer an additional corridor puzzle or a free-text connection that the slice no longer has.

### `pacing.yaml`

Replace the complete `transfer_window_1c` entry with this entry, in the existing key order:

```yaml
- id: transfer_window_1c
  scene_id: 1C
  at_turn: 5
  effects:
  - fact_id: transfer_window_missed
    equals: true
  realizations:
  - verbatim: true
    text: >-
      The view down the observation shaft goes dark.
      Brandon says, "That chance is gone. We can still try the service entrance.
      Follow me through it if you want to try. We will have to risk the sweep."
```

Model: `collapse_3c.realizations` and `routes_collapse_3c.realizations`, which already use `verbatim: true` for a consequence the player must see. The order inside the new realization is `verbatim`, `text`; unlike the conditional examples it needs no `when`.

This text works even if Kristin never studied the captives. It confirms no captive identity, does not say that she copied anything, does not teach the route, and does not narrate either character entering. “We will have to risk” forecasts the recovery's cost; `terminal_sweep_closing` remains an earned recovery effect. The only deadline effect remains `transfer_window_missed`. Keep the scene timing row and transition unchanged.

### `handoffs.yaml`

In the existing `facility_proof` entry, replace only `cue_text`:

```yaml
  cue_text: >-
    Brandon says, "Check the loading docks for signs of activity."
```

In the existing `captives_confirmed_alive` entry, replace only `cue_text`:

```yaml
  cue_text: >-
    Brandon says, "Study the people through the observation shaft."
```

Model: those entries' existing one-step pointers, with Brandon giving the advice. Their reveal availability must retire them after the miss through the A/B predicates above and the existing cue lifecycle. Keep their `fallback_text`, source fields, and `must_convey` groups. In particular, do not move the two advantage deliveries from 2A to 1C or make the deadline deliver them. A recovery invitation belongs to the pressure realization, not to an advantage fallback masquerading as success.

### `storylet-routes.yaml` and `storylets.md`

These companion files must agree with the revised live-view eligibility; they were checked in addition to the six requested package files.

In SL-1C-A, replace `activation.conditions: []` with:

```yaml
    conditions:
    - fact_id: transfer_window_missed
      equals: false
```

In SL-1C-B, replace `activation.conditions` with:

```yaml
    conditions:
    - fact_id: facility_proof
      equals: true
    - fact_id: transfer_window_missed
      equals: false
```

Model: SL-1C-D's existing fact-predicate activation, using the other truth value. Keep the enclosing order `scene_id`, `conditions`, `pacing`. The A gate retires its observation invitation as well as its cue; the missed-window recovery remains usable without A or B, as its current declaration intends. No observation fact is granted by recovery.

In SL-1C-B replace `activation.pacing` with:

```yaml
    pacing:
      earliest_turn: 0
      target_turn: 2
      latest_turn: 3
      pressure_bias: normal_before_target; prefer_after_target; strongly_prefer_near_latest
```

In SL-1C-C replace `activation.pacing` with:

```yaml
    pacing:
      earliest_turn: 0
      target_turn: 3
      latest_turn: 4
      pressure_bias: normal_before_target; prefer_after_target; strongly_prefer_near_latest
```

Model: SL-1C-A's current pacing block. These preferences now precede closure. They do not shorten the existing deadline or impose another action gate.

In SL-1C-B replace `pressure_role` with:

```yaml
  pressure_role: >-
    Show living captives when Kristin studies the processing line.
    Brandon offers a choice between copying their numbers and asking him about the transfer route.
```

In SL-1C-B-R1 replace `dramatic_intent` with:

```yaml
    dramatic_intent: Confirm that the sedated prisoners are alive.
```

This removes the old suggestion that free observation establishes the need for infiltration. Its operations never asserted that fact.

For SL-1C-B, SL-1C-C, and SL-1C-D replace `non_coercion_note` with:

```yaml
  non_coercion_note: >-
    Brandon may offer these actions in dialogue. Kristin chooses what to attempt.
    Equivalent player actions may earn the same result.
```

Model: the existing `non_coercion_note` field. The current blanket instruction not to present actions as choices conflicts with the chosen dialogue direction. This replacement permits in-world advice, not a mandatory command menu.

In `storylets.md`, replace SL-1C-B's complete `Pacing window` block with:

```markdown
**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 3`
```

Replace SL-1C-C's complete `Pacing window` block with:

```markdown
**Pacing window**
- earliest: `turn 0`
- target: `turn 3`
- latest: `turn 4`
```

Model: SL-1C-A's existing Markdown pacing block. Append this bullet to `Available when` in each of SL-1C-A, SL-1C-B, and SL-1C-C:

```markdown
- The transfer window remains open.
```

In SL-1C-B, replace its final two `Possible realizations` bullets (Brandon stopping an impulsive move and Kristin resenting the restraint) with:

```markdown
- Brandon offers copying the prisoner numbers for stronger proof.
- Brandon offers help with the transfer route at the cost of the full number set.
```

In SL-1C-D, insert this first bullet under `Possible realizations`, before the existing earned consequence:

```markdown
- Brandon invites Kristin to follow him through the service entrance. The offer alone grants nothing.
```

Replace the 1C coverage-table row at the end of `storylets.md` with:

```markdown
| [1C](plot.md#scene-1c--discovery-of-the-facility) | `SL-1C-A` … `SL-1C-D` | Facility discovery, living captives, one advantage, costly recovery after a missed window |
```

These edits keep the companion aligned with the plot and remove its obsolete national-scale description of 1C.

### `incidents.yaml` and `world.yaml`

No changes. The incident already declares two exclusive outcomes, the recovery, the missed event, and immediate completion after an earned outcome. Existing world declarations suffice:

| Name used by the proposal | Existing declaration / placement |
| --- | --- |
| Kristin / Brandon | Protagonist defaults to `freight_terminal`; `companions: [brandon]` places Brandon with her. |
| Loading docks / observation shaft | `loading_docks.parent: freight_terminal`; `observation_shaft.parent: loading_docks`. |
| Processing line / prisoners | `processing_line.parent: service_level`; scene placement puts `captives` there. Uniforms and numbers describe those captives; no new device is offered. |
| Service entrance | Existing fixed item, placed at `freight_terminal` in 1C. |
| Transit token | Existing item retained by the original route delivery. The new invitations require no new custody claim. |
| Copied record | `prisoner_number_record` starts hidden at the processing line. Only `processing_numbers_copied.on_assert` moves and reveals it. |

No new guards, ladders, notebooks, cameras, terminals, phones, or passages are introduced. The existing copy delivery's comparison with missing-person records stays a resolved consequence; it is not turned into a new physical document-search task.

## Boundaries and remaining evidence

The offers disclose possible actions, not JANUS, Brandon's development role, the bait scheme, Michelle's resistance, her confirmed location, the national network, or the architects' strategy. Brandon's useful access remains unexplained. Each new narrator-facing instruction uses short sentences and concrete names. No shared narrator rules change, so there is no six-path engine prompt edit.

The intended sequence is inspect → observe → choose; the missed-window alternative is closure → invitation → chosen recovery. Example inputs use the player-input guide: `Inspect the loading docks.`, `Study the prisoners through the observation shaft.`, then either `Copy the prisoner numbers.` or `Ask Brandon about the transfer route.` After the miss: `Follow Brandon through the service entrance.` These are examples for reviewing the material, not mandatory player phrasing or a replacement for raw-player testing.

This is an artifact-based diagnosis, not a new experiment. `results.json` does not contain the full narrator payloads or world-matching traces, so it cannot identify every input that caused the grounding drift. The recorded Phase 1 scripted playthroughs establish that both outcomes and recovery can reach 2B; they do not prove strangers will choose them. The proposal needs package validation, payload comparison, and a newly authorized live smoke before any claim of improvement. Read the full response together with committed facts, especially at the T5 boundary. Check that the miss alone grants nothing and that delayed observation cannot renew the number-copy offer.

If those checks show an existing story mechanism cannot express or display these changes, stop for review. Do not add an engine repair, broaden the matcher, or declare Phase 1 complete on the strength of this document.
