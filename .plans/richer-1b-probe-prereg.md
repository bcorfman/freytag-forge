# Preregistration: the richer scene 1B, opening and first turns

Written 2026-11-02 before any billed 1B run. Brandon said "apply the fixes (especially the ones already shown to work in other
scenes) and run the full probe". The 1B story carries the 1A lessons (plain names, scoped aliases, exact evidence groups, aligned
windows). Same method and instruments as `.plans/richer-1a-probe-prereg.md`.

**Smoke.** The free offline replay (network blocked at the socket, stubbed replies) ran the baseline script for 7 turns with no
crash before any billed call. A live smoke row is skipped because Brandon asked for the full probe and the harness and runtime are
unchanged since the 1A run.

## Questions
- **Q1 Invented material.** For the same seven commands, how many plain things does the matcher resolve as new, and what does the
  narrator invent, with the old 1B versus the new one?
- **Q2 Authored details delivered when earned (candidate).** Picnic (kickstand, empty leash, one cup tipped), the stranger mouthing
  the broadcast a half-beat ahead, the emergency-water label with a lot number after Brandon's explanation, the keypad he does not
  look at and the freshly oiled drain latch.
- **Q3 No regression.** The bench cache is recovered, Brandon is identified, the gate and drain departure delivers, zero protected
  terms, zero clarification questions. What the narrator says the recovered photograph shows is recorded for both arms.
- **Q4 Opening.** Does the shipped 1B opening use declared park things (bicycle, loudspeaker, picnic) instead of inventing others?

