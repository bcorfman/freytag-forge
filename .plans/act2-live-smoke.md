# Act 2 live smoke preregistration

Written 2026-11-01, before any billed call. Parent: the Act 2 rebuild in
[game-reimagination-plan.md](game-reimagination-plan.md). Same method as
[phase1-live-smoke.md](phase1-live-smoke.md).

## Question

Do the three Act 2 incidents (`i_2a_real_leak`, `i_2b_audit`, `i_2c_rebecca_corridor`) run
end to end against the real narrator with a raw blind player, without harness faults, stale
cues, impossible handoffs, silent state loss or an unearned fact? A smoke of the harness and
the slices, not a rate. One row proves nothing about rates.

## Design

- Arm `current`, the working-tree package. One row per run, no retries, no replacement rows,
  no pooling across scenes or prefixes.
- Start: a synthetic arrival at the scene, built from the predecessor's exit facts. Never
  pooled with whole-game results.
- Player: the raw blind player child from the entry screen. No hints about incidents,
  outcomes or terminals.
- Prefixes (scripted, spend no player request): `none`; `missed_window` (five neutral
  commands that earn no outcome, so the window closes on turn 5); `stall` (eight neutral
  commands, so the turn-6 nudge and the neutral exit both happen).
- Stop: the successor scene is reached (2B, 2C, 3A), the story ends, or 30 commands.
  Caps per row: 80 Cloudflare requests, 40 player requests.

## Rows, in order

1. 2C `missed_window`. Carries the engine change (neutral recovery), so it runs first.
2. 2C `none`, 2C `stall`.
3. 2B `missed_window`, `none`, `stall`.
4. 2A `missed_window`, `none`, `stall`.

Run row 1 alone first. Rows 2 to 9 run only after its result is read.

## Recorded per row

Commands and responses; exit cause (each declared outcome, missed window plus recovery, or
neutral recovery); turns in the scene; whether the matching successor entry variant showed;
per turn `cue_fact_id` against facts already true (any hit is stale); clarification and
rejection counts; dropped segments; request and recovery counts; final scene; `ended_by`;
the turn the nudge and the neutral exit showed.

## Keep rule

A row passes if the harness completes (or stops with an attributed cap/outage failure), the
artifacts check passes, and there is no stale cue, impossible handoff, unearned fact or
unexplained state loss. Specifically for 2C: a missed window or stall must leave
`committed_to_transmit`, `committed_to_rescue`, `detention_sectors_sealed` and
`evidence_not_transmitted` all false. Any finding is diagnosed from the transcript before the
next billed run, not patched with wording.

## Results (2026-11-01)

Artifacts: `bench/results/act2-smoke-N-*` (gitignored; local). Two sets, no row ever replaced.
Rows 1 to 13 ran with a probe that pre-activated every scene storylet, including the recovery
storylets, which the real engine never does (`_activate_pacing` adds a storylet only when its
activation conditions hold). Rows 14 to 22 are the clean set after the probe fix.

### Defects the smokes found, all fixed

- **2B stall (row 6):** the first 2B beat listed `JANUS` in its Details, so the narrator was
  handed a term the leak guard then refused. Removed from `plot.md`.
- **2A (rows 7 to 9):** `k_supervisor_escorting` was player-visible with `action_evidence`, so
  the exact matcher selected it for "Examine the cooling manifold..." and its mis-sourced effects
  failed validation on every retry. Seven pacing-fact knowledge entries are now unmatchable, and
  three hidden route-effects entries make each recovery's effects equal its knowledge
  (`tests/test_act2_knowledge_sources.py`).
- **2B stall exit (found before the smokes):** `audit_recovery_2b` had a stray
  `processing_numbers_copied == false`, so a player who copied the numbers in 1C and stalled in 2B
  never left. Removed; the stall audit now carries 1C advantages.
- **Probe fidelity (row 11):** pre-activated recovery storylets let a recovery commit on turn 4.
  Probe fixed; rows 14 to 22 are the clean set.

### Clean set, rows 14 to 22

| Row | Scene / prefix | Result |
| --- | --- | --- |
| 14 | 2C missed_window | pass; 3A at turn 8; no commitment or cost fact |
| 15 | 2C none | pass; 3A at turn 8 |
| 16 | 2C stall | pass; 3A at turn 8 |
| 17 | 2B missed_window | harness stop: final narration rejection, 'research files' (unavailable knowledge) after the retries; the player typed a Michelle's-research query |
| 18 | 2B none | pass; 2C at turn 11 |
| 19 | 2B stall | pass; 2C at turn 9 |
| 20 | 2A missed_window | pass; 2B at turn 7 |
| 21 | 2A none | pass; 2B at turn 7 |
| 22 | 2A stall | pass; 2B at turn 7 |

No stale cue, no unearned commitment fact in 2C, no loop. `unearned_facts` is non-empty on 2A and
2B recovery exits only because the recovery realization asserts its own authored effects
(`cover_suspected`, `restricted_corridor_access`, `brandon_name_kept`); that is the design, not a
leak, but the classifier should learn it.

### What the smokes do not show, and what they do

- The keep rule is met for eight of nine rows. Row 17 is the existing friction where the narrator
  echoes a guarded term and, after the retries, the player gets a rejection. The probe treats
  that as a row failure; a real player could retype. Treating a final rejection as a recorded
  rejected turn would make the probe faithful.
- **Every one of the eight passing rows left the scene by a recovery bridge.** In the three
  blind-only rows (15, 18, 21) no player earned an outcome: no name choice, no
  transmit-or-rescue, no convincing inspection. In 2B the blind player searched terminals for
  Michelle's research and never pulled their own file; in 2C they kept questioning Rebecca and the
  authored offer and the purge-tablet moment never surfaced. The exits are mechanically sound; the
  redesign's own moments are not yet visible to a stranger. 1C solved this by having Brandon offer
  the moves in the narration (`1c-brandon-offers-moves.md`); Act 2 has no equivalent yet.
- One row per cell, scripted prefixes, one blind player: nothing here is a rate.

## Round 2: do the offers make the moves visible? (preregistered 2026-11-01, before any billed call)

Change under test (branch `act2-visible-moves`): each Act 2 `entry_text` now has a character
state the moves, the 1C technique. 2A: the supervisor says "show me" at the cooling manifold and
Brandon says "be precise". 2B: Brandon points at the archive terminals, the JANUS records and
Kristin's own file, and asks to delete his name or be told to leave it. 2C: Rebecca's offer, the
purge order and Brandon's yes are told in the entry, then Brandon offers the uplink or the
transfer carts. New fixed things `cooling_manifold`, `broadcast_uplink`, `transfer_carts`. The 2C
outcome entries lost the offer and purge-order sentences (the entry owns them now).

