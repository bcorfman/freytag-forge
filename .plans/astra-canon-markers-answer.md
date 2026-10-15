**The judge needs correction, but widening whole-turn exemptions would weaken it. Use text-level attribution and rejudge saved transcripts before buying another hosted run.** No files changed or billed calls made.

| Decision | Verdict | Reason |
|---|---|---|
| D1 | **Modify** | Committed bundles are better evidence, but the hosted test still collects grounding IDs, and scene-wide knowledge loses reveal timing. |
| D2 | **Agree** | The disputed October 12 disclosure passages match forced-handoff or ending content; empty reveal IDs do not establish a narrator leak. |
| D3 | **Modify** | Supplying provenance is correct; whole-turn markers do not identify which prose deserves the exemption. |
| D4 | **Agree** | The repairs address script defects at their source; deterministic preflight checks should have preceded further hosted spending. |
| D5 | **Modify** | The quoted departures are authored bridges, not the named reveals’ `delivery_text`; the safety conclusion largely holds, but its explanation needs correction. |
| D6 | **Disagree** | A committed reveal or earned transition licenses particular content, not every sentence on that turn. |

**1. Measurement validity**

Correcting a demonstrated judge fault is legitimate. The [grounding guide](/home/bcorfman/dev/freytag-forge/docs/world-model-grounding.md) explicitly requires fixing known judge faults before comparisons.

However, 6→8 does not validate the correction: the transcripts changed, and the same disputed examples informed the fix. Freeze the rubric, independently label authored spans and genuine leaks without seeing verdicts, then evaluate both versions on identical saved text—including held-out examples and mixed turns containing actual narrator errors. This is a proposed calibration procedure, not an already demonstrated project result.

**2. Marker precision**

**Verified:** [`_compose_authored_handoff`](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:1354) appends a separate delivery segment; cues are appended separately too. [`_apply_authored_transition`](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:932) emits bridge and entry segments. Forced-handoff preparation can retain narrator prose or replace it with fallback text. Ending backstops append route fallback text.

Thus, a marker says “contains authored content,” not “is authored content.”

| Option | Risk | Implementation cost |
|---|---|---|
| **(c) Identify exact authored spans, retain everything** | Lowest, with eligibility/provenance checks | Moderate |
| **(a) Current whole-turn markers** | Ambiguous exemption; missed bridges | Lowest |
| **(d) Remove authored text** | Loses evidence needed for exits, investigation and coherence | Moderate |
| **(b) Widen whole-turn markers** | Broadest opportunity to excuse unrelated leaks | Low |

Pick **(c)**. Cost order is approximately **a < b < c ≈ d**; overall measurement-risk order is **c < a < d < b**, although deleting authored text may be worst for particular quality checks.

Use existing response segments, bundle selections, cue IDs, transitions, model-stage replies and package text. Compare literal text only against content eligible for that turn; matching arbitrary package sentences could excuse a copied future secret. Preserve uncertain attribution as unknown. This needs harness work, not a new engine mechanism; the hosted progress artifact currently discards useful segment/bundle detail.

**3. The `exit_motivated` drop**

**Verified:** This was **four losses**—1A, 1C, 2A, 3B—and **one gain**, 3A. The [run-5 reasons](/home/bcorfman/dev/freytag-forge/artifacts/e2e-llm-canon.json) demand a discovery/destination connection; 3B specifically demands a place to go. The existing prompt already required naming what was found and where it points.

**Inference:** The added sentence could change emphasis, but changed narration and judge variability also explain the movement. Neither “prompt regression” nor “just noise” is established.

Cheapest useful isolation: rejudge the **same five scene inputs**, holding markers fixed, with that sentence present versus absent, three repeats each: **30 judge calls**, no hosted gameplay. That tests the sentence specifically, not the entire marker change.

**4. Sample size and spend**

Treat 8/9 versus 6/9 as a descriptive observation, not evidence of improved accuracy or player safety. Both runs scored 28/63; a larger safety score could reflect fewer false positives or more missed leaks.

My minimum pilot:

