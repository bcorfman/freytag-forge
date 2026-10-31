# ChatGPT prompt: diagnose the stage 2 prose evidence for the hidden bench clues

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the diagnosis to `.plans/chatgpt-t9h-stage2-diagnosis-plan.md`.

---

Scene 1B's transit token, handwritten number sequence and Michelle's photograph are now hidden under the park bench until the player earns them. Your authored plan for that change is `.plans/chatgpt-t9h-route-e-hidden-clues-plan.md`. It was applied and then measured in a frozen, preregistered billed run: `.plans/grounded-llm-environment-narration/t9h-hidden-clues-prereg.md`.

Stage 1 passed. Stage 2 (prose) did not. The evidence is in `bench/results/environment-narration/t9h-hidden/prose/`: `report.md`, `rows.json`, `capture.json`, `worker.log`, and `sheets.md/` (`labels.json`, `blind_key.json`, `blind_sheet.md`, `labels.freeze.json`). The scorer and its tests are `scripts/ringer/environment_narration/hidden_bench_prose_probe.py` and `tests/test_hidden_bench_prose_probe.py`. Stage 1 is in `.../t9h-hidden/probe/`. Brandon's running record of this work is the last sections of `.plans/grounded-llm-environment-narration.md`.

The story package as applied is the uncommitted diff in `data/stories/continuity-initiative/` (`git diff` on `plot.md`, `world.yaml`, `knowledge.yaml`, `handoffs.yaml`, `storylet-routes.yaml`, `storylets.md`). The narration request path that produced the rows is `storygame/runtime/cloudflare.py`.

Do your own investigation. Establish from the artifacts, not from this prompt, what each failed gate and each label actually shows, whether the preregistered gates measured what the player sees, which findings are real defects of the package or the narrator material and which are measurement artifacts, and what each cause is. Read the P0 and P1 rows against each other and against the payloads in `capture.json`. Check your own earlier plan for anything it got wrong or left unverified.

Follow `AGENTS.md` and the guides it links, especially `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`, `docs/scene-fixing-guide.md` and `docs/player-input-guide.md`. For every fix you propose, use only techniques the project already proved, remove before adding, rank fixes to the material above rules, never propose regex or parsing of reply text, and say plainly when a proposal is new. Mark every plot, knowledge or handoff change as a plot change so Brandon can approve it before it is applied. Do not write code, do not apply any change, and do not rerun or resample the billed stage.

The diagnosis must contain: the cause of each failed gate with the artifact lines that show it; which results are measurement flaws and which are defects; exact old and new text for any proposed change; the cheapest free check and the cheapest billed check for each (arms, sample count, cost); tests to add or change; whether the integration smoke (stage 3 in the preregistration) can proceed on its own gates; what could break; and what you could not verify.
