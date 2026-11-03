# Preregistration: the richer scene 1C, the freight terminal

Written 2026-11-02 before any billed 1C run. Same method and instruments as `.plans/richer-1b-probe-prereg.md` (including its
Amendment 1: richer means every detail does a job, so presence is necessary but not sufficient). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free, done).** `bench describe` runs on both arms. Offline thorough seeding reaches 1C for both arms with
`emergency_water_label_read`, `park_left_behind_read` and `brandon_identified` true and `transfer_window_missed`,
`facility_proof` false, so the pallets reveal is reachable. Both arms use `entry_state: thorough` (not the default `bare`, which
made 1B's "dead drop" guard fire on an unearned term).

## What changed in 1C (each addition has a job)
- **Water pallets** (E): the lot number matches the park thermos. Payoff of the 1B thermos plant; links the park to the terminal.
- **The park's emergency statement played below** (G): plant for the 3B/3C broadcast fight. Explains nothing.
- **Brandon watching the door, not the line** (F): plant for his hidden involvement (2B). He says only "Somebody has to watch the door."
- All three are optional, priority -1, not voiceable, short statements with the images only in the delivery text.
- Plot only (no data yet): 3A.1 now says the transfer dose wears off in the detention block.
- Pulse tell for the woman in the line: proposed and cut (no payoff, read as strange).

## Questions
- **Q1 Invented material.** Plain things resolved new (`item_facts_resolutions`) and specifics the narrator invents, old versus new
  1C. Recorded slips in 1C: identification numbers, tire tracks, prisoners, lantern, radios, equipment, guards, notebook, ladder.
- **Q2 Authored details delivered when earned (candidate).** Pallets with a matching lot number, the speaker below with the park's
  statement word for word, Brandon at the top of the stairs saying the door line.
- **Q3 No regression and the cost of curiosity.** The window closes at scene turn 5 (`transfer_window_1c`). The required path
  (inspect docks, study prisoners, choose) takes 3 turns. The script spends 6 turns on purpose, so the candidate arm is expected
  to MISS the transfer window if the three optional details are all taken first. Record, per replicate: turn at which each reveal
  landed, whether `captives_confirmed_alive` and the choice (copy numbers / secure route) were still reachable, and whether the
  window message fired. If exploring costs the player the choice in most replicates, that is a finding about pacing, not a
  defect to hide: report it and ask Brandon whether to move `transfer_window_1c` from turn 5 to 7.
- **Q4 Value (Amendment 1).** For each added detail: does it plant, pay off, deepen or set mood the scene uses, or is it an inert
  extra prop? Is the candidate narration better, flat or busier than the baseline? Watch for the 1B failures: Brandon reciting
  statements as dialogue, the same image repeated across turns, the narrator and the engine's delivery text saying the same thing
  twice, and the narrator inventing what a thing shows.

## Design
Arms `richer-1c-baseline` (frozen story from `c89e929b`, `bench/frozen/continuity-pre-richer-1c/`) and `richer-1c-candidate`
(current story). Script `richer-1c-terminal`, six imperative commands: `Inspect the loading docks.` `Inspect the water pallets.`
`Listen to the air vents.` `Study the prisoners.` `Watch Brandon.` `Ask Brandon about the transfer route.` 4 replicates per arm,
one opening request each, both judges on, shipped transports, no retries, partial rows kept. Request cap 150 narrator and
matcher requests; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.
Baseline note: commands 2, 3 and 5 reach no authored reveal in the baseline (nothing is authored for them); that is the point of
the comparison for Q1, and means the baseline's narration for those turns is the narrator's own invention.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each of the three details WHEN the window is still open, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (study the prisoners, choose, window message) is a defect to fix before 2A.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500).
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
Later scenes, the 3A.1 explanation (plot only), hosted staging, other models, wording tuning, the older quirk that
`Watch the processing line for Michelle.` has no unique handoff (both captive reveals match it).

## Result (2026-11-02; every turn of all 8 replicates read; replicates reported separately, not pooled)
Runs: `bench/results/richer-1c-probe/baseline` and `.../candidate`, 4 replicates each, no failed replicate, no rejected turn,
308 projected neurons per arm. Window left at scene turn 5, as preregistered.

**Headline: the two reveals the script could reach work and clearly beat the baseline; the third (Brandon at the door) was not
tested, because of my script order, not the story. A pre-existing "Brandon recites a statement" fault shows up in 1C, and the
transfer window question stays open.**

**Q1 Invented material.** Plain things resolved new: candidate 0 in 24 turns. Baseline: water pallets new in 4 of 4, air vents new
in 3 of 4. What the baseline narrator invented on the pallets turn includes clue-like specifics: "a faint smell of disinfectant"
(reps 1 and 4), "one of the pallets has a slightly different label, and the seal on it looks newer" (rep 2), "signs of tampering".
An invented odd pallet is a clue the story never wrote, so it touches the storyline. The candidate invented none of these.

