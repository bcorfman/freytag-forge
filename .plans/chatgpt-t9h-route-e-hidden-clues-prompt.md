# ChatGPT prompt: author the hidden bench discovery in scene 1B

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the plan to `.plans/chatgpt-t9h-route-e-hidden-clues-plan.md`.

---

Brandon decided that in scene 1B (`data/stories/continuity-initiative/plot.md`) the transit token, the handwritten number sequence and Michelle's photograph are hidden under the park bench. The player finds them. They are not visible, listed or described before the player earns that discovery.

Your earlier diagnosis is in `.plans/chatgpt-t9h-route-e-plan.md` (see "Why 1A behaves differently" and proposal 6, the hidden-discovery option). The recorded smoke rows it was built from are `bench/results/environment-narration/t9h/smoke/e/rows/`.

Read how the scene 1A memory card is hidden, earned, moved to Kristin and revealed, in every file that touches it (`plot.md`, `world.yaml`, `knowledge.yaml`, `handoffs.yaml`, `pacing.yaml`, and the earlier fixes and W-decisions in `.plans/grounded-llm-environment-narration.md` and its folder). Then read every 1B entry in those files, including what the later 1B entries (`k_sl_1b_a_r1`, `k_sl_1b_a_r2`, the man-identification beat) and the handoff cues require from the clues, and how the 1B route commands in `scripts/ringer/transcript_1a/live_baseline.py` (`observe_park_bench_1b`) would play against your design.

Do your own investigation of what is needed. Follow `AGENTS.md` and the guides it links, especially `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`, `docs/scene-fixing-guide.md` and `docs/player-input-guide.md`. Use only techniques the project already proved, remove before adding, and say plainly when a proposal is new. Mark every plot, knowledge or handoff change as a plot change so Brandon can approve it before it is applied. Do not write code and do not apply any change.

The plan must contain: the exact old and new text for each file; the earning action or actions and the player inputs that must work (and the ones that must not); what each of the three clues' later uses still needs; the premature cue in the 1B handoff text; the cheapest free check and the cheapest billed probe for the change (arms, sample count, cost); tests to add or change; what it could break; and what you could not verify.