Question: does a raw blind player now reach a real outcome (not a recovery bridge) in each scene?
Rows: the three blind-only cells, prefix `none`, one row each, no retries, same caps and keep
rule as above. Order 2A, 2B, 2C; read each before the next. Outcome sought: exit cause is one of
the declared outcomes. One row each is a smoke, not a rate; a miss is diagnosed from the
transcript before any rewording.

Round 2 log. Row 23 (2A none, offers): left by missed window plus recovery at turn 7; the player went
to the manifold and inspected it, never explained a diagnosis, because the narration gives
nothing to diagnose. Row 24 (2B none): run-failure, `narration mentions protected knowledge
'janus'`: Brandon's line said "JANUS records". Reworded without the term; row 24 stays recorded,
row 26 is the rerun.
Round 2b: observation steps added for 2A (SL-2A-B, `manifold_fault_found`) and 2B (SL-2B-A,
`kristin_file_read`), built by Ringer run act2-visible-moves. Row 25 (2C none): earned
`committed_to_transmit` on turn 1, no recovery. Row 27 (2A none): earned `inspection_convincing` at
turn 4 (observe at the manifold, then explain it). Row 28 (2B none): file pulled on turn 1, but "Tell
Brandon to leave his name in the record" matched neither outcome (the name group wanted "Brandon's
name" or "name in the build record"), so the scene left by recovery at turn 8. Widened both
outcomes' name group to "his name", "name in the record", "the record"; row 29 is the rerun.
`unearned_facts` listing `restricted_corridor_access` on an earned 2A exit is the same classifier
gap as before: the realization asserts it.
Round 2c: row 29 and 30 (2B) earned `k_sl_2b_b_r4` (turn 2 and turn 3) but stalled afterward; the
player never used the medical terminal, so the scene left by recovery at turn 15. Nothing told the
player the maintenance line exists. The keep and erase deliveries now end with the terminal printing
the "Shelly" line and "Kristin has time to type one reply on the medical terminal." Row 31 (2B none):
pulled the file (T1), kept Brandon's name (T2), replied on the medical terminal (T3), left for 2C at
turn 3 with exit cause `brandon_name_kept`, no recovery, no unearned fact.

Result of round 2 (one blind row per scene, prefix none, no rate): every Act 2 scene now earns a real
outcome without a recovery bridge: 2A `inspection_convincing` at turn 4 (row 27), 2B `brandon_name_kept`
plus the reply at turn 3 (row 31), 2C `committed_to_transmit` at turn 1 (row 25). Technique: 1C's. The
entry text states the moves; 2A and 2B add an observation step the choice requires. Not shown: the
`cover_suspected`/doubted and erase outcomes, missed windows and stalls with the new steps, or any rate.
Open: 2C resolves on turn 1, so its pacing and the negotiation set piece are thin; the canonical scripted
journey still waits six filler turns in 2A.

## Round 3: do the earned observations hold up live after PR #742? (preregistered 2026-11-01, before any billed call)

Change under test (`main` at `3f73ea9c`): earned observation before the choice in 2A, 2B and 2C; 2C's
Brandon "Yes." now follows the 2B choice inside the earned observation (`delivery_variants`); the recovery
events no longer fire after the player has chosen. Round 2 rows 25, 27 and 31 predate all of this.

Question: does a raw blind player (prefix `none`) still reach a real outcome, with no recovery bridge and no
rejected narration, through the new observations? Rows 32 (2A), 33 (2B), 34 (2C): one row each, no retries,
same caps as Round 2 (at most 30 commands, 80 Cloudflare / 40 player requests). Order 2A, 2B, 2C; read each
transcript and the composed delivery text before starting the next. 2B and 2C start from the probe's
synthetic clean-exit arrivals (kept name), so these rows say nothing about the erased slice.
Pass for a row: exit cause is a declared outcome, no `run-failure.txt`, no stale cue. Fail is diagnosed from
the transcript before any rewording. One row per scene is a smoke, not a rate.
Not in this round (needs its own preregistration): the kept/erased 2C slices with the three replicates,
missed-window and stall rows with the new steps.

Round 3 result (2026-11-01, Ringer run `act2-visible-moves`, one blind row per scene, prefix `none`, no rate):
all three rows met the preregistered pass rule: declared outcome as exit cause, no `run-failure.txt`, no stale cue,
no rejection, no recovery bridge, no unearned fact. Artifacts: `bench/results/act2-smoke-32-2A-none-r3`, `-33-2B-none-r3`,
`-34-2C-none-r3`.

- Row 32 (2A): observe at the manifold (turn 1, `k_sl_2a_b_r1`), then explain it to the supervisor (turn 2): exit cause
  `inspection_convincing`, `supervisor_convinced`, no `cover_suspected`. The row's `recovery_count` 1 is a narration-retry
  request on the exit turn, not a recovery bridge (`transition_cause` is `earned`).
- Row 33 (2B): pull Kristin's file (turn 1), keep Brandon's name (turn 2), reply on the medical terminal (turn 3): exit cause
  `brandon_name_kept`, Rebecca's corridor entry delivered.
