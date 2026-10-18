# ChatGPT prompt: revise the 2A cooling-service archive panel route (round 2)

Paste everything below the line into the ChatGPT Desktop thread used for the 2A
door work. It has the repository. Bring the answer back to Claude Code, which
applies it through a Ringer task and re-runs the free checks.

---

Your first answer (committed as `3692b4c0`; see
`.plans/astra-2a-grounded-route-plan.md`) declared a fixed panel,
`cooling_service_archive_panel`, as the 2A route into the records archive. A
billed smoke (`bench/results/stage7-door-grounded-smoke/`) and a code read found
three problems. Revise the story text only. No code, no matcher or engine
changes, no `knowledge.yaml` or `handoffs.yaml` changes.

## What went wrong

1. **The `t_2a_2b` bridge can claim something that did not happen.** The bridge
   is authored text appended when the earned transition fires. It says "The
   cooling-service archive panel gave them direct access to the records archive.
   They entered the records archive." But the 2A exit never depends on the
   panel (the transition triggers are unchanged and must stay unchanged). A
   player who earns the exit without touching the panel is told they used it.
   In the smoke the narrator had just described a locked panel with a keypad, so
   the bridge also contradicted the turn above it.
2. **The new 2A.3 paragraph never reaches the narrator.** The narrator prompt is
   built from `setting_facts` (as CONSTRAINTS rules), storylet text (SCENE), and
   THINGS. Beat prose in `plot.md` is not sent. Check this with
   `python -m bench prompt --scene 2A --beat 2A.3 --text`: neither the old
   console-limits paragraph nor the new panel paragraph appears. So the only
   channel your text had was the four `setting_facts` lines, and they did not
   stop the narrator inventing a "maintenance access panel" with a keypad and a
   screen.
3. **The panel only reaches THINGS if the per-turn match call names it.** A fixed
   thing is listed in THINGS only when the match call's `refers` list includes
   it (see `ItemFactsProvider.prepare_turn`). Nothing you can write forces that.
   What you can do is make the aliases and the declared name the obvious match
   for the words the player and narrator use.

## What I need

Read `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md` and
`docs/markdown-story-authoring.md` first. Then give me, as exact old/new text:

1. **A new `t_2a_2b` bridge** that is true whether or not the player ever found
   the panel. It may say they reached the infrastructure corridors under their
   inspection cover and went on into the records archive. It must not say how
   they got in, must not name the panel, and must not add a credential, lock or
   second check. Keep the existing 2B `entry_text` working after it.
2. **Where the panel's identity and affordance can actually reach the
   narrator.** Options to weigh, with the proven technique each copies: more or
   better `setting_facts` in 2A (keep them true, visible-state sentences, 12th
   grade, one idea each); a storylet realization in `storylets.md` if one of the
   existing 2A storylets can carry it; or dropping the 2A.3 paragraph. Remove
   or move the 2A.3 paragraph accordingly. The goal: when the player searches for
   a concealed route or access panel, the narrator finds the declared panel
   already in the material and has no gap to fill with a keypad, screen, lock or
   second panel.
3. **Whether any alias or the item name should change** so "access panel",
   "concealed panel", "hidden panel", "panel", "grille" and "seam" resolve to the
   panel and the match call picks it. Remember bare common words are
   leak-scanned in earlier scenes; the current aliases already pass the loader.
4. **Confirm the normal exit.** `t_2a_2b` must still fire without the player
   ever looking for the panel, and nothing you write may add a panel fact to its
   eligibility. State exactly which files and lines you touch.

Keep the usual rules: no facts created by prose, no keyword or regex gates, no
restriction on player wording, no archive contents disclosed in 2A, JANUS stays
earned in 2B. For each change, say the technique it copies, what it could
break, and what you could not establish.
