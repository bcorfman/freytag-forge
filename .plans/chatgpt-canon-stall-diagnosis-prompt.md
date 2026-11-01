# ChatGPT prompt: diagnose why the hosted @llm-canon run keeps aborting in scene 1A

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the diagnosis to `.plans/chatgpt-canon-stall-diagnosis-plan.md`.

---

The hosted `@llm-canon` test (runbook section 7, `docs/testing-runbook/hosted-probes.md`) has aborted three times in a row in scene 1A on staging, so no canon verdict has been recorded. `@spine` passed on staging in the same round.

The three attempts are in `bench/results/staged-de04ad8e/canon/`, `bench/results/staged-fa60c481/canon/` and `bench/results/staged-b0d5d6f5/canon/` (each: `canon-report.md`, `canon-run.log`, `e2e-llm-canon-progress.json` and `.md`, `identity.json`). The passing spine run is `bench/results/staged-de04ad8e/spine/` (`e2e-spine.json`, `operator-note.md`). The Ringer manifests that ran them are `scripts/ringer/staged-de04ad8e/staged-regression.json` and the canon manifests derived from it. PRs #737 and #738 (`git log`, `frontend/e2e/`) changed the canon harness between the attempts; the manifests for those fixes are in `scripts/ringer/canon-conditional/`.

The test code is the `@llm-canon` test in `frontend/e2e/scene-runtime.spec.js`, with `frontend/e2e/canon-journey.js`, `frontend/e2e/package-clock.js`, `frontend/e2e/package-clock-controller.js` and `frontend/e2e/scene-walk.js`. The story's timing and scene data are `data/stories/continuity-initiative/pacing.yaml` and the scene 1A files in the same folder. Brandon's running record is the last "Update" paragraphs near the top of `.plans/grounded-llm-environment-narration.md`.

Do your own investigation. Establish from the artifacts and code, not from this prompt, what each abort actually shows, whether the canon test's expectations match how scene 1A is authored to play, whether the failures are defects in the game or in the test harness, and what the cause of each is. Compare the canon attempts against the spine run turn by turn. Check the two harness fixes already merged for anything they got wrong or left unverified, and say whether other scenes are likely to hit the same kind of problem.

Follow `AGENTS.md` and the guides it links. For every fix you propose, use only techniques the project already proved, remove before adding, and say plainly when a proposal is new. Mark every plot, pacing or story-data change as such so Brandon can approve it before it is applied. Do not write code, do not apply any change, and do not run any billed test.

The diagnosis must contain: the cause of each abort with the artifact lines that show it; which results are test-harness flaws and which are game defects; exact old and new text for any proposed change; the cheapest free check for each fix; tests to add or change; what could break; what you could not verify; and whether one more billed canon run is justified and on what condition.
