# ChatGPT prompt: fix the narrator saying the grille "is not the cooling-service archive panel" (round 3)

Paste everything below the line into the ChatGPT Desktop thread used for the 2A
door work. It has the repository. Bring the answer back to Claude Code, which
applies it through a Ringer task and re-runs the free payload diff.

---

Your round-2 text (committed as `ad8d0c76`, source
`.plans/astra-revise-bridge.md`) worked on the main defect in the smoke
(`bench/results/stage7-door-grounded-smoke2/`, read `results.json`): no keypad,
screen or lock was invented, the bridge is true, and the raw player reached the
archive. One narrator sentence is wrong. In the grounded arm's 2A narration:

> She notices a ventilation grille that looks like it hasn't been used in a
> while, but it's not the cooling-service archive panel.

That sentence names the declared object and then denies that the grille is it.
Your own `setting_facts` say the opposite ("The cooling-service archive panel
looks like a ventilation grille", "The access panel beside the inspection
console is the cooling-service archive panel"). It also leaks the authored name
into prose and invites the player to hunt for a second, "real" panel. N=1, so it
may be noise, but the cause is probably in the material.

## What the narrator saw

`bench/results/stage7-door-grounded-smoke2/prompts/grounded.json` has the exact
user prompt. The full phrase "cooling-service archive panel" appears 12 times:
one THINGS line (`... State: closed. If it changes, give "state": "open".`) and
eleven CONSTRAINTS lines (the placement line plus your ten `setting_facts`).
Two of those lines relate the panel to other words: "looks like a ventilation
grille" and "The access panel beside the inspection console is the
cooling-service archive panel."

## Hypotheses to weigh (do not assume any is right)

1. **Echo.** `docs/world-model-grounding.md` says "The narrator echoes what it
   reads." Twelve mentions of one long name make it the default noun.
2. **Two names for one thing.** The identity sentence and "looks like a
   ventilation grille" give the small model two nouns to reconcile, and it
   split them into two objects.
3. **Negative hardware sentences prime contrast.** "has no lock / no keypad / no
   screen" may encourage "it's not X" phrasing.

## What I need

Read `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md`, and the
memory-style rules they point to (subtractive fixes first; narrator rules last;
12th grade, one idea per sentence). Then give me exact old/new text for the
smallest change that removes the "not the panel" contrast, in this order of
preference:

1. **Subtract.** Remove or merge `setting_facts` lines (for example drop the
   identity sentence, or fold "looks like a ventilation grille" into the
   placement/affordance line) so the narrator has one noun and fewer mentions.
2. **Reword** surviving lines so the panel is described once, as one object,
   without a second name to contrast it with.
3. **Only if 1 and 2 cannot work,** one story-neutral narrator rule (and say why
   no material fix is enough). Do not add a regex or keyword gate.

Keep what the smoke showed working: no keypad, screen, lock or second panel
invented; the route-neutral bridge; the normal 2A exit independent of the panel;
no archive contents disclosed in 2A; JANUS earned in 2B. State exactly which
lines in `plot.md` (and `world.yaml`, if you change an alias or the name) you
touch, what each could break, and what you could not establish. If you change
the name or aliases, say how "access panel", "hidden panel", "grille" and "seam"
still resolve to it (the match call must still pick it).
