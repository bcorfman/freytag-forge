# Brief for ChatGPT Desktop: review the design of freytag-forge as a whole

You have helped fix this project one defect at a time. I now want the opposite view. Read the project and tell me where the design itself is wrong or expensive, and what you would change. You are not bound to the current design. Where a rule in `AGENTS.md` or the PRD is the cause of a recurring problem, say so and argue for changing the rule. If something is sound, say that too and say why, so I know what to keep.

Read the files yourself. Cite a file (and a line or entry) for every claim. Separate what the evidence shows from what you suspect. Do not give generic advice about LLM games.

## What the project is

An engine for interactive roleplay stories. The player types free text. A small non-reasoning Llama-class model narrates each turn. The engine owns world facts. A story is a package (`data/stories/<story>/`): `plot.md`, `knowledge.yaml` (reveals, scene frames), `world.yaml` (entities, facts), `handoffs.yaml` (cues, forced deliveries), `storylet-routes.yaml`, `pacing.yaml`, `storylets.md`. One shipped story ("The Continuity Initiative", nine scenes, planned for a two-hour play). The engine is meant to run other stories.

Start with: `AGENTS.md`, `docs/PRD.md`, `docs/contributor-guide.md`, `docs/world-model-grounding.md`, `docs/markdown-story-authoring.md`, `docs/testing-runbook.md`, `.plans/world-model.md` (the W decisions), `.plans/scene-affordance-e2e.md` (the running record of what was measured and changed; read it from the end backwards). Runtime: `storygame/runtime/{engine.py,cloudflare.py,candidate_matcher.py,narration_safety.py,knowledge.py,state.py,validation.py}`, `storygame/story_package/{loader.py,models.py}`. Bench and live measurement: `bench/`, `scripts/ringer/affordance/`, `frontend/` blind-player E2E.

## How we work today (the process is also in scope)

- Story and plot text are written in ChatGPT Desktop (you). Code is written by cheap worker models under a tool (Ringer) that runs an executed check. An orchestrating model writes specs, reviews and measures. The owner decides.
- Measurement: an LLM blind player plays each scene on a hosted staging copy, three replicates, nine scenes. Failures are read by hand from recorded turns and prompts.

## Evidence of recurring problems (check each against the code; challenge my reading)

1. **Guard vocabulary is global, availability is per scene.** The narration safety scan builds guarded phrases from every item alias, every multi-word `must_convey` phrase, every entity name and alias. A phrase is allowed only when its owner is earned or nameable in the current scene. Result: rejected turns kept appearing for ordinary words ("encrypted message", "coded message", "archive crisis", "escape route", "rescue efforts", "security officer", "Rebecca's desk"). A per-reveal `leak_terms` list was added to split leak vocabulary from recall vocabulary. Declaring a new world item with any name rejects that name in every scene where the item is not placed (a scan of nine scenes showed 13 to 16 new rejections out of 19 cases per scene for a broad declaration, 1 per scene for a minimal one). See the plan entries "Leak terms split", "2C declaration decision", and `storygame/runtime/narration_safety.py`.
2. **A missed pointer has no second chance.** A cue is delivered once (`delivered_cue_ids`). `nudge_after_turns` exists in `models.py` and is read by nothing. A scene ends by timer after a fixed turn count and then the engine forces the missing deliveries, so the player gets reveals they did not earn. Three open cases share this: 2A (a player answered the supervisor's question with forms instead of naming the inspection), 2C (a Michelle-first player never takes the copy step), 1A (a player never searches the drawer). See the entries "Timer-ending audit", "Reach-the-reveal round".
3. **Reveals fire on exact word groups.** Each reveal has `action_evidence`: groups of phrases, one phrase from each group must be in the command, fixed synonym classes only. Authors maintain lists of 20 to 40 verbs and objects by hand. Blind players type natural verbs that miss ("Retrieve", "Take", "Use my copied files"). There is a semantic fallback (search `semantic_ask` and Jev in `cloudflare.py`). Judge whether the whole word-group approach is the right authoring surface and what the fallback really covers.
4. **The narrator narrates the command, not the scene.** A billed probe of 72 replies showed that adding a scene sentence about the copied files did not make the narrator bring them up; it invents objects (consoles, doors, guards) around the command. Many rules were tried and most lost (see "Fixing a Scene" in `AGENTS.md`).
5. **Measurement is noisy and cross-cutting misses are common.** Play exits across full runs moved 24 of 24, 20, 19, 23 of 24 with no change that explains the swings; only the rejected-turn count (7, 3, 2, 0) moved with the fixes. Specs written in good faith missed a third reader of a shared index and a cross-scene alias rule; both were found by hand. A regression corpus test of 479 saved narrations is being added to catch the class.
6. **Story-agnostic engine versus story data.** The engine must not name story nouns, yet scene logic lives in many files (plot.md front matter, knowledge.yaml, handoffs.yaml, storylet-routes.yaml, pacing.yaml, world.yaml), and one scene fix often touches four of them.

## What I want from you

1. **A ranked list of the design flaws you find** (at most eight), each with: the evidence (file and entry), the cost it imposes (rejected turns, stalled scenes, author effort, review effort), and your confidence. Include flaws I did not list. Include flaws in the rules themselves (`AGENTS.md`, PRD) and in the process, if you see any.
2. **For each flaw, a proposed redesign.** Be concrete: what changes in the data model, the scan, the matcher, the pacing or the workflow; what stays; how to migrate the shipped story without rewriting it; what it costs in worker-model tasks; the single risk that would make it lose; the cheapest offline check and the smallest live check. Mark each as incremental (a field, a rule, a test) or structural (a changed concept). If a structural change needs a rewrite of a core part, say which part and why incremental will not do.
3. **Answer these directly:**
   - Should guarding be global with exemptions, or scoped (a name or phrase guarded only where it matters, or only before the scene that introduces it)? What is the smallest model that removes the "declare a thing, break narration elsewhere" trap without letting early leaks through?
   - Is the right reaction to a missed pointer a repeated cue, a staged escalation (cue, then a stronger delivery pointer, then the forced delivery), a timer that explains what was lost, or something else? The nudge field is dead; should it be built or deleted?
   - Is exact word-group matching the right primary mechanism, a fallback to something semantic, or a typed intent layer the author fills in once per reveal? What would make authoring a reveal cheaper and its miss rate lower?
   - Where should the line between engine and story data sit so a scene fix touches one place?
   - What should be measured, how often, and with how many samples, to get a signal that is cheaper than a nine-scene by three-replicate run and less noisy?
4. **What to stop doing**: which current practices cost more than they return.
5. **What to keep**: which parts of the design are right and should not be touched.
6. **A sequenced plan** of at most ten steps, ordered by (reduction in rejected turns and stalled scenes) divided by (cost and risk), where each step is small enough to be one worker task or one story round with you. For each step say what evidence will show it worked.

## Rules for the answer

- Short sentences. A diagnosis section first (at most twenty lines), then the ranked flaws with redesigns, then the plan.
- Say what you could not verify and what you assumed.
- If you disagree with how I framed a problem, say so and say why.
- Narrator-facing text you propose must be at an 8th-grade reading level. Anything else may be technical.
