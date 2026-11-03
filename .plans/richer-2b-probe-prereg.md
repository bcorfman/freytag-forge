# Preregistration: the richer scene 2B, the records archive

Written 2026-11-03 before any billed 2B run. Same method and instruments as `.plans/richer-2a-probe-prereg.md` (including the
1B value rule: presence is necessary but not sufficient; every added detail must do a job). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free, done 2026-11-03).** `bench describe` runs on both variations; the baseline and candidate package hashes differ
(`7e56b9d9...` and `c901fc3c...`). An offline walk of the script through the matcher (facts applied as each reveal establishes them,
scene turn = command number minus one) gives F, A, E, B-R4, G, C-R3 on commands 1 to 6. Whole quick suite on the branch: 4064 passed,
30 skipped; repo-wide ruff clean. Both arms use `entry_state: thorough`.

## What changed in 2B (each addition has a job)
- **Held transfers** (F, 2B.2): dozens of prisoner transfers pushed back a week under maintenance tickets, every ticket closed
  "sensor fault", the excuse that closed the 2A alarms. Shows Michelle's quiet resistance before she speaks, rhymes with the 2A alarm
  log, plants the maintenance channel for 2C.5 and the delayed transfers for 3A. It does not name Michelle. Declared thing:
  `transfer_queue`.
- **Badge-reader checks** (E, 2B.3, needs the file read): the build record's access section lists the three checks Brandon said he knew.
  Pays off the 2A badge remark and gives Kristin a concrete accusation. Declared thing: `build_record`.
- **Ticket header** (G, 2B.4, needs the crisis understood and the transfers seen): the maintenance line carries the same header and
  closing code as the held transfers. Lets Kristin trust that the message is not a trap; she was left as bait.
- All three are optional, priority -1, not voiceable, short statements with the images in the delivery text. Windows: E and F 0/6/6,
  G 4/6/7. **Lesson (found by `tests/test_act2_probe.py` [2B-2C]):** `_activate_pacing` opens a storylet early ("earned forward") only
  when every storylet in the scene with an earlier `target_turn` has fired. SL-2B-C (earliest 4, target 6) depends on that to be
  reachable on a fast path (pull file, keep name, reply), so no new optional storylet may have a target earlier than 6. Targets of 2
  would have blocked Michelle's reply until turn 4 for any player who skipped the extras. The audit window closes at scene turn 5
  (`audit_window_2b`); the extras also require it not to be missed (E, F), so they cannot land later.

## Questions
- **Q1 Invented material.** Plain things resolved new, and specifics the narrator invents (ticket numbers, names of staff, what the
  three badge checks are), old versus new 2B. The baseline has nothing authored for a queue, an access section or a header.
- **Q2 Authored details delivered when earned (candidate).** F on command 1, E on command 3, G on command 5. Each lands on the command
  that asks for it, with the facts it needs. Record the turn G landed: it needs scene turn 4 or later.
- **Q3 No regression and the cost of curiosity.** The required path is the file pull, the choice and the reply. This script spends six
  commands on purpose and puts the choice (command 4) before the audit window closes at turn 5. Record per replicate: the turn each
  reveal landed, whether `k_sl_2b_b_r4` landed on command 4, whether `k_sl_2b_c_r3` landed on command 6 (after the window message
  turned on the missed-window path) and whether the scene was left by an earned transition. If detouring costs the choice in most
  replicates, ask Brandon whether `audit_window_2b` should move from turn 5 to 6.
- **Q4 Value.** For each detail: does it plant, pay off, deepen or set mood, or is it an inert prop? Is the narration better, flat or
  busier than baseline? Watch the known faults: Brandon or the narrator reciting statements as dialogue, the engine's delivery text
  repeating what the narrator just wrote, the same image repeated, the narrator inventing what a thing shows, and the narrator
  naming Michelle as the author of the held transfers (the delivery must leave that to Kristin).