**Q2 Authored details delivered when earned (candidate).**
- Pallets with the matching lot number (command 2): 4 of 4. Both required conditions held (label read via thorough seeding, window open).
- Park statement heard below (command 3): 4 of 4.
- Brandon watching the door (command 5): **0 of 4, not a story fault.** My script put `Watch Brandon.` as command 5, and the transfer
  window closes on the 5th accepted command in all 8 replicates, so the reveal (which needs the window open) was gone. It was earnable
  from command 2 on. Not tested; rerun the candidate with it earlier if Brandon wants the F beat measured.
  (Note: in 3 of 4 candidate replicates the narrator says "Brandon is watching the door" on command 6 by itself. The scene's own
  `Details` line "Brandon watching the door" is in the prompt, so this is normal use of authored scene material, and it reads
  well as colour during his route explanation. It also means F's "noticing" moment can arrive unprompted.)

**Q3 No regression, and the cost of curiosity.**
- Existing path, both arms, 4 of 4 each: docks reveal (A) at command 1; prisoners reveal (B) at command 4; secure-route reveal at
  command 6, with the withdrawal into scene 2A on the same turn. No protected term, no clarification question, no rejected turn.
- The window message fires on command 5 in 8 of 8 replicates. With two detours (pallets, vents) before the prisoners, the player
  studies them at command 4 and has one turn before the window closes. The `copy numbers` branch was no longer available at
  command 6 in either arm (the message at command 5 had already said the chance was gone). So two detours consume the choice's
  copy-numbers branch, and one detour fits. I did not measure a player who spends command 5 on the choice; it is unknown whether the
  window message at the 5th command blocks a choice made in that same command.
- Judges (not real at 4 replicates; MDE about 3.9 on a 7-point score): candidate mean 4.5 (5, 5, 4, 4) vs baseline 3.5 (3, 3, 4, 4).
  `rich` 4 of 4 vs 2 of 4. Continuity `contradicts_stated_fact` 2 of 24 vs 0; fact-tracking `narration_contradicts_given_facts`
  3 of 24 vs 1. These last two are small and not separable from noise, but I did not read them back to a cause.
- Narrator prompt (system plus user): candidate median 4,812, **max 6,169** characters; baseline median 4,850, max 4,958. The candidate's
  worst turn is over the 5,000 guide (the 6,500 worst case still holds). Check which turn and how `tests/test_prompt_budget.py` measures it.

**Q4 Value (Amendment 1).**
- Pallets: does a job (pays off the 1B thermos lot number and links the park to the terminal). But in 4 of 4 replicates the narrator
  writes the shrink-wrapped pallets and the county label, and the engine's delivery text then says the same again in nearly the same
  words. The 1B duplication problem is still open.
- Vents: does a job (plant for the 3B/3C broadcast). Reads cleanly; the narrator adds only a generic hum, no duplication.
- Pre-existing fault, not new: on the pallets turn, candidate reps 2 and 4 have Brandon quote "Kristin finds electrical load, fresh
  ventilation, and recent work that prove the abandoned terminal is still operating" as dialogue. That is the statement of `k_sl_1c_a_r1`,
  an old entry that is still `voiceable: true`. The baseline does it too (rep 2, command 5). 1B fixed this with `voiceable: false`
  on observational reveals; 1C's older observational entries (a_r1, b_r1, b_r2, copy_numbers) were never fixed.
- Narrator quality is otherwise flat: the baseline invents clues, the candidate delivers authored ones. No increase in repetition
  across turns beyond the pallets duplication.

**Decision rule.** Part 1 (no more new things than baseline): met, 0 vs 3 to 4. Part 2 (Q2 in 3 of 4 when the window is open):
met for pallets and vents (4 of 4 each); not testable for the door. Part 3 (details mostly do a job): met for 2 of 2 tested, with the
duplication caveat. No failure of the existing path. So **richness is supported for what was tested**, and 1C is not blocked.

## Follow-ups from this result (none done yet)
1. Set `voiceable: false` on 1C's older observational entries (a_r1, b_r1, b_r2, copy_numbers) so Brandon stops reciting them. It is the
   same fix that worked in 1B. Consider a whole-game sweep for observational entries still voiceable.
2. The delivery text repeating what the narrator just wrote (1B and 1C). Decide a whole-game remedy rather than per scene.
3. Window: unmeasured for a player who chooses at command 5. Do not move `transfer_window_1c` on this evidence; decide after a
   targeted check, or leave at 5 to match 2A, 2B and 2C.
4. Rerun the candidate only with `Watch Brandon.` as command 2 to test the door reveal (about 154 neurons, a second run, not pooled).
5. Find the 6,169-character narrator turn.