- Row 34 (2C): the first reply to Rebecca earns the observation (turn 1: purge order, Brandon's "Yes.", both moves),
  the uplink command earns `committed_to_transmit` (turn 2), exit to 3A with the detention-sector entry.
- Still not shown: the kept/erased 2C slices with three replicates (2B starts here were synthetic, kept name), the
  doubted/`cover_suspected` and erase outcomes, missed windows and stalls with the new steps, and the 1C recovery audit.
  2C still resolves in two turns, so its negotiation set piece stays short.

## Round 4: kept/erased 2C slices, missed windows and stalls (preregistered 2026-11-01, before any billed call)

Authorized by Brandon on 2026-11-01 ("do the billed Cloudflare runs next"). Build under test: `main` at `3f73ea9c`
plus one probe change (a `--ledger kept|erased` option on `act2_probe.py`, free, built by Ringer, dry-run
verified before any billed row; correction 2026-11-01: the first draft assumed 2C entry-line variants that were
removed in `f917b4b0`, so the ledger now shows only in the observation delivery). No story or engine change in this round. Cloudflare Workers AI only; per-row
caps unchanged (at most 30 commands, 80 Cloudflare / 40 player requests). One Ringer task per row, run name
`act2-visible-moves`, no retries, no replaced rows; a run-failure is recorded as a row and reported verbatim.

Rows (blind player after any scripted prefix; synthetic arrivals as in Round 3):

| Rows | Cell | Question |
| --- | --- | --- |
| 35 to 37 | 2C, ledger kept, prefix none, 3 replicates | Does a blind player earn a transmit or rescue outcome, with the kept-name observation sentence and no recovery bridge? |
| 38 to 40 | 2C, ledger erased, prefix none, 3 replicates | Same, with the erased-name observation sentence ("He glances at Kristin as he says it.") and the erased ledger facts? |
| 41 to 43 | 2A, 2B, 2C, prefix missed_window | Does a missed window leave by the recovery bridge with no unearned outcome, and is 2C neutral (no commitment, no cost)? |
| 44 to 46 | 2A, 2B, 2C, prefix stall | Does a staller leave the scene (nudge at turn 6, withdrawal by the recovery) without a stuck loop? |

Pass per row: no `run-failure.txt`, no stale cue, no rejection, exit within the 30-command cap, and
- slice rows: exit cause is `committed_to_transmit` or `committed_to_rescue`; the earned observation (`k_sl_2c_c_r1`) delivers the
  matching ledger sentence (kept: "He says it coldly and avoids Kristin's eyes."; erased: "He glances at Kristin as he says it."),
  or the row records that the observation was not earned; no unearned fact; recovery count 0.
- missed-window rows: exit cause `missed_window_plus_recovery` or `neutral_recovery`; 2A shows no
  `supervisor_convinced` and no `cover_suspected` it did not earn; 2C asserts no commitment fact and no outcome cost.
- stall rows: scene exit observed, `stuck_loop` false, nudge seen at turn 6.
Reading rule: read the transcript and composed delivery text of every row (passes too) before reporting. A miss is
diagnosed from the transcript and the recorded prompt before any rewording; a reword is a new preregistered round.
Three replicates per slice are a smoke on variance, not a rate. Not in this round: 2A doubted and 2B erase outcomes
(a blind player is unlikely to reach them; a scripted-prefix design would need its own preregistration), 1C recovery.

Round 4 result (2026-11-01, Ringer run `act2-visible-moves`, 12 rows run once each, no retries; artifacts under
`bench/results/act2-smoke-35-*` to `-46-*`). 10 rows completed and met the preregistered pass rule; 2 rows ended
in a recorded run-failure. I read the transcripts of the 10 completed rows and the traces of the 2 failures.
Not a rate.

| Rows | Cell | Result |
| --- | --- | --- |
| 35, 37 | 2C kept, none | `committed_to_transmit` on turn 2 each; kept sentence ("He says it coldly and avoids Kristin's eyes.") delivered on turn 1; recovery 0, rejections 0 |
| 36 | 2C kept, none | **Run failure, no result:** Cloudflare `fetch failed` (`HeadersTimeoutError`, 300 s) while narrating turn 2, after turn 1 had delivered the kept sentence. Infrastructure, not story. Not replaced, per the preregistration |
| 38, 39, 40 | 2C erased, none | `committed_to_transmit` on turn 2 each; erased sentence ("He glances at Kristin as he says it.") delivered on turn 1, never the kept one |
| 41 | 2A missed window | **Run failure, no result:** `ProposalValidationError: narration mentions unavailable knowledge 'cooling fault'` on the first scripted command ("Inspect my work order beside the facility gate."), after retries. The same command passed in row 44, so this is intermittent. Same family as row 17: the narrator echoes a guarded earnable term. The recorded prompt is not in the artifacts, so the cause (what the narrator was shown) is not yet diagnosed. No reword made |
| 42 | 2B missed window | Window fact at turn 5, nudge effect (`audit_reaches_stacks`) at turn 6, exit by recovery on turn 8 to 2C. `brandon_name_kept` is asserted by the recovery by design |
| 43 | 2C missed window | Window turn 5, `purge_alarm_active` and `purge_recovery_ready` turn 6, exit turn 8 with a neutral recovery: no commitment fact, no outcome cost |
| 44 | 2A stall | Window turn 5, `supervisor_escorting` turn 6, exit turn 7 with `cover_suspected` and `restricted_corridor_access` from the recovery bridge (design). The scripted prefix had observed the manifold on turn 3 and never explained it |
| 45 | 2B stall | Window turn 5, nudge turn 6, a clarification on turn 8 ("archive terminals or the medical terminal?", intended behaviour, does not burn the window), exit turn 9 |
| 46 | 2C stall | Window turn 5, alarm and recovery turn 6, exit turn 8 with a neutral recovery |

What this shows:
- The ledger split in the 2C observation works live: 5 of 5 completed slice rows delivered the sentence for their
  ledger and never the other. All five committed to transmit; no rescue commitment was sampled. 2C still resolves
  in two turns.
- Missed windows and stallers leave 2A, 2B and 2C through the recovery bridge at turn 7 to 9, with no stuck loop,
  no stale cue and no rejection in the 5 prefix rows that completed (42 to 46). The 2C recovery is neutral.
- Timing assumption (window turn 5, nudge turn 6) holds on all six prefix rows that completed in the sense
  that the engine events fired on those turns.

Probe caveats, not story defects:
- `nudge_seen_turn` is `None` in every prefix row: the probe looks for the nudge's text verbatim, but the nudge is a
  non-verbatim realization whose effect fact is what fires. The preregistered "nudge seen at turn 6" is therefore
  met through the effect fact, not the probe field.
- `unearned_facts` lists `brandon_name_kept` (rows 42, 45) and `cover_suspected`/`restricted_corridor_access`
  (row 44). Those are what the recovery bridges assert by design; the classifier cannot tell a bridge from an
  earned outcome.

Open: rows 36 and 41 are unresolved (an infrastructure timeout and one intermittent guard rejection). A replacement
for row 36 or a probe of row 41's recorded prompt needs its own preregistration. Still not run: 2A doubted and 2B
erase outcomes, rescue commitment in 2C, 1C recovery audit.

## Round 5: replacements for rows 36 and 41 (preregistered 2026-11-01, before any billed call)

Authorized by Brandon on 2026-11-01 ("yes to 36 and 41"). Build under test is Round 4's, unchanged: `main` at
`3f73ea9c` plus the free `--ledger` probe change. No story or engine change.

Row 41 recorded-prompt diagnosis (free, offline: `assemble_turn_prompt` path with the transport mocked, 2A arrival,
the row's first command "Inspect my work order beside the facility gate."). The row's own artifact held no prompt
(the run failed on turn 1, `partial-trace.json` was empty). Findings from the reconstructed prompt:
- The SCENE section tells the narrator the phrase three times: the frame ("...and the fault is real"), the pressure
  line ("Prove the cooling fault is real to get inside") and the entry statement ("...must prove the cooling fault is
  real to get inside"). The CONSTRAINTS say "Use only what the SCENE section tells you."
- The guard (`narration_safety.py`, "unavailable knowledge") rejects any unearned leak term not covered by a cited
  grounding statement or the handoff text. "cooling fault" is an auto-derived leak term: it is a multi-word
  `must_convey` phrasing of `k_sl_2a_c_r5` and `k_sl_2a_c_r6`, which set no `leak_terms` override.
- This turn offered no candidates and no known ids to cite, so a narrator that echoes the phrase cannot ground it.
  The same command passed in row 44 because that narration avoided the phrase.
Hypothesis (not yet tested): the rejection is a sampling-dependent collision between scene-frame wording the model is
told to use and a guarded earnable phrase, not a defect specific to the missed-window prefix. Candidate fixes are not
chosen here; per the scene-fixing guide step 2 they need a probe with one arm per cause and 10 to 15 samples per arm,
under its own preregistration. Nothing is reworded in this round.

Rows (one each, no retries, same caps as Rounds 2 to 4, run name `act2-visible-moves`):
- Row 47: replacement for row 36, 2C, ledger kept, prefix none. Pass rule as Round 4's slice rows.
- Row 48: replacement for row 41, 2A, prefix missed_window. Pass rule as Round 4's missed-window rows. A second
  rejection of the same kind counts as a recorded miss and as weak evidence for the hypothesis; it is not retried.

Round 5 result (2026-11-01, Ringer run `act2-visible-moves`, one row each, no retries):
- Row 47 (2C kept, none; replaces 36): met the pass rule. First reply to Rebecca earned the observation with the kept
  sentence ("He says it coldly and avoids Kristin's eyes."), the uplink command earned `committed_to_transmit` on
  turn 2, exit to 3A, recovery 0, rejections 0, no unearned fact. The kept slice now has three completed rows
  (35, 37, 47) and the erased slice three (38 to 40); all six committed to transmit.
- Row 48 (2A missed window; replaces 41): **run-failure, no result**, `ProposalValidationError: narration mentions
  unavailable knowledge 'cooling fault'`, again on the first scripted command, `partial-trace.json` empty. This is the
  second miss of the same kind on the same command. The same command, same arrival, passed once (row 44, stall prefix).
  So "Inspect my work order beside the facility gate." was rejected on turn 1 in 2 of 3 live attempts. The Round 5
  hypothesis (scene-frame wording told to the narrator collides with an auto-guarded earnable phrase) is consistent with
  both misses but is still untested; a sampling probe is the next step and needs its own preregistration. The 2A
  missed-window path itself has not yet been observed live, only the 2A stall path (row 44).

## Round 6: sampling probe for the 2A "cooling fault" rejection (preregistered 2026-11-01, before any billed call)

Authorized by Brandon on 2026-11-01 ("yes"). Follows the scene-fixing guide step 2: one arm per likely cause, replay
the same recorded turn live, read every narration. Cloudflare Workers AI only. No change to `data/` or `storygame/`:
each arm runs from a scratch copy of the story package, so the repository package is untouched.

Fixed turn: 2A arrival (the probe's synthetic `_state`), first command "Inspect my work order beside the facility
gate.", one narration turn per sample, a fresh state per sample, no player model. 12 samples per arm, 36 in all, all
three arms started together so time of day is shared. Per-arm Cloudflare cap 60 requests (5 per sample), hard stop at
the cap, no retries of a failed sample beyond the engine's own single recovery.

Arms:
- `control`: the current package. Expectation from rows 41, 44 and 48: final rejection on a large share of samples.
- `wording`: the scene text the narrator is shown no longer says "cooling fault". Three exact replacements in the
  scratch copy: `knowledge.yaml` scene pressure line "Prove the cooling fault is real to get inside" becomes
  "Prove the cooling system is failing to get inside"; the `k_scene_2a_entry` statement ("...must prove the cooling
  fault is real to get inside.") likewise; the 2A `objective` in `plot.md` ("Get inside by proving the cooling fault is
  real") becomes "Get inside by proving the cooling system is failing". Guard data unchanged.
- `leakterms`: the scene text is unchanged, but `k_sl_2a_c_r5` and `k_sl_2a_c_r6` get an explicit `leak_terms` list
  (a precedent exists: `k_supervisor_escorting` sets `leak_terms: []`) that keeps their outcome-specific phrasings and
  drops the bare "cooling fault", "pressure problem", "ventilation fault" and "ventilation problem". r5 list: genuine
  cooling-water pressure fault, genuine pressure problem, genuine cooling fault, real ventilation fault, restricted
  infrastructure corridors, infrastructure corridors, restricted corridor access, console used. r6 list: restricted
  infrastructure corridors, infrastructure corridors, restricted corridor access, console used.

Recorded per sample: final result (ok, or the exception class and message with the offending term), whether the
engine's own single recovery fired, request counts, the full narration. Free dry mode builds each arm's package
offline and asserts the arm differences (the prompt and the leak-term map) before any billed call.

Scoring and decision rule, fixed now:
- Primary: final-rejection count per arm out of 12. Secondary: samples where a first attempt was rejected and recovered.
- Control must show at least 3 of 12 final rejections, or the probe cannot discriminate causes and I report that and
  stop (no fix chosen).
- An arm "wins" if it has at most 1 of 12 final rejections AND control has at least 4 more than it. If `wording` wins,
  the cause is the scene wording and that is the preferred fix, because it changes source material and keeps the guard
  intact. If only `leakterms` wins, the cause is the guard collision. If both win, prefer `wording`. If neither wins,
  neither cause is confirmed and the next arm needs its own preregistration.
- Every narration in a winning arm is read. `wording` must still tell the player the aim is to prove the cooling
  trouble is real; `leakterms` must not name an earnable outcome early. A win with a degraded narration is not a win.
- Rejections naming a different term are reported by term, not folded into "cooling fault".
Not in this round: any change to the repository story data. A fix is a separate step, decided by Brandon after reading
this round, then verified by the 2A rows 32, 41/48-style missed-window and stall paths.

Round 6 result (2026-11-01, Ringer runs `act2-r6-smoke-control` then `act2-r6-arms`; artifacts
`bench/results/act2-guard-smoke-control` and `bench/results/act2-guard-{control,wording,leakterms}`): 12 samples per
arm, same fixed turn, all started together, every sample completed (no transport errors, no cap hit, no raw player
events; 12 to 22 Cloudflare requests per arm).

| Arm | Final rejections | Term | Notes |
| --- | --- | --- | --- |
| control | 7 of 12 | all 7 "cooling fault" | the engine's recovery never fired (recovery count 0 on every sample), so a rejected turn goes straight to the player |
| wording | 0 of 12 | none | |
| leakterms | 0 of 12 | none | |

Preregistered rule applied: control had at least 3 rejections (7), and both arms had at most 1 with control at least 4
above them, so both arms win. Tie-break fixed in advance: prefer `wording`. The narration read (all 24) agrees:
- `wording`: stays on the cooling system (water flow, efficiency, manifold) with no parroting of the scene phrase. It
  invents specifics in 5 of 12 ("a 30% reduction in efficiency due to a faulty valve", "a fault in the manifold"),
  which brush against the diagnosis the player makes at the manifold. The control's accepted samples are the same kind
  of text, so this is not new.
- `leakterms`: in 9 of 12 samples Kristin mutters the scene's own phrase ("Cooling fault, priority one, scheduled for
  inspection tonight"), which is the narrator copying the SCENE section, and sample 7 has the supervisor say the manifold
  is "functioning within normal parameters", which contradicts the real fault. Sample 9 says "inspection tomorrow".
  It stops the rejection by loosening the guard and makes the prose worse.

Conclusion (one scene, one turn, one command, 12 samples per arm, not a rate): the 2A first-turn rejection is caused
by the scene wording the narrator is told, colliding with the auto-guarded phrase from `k_sl_2a_c_r6`. Rewording the
three 2A lines fixes it in this sample set and keeps the guard intact. It also explains rows 41 and 48 (hypothesis
confirmed for that turn). The collision is in the scene pressure line, so it can recur on any 2A turn, not only the
first.

Free audit across all scenes (text match of scene-entry statements and objectives against the leak-term map): the
only entry statement that collides with an earnable outcome entry is 2A (`cooling fault`, owner `k_sl_2a_c_r6`). Two
other matches are worth a look but are untested and may be exempt: `k_scene_3c_entry` contains "exposure and escape",
a leak term of `k_resolution_complete`, and several objectives contain `michelle`, `archive`, `evidence` or `purge`,
which are leak terms of other scenes' entry statements.

Not done: no story edit. The fix (the three `wording` replacements in `knowledge.yaml` and `plot.md`) needs Brandon's
go-ahead, then the usual propagation tests and a live 2A recheck of the 2A paths that rejected (rows 41 and 48).

## Round 7: live recheck of the 2A rewording (preregistered 2026-11-01, before any billed call)

Authorized by Brandon on 2026-11-01 ("yes apply the 2A rewording"). Change under test: the three-line 2A rewording
from Round 6 applied to the repository package: `knowledge.yaml` pressure line and `k_scene_2a_entry` statement become
"...prove the cooling system is failing to get inside", and the 2A `objective` in `plot.md` becomes "Get inside by
proving the cooling system is failing". Left unchanged on purpose: the `plot.md` summary-table row 58 and the
`knowledge.yaml:190` `purpose` line, neither of which reaches the narrator in the reconstructed prompt.

Free first (Ringer, no billing): the edit, the one test that asserted the old line, the Round 6 probe's arms (its
`wording` arm becomes a `legacy` arm that restores the old text, so the probe can still reproduce the old behaviour),
and the focused propagation suites.

Then billed, Cloudflare only, same caps and conventions as before, no retries:
- Probe, `control` arm on the now-fixed package, 12 samples of the same fixed turn. Pass: at most 1 of 12 final
  rejections (Round 6 control had 7 of 12), and every narration read for a regression (parroting of the scene text,
  contradictions of the real fault).
- Row 49: 2A, prefix missed_window (the cell rows 41 and 48 could not complete). Pass rule as Round 4's missed-window
  rows.
- Row 50: 2A, prefix none, blind player. Pass: declared outcome, no recovery bridge, no rejection (row 32 passed before
  the change).
A failure is diagnosed from the transcript before anything is reworded. One row each is a smoke, not a rate.

Round 7 result (2026-11-01, Ringer runs `act2-visible-moves`; artifacts `bench/results/act2-guard-postfix-control`,
`act2-smoke-49-2A-missed-window-postfix`, `act2-smoke-50-2A-none-postfix`). The rewording was applied by a Ringer task
whose own check had three bugs of mine (a `grep -c` under `pipefail`, no `node_modules` link, an unstaged-only
`git diff`); I fixed the check and ran it by hand against the finished worktree, where it passed: 371 Python tests,
178 node tests, ruff, dry probes of all three arms, data diff exactly 3 lines. I exported the patch by hand and applied
it. The full suite has not been run.
- Post-fix control, 12 samples of the fixed turn: **0 of 12 rejections** (Round 6 control: 7 of 12), 12 Cloudflare
  requests, no cap hit. All 12 narrations read: none says "cooling fault"; none contradicts the real fault. Residual
  quality notes, none new: Kristin mutters "Cooling system failure, priority one..." in 2 of 12 (the `leakterms` arm did
  it 9 of 12), 2 of 12 invent "a 30% reduction in efficiency due to a faulty valve", and samples 9 and 11 have Brandon
  say "we already know the cooling system is failing" and a supervisor who stonewalls ("not for you to know").
- Row 50 (2A none, blind): earned `inspection_convincing` on turn 2 (observe the manifold, then explain it), no
  recovery bridge, no rejection. Same result as pre-change row 32.
- Row 49 (2A missed-window prefix): first command passed (the command that failed rows 41 and 48). It did **not**
  exercise the recovery bridge: the prefix's third command ("Examine the cooling manifold...") earned
  `manifold_fault_found`, the window was missed on turn 5, and the blind player then explained the fault on turn 6 and
  earned `inspection_convincing` after the window. So the preregistered pass rule for missed-window rows (exit cause is a
  recovery) is not met, and the row shows a different sound path instead: an outcome earned after the window still
  lands, with no `cover_suspected`, because the recovery no longer fires after the choice. `unearned_facts` listing
  `restricted_corridor_access` is the known classifier gap (the realization asserts it). The 2A recovery bridge itself
  was last seen live in row 44 (stall, before the rewording).

Conclusion: the 2A first-turn rejection is gone in this sample set (0 of 12 versus 7 of 12 before) and the 2A earned path
still works. A pure missed-window 2A row on the new text, with a prefix that does not reach the manifold, was not run.

## Round 8: 3A reunion and radio signal live smoke (preregistered 2026-11-02, before any billed call)

Authorized by Brandon on 2026-11-02 ("yes to live-smoke 3A with one blind row and one committed_to_rescue row").
Change under test: branch `3a-reunion-radio-propagation` on `main` at `7cd1b35e`: the 3A reunion is one unhurried
moment (`k_sl_3a_a_r1`/`r2`) and Kristin gives the uprising signal on Michelle's stolen radio (`k_sl_3a_c_r1`/`r2`).
`act2_probe.py` cannot start in 3A (it is incident-based), so a small `act3a_probe.py` reuses its player, provider
and spend helpers. Arrivals are synthetic, built from the 2C exit facts of `SL-2C-D-R3` (transmit) or `SL-2C-D-R4`
(rescue) plus the `CARRIED_FACTS_2C` set; never pooled with whole-game results.

Question: with a raw blind player, does 3A show the unhurried reunion and the radio signal, leave by the earned
transition to 3B, and show the matching entry line, without rejected narration, stale cues or a stuck loop?

Rows (one each, no retries, no replaced rows, one Ringer task per row, run name `act3a-reunion-radio`):

| Row | Ledger | Question |
| --- | --- | --- |
| 51 | `committed_to_transmit` (the blind default) | Reunion and signal beats show; exit to 3B is earned |
| 52 | `committed_to_rescue` | Same, and the freed-captives entry variant shows |

Row 51 runs alone first; row 52 runs after its transcript is read. Caps per row: at most 30 commands, 80
Cloudflare / 40 player requests. Cloudflare Workers AI only.

Pass per row: no `run-failure.txt`; no stale cue; no rejection; no stuck loop (`repeated_response_streak_max` under 3);
`ended_by` is `scene_3b` within the cap, with `transition_cause` earned; recovery count 0; `michelle_reached`,
`uprising_prepared` and `detention_uprising_started` true at exit. Recorded, not scored: whether the delivered
reunion text contains "unhurried"; whether the signal delivery says Kristin gives the signal; whether the entry
variant (row 52 only) showed; the turn each beat appeared; commands used. Reading rule: read the transcript of both
rows, passes included, before reporting; a miss is diagnosed from the transcript and recorded prompt before any
rewording, and a reword is a new preregistered round. Two rows are a smoke, not a rate.

Round 8 result (2026-11-02, Ringer run `act3a-reunion-radio`, one blind row per ledger, no retries, no rate):
both rows met the preregistered pass rule except one line on row 52 (below). Artifacts:
`bench/results/act3a-smoke-51-3A-transmit`, `bench/results/act3a-smoke-52-3A-rescue` (gitignored; local). Probe built by
Ringer (`act3a_probe.py`, `check_act3a_probe.py`, `tests/test_act3a_probe.py`); dry runs reach 3B for both ledgers.

- Row 51 (transmit): 10 commands, `ended_by` `scene_3b`, exit cause `earned_transition`, 10 requests, no run-failure,
  rejection, clarification, recovery, stale cue or stuck loop. `michelle_reached`, `uprising_prepared` and
  `detention_uprising_started` true at exit. Reunion text ("For one unhurried moment ...") delivered on turn 2; signal text
  ("Michelle hands Kristin the stolen radio and Kristin gives the signal.") on turn 10.
- Row 52 (rescue): 9 commands, `scene_3b`, earned transition, 9 requests, no run-failure, rejection, stale cue or stuck
  loop; the freed-captives entry variant showed on the entry screen. Reunion on turn 3, signal on turn 7.
  **Strict miss:** `recovery_count` is 1, where the preregistration said 0. It is a semantic-refusal retry on turn 2
  ("Listen to Michelle's transmission."): no reveal was selected and `transition_cause` was none; it is not a recovery
  bridge. The reply to that turn invented a radio voice for Michelle ("I'm in a holding block"), which the next turn's
  reunion then contradicts only mildly.
- Observation, not a failure: in row 51 the signal landed on "ask Michelle where the emergency surface gates are", so
  Kristin gives the signal without the player ordering it. In row 52 it landed on "Follow Michelle toward the
  checkpoints", which fits. One of two rows shows it, so no fix is chosen; the command matches the existing
  `k_sl_3a_c_r1` action evidence (verb "ask", noun "emergency surface gates"; read from `knowledge.yaml`, not yet probed),
  which this wording change did not touch.
- Not shown: a row that earns the signal by Kristin's own order (the canon prompt "Signal the prisoners ..."), the
  `SL-3A-C-R2` "warns Michelle about the codes" path, and the neutral/staller exit from 3A.

## Round 9: the four untested Act 2 slices (preregistered 2026-11-02, before any billed call)

Authorized by Brandon on 2026-11-02 ("Yes, one preregistered round"). No story or engine change. The only change is
the probe: Ringer run `phase2-prep` adds four scripted prefixes to `act2_probe.py` (`pure_missed_window`, `doubted`,
`erased`, `rescue`), each the shortest command list that earns its target, checked offline against the real action
evidence. Each prefix is scripted, so it spends no player request; the blind player takes over after it. Cloudflare
Workers AI only. Row numbers continue from Round 8.

The free 3C look (2026-11-02) is recorded here, not tested: the 3C pressure line is "Expose the network and escape",
which does not contain the guarded phrase "exposure and escape" (`k_resolution_complete` alias). Only the 3C entry
statement does, and the guard exempts a term that a grounded statement covers. 3C is probably exempt, unlike 2A, but a
live 3C row waits for Round 10, after the Phase 2 rebuild changes 3C anyway
([phase2-finale.md](game-reimagination/phase2-finale.md)).

Rows (one each, no retries, no replaced rows, one Ringer task per row, run name `act2-round9-slices`):

| Row | Scene, prefix | Question |
| --- | --- | --- |
| 53 | 2A `pure_missed_window` | With no manifold observation, does the window close on turn 5 and SL-2A-D carry the staller to 2B? |
| 54 | 2A `doubted` | Does the doubted outcome show, with `cover_suspected`, and does the matching 2B entry variant show? |
| 55 | 2B `erased` | Does the erase outcome show, with the development-record gap as its cost, and the matching 2C entry? |
| 56 | 2C `rescue` (ledger kept) | Does the rescue commitment show with `evidence_not_transmitted`, and the freed-captives 3A entry? |

Row 53 runs alone first; rows 54 to 56 run after its transcript is read. Caps per row: 30 commands, 80 Cloudflare and
40 player requests.

Pass per row: no `run-failure.txt`; no stale cue; no rejection; no stuck loop (`repeated_response_streak_max` under 3);
the scene is left for its successor within the cap; `exit_cause` equals the row's target (53:
`missed_window_plus_recovery`; 54: `inspection_doubted`; 55: `brandon_name_erased`; 56: `committed_to_rescue`).
Fact checks at exit: 53 neither `supervisor_convinced` nor `manifold_fault_found` before the recovery; 54
`cover_suspected` true and `supervisor_convinced` false; 55 `evidence_gap_development_record` true and
`brandon_name_kept` false; 56 `committed_to_rescue` and `evidence_not_transmitted` true, `committed_to_transmit` and
`detention_sectors_sealed` false. Recorded, not scored: the turn each outcome landed, the successor entry variant,
commands used, recovery count (1 is expected for row 53 only). Known classifier gap: `unearned_facts` lists facts a
recovery bridge asserts by design.

Reading rule: read the transcript of all four rows, passes included, before reporting. A miss is diagnosed from the
transcript and the recorded prompt before any rewording, and a reword is a new preregistered round. Four rows are a
smoke, not a rate.

Round 9 result (2026-11-02, Ringer runs `act2-round9-slices`, one row each, no retries; artifacts
`bench/results/act2-smoke-53-2A-pure-missed-window`, `-54-2A-doubted`, `-55-2B-erased`, `-56-2C-rescue`, gitignored).
One row met the preregistered pass rule. The other three missed, and each miss traces to the new scripted prefix, not
to the story. Probe build (Ringer `phase2-prep`) and its dry runs passed; the dry scripted provider cannot show that a
command matches real evidence, which is exactly what these rows found.

| Row | Result | Why |
| --- | --- | --- |
| 53 2A `pure_missed_window` | **Run-failure** on turn 5, `narration mentions unavailable knowledge 'cooling-water pressure fault'` | Prefix not pure: command 3, "Trace the ventilation duct above the gate.", matches `k_sl_2a_b_r1` (verb "trace", noun "ventilation"), so `manifold_fault_found` was earned on turn 3 and the recovery bridge was never tested. Turn 5 ("Examine the gate tablet ...") then rejected: the narrator named the fault the player had just found, and that phrase is also an auto-guarded leak term of the unearned outcomes `k_sl_2a_c_r5`/`r6`. |
| 54 2A `doubted` | **Run-failure** on turn 2, same term | Scripted command 2 itself contains the guarded phrase ("Explain my vague cooling-water pressure fault ..."), taken from the knowledge entry rather than from narration. The narrator echoed it and the guard rejected it, with no recovery before the player. |
| 55 2B `erased` | **Pass** | Outcome `brandon_name_erased` on turn 2, 3 commands, `ended_by` `scene_2c`, `evidence_gap_development_record` true, `brandon_name_kept` false, no rejection, stale cue or loop, recovery 0, 3 requests. 2C entry text was the standard corridor entry. |
| 56 2C `rescue` | **Miss**: `exit_cause` `committed_to_transmit` | Prefix too short: its first command did not earn the Rebecca observation (she asked a question instead), so the rescue commitment was never reached and the blind player later transmitted. The 3A entry showed the transmit variant. No rejection, stale cue or loop. |

Reading all four: row 55's turn 2 repeats the file facts from turn 1 inside the outcome delivery (by design of the
outcome realization). Rows 53 and 54 show an engine friction already seen in Round 6 and row 17: a final guard rejection
goes to the player with no recovery attempt. It now has a third trigger, a narrator that names a fact the player has
already earned when a guarded outcome phrase is the same words.

Not shown: the 2A recovery bridge on a pure missed window, `inspection_doubted`, `committed_to_rescue`. Fix needed
before any new row, all in the probe (no story edit): 53 replace the ventilation command with one that matches no 2A
observation evidence; 54 write the vague-diagnosis command from words the narration has shown, not from guarded phrases;
56 add the commands that earn the Rebecca observation before the commitment. Replacement rows break the "no replaced
rows" rule, so they need Brandon's go-ahead as in Round 5.

### Round 9b: replacement rows for 53, 54 and 56 (preregistered 2026-11-02, before any billed call)

Authorized by Brandon on 2026-11-02 ("Yes, replace the three rows"). A deliberate deviation from Round 9's "no replaced
rows". No story or engine change; the probe prefixes only, fixed by Ringer task `fix-round9b-prefixes` and checked free
against the runtime's own matcher (`candidate_matcher._matches_all`) before any billed call:
- `pure_missed_window` (2A): command 3 becomes "Trace the cable run along the gate wall." The old one matched
  `k_sl_2a_b_r1`. All five commands now match no 2A knowledge entry.
- `doubted` (2A): command 2 becomes "Give my supervisor a long, vague explanation of the failing water pressure." It
  matches only `k_sl_2a_c_r6`, and neither command contains a guarded outcome phrase.
- `rescue` (2C): the list becomes "Ask Rebecca what she offers for Michelle." then "Free the captives on the transfer
  carts." They match `k_sl_2c_c_r1` and `k_sl_2c_d_r4` in the order the rescue commitment needs.

Rows 53b, 54b and 56b: one each, no retries, no further replacements, same pass rule, caps and reading rule as Round 9.
Row 53b runs first alone; 54b and 56b after its transcript is read. Row 55 stands. A final guard rejection, if it
recurs, is a recorded miss and a finding, not a retry.

Round 9b result (2026-11-02, Ringer runs `act2-round9-slices`, one replacement row each, no retries; artifacts
`bench/results/act2-smoke-53b-2A-pure-missed-window`, `-54b-2A-doubted`, `-56b-2C-rescue`, gitignored). All three met the
Round 9 pass rule. No run-failure, rejection, clarification, stale cue or stuck loop in any row.

| Row | Result |
| --- | --- |
| 53b 2A `pure_missed_window` | Window missed on turn 5, `supervisor_escorting` showed, the recovery bridge carried them to 2B on turn 7 (`missed_window_plus_recovery`). `cover_suspected` and `restricted_corridor_access` true from the recovery by design; `manifold_fault_found` and `supervisor_convinced` false at the window. After the window the blind player inspected the manifold and explained it; no outcome landed, as designed. 7 requests. First live observation of the 2A recovery bridge on the rewritten text. |
| 54b 2A `doubted` | `inspection_doubted` on turn 2, `cover_suspected` and `restricted_corridor_access` true, `supervisor_convinced` false, 2 requests. The 2B "supervisor had logged them at the gate" entry variant showed. No guarded-phrase rejection: the command no longer carried the outcome words. |
| 56b 2C `rescue` | `committed_to_rescue` on turn 2 with `evidence_not_transmitted` true and `committed_to_transmit`, `detention_sectors_sealed` false, 2 requests. The 3A freed-captives entry variant showed ("The captives Kristin had freed from the transfer carts ..."). First live rescue commitment. |

With row 55, every Act 2 outcome and every Act 2 recovery bridge has now been seen live at least once: 2A convincing
(row 50), doubted (54b), missed window (53b); 2B kept, erased (55) and stall (45); 2C transmit, rescue (56b), missed
window and stall (46). Still true: one row per cell is a smoke, not a rate. Still open from this round: the narrator
can name an already-earned fact whose words are a guarded outcome phrase (row 53's turn 5), and a final guard rejection
reaches the player with no recovery. Both are engine friction already recorded (row 17, Round 6), not new story
defects, and neither recurred in rows 53b, 54b or 56b.

## Round 10: the finite 3C finale (preregistered 2026-11-02, before any billed call; NOT YET AUTHORIZED)

Change under test: the Phase 2 rebuild of 3C ([phase2-finale.md](game-reimagination/phase2-finale.md),
[phase2-3c-contract.md](game-reimagination/phase2-3c-contract.md)): incident `i_3c_evacuation` (outcomes
`evacuation_clean` via `SL-3C-C-R1`, `evacuation_costly` via `SL-3C-C-R2`, neutral recovery `SL-3C-H`), window event
`evacuation_window_3c` at turn 9 and nudge at turn 10 (both **assumed**, unmeasured), and the ending latched by
`evacuation_complete` with seven aftermath variants. Probe: `scripts/ringer/phase2/act3c_probe.py` (Ringer
`phase2-3c-probe`), synthetic 3C arrival from the 3B bridge facts only, so the blind player must still earn the
broadcast and archive episodes. Cloudflare Workers AI only. Caps per row: 30 commands, 80 Cloudflare and 40 player
requests. Run name `act3c-finale`. One row each, no retries, no replaced rows.

Question: with a raw blind player after the scripted prefix, does 3C end by its ending (not a timeout), with the right
aftermath variant, no rejected narration, no stale cue and no stuck loop? The 3C overlap from the free look is
now moot: the propagation removed the canonical event `resolution_complete` and `k_resolution_complete`, so the guarded
phrase "exposure and escape" no longer exists in the package.

| Row | Prefix | Expected `exit_cause` | Expected variant paragraph |
| --- | --- | --- | --- |
| 57 | `none` (blind from the first turn) | any of the three, recorded | whichever matches |
| 58 | `clean` | `evacuation_clean` | `barrier_held` |
| 59 | `costly` | `evacuation_costly` | `lower_levels_lost` |
| 60 | `stall` | `neutral_recovery` | `surge_forced_evacuation` |

Row 57 runs alone first; rows 58 to 60 after its transcript is read.

Pass per row: no `run-failure.txt`; no first-turn or later rejection; no stale cue; `repeated_response_streak_max`
under 3; `story_complete` true within the cap; `exit_cause` and variant as in the table (row 57: story ends by a
declared outcome or the recovery, never by hitting the cap). Rows 58 to 60 must also leave the other outcome's fact
false, and row 60 must set no outcome fact. Recorded, not scored: the turn each episode and the window/nudge fired, the
full ending text, which variants showed, commands used. Reading rule: read all four transcripts, passes included; a
miss is diagnosed from the transcript and recorded prompt before any rewording, and a reword is a new preregistered
round. Four rows are a smoke, not a rate. The turn-9 and turn-10 timing is an assumption copied from the 5/6 pattern;
Round 10 only checks that the events fire and the staller ends, not that the pacing is right.

Round 10 result, row 57 (2026-11-02, Ringer run `act3c-finale`, `bench/results/act3c-smoke-57-3C-blind`, gitignored):
**run-failure after 18 turns**, `ProposalValidationError: narration mentions guarded term 'card'` (the 1A memory-card
term, a leak term in a late scene; the known "final rejection reaches the player" friction, third observation). Rows 58
to 60 were not run. Diagnosed from the transcript and the package, no reword:
- **The neutral recovery could not fire.** `SL-3C-H` (and its entry `k_sl_3c_h_r1`) required `truth_no_longer_containable`
  and `rebecca_captured`, which the contract said it must not, and it was written as an action-earned entry ("let the
  surge carry the captives") instead of the event-driven Act 2 recovery shape. A player who has not finished the broadcast
  and archive episodes therefore never reaches the recovery: the Phase 1 gap "a neutral staller stays in 3C" was not closed.
  The dry stall path hid it because the probe scripted both episodes and the recovery command itself.
- **A blind player did not find the next move.** After the broadcast beat landed on turn 1 ("Rebecca is leaving the
  executive office with the Portable data case."), the player re-sent the evidence package about ten times and never
  countered Charles's claim (`SL-3C-A-R2`, which sets `truth_no_longer_containable`) or went after Rebecca. The 3C
  episodes do not offer their next move the way 1C's Brandon does. Recorded, not fixed here.
- Fix in progress (Ringer `phase2-3c-finale`, task `fix-3c-recovery-shape`): recovery gated by the window alone, Act 2
  shape, honest dry stall. Rows 57 to 60 then need a fresh go-ahead, because row 57 is replaced.

### Round 10b: replacement row 57b, then rows 58 to 60 (preregistered 2026-11-02, before any billed call)

Authorized by Brandon on 2026-11-02 ("Yes, replace 57 and run 58 to 60"). A deliberate deviation from Round 10's "no
replaced rows". Change under test: commit `afbd76d0`: `SL-3C-H` gated by `evacuation_window_missed` alone, in the
Act 2 recovery shape (world-only `k_evacuation_recovery_ready` and `k_sl_3c_h_route_effects`, event
`evacuation_recovery_3c` at turn 10), and an honest `stall` prefix (eight neutral commands, no scripted episodes).
Free evidence already in hand: the 3C stall-exit audit passes without its xfail, and the dry stall row reaches
`neutral_recovery`. Same table, pass rule, caps, run name and reading rule as Round 10. Row 57b (blind) runs alone first,
output `bench/results/act3c-smoke-57b-3C-blind`; rows 58, 59, 60 follow after its transcript is read. One row each, no
retries, no further replacements. A final guard rejection is a recorded miss and a finding.

Expected limits, stated now so they are not read as surprises: a blind player may again fail to find the next 3C move
(counter Charles, go after Rebecca). Row 57b passes if the story ends by an outcome or by the neutral recovery within
the cap and the other pass-rule items hold; if the blind player stalls, the recovery at turn 9 to 10 is what ends it.

Round 10b result (2026-11-02, Ringer run `act3c-finale`, one row each, no retries; artifacts
`bench/results/act3c-smoke-57b-3C-blind`, `-58-3C-clean`, `-59-3C-costly`, `-60-3C-stall`, gitignored). All four rows met the
preregistered pass rule: no run-failure, rejection, clarification or stuck loop; `story_complete` true by an earned
ending, never by the cap; the expected `exit_cause` and variant paragraph showed; the other outcome's fact stayed false.

| Row | Result |
| --- | --- |
| 57b blind | The blind player re-sent the evidence package and never countered Charles or chased Rebecca. The neutral recovery ended the story on player turn 8 (`neutral_recovery`), with the base ending and the `surge_forced_evacuation` paragraph. Only `truth_no_longer_containable`, `evacuation_*` facts set; no outcome fact. 8 requests. **The fix works from a cold stall: row 57 failed here before it.** |
| 58 clean | Broadcast, archive, then `evacuation_clean` on turn 3. Variants `barrier_held` and `archive_copies_distributed`. 3 requests. |
| 59 costly | Same, then `evacuation_costly` on turn 3. Variants `lower_levels_lost` and `archive_copies_distributed`; the delivery folds in the gate release. 3 requests. |
| 60 stall | `neutral_recovery` on turn 8 with `surge_forced_evacuation` and `archive_copies_distributed`. No outcome fact. 8 requests. |

Two probe defects, found when reading row 60, found after the rows ran (fixed by Ringer `fix-act3c-probe-stall-and-turns`):
- Row 60's live prefix still scripted the broadcast and archive episodes before the neutral commands, so it is "both
  episodes done, then stall", not a pure stall. Row 57b is the pure stall.
- The probe set the arrival `turn_index` to 2, which moved every 3C window event two player turns early: the window fired
  on player turn 7 and the nudge on 8, not 9 and 10. All four rows share this offset, so the Round 10b timing numbers
  are not the real pacing. Outcomes, variants and the recovery are unaffected.

Findings for Brandon: (1) the ending is reachable from nothing (57b), which is the Phase 1 gap closed; (2) a blind player
does not find 3C's next move on their own (the episodes do not offer it the way 1C's Brandon does), so the neutral ending
is what an unguided player gets; (3) the window is a hard timer: a player who needs more than about 9 turns for
broadcast, archive and barrier is carried out neutrally; the 9 and 10 are still an unmeasured assumption; (4) the
"final guard rejection with no recovery" friction showed in row 57 ('card') and is still open; (5) the ending
paragraphs are short and plain, written to the contract; they want your pass.