## Design (shipped transports, runtime-wired capture, no retries, no replacement samples, partial rows kept)
Arms `richer-1b-baseline` (frozen story from `b13ba90c`, `bench/frozen/continuity-pre-richer-1b/`) and `richer-1b-candidate`
(current story). Script `richer-1b-park`, seven canonical imperative commands in order: `Look at the picnic blanket.`
`Search beneath the park bench.` `Look at the photograph.` `Watch the stranger.` `Ask the man about Michelle.`
`Examine the thermos.` `Follow Brandon through the service gate.` 4 replicates per arm, each with one opening request, both judges on.
Request cap 150 narrator and matcher requests in all; judge calls reported separately. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or
`AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.

## Scoring (every turn read by hand; per replicate, never pooled)
- **Q1:** per arm and command, plain things resolved new (`item_facts_resolutions`), and every specific the narrator invented
  (numbers, names, labels, writing). Harmless scenery is information only (Brandon: invented things are fine unless they affect the
  main storyline); list any that touch the storyline.
- **Q2:** per command, whether the authored detail appears.
- **Q3:** `bench_clues_recovered` after command 2; `brandon_identified` after command 5; `park_pursuit_resolved` after command 7;
  protected terms; clarification questions; what command 3 says the photograph shows.
- **Q4:** declared park things named in the opening; invented ones listed.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves fewer plain things as new than the baseline on commands 1 and 6, and Q2 holds in at
  least 3 of 4 replicates for each of picnic, stranger, thermos and gate.
- A Q3 failure in the candidate is a defect to fix before scene 1C.
- Record every narrator prompt's length against the budgets in `tests/test_prompt_budget.py`.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
Later turns after the escape, other scenes, hosted staging, other models, wording tuning.

## Amendment 1 (2026-11-02, before any 1B turn was read): richer means added value
Brandon: "it's supposed to make the story richer not just filled with more stuff that doesn't add value." Q2 as written only checks
that an authored detail appears. Add **Q5 Value.** For each replicate of the candidate, read the narration against the baseline's
and record, per authored detail (picnic, mouthed broadcast, thermos label, keypad and oiled latch), whether it does a job in the
scene: plants the hidden role or the 3B/3C broadcast payoff, corroborates a clue, deepens a character, or sets mood the scene's
tension uses; or whether it is just an extra prop listed in passing. Also record whether the candidate narration reads better, flat,
or busier than the baseline. The decision rule changes: richness is supported only if Q2 holds as stated **and** Q5 finds the
details mostly do a job (a detail delivered but inert counts against the candidate, and is a reason to cut it from the story).

## Result (2026-11-02; every turn of all 8 replicates read; replicates reported separately, not pooled)
Runs: `bench/results/richer-1b-probe/baseline` and `.../candidate`, 4 replicates each, none failed. The first baseline attempt died
before judging and was rerun in place. Entry state was the default `bare` (1 committed knowledge), see "Cause of the rejections".

**Headline: the probe does not support richness yet, and it found a defect.** The candidate never delivered the gate escape (command 7)
in any replicate (the baseline did in 3 of 4), and the richer material read as repeated recitation more than as richer story.

**Q3 No regression.**
- Bench cache after command 2 (`k_sl_1b_d_r1`): baseline 4/4, candidate 4/4. Brandon identified after command 5 (`k_sl_1b_b_r2`): 4/4 both.
- Gate and drain departure (`k_sl_1b_c_r1`): baseline 3/4 (replicate 2 lost turn 7); **candidate 0/4**. Candidate turns ended at: rep 1 after
  command 6 (turn 7 rejected), rep 2 after command 5 (turns 6 and 7 rejected), rep 3 after command 6 (turn 7 rejected), rep 4 after
  command 5 (turns 6 and 7 rejected). **This is a Q3 failure: a defect to fix before scene 1C.**
- Every rejection is `narration_known_term_leak` on "dead drop", after the guard's retry also failed. Baseline replicate 2 turn 7 has the
  same code. Candidate 6 rejected turns, baseline 1. No protected term reached a player-visible turn; no clarification questions.
- Photograph (command 3), both arms: the delivered line says it shows the face of the man following her, but the narrator describes
  Michelle's face ("bright smile and sparkle", "determined face", "smile seems distant", "best friend's face") in 7 of 8 replicates. A held item
  shows only "Held by", so the narrator makes up the picture, and it contradicts the delivery line. The owed fix is real: keep a
  one-line depiction on held items.

**Cause of the rejections (read from the recorded prompts).** The candidate turn prompts list the photograph reveal text ("The photograph
recovered from Michelle’s dead drop gives Kristin the face...") twice, as a SCENE fact and as "Brandon Corfman may say this aloud". "dead drop"
is a leak term of the 1A card reveal `k_sl_1a_b_r1`. Under the default `bare` entry that reveal is not earned, so the guard rejects the
phrase. In real play the player has earned it in 1A, so the guard may not fire; **this is a hypothesis, not checked**. The bench has
`entry_state: thorough` to seed earned knowledge. Two real problems remain whatever the seeding: (1) the small narrator reads the "may say
aloud" lines as a script and has Brandon recite them as dialogue (candidate rep 1 and 3 command 6: "Kristin reads the park as a moment cut
short: a bicycle on its kickstand ..."); (2) the richer scene has more such lines, which is why candidate rates are 4/4 against baseline 1/4.

**Q1 Invented material.**
- Plain things resolved new: command 1 baseline 4/4 (picnic blanket, plus rock in rep 1 and paper in rep 2; reps 3 and 4 mention paper or a torn
  notebook page in the prose), candidate 0/4. Command 6 baseline 4/4 (thermos), candidate 0/2 reached. Baseline rep 2 also resolved "stranger" new.
  Decision rule part 1 is met: fewer new things on commands 1 and 6.
- Baseline specifics invented: a piece of paper under a rock or in the bench slats (openings of reps 1 and 3), "black jacket", "tall and
  imposing", "Dr. Michelle McGehee", "a trap". Candidate specifics invented: only the photograph picture above. None touch the storyline
  except the photograph.
- Candidate item-facts noise: "two cups left unplaced" (3 of 4) and "empty item_facts entry for Kristin" (2 of 2 thermos turns); harmless.

**Q2 Authored details delivered when earned (candidate).**
- Picnic (kickstand, leash, tipped cup): 4/4 on command 1.
- Mouthed broadcast: 4/4 on command 4, with Brandon not yet named. Good plant.
- Thermos label with lot number: 2 of 4 reached command 6 and both delivered it; the other 2 were rejected.
- Keypad and oiled latch at the gate: **0/4** (command 7 never delivered).
- Decision rule part 2 (3 of 4 for each of picnic, stranger, thermos, gate) fails on thermos and gate.

**Q4 Opening.** Declared park things named: candidate 2 of 4 (loudspeaker in rep 2; bike, blanket and loudspeaker in rep 4); baseline 0 of 4, and
2 of the 4 baseline openings invent a paper in the bench slats. The shipped openings use the declared things rarely.

**Q5 Value (Amendment 1), candidate vs baseline, by hand.**
- **Mostly not richer yet.** The authored picnic image is a good beat on command 1, but the narrator writes it and then the engine's delivery text
  says it again in nearly the same words, in all 4 replicates ("two cups sit beside a thermos: one is tipped over..." twice in one paragraph).
- The same image is recited again on command 2 (a bench search), in 4/4 replicates, and a third time in Brandon's mouth on command 6 (reps 1, 3).
  The mouthing line repeats on command 5 in all 4 replicates. Repetition, not development.
- What does a job: the mouthing plants Brandon's hidden role and the 3B/3C broadcast payoff (the stranger-then-Brandon reveal reads well in rep 2 and 4);
  the thermos label corroborates his water warning (reps 1 and 3). The kickstand, leash and tipped cup set mood but connect to nothing yet and are
  then repeated. The keypad and latch could not be judged.
- Candidate narration is busier, not clearly better. The baseline reads thinner but mostly cleaner. The baseline's invented paper is the weak point.
- Judges (do not read as real; MDE 3.87 on a 7-point score with 4 replicates): candidate mean 5.5 (6, 4, 6, 6) vs baseline 4.25 (3, 4, 5, 5).
  The `rich` criterion counts candidate **0/4** vs baseline 3/4, `canon_consistent` 3/4 vs 0/4. Fact tracking: invented_change 0/22 vs 3/27,
  narration contradicts given facts 0/22 vs 2/27; continuity contradicts_stated_fact 2/22 vs 0/27.
  The `rich` result fits my hand reading (repetition), but with 4 replicates it is a signal, not a finding.

**Prompt budget.** Candidate narrator prompts (system plus user) median 4,960, max 5,767 characters, user part max 3,240; baseline median 4,724,
max 5,173. Check these against how `tests/test_prompt_budget.py` measures the 5,000 limit before adding more per-scene material.

## Follow-ups from this result (none done yet)
1. Rerun only the candidate with `entry_state: thorough` (a second run, never pooled) to see whether the "dead drop" rejections vanish.
2. Stop the narrator reciting scene lines: do not show a reveal's statement to the narrator both as a SCENE fact and as "may say aloud", and do not
   offer scene-image statements (the park image, the loudspeaker line) as lines Brandon may say. Read the recorded prompt first, fix the material at
   the source, no new prompt rule (see the narration-fix-strategy memory). Then decide how the delivery text and the narrator's own image stop saying
   the same thing twice.
3. Keep a one-line depiction on held items (photograph) so the narrator stops describing Michelle's face.
4. Make the candidate details earn more: give the picnic image a payoff (who sat there, what the cups connect to) or cut it to one line.
