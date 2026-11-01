# ChatGPT prompt: establish why the hosted canon judge scored the story 25 of 63

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the result to `.plans/canon-quality-diagnosis-plan.md`.

---

The hosted `@llm-canon` test completed for the first time: `bench/results/staged-1abb54b0/canon/` (`e2e-llm-canon.json`, `e2e-llm-canon-progress.json`, `canon-run.log`, `operator-note.md`, `identity.json`). It played 75 turns through all nine scenes and the judge scored 25 of 63; `protected_safe` failed in scene 3C. The judge and test code are `frontend/e2e/roleplay-judge.js`, `frontend/e2e/scene-runtime.spec.js`, `frontend/e2e/canon-journey.js` and `frontend/e2e/canon-policy.js`. The story is `data/stories/continuity-initiative/`. The earlier record is in `.plans/chatgpt-canon-stall-diagnosis-plan.md` and `.plans/grounded-llm-environment-narration.md`.

Do your own investigation. For every boolean the judge failed in every scene, establish from the artifacts and code what the cause is, and give the artifact lines that prove it. Decide for each whether it is a fault in what the judge was given or asked, an artifact of the scripted canon prompts, missing or conflicting story material, or noise from a single sample. Treat the 3C `protected_safe` failure first, since that is the safety result. Look across scenes for causes shared by more than one scene.

Follow `AGENTS.md` and the guides it links, especially `docs/scene-fixing-guide.md`. For every fix, use only techniques the project already proved, remove before adding, and say plainly when a proposal is new and what you checked. Mark every plot, pacing or story-data change as such so Brandon can approve it before it is applied. Do not write code, do not apply any change, and do not run any billed test.

The result must contain: the cause per failed boolean per scene with artifact lines; which are judge or harness faults and which are game defects; exact old and new text for any proposed change; the cheapest free check for each; what could break; what you could not verify; and the order in which the fixes should be done.