- Blind-label three existing complete journeys.
- Run each judge version three times on every scene: **3 journeys × 9 scenes × 2 versions × 3 repeats = 162 judge calls**.
- Primary measures: false disclosure accusations and missed genuine disclosures against labels.
- Secondary measures: all seven checks separately, repeat disagreement, scene-level paired changes, errors and cost.

Reuse these calls for the sentence check only if the experimental arms actually isolate it. Report uncertainty clustered by journey; 81 scene judgments per arm are not 81 independent playthroughs. Three journeys are a pilot, not guaranteed statistical resolution. The [runbook](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:242) requires several complete runs and an explicit distinguishability assessment.

**5. Reading the verdicts**

I inspected all three cited October 12 departure/ending turns and the October 15 disputed departures.

- **October 12, rep 1, 1A turn 14:** the Continuity Initiative disclosure matches the forced-handoff content. I agree it should not count as unauthorized narrator disclosure.
- **October 12, rep 1, 3C turn 14:** the Phase Two disclosure appears in route fallback/ending content after the narrator’s evidence-packing prose. Again, the cited disclosure is not a narrator leak.
- **October 15, 3B departure:** “began the broadcast” is in [`plot.md`’s bridge](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/plot.md:732). The reveal’s delivery instead describes disconnecting the relay and sending Brandon’s confession. The same bridge-versus-delivery distinction applies to 1B and 2A.

These findings reject the **cited safety accusations**, not every possible defect in those scenes. Echoing an earned reveal can still fail progression through repetition, contradict current state, misattribute knowledge, or add an unearned secret. Authored content can also have an authoring/timing defect even when narrator attribution is wrong.

**6. Script repairs**

The commit diffs support the diagnoses: stale prompts missed reveal evidence, Rebecca was named prematurely, and 45 turns could not cover package pacing. The prompt repair also changed **2B**, beyond the brief’s emphasis on 1C/2A.

The [name test](/home/bcorfman/dev/freytag-forge/tests/test_spine_prompt_names.py) belongs at the fixture layer: it prevents an informed test author from supplying unavailable names. It does not replace runtime narration safety. Its private-validator dependency and regex-based JavaScript extraction are maintenance weaknesses; I would not extend that parsing approach.

The larger budget retains `MAX_STALLED_TURNS = 5` and scene handoff bounds, so it does not simply remove stall detection. But “some storylet fired” is weaker than “the intended reveal chain progressed.” Also, the hosted loop can stop after exhausting 3C prompts without asserting story completion. Nine visited scenes are insufficient.

**7. Additional risks**

1. **Temporal leakage:** `judge-journeys.js` unions knowledge across the whole scene. A late-earned fact can retroactively excuse an earlier disclosure. Supply turn-level eligibility.
2. **Two evidence paths:** the hosted [`recordRevealedKnowledge`](/home/bcorfman/dev/freytag-forge/frontend/e2e/scene-runtime.spec.js:33) still uses segment grounding IDs. D1’s bundle correction is not consistently applied.
3. **Incomplete judge reference:** `sceneCanon()` supplies situation, pressure and earned statements, while the prompt refers to “five source files.” It supplies no explicit inventory of unearned protected facts. Some confident safety classifications therefore exceed the supplied evidence.

**Next three actions, ranked**

1. **Free:** preserve segments/bundles, correct bridge attribution, and audit turn-level knowledge plus completion evidence. Move this below calibration only if existing artifacts already prove those contracts.
2. **Free:** independently label saved disputed and held-out mixed turns. If whole-turn markers consistently isolate content without missing leaks, reconsider whether span extraction is worth its cost.
3. **Billed: approximately 162 judge calls:** run the paired saved-transcript pilot. Buy hosted gameplay only if missing evidence cannot be recovered offline.

For option (c), replace the four marker-related sentences in `roleplay-judge.js` with:

> “The supplied labels identify text inserted by the runtime. Exempt only those spans from narrator-disclosure penalties. Judge all other text normally. Use knowledge available on that turn. Read the full turn when judging exit motivation and other quality checks.”

This follows the existing guidance to separate narrator text from story sentences; the specific span-label implementation still needs validation.