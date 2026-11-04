# Preregistration: the richer scene 3A, the detention level

Written 2026-11-03 before any billed 3A run. Same method and instruments as `.plans/richer-2c-probe-prereg.md` (including the
1B value rule: presence is necessary but not sufficient; every added detail must do a job). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free).** `bench describe` runs on both arms (package hashes: baseline `5ab57e3e...`, candidate `7b6d8c45...`). Offline,
`tests/test_richer_3a.py` hands each scripted command to its intended reveal given the facts the earlier commands establish. Whole
quick suite on the branch: 4127 passed, 31 skipped; ruff clean. Both arms use `entry_state: thorough`. The thorough entry state earns
`broadcast_loop_confirmed`, `lemon_cake_calendar_read` and `committed_to_rescue` but NOT `held_transfers_seen` or `badge_craft_noted`
(checked offline), so the candidate arm sets `entry_facts` to those two (this exercises the variants of the wrist tags and the reader).
The frozen baseline does not declare them, so its arm cannot set them; it has nothing authored for tags, the radio loop, the proof or
the reader anyway.

## What changed in 3A (each addition has a job)
- **Wrist tags** (F, 3A.1): every captive's transfer date is a week old; Michelle held them one ticket at a time from the archive
  terminal. Pays off the 2B held transfers and the 2C cart tags, answers "who held them" and "why are they alive". With
  `held_transfers_seen` the tags carry the closing code. Declared thing: `wrist_tags`.
- **Loop in the radios** (G, 3A.1): Michelle's coded words ride inside the facility's own repeating message and change one word; the
  guards no longer hear it. Pays off the loops of 1A, 1B and 1C, answers how the captives came to trust a voice they could not see, and
  plants 3B/3C ("when it stops, everyone will know"). No new thing (uses `stolen_radio`); with `broadcast_loop_confirmed` it says "the same
  ninety seconds".
- **Michelle's private proof** (H, 3A.2): after the medical level, a question about the kitchen calendar; she answers "Saturday,
  circled, K, lemon cake" and apologizes for the birthday. Pays off the 1A calendar; the facility never saw that wall, so the player can
  stop doubting her after the false-recollection experiments. Needs the new fact `lemon_cake_calendar_read`, which `k_sl_1a_g_r2` now
  sets (the only existing entry changed). No new thing.
- **Checkpoint reader** (I, 3A.4): Brandon opens it on the first pass without looking at the keypad; Michelle's people watch him instead
  of the door. Pays off the 1B keypad and the 2A/2B badge checks (with `badge_craft_noted`: "the same ease he showed at the gate"), and
  plants his usefulness against their distrust. Declared thing: `checkpoint_reader`.
- F, G, H, I are optional, priority -1, not voiceable, short statements, windows 0/8/9 (every existing 3A storylet has earliest 0, so
  no forward-activation ordering is at risk).

## Questions
- **Q1 Invented material.** Plain things resolved new, and specifics the narrator invents (what the tags say, who held the transfers,
  what the radios play, the proof's content, what the reader checks), old versus new 3A. The baseline has nothing authored for any of them.
- **Q2 Authored details delivered when earned (candidate).** F on command 2, G on command 3, H on command 5, I on command 7. Each lands
  on the command that asks for it. Record the turn each landed and whether any was refused or went to a different reveal.
- **Q3 No regression.** Required path: reunion (`k_sl_3a_a_r1`, command 1), the medical level (`k_sl_3a_b_r2`, command 4), the framed
  official (`k_sl_3a_d_r1`, command 6), the uprising (`k_sl_3a_c_r1`, command 8) and the bridge to 3B (command 9). Record per replicate
  the turn each landed and whether the scene was left by an earned transition.
- **Q4 Value.** For each detail: does it plant, pay off, deepen or set mood, or is it an inert prop? Is the narration better, flat or
  busier than baseline? Watch the known faults: the narrator or Brandon reciting statements as dialogue, the engine's delivery text
  repeating what the narrator just wrote (echo; the reader delivery says Brandon never looks at the keypad, the likeliest echo), the same
  image repeated, the narrator inventing what a thing shows, and Michelle's explanation ("I held them") appearing before the tags are read.

## Design
Arms `richer-3a-baseline` (frozen story from `e28473a1`, `bench/frozen/continuity-pre-richer-3a/`) and `richer-3a-candidate` (current
story, `entry_facts` held_transfers_seen and badge_craft_noted), script `richer-3a-detention` (nine imperative commands): `Free the
captives.` `Read the wrist tags.` `Listen to the stolen radio.` `Enter the medical level.` `Ask Michelle about the lemon cake.` `Ask the
senior official about the gate codes.` `Check the checkpoint reader.` `Tell the prisoners to start the uprising at the checkpoints.`
`Lead the prisoners upward toward the command levels.` 4 replicates per arm, both judges on, shipped transports, no retries, partial rows
kept, one opening request each. Projected cost at 11 neurons per turn, opening included: 10 turns x 4 replicates = 440 per arm, 880 in
all. Request cap 150 narrator and matcher requests per run; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or
`AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC. 3A pressure events fire at turns 8 and 9 (lockdown, code deadline); the uprising is command 8.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each detail, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (Q3) is a defect to fix before 3B.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500), and name any
  turn over 5,000.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
The transmit branch of 2C entering 3A (the thorough entry state chose rescue), the other order of commands, the 3A.2 experiments
detail beyond the proof, later scenes (the loop plants pay off in 3B and 3C), hosted staging, other models, wording tuning.

## Owed to other scenes (so the plants pay off)
3B/3C: the loop in the radios is the facility's own repeating message; the final broadcast must replace it ("when it stops, everyone will
know"), and every outbound channel is watched (2C monitor light), so the broadcast must be forced from Rebecca's office. 3B can use
Brandon's ease at readers when he opens doors on the climb. The supervisor on Rebecca's purge list (a payoff for the 2A alarm log) is
still not covered.