## Design
Arms `richer-2b-baseline` (frozen story from `e48b8ec4`, `bench/frozen/continuity-pre-richer-2b/`) and `richer-2b-candidate` (current
story), script `richer-2b-archive` (six imperative commands): `Read the transfer queue.` `Pull up my file.` `Read the access section of
the build record.` `Keep Brandon's name in the build record.` `Read the maintenance line.` `Type one reply to the maintenance line on the
medical terminal.` 4 replicates per arm, both judges on, shipped transports, no retries, partial rows kept, one opening request each.
Projected cost at 11 neurons per turn, opening included: 7 turns x 4 replicates = 308 per arm, 616 in all. Request cap 150 narrator and
matcher requests per run; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.
Baseline note: commands 1, 3 and 5 reach no authored reveal in the baseline; that is the Q1 comparison.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each detail, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (file pull, the keep choice, Michelle's reply) is a defect to fix before 2C.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500), and name any turn
  over 5,000.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
The erase branch (`k_sl_2b_b_r5`) and the missed-window path under the new details, later scenes (the plants pay off in 2C, 3A, 3B and 3C),
hosted staging, other models, wording tuning.

## Owed to other scenes (so the plants pay off)
2C.5: Michelle's second message arrives as a maintenance ticket with the same header and closing code. 3A: the held transfers explain why
the captives are still alive and waiting. 3B/3C: the badge checks (Brandon's access knowledge) can surface when he opens doors for them.

## Result (run 2026-11-03, branch `richer-narration-2b`, commit `2d768426`)
Outputs `bench/results/richer-2b-probe/{baseline,candidate}` (gitignored), 4 replicates each, none failed, 0 rejected turns and 0 guard
rejections in either arm, 616 projected neurons. Every turn of both arms read by hand. Replicates reported separately; the judge scores
are not real signal (4 replicates). One baseline narration reply had a malformed segment that the transport dropped and logged.

**Headline: richness is supported on the 2B path. All three details landed on the command that asks for them in 4 of 4 replicates, the
existing path did not regress, and one older defect (b_r4 re-delivering the file pull) is more visible with the detours.**

- **Q1 Invented material.** Plain things resolved new: baseline 2 in 24 turns (`Kristin's file` on command 4, replicates 1 and 4), candidate 0
  in 24. Specifics the baseline narrator makes up where the candidate has authored text: command 1 sends Kristin to "the medical terminal
  tied to the detention levels" and never finds a queue (4/4); command 3 invents "a list of authorized personnel and their clearance
  levels" for the access section (4/4); command 5 invents a countdown timer at "2 minutes and 14 seconds" (3/4, the same number each time)
  and, once, a "malfunctioning airlock on the detention level". Candidate invents nothing concrete; commands 5 in replicates 2 and 4 add
  generic "technical jargon / cryptic error messages" before the delivery. The three badge checks were never named by the narrator.
- **Q2 Authored details delivered when earned.** Held transfers on command 1: 4/4. Badge checks on command 3: 4/4. Ticket header on command 5:
  4/4 (it needs scene turn 4 or later; it landed at the first chance). The other reveals also landed 4/4: file pull on command 2, keep
  choice (`k_sl_2b_b_r4`) on command 4, Michelle's reply (`k_sl_2b_c_r3`) on command 6. Baseline: file pull, keep and reply 4/4; commands 1, 3
  and 5 reach nothing authored, as expected.
- **Q3 No regression and the cost of curiosity.** The detours cost nothing: in 4/4 replicates the choice landed on command 4 (before the
  audit window closes at turn 5), Michelle's reply landed on command 6, and the scene was left by the same earned transition to 2C after
  turn 6 as in the baseline (4/4 both arms, `advanced_offline` false). The windows fix (targets 6) held on the fast path in the offline test; this
  run did not exercise the three-command fast path live.
- **Q4 Value.**
  - Held transfers: does a job. It replaces an invented dead end with the first concrete sign that someone inside is fighting, in the
    building's own excuse, and sets up the header rhyme. The delivery's last clause ("someone is using it on purpose") carries the point.
  - Badge checks: does a job. It turns the baseline's invented personnel list into a payoff for the 2A remark. Weakness: the narrator
    writes "Brandon watches her, eyes fixed on the screen" and the delivery then says "Brandon watches her read and says nothing"
    (4/4), the known echo of delivery text. The closing sentence adds only the silence.
  - Ticket header: does a job. "Whoever held them wrote this" lands cleanly 4/4 and makes the message trustworthy before the reply. In
    replicates 1 and 3 the narrator adds that the line "might hold the key to finding Michelle", which is her own goal, not a leak.
  - Narration is busier than baseline, but each addition is a clue or payoff, not a prop.
- **Judges.** Candidate 6, 6, 5, 5 against baseline 5, 4, 5, 4 (means 5.5 and 4.5). With four replicates this is not reported as a real gap.
  Continuity: contradicts_stated_fact 0/24 both arms; `protagonist_acts_beyond_command` 4/24 candidate (all on command 4) against 3/24
  baseline (command 4 twice, command 6 once). Fact tracking: missed_change 0, invented_change 0 in both arms; changes attributed to the
  narrator 0 candidate against 2 baseline (the `Kristin's file` creations).
- **Prompt budget.** Narrator prompt (system plus user) median 5,480 candidate against 5,226 baseline, max 5,860 against 5,639. Baseline 2B was
  already over 5,000 on 20 of 24 turns, so this is not new, and no turn nears the 6,500 worst-case cap. Command 2 jumps to 5,791 and 5,860 in
  replicates 2 and 4 (baseline 5,117), when the matcher resolved the build record: about 700 characters of added THINGS lines.
  `tests/test_prompt_budget.py` passes.
- **Item-facts noise (harmless).** Replicates 2 and 3, command 4: the capture tried to place the build record on the archive terminals
  and was refused ("fixed things cannot move"); replicate 2 also logged "archive terminals has no valid place or condition". Nothing changed in state.

**Defects and follow-ups (none done):**
1. **Older, now more visible:** the `k_sl_2b_b_r4`/`r5` deliveries open by re-delivering the file pull ("Kristin pulls her own file first. It says she
   was retained ... Kristin was bait."). Both entries require `kristin_file_read`, so that content was always delivered a turn or more earlier
   by `k_sl_2b_a_r1`. The continuity judge flags command 4 as acting beyond the command in 4/4 candidate and 2/4 baseline replicates. A
   subtractive fix at the source (drop the restated sentences from both deliveries; keep JANUS, Brandon's admission, the choice, the copied
   files and the printed line) needs a decision because it edits existing protected entries and the act2 probe's scripted copy of them.
2. The badge-checks delivery's last sentence duplicates what the narrator writes. Drop it if the next pass wants a shorter beat.
3. The three-command fast path (pull, keep, reply) is covered by `tests/test_act2_probe.py` offline, not by a live run.
