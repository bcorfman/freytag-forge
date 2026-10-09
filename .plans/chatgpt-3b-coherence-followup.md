# ChatGPT Desktop follow-up: correct the 3B coherence answer (2026-10-08)

Paste everything below the line into the SAME chat as the first answer.

---

Thank you. The plot verdict is useful. Several parts of the answer need
correcting before I can use it. Re-read the files, then answer each point. Do
not edit files.

1. **Your proposed frame repeats the pull we removed.** You wrote `situation`:
   "...on the way to Rebecca's office and the broadcast relay." and `pressure`:
   "...then open the relay for the broadcast." In live play, every time the
   scene text named the office or the relay, players typed "Reach the office"
   or "Seize the relay" and never tried the false alarms (PR 532 removed them
   from the opening text; PR 533 removed them from the 3A bridge text). The
   rule we follow is: take the pulling line out, do not add a new one. Write
   two alternatives that do not name Rebecca's office, the relay or the
   broadcast at all, and that name only JANUS and what Kristin can do to it.
   Say which of the three (yours, or either of the new ones) you expect to
   keep players on the first step, and why. Do not claim certainty; we will
   test them.

2. **The objective.** You marked `objective: Overload JANUS with false alarms`
   a contradiction and said to restate the broadcast. PR 533 narrowed it on
   purpose, and the run after it was the first where players touched the
   inspection console. Argue the other side: is "false alarms" a true and
   complete objective for the first part of the scene, given that the scene
   frame, the cues and the later steps carry the rest? If you still think it
   must change, show the exact wording and why it will not pull players to
   the end of the chain.

3. **Staged cues.** You called the relay cue (`handoffs.yaml`, `relay_open`)
   and the Brandon voice-channel cue (`brandon_confession_available`) pulls
   and said to "present them late". Read `storygame/runtime/engine.py` (around
   the `staged_cue_fact_id` and `knowledge.requires` logic) and
   `docs/markdown-story-authoring.md`. Does the engine already show a cue only
   after the reveal behind it can be earned? If so, retract those two verdicts
   or say what is still wrong.

4. **"Relay" and "broadcast" are not the same thing in the story.** Plot 2C
   says the broadcast system can only be started manually from Rebecca's
   secured office. Plot 3B.4 has Brandon free the external communications
   relay in the relay chamber so the broadcast can run. Yet the scene's
   `location_id` is `broadcast_relay`, the frame says the group needs "an
   opening to reach the broadcast relay", and `k_scene_3b_entry` says the
   relay is the "immediate contested objective". Spell out, step by step, who
   does what and where: the broadcast start, the relay disconnect, Brandon's
   confession. Then say whether the story ever says Kristin herself must reach
   the relay, or only that Brandon does. State if any scene text contradicts
   this.

5. **Boundary texts you did not check.** Read the 3A scene text, including
   3A.4, the `t_3a_3b` and `t_3b_3c` bridge texts and the 3C `entry_text`.
   Quote any line that names the office or the relay as the player's next
   destination at the start of 3B. Say whether each is true to the plot and
   whether it will pull a player past the false alarms.

6. **`location_id: broadcast_relay`.** You said to audit it separately. Do the
   audit now. What does the engine or the narrator do with a scene's
   `location_id` (check `docs/world-model-grounding.md` and how scene
   location feeds the opening and the places the narrator may name)? Kristin
   is placed in `security_corridors`. Would `security_corridors` be a true
   `location_id` for 3B, and what else would change if it were?

7. **Check your quotes.** Several rows in your table cite line numbers and
   quote text. Re-open each file and confirm every quote is verbatim and the
   line number is right. Mark any you could not verify. Remove any row you
   cannot support.

8. **Reading level.** Every line you propose for `situation` and `pressure`
   goes to a small non-reasoning model. Short common words, one idea per
   sentence, no "contested", no joined demands. Check your proposals against
   `AGENTS.md` "Writing Narrator Rules" and rewrite any that fail.

Finish with a short corrected table that lists only the lines whose verdict
changed, and one sentence saying whether you now think the first answer's main
conclusion (the opening gives conflicting directions) still stands.
