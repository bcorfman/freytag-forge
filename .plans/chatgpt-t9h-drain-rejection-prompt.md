# ChatGPT prompt: diagnose the new evidence on the storm drain rejection

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the diagnosis to `.plans/chatgpt-t9h-drain-rejection-plan.md`.

---

In the Route E bench for scene 1B, the last player command is `inspect the storm drain` (turn index 5 in each replicate). Earlier work on why that turn is rejected is your own plan `.plans/chatgpt-t9h-route-e-plan.md` (proposal 5) and the work that followed it, listed in the order it was done:

- `.plans/grounded-llm-environment-narration/t9h-drain-question-prereg.md`, result in `bench/results/environment-narration/drain-probe-report.md` and `drain-probe-rows.json`
- `.plans/grounded-llm-environment-narration/t9h-j1-screen-prereg.md`, result in `bench/results/environment-narration/j1-screen-report.md` and `j1-screen-rows.json`
- `.plans/grounded-llm-environment-narration/t9h-j1-scope-prereg.md`, result in `bench/results/environment-narration/j1-scope-report.md` and `j1-scope-rows.json`
- `.plans/grounded-llm-environment-narration/t9h-j1c-wiring-plan.md` and `t9h-j1c-wiring-probe-prereg.md`, result in `bench/results/environment-narration/j1c-wiring-report.md` and `j1c-wiring-rows.json`
- `.plans/grounded-llm-environment-narration/t9h-j1c-drain-enforced-prereg.md`, and its smoke in `bench/results/environment-narration/t9h-drain/smoke/` (`off/rows`, `on/rows`, `worker.log`, `spent.json`)

The running status of all of it is in `.plans/grounded-llm-environment-narration.md`, in the sections headed "T9h route E" and, at the end of the file, "T9h latency work".

The new evidence is the drain turn (turn index 5) of every replicate in these recorded Route E runs, each with `rows/rows.json`, `rows/summary.json` and `worker.log`:

- `bench/results/environment-narration/t9h-hidden/smoke/` (preregistered stage 3, see `.plans/grounded-llm-environment-narration/t9h-hidden-clues-prereg.md` and its stage 3 addendum; report in `report.md`)
- `bench/results/environment-narration/t9h-latency/hedge-short/`, `all-on/`, `on-2/` and `off-2/` (see `.plans/grounded-llm-environment-narration/t9h-latency-prereg.md`)

The runner that wrote the rows is `scripts/ringer/transcript_1a/live_baseline.py`, and the report script is `scripts/ringer/environment_narration/hidden_clues_smoke_report.py`. The verifier and the observation path are `storygame/runtime/observation_verifier.py`, `storygame/runtime/observation.py`, `storygame/runtime/item_facts.py` (`_observation_context`), `storygame/runtime/capture.py` and the flag wiring in `storygame/web_demo.py`. The story package is `data/stories/continuity-initiative/` (the drain is declared in `world.yaml`, the scene in `plot.md`).

Do your own investigation. Establish from the artifacts, not from this prompt: what the drain turn rows show, under which verifier configuration each set of rows was recorded, whether the earlier evidence above accounts for what these rows show or leaves something unexplained, which causes are real defects and which are measurement artifacts, what a rejected drain turn costs in model calls and seconds, and what each cause is. Read the rows against the recorded prompts, provider responses, observation requests and call timings in them, and against the earlier probe rows.

Follow `AGENTS.md` and the guides it links, especially `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`, `docs/scene-fixing-guide.md`, `docs/contributor-guide.md` and `docs/player-input-guide.md`. For every fix you propose, use only techniques the project already proved, remove before adding, rank fixes to the material above rules, never propose regex or parsing of reply text, never lower a verifier threshold or add a per-thing exception, and say plainly when a proposal is new and unmeasured.

The diagnosis must contain: the cause of what the rows show, with the artifact lines that show it; which findings are defects and which are measurement flaws; exact old and new text for any proposed change; the cheapest free check and the cheapest billed check for each proposal (arms, sample count, cost); tests to add or change; whether the full enforced stage drafted in `.plans/grounded-llm-environment-narration/t9h-j1c-drain-enforced-prereg.md` should proceed as written, change, or wait; and what remains unverified. Mark every plot change as requiring Brandon's approval. Do not change code, tests, the story package, historical artifacts or the preregistrations; make no billed calls; write only the plan file.
