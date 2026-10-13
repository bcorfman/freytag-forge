# ChatGPT prompt: the @spine 2C knowledge-guard 409

You can see the freytag-forge project. Please diagnose and propose a fix for one problem. Do not change anything outside it.

## The problem

The hosted `@spine` end-to-end test failed on staging (SHA `f8247eb6`, main after PR 625) at the second 2C prompt, with:

    Turn API returned HTTP 409: narration mentions unavailable knowledge 'transmit the evidence'

That is a `ProposalValidationError` with code `narration_known_term_leak`, raised in `storygame/runtime/narration_safety.py` (the `known_terms` loop, near the "narration mentions unavailable knowledge" message). The player's turn is lost.

## Evidence

- The journey is `scenePrompts` in `frontend/e2e/canon-journey.js`, driven by the `@spine` test in `frontend/e2e/scene-runtime.spec.js`. The run passed 1A, 1B, 1C, 2A and 2B, then reached 2C.
- 2C prompt 1 succeeded: "Assess the executive channel's private offer and whether the people running this are turning on each other."
- 2C prompt 2 got the 409: "Assess the cost of transmitting our evidence right now to the people still held here."
- The player typed "transmitting our evidence". The rejected phrase is "transmit the evidence", so the narrator did not copy the player's words exactly. Check this reading yourself.
- The phrase appears in `data/stories/continuity-initiative/knowledge.yaml` (about lines 1702, 1728, 1744, 1773, 1791) as a `leak_terms` / alias entry for the 2C plan knowledge (`k_sl_2c_d_r1`, `k_sl_2c_d_r2`), and in `handoffs.yaml` (lines 169, 183).
- The guard exempts a term only when it is in the handoff text, the knowledge is earned, the term is in this turn's grounding statements, or it is in the projected beat text. The player's command text is not an exemption.
- Recent related fixes, for the pattern: PR 622 (scene-only words moved to `scoped_aliases`), PR 624 (`leak_terms` authoritative for multi-word phrases), `22f818ad`, `5e6356c7`. Same failure class earlier: 'bench' and 'michelle's files' in 1A.
- The run artifacts are not in the repo. The facts above are everything the trace showed.

## Questions to answer

1. Why did the narrator produce "transmit the evidence" at that point? Read the narrator prompt this turn would get, using the narrator-writing guide and the scene-fixing guide.
2. Had the knowledge the phrase belongs to been earned or unlocked by the time the spine reached 2C prompt 2? If it had, why did the guard still reject it? If it had not, is the spine prompt asking about something the story has not yet revealed?
3. Is the real defect in the story material (a term that should not be guarded, or a term that should be scoped, `leak_terms` wording), in the spine prompt, or in the guard's logic?

## Constraints

- Follow `AGENTS.md`: `docs/scene-fixing-guide.md` (find the source line before changing anything), `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`, `docs/player-input-guide.md`.
- Fix the material at the source. Rules last. Never a regex.
- Scene-only vocabulary must not produce errors outside its scene (decision in `.plans/astra-implementation-plan.md`, Phase 4 item 2, 2026-10-13).
- A fix must work for any story, not only this one: no story-specific code in the shared runtime.
- Recommend only techniques the plan's decisions, the grounding guide or earlier scene fixes already cover. If none covers it, say so and propose a new one with its risk.
- Do not propose "retry the narrator once" or a neutral fallback line as the fix. That is a separate open question about the failure path.

## What I need back

- The cause, with file and line for each claim, and what you could not verify.
- The smallest fix at the source, the files it touches, and the tests that would prove it (hermetic, no live worker).
- How to check it live: which prompt, how many samples, and what result means success.
