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
