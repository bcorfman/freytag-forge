**The verifier enforced a broader requirement than Brandon’s card-finding requirement:** it demanded that the narration present all four public drawer contents at the drawer. The rejected underside searches answered the player’s action but omitted that inventory.

There is also a separate opening-case problem, and the plan’s diagnosis overstates what those prompts contained. No files were changed or billed calls made.

**Causes and evidence**

I compared the current runtime with `d766a0ef`; there is no `storygame/` diff, so the cited implementation applies to the smoke.

1. **Observation scope loses the distinction between inside and underneath.**

   [`WorldCapture._set_observation_request`](/home/bcorfman/dev/freytag-forge/storygame/runtime/capture.py:215) selects a referred entity and assigns `look`, `open`, or `enter`. `ObservationRequest` has no field for “under this object.”

   [`build_observation_context` and `_required_ids`](/home/bcorfman/dev/freytag-forge/storygame/runtime/observation.py:68) then require visible item descendants of the focused container/supporter. `_required_ids` receives neither the command nor the request kind. Consequently, focusing an open drawer makes its interior contents mandatory even when the action is underneath it.

   The four contents are real package declarations: `pens`, `binder clips`, `stapler`, and `spare batteries` in [`world.yaml`](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:169).

2. **The prompt and verifier turn those contents into mandatory prose.**

   [`ItemFactsProvider._section_user_prompt`](/home/bcorfman/dev/freytag-forge/storygame/runtime/item_facts.py:707) emits:

   > Show these in your reply: binder clips, pens, spare batteries, stapler.

   The same underside prompts also say that searching under the drawer finds nothing more.

   [`relations_from_context`](/home/bcorfman/dev/freytag-forge/storygame/runtime/observation_verifier.py:22) converts each required item into a relation at `drawer`. `_question_for` explicitly treats an omitted item as false. `VerifierReport.accepted` requires every relation to pass. Thus merely answering the underside search correctly is insufficient.

3. **The smoke demonstrates exactly that failure—not a failed card discovery.**

   Row IDs below use zero-based replicate/turn indices, consistent with the plan.

   | [Smoke rows](/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/enforce-stage1/smoke/rows/rows.json) | Evidence |
   |---|---|
   | `r0t0` | `inspect the drawer` already delivers the card: taped beneath the drawer, peeled loose, pocketed. |
   | `r0t1` | Opens the drawer and describes all four supplies; all four relations score `0.96`. |
   | `r0t2`, attempts 1 and 2 | Both describe searching underneath and finding nothing more. Neither mentions the supplies. All four relations reject at `0.02–0.03`. Final narration is null; error is `ProposalValidationError`; elapsed time is `10.066 s`. |
   | `r0t3`, attempt 1 | Same omission and rejection. |
   | `r0t3`, attempt 2 | Adds the four supplies inside the open drawer; scores `0.94–0.96`, commits; total time `7.860 s`. |

   On turns 2 and 3, the card is already held by Kristin. These are **post-recovery searches**, not tests of whether an initial underside search can earn the card.

   [`WorldCapture.preview_commit`](/home/bcorfman/dev/freytag-forge/storygame/runtime/capture.py:281) applies proposed item facts to the candidate before verification. [`RuntimeEngine._preview_observation`](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:202) raises `observation_unverified`; `_turn_active` permits the shared recovery and restores the snapshot on exhaustion.

   I confirmed that the two attempts use identical user prompts. The retry adds only the generic “Your last reply did not follow the narration rules…” instruction. It does not identify the missing supplies. The failed row’s recorded places are unchanged; those place dictionaries alone do not prove restoration of every runtime field.

4. **The eight shadow rejects contain two distinct cases.**

   In the [post-change shadow rows](/home/bcorfman/dev/freytag-forge/bench/results/environment-narration/shadow-sample3-postchange/full/rows/rows.json):

   - **Underside searches:** `r1t2`, `r1t3`, `r2t2`, `r4t3`, `r6t3`, `r9t2`. All have request kind `look`, focus `drawer`, and four required interior relations. Their prompts explicitly require the supplies; their prose omits them.
   - **Inspections that open the drawer:** `r0t0`, `r3t0`. Both start with a closed drawer, have request kind `open`, and return `item_facts` setting it open. The post-change verifier consequently requires its newly visible contents.

   **Correction to the plan:** neither rejected inspection prompt contains “Show these in your reply.” Both contain the supplies in THINGS, but the explicit requirement appears only after opening changes visibility. The [diagnosis record](/home/bcorfman/dev/freytag-forge/.plans/grounded-llm-environment-narration.md:902) incorrectly generalizes that instruction to every failing prompt.

   All 32 omitted relations were correctly rejected under the implemented contract. Calling the turns human-acceptable measures a different criterion; it does not make those verifier answers incorrect.

