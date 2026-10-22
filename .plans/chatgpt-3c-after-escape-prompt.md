# ChatGPT prompt: write a plan for Scene 3C after the escape

Paste everything below the line into ChatGPT Desktop. It has the project files open. Write the plan to `.plans/chatgpt-3c-after-escape-plan.md` (replace the existing one; it was written from an earlier prompt).

---

Two blind-player rows of Scene 3C, both started right after the escape, ended at the deadline instead of an earned ending:
`bench/results/stage7-3c-escape-close-smoke/rows.json` (arms `item-facts` and `no-close`). Two earlier deadline rows are in `bench/results/stage7-3c-relay-access-maintenance_network/` and `bench/results/stage7-3c-world-capture-row/`.

Read every turn of all four rows in full, together with the whole story package under `data/stories/continuity-initiative/` (plot 3A through 3C included) and the record of earlier work on this scene (`.plans/`, especially `implementation_plan.md` and the surface-binding result). Do your own investigation. Find what is wrong, if anything, from the files, and quote the lines you rely on. For each cause say whether it is a plot, package-data or engine problem and name the line that decides it.

Follow `AGENTS.md` and the guides it links. Use only techniques the project already proved, remove before adding, and say plainly when a proposal is new. Do not re-propose something the record shows lost. Mark any plot change as a plot change so it can be approved before it is applied. Do not write code.

The plan must contain: per-turn diagnosis, ranked fixes (exact file, old text, new text, earlier fix followed, what it could break), order of work one measured step at a time, the cheapest probe for each fix, tests to add or change, risks, and what you could not verify.
