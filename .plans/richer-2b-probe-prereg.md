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