**Proposed solution**

Make the observation contract reflect **what part of the object the action examines**, while preserving ordinary contents coverage.

- Extend the bounded, model-proposed observation intent with a validated scope, distinguishing an underside search from interior inspection/opening and exterior inspection. Resolve its target through the existing entity resolver. No drawer-specific branch, command whitelist, or regex interpretation.
- Derive mandatory observations from that scope and the candidate facts. For an underside search, interior supplies remain available grounding material but are not mandatory mentions. Preserve their declarations and referenceability.
- Retain required contents for actual interior inspections and newly exposed contents when opening. Give the narrator the **conditional obligation before generation**, using the existing contingent-content projection: opening makes those public contents relevant; leaving the container closed does not permit describing them as seen.
- Keep prompt requirements and verifier requirements derived from the same scoped contract, evaluated against the appropriate pre-turn and candidate states.

This fixes the six underside cases at the requirement-selection layer. It does **not** excuse the two opening cases from the plan’s contents requirement; those need the conditional prompt obligation and measured narration compliance.

The card’s discovery remains the existing authored reveal mechanism:

- Hidden placement beneath the drawer: [`plot.md`](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:86).
- Earned reveal and delivery explicitly saying “beneath”: [`k_sl_1a_b_r0` and patrol variant](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:332).
- `memory_card_recovered` moves it to Kristin and reveals it: [`world.yaml`](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:344).

Do not expose the hidden card through observation context, make opening alone reveal it, or remove the exhausted-underside behavior after recovery.

This preserves the [regression matrix](/home/bcorfman/dev/freytag-forge/.plans/grounded-llm-environment-narration.md:283): passenger-seat contents, telescope-tray coverage, boarding, visibility, custody, and closed-container protection remain required. Globally making container contents optional would violate that contract. Making the supplies optional even during interior inspection would require an explicit plan amendment; I would not hide that change inside this fix.

**Verification within the plan**

First, free deterministic verification:

- Add real-package and synthetic-package cases separating interior, exterior, and underside scopes, with containers both open and closed.
- Test discovery from an **unrecovered-card start**, followed by repeated underside searches. Check earned delivery, “under/beneath,” custody, hidden protection, and no duplicate discovery.
- Exercise the observed `feel under the drawer` phrasing before recovery. Its verb is absent from the current exact `action_evidence` groups; these recordings do not establish that initial path. Verify the bounded fallback, or use an author-reviewed alias if needed.
- Preserve contents requirements for opening, seat inspection, and the synthetic tray; test changed custody, unrelated moves, ambiguity, compound actions, and scope limits.
- Replay saved proposals offline to demonstrate which requirements change. Keep historical rows and labels frozen; this replay is diagnostic, not a new measured success rate.
- Check full rollback, recovery budgets, save/load, and game-break behavior with fault injection. Inspect prompt diffs across narration paths.

For billed verification, **the changed contract needs a new preregistration**. The existing [stage-1 preregistration](/home/bcorfman/dev/freytag-forge/.plans/grounded-llm-environment-narration/t9-enforce-stage1-prereg.md) froze the route specifically to isolate enforcement. A scope/prompt change cannot be run under it and represented as the same experiment.

Prepare fixtures, harness, exact call counts—including intent classification—and dollar ceilings first. Obtain Brandon’s approval before billing; record the merged main SHA and staging deployment. Use new artifact directories, separately authorized smoke/full runs through Ringer, blind labels frozen before verdicts, and no pooling, replacement samples, or retries of partial runs.

Retain stage-1 gates: at most one unsuccessful observation turn; zero committed required-observation misses; existing safety, rollback, two-attempt/two-verifier-request, latency, and false-rejection limits. Add explicit scope-correctness checks so an empty requirement list cannot manufacture a pass.

A passing screen still requires the plan’s **300 withheld turns plus 72 two-package sequence turns**, unchanged acceptance targets, and fresh confirmation fixtures after any material change.

**Risks**

- Scope misclassification could suppress legitimate coverage. Ambiguity must not silently select the least demanding scope.
- Empty required relations mean the current verifier checks no absence claim. “Nothing underneath” and invented discoveries still need independent evaluation.
- Parent identity alone does not distinguish `in` from `under`; any new relation checks must preserve that distinction.
- The opening cases expose a pre-generation/post-change contract gap. Narrowing underside scope alone will not solve them.
- Generic retries may repeat omissions; this smoke demonstrates that possibility but provides no reliable rate.
- The observed card handoff on `inspect the drawer` does not prove every initial underside phrasing works. That is the central missing verification for Brandon’s requirement.