# ChatGPT prompt: diagnose the route E rejections of the T9h stage S smoke run

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the plan to `.plans/chatgpt-t9h-route-e-plan.md`.

---

In the T9h stage S smoke run, route `observe_park_bench_1b` (scene 1B) ended several turns unsuccessfully while routes `observe_look_inside_under` and `observe_supporters_1a` did not:
`bench/results/environment-narration/t9h/smoke/e/rows/rows.json` and `summary.json` (compare with `.../smoke/c/rows` and `.../smoke/d/rows`; `.../smoke/worker.log` and `spent.json` hold the Worker side).

Read every turn of the route E rows in full: the commands, the recorded narrator prompts, the provider responses, `item_facts`, the committed or rejected narration, `error`, `engine_opened`, `observation_request`, `call_timings`. Read them together with scene 1B in `data/stories/continuity-initiative/plot.md`, the 1B entries in `knowledge.yaml` and `handoffs.yaml`, and `world.yaml`. Then read the code that decided each turn (start at `storygame/runtime/engine.py` `_preview_observation`, `storygame/runtime/capture.py` `preview_commit` and `_moved_unrelated`, `storygame/runtime/item_facts.py`, the THINGS rendering in `storygame/runtime/cloudflare.py`), and how the harness started these replicates (`scripts/ringer/transcript_1a/live_baseline.py`, `tests/journey_prefix.py`, `tests/test_live_baseline_scene_start.py`).

Do your own investigation. Find what is wrong, if anything, from the files, and quote the lines you rely on. For each cause say whether it is a plot, package-data, prompt-material, engine or harness problem and name the line that decides it. Compare with how the scene 1A drawer and its card reach the same prompts, and with earlier fixes recorded in `.plans/grounded-llm-environment-narration.md` and the files under `.plans/grounded-llm-environment-narration/`.

Follow `AGENTS.md` and the guides it links, especially `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md` and `docs/narrator-writing-guide.md`. Use only techniques the project already proved, remove before adding, and say plainly when a proposal is new. Do not re-propose something the record shows lost. Mark any plot change as a plot change so it can be approved before it is applied. Do not write code.

The plan must contain: per-turn diagnosis of the route E turns, ranked fixes (exact file, old text, new text, earlier fix followed, what it could break), order of work one measured step at a time, the cheapest probe for each fix (name the arms, the sample count and the cost), tests to add or change, risks, and what you could not verify.
