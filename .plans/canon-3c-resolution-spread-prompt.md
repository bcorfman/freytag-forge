# ChatGPT prompt: establish how scene 3C's resolution can unfold across turns

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the result to `.plans/canon-3c-resolution-spread-plan.md`.

---

In the first complete hosted canon run (`bench/results/staged-1abb54b0/canon/e2e-llm-canon-progress.json`, scene `3C` in `by_scene`), the player's scene-3C turns before the last one return little, and the final turn delivers the ending and many facts at once. The story is `data/stories/continuity-initiative/`; the relevant files are `storylet-routes.yaml` (canonical resolution events), `pacing.yaml` (the 3C scene points and `ending`), `knowledge.yaml` and `plot.md` scene 3C. The harness that plays the journey is `frontend/e2e/canon-journey.js`; its offline eligibility replay is `scripts/generate_spine_expected_reveals.py`.

Do your own investigation. Establish from the artifacts and code why the 3C resolution lands where it does, what the story's authored intent is for the order and timing of its resolution beats, and whether those beats can reach the player on separate turns using only mechanisms the project already proved. Check the project's pacing and handoff guides and the earlier scene fixes before proposing anything.

Follow `AGENTS.md` and the guides it links, especially `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md` and the pacing authoring guide under `docs/markdown-story-authoring/`. Use only techniques the project already proved, remove before adding, and say plainly when a proposal is new and what you checked. Mark every plot, pacing or story-data change as such so Brandon can approve it before it is applied. Keep the scene within the 2-hour pacing budget in the plan record. Do not write code, do not apply any change, and do not run any billed test.

The result must contain: the cause with artifact lines; the authored intent with quotes; each proposed change with exact old and new text; the cheapest free check for each; what could break; what you could not verify; and the order the fixes should be done.
