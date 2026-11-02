# ChatGPT prompt: correct the Scene 1A opening and truck plan

Paste everything below the line into ChatGPT Desktop. It has the project files
open, so it reads them itself. Bring the updated plan back to Claude Code, which
applies it through Ringer tasks and probes it.

---

## 2026-11-02: update `.plans/1a-opening-and-truck-feedback-plan.md` in place

Edit the plan; do not regenerate it. Keep the step numbering. Mark every changed
or added item "corrected" or "new", and refresh Status, "Resume here" and the
Completion record. Read `AGENTS.md` first.

Brandon has now ruled on the open results. These are his words, verbatim. Where the
plan conflicts with any of them, correct the plan. You establish where it conflicts
and what each ruling means for the steps, the acceptance table and the decision
boundary; do not assume it conflicts nowhere.

> 1. The world state should show Kristin in the driver's seat, so if "get in the truck" is typed again, the engine/harness should catch this first and say "You're already in the truck" (or something similar) rather than have narration handle this
>
> 2. The area outside the house should be described because the truck is outside (i.e., outside is a parent location, and the truck cab has windows so the player should be able to view the parent location through the windows
>
> 3. There can be a glove compartment with things in it, but the card and/or laptop do not have the glove compartment as a parent container, so this is bad/wrong narration
>
> 4. Yes, the kitchen needs narration, and it used to have this -- not sure what happened here
>
> 5. Yes, there should be an emotional reaction.

Earlier rulings that already stand (check the plan states them correctly): fixes must
be general and not specific to the commands in the transcript; invented details are
fine unless they affect the main storyline; it is fine for Kristin to pick up the
laptop when she gets into the truck, because the narration already said the laptop
was in the truck and plugging in the card is the natural next step.

### Read

| What | Where |
| --- | --- |
| The plan | `.plans/1a-opening-and-truck-feedback-plan.md` |
| Probes and their scored results | `.plans/1a-opening-and-truck-feedback/probe1-prereg.md` to `probe4-prereg.md` (Result sections) |
| The live replicates and their scored results | `.plans/1a-opening-and-truck-feedback/replicates-prereg.md` (Result section); rows in `bench/results/1a-opening-and-truck/replicates-*` |
| Code and story changes so far | commits `e41878c3` (boarding-turn prompt), `7794e4b9` (kitchen start and opening text), `9abc76fb` (replicate results) |
| Earlier direction on engine text versus LLM-written environment prose | `.plans/1a-transcript-continuity-plan.md`, `.plans/grounded-llm-environment-narration.md`, commit `289e2575` |
| History of the 1A opening text | `git log -p` for `data/stories/continuity-initiative/plot.md` and `knowledge.yaml` |
| Project rules | `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`, `docs/player-input-guide.md` |

### Return

The full updated plan, then a short list of what you changed and why, each item
tied to the ruling or the artifact that required it. For every step that needs a
billed run, state the number of calls it needs.
