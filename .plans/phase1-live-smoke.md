# Phase 1 live smoke preregistration

Written 2026-10-24, before any billed call. Parent:
[game-reimagination-phase1.md](game-reimagination-phase1.md) step 8 part 2.
Brandon (2026-10-24): there is no danger of exceeding the Cloudflare cap; run when ready.

## Question

Does the shipped 1C incident slice run end to end against the real narrator with a
raw blind player, without harness faults, stale cues, impossible handoffs or silent
state loss? This is a smoke test of the harness and the slice, not a quality
measurement. One row proves nothing about rates.

## Design

- Arm: `current` only (the package on `main`, no variation script).
- Start: a synthetic 1C arrival with the 1B facts the unit tests assert
  (`tests/test_continuity_1c_incident.py::_state`). It is not a carried whole-game
  history; never pool it with whole-game results.
- Player: the raw blind player child (`door_ask_player.mjs`) from the entry screen.
  No hints about incidents, outcomes or terminals.
- Stop: the scene reaches 2B, the story ends, or 30 commands. No retries, no
  replacement rows, no pooling. Partial artifacts are kept; a run failure leaves
  `run-failure.txt` in place.
- Caps: smoke n=1: 80 Cloudflare requests, 40 player requests. Full n=12 would be a
  separate preregistration and needs a human decision after reading the smoke.

## Recorded per row

Commands and responses; 1C exit cause (copy numbers, secure route, missed window
plus recovery, other); turns in 1C; whether the matching 2A entry variant was shown;
per turn `cue_fact_id` against facts already true (any hit is a stale cue); clarification
and rejection counts; segments dropped; request and recovery counts; final scene;
`ended_by`.

## Keep rule

The smoke passes if the harness completes (or stops with a clearly attributed
cap/outage failure), the artifacts check passes, and no stale cue, impossible handoff
or unexplained state loss appears. Any such finding is a Phase 1 defect to diagnose
from the transcript before the next billed run, not a wording patch.

## Result of smoke 1 (2026-10-24)

Artifacts: `bench/results/phase1-slice-smoke-1/`. Harness completed (50 Cloudflare, 30
player requests); the artifacts check passed. Ringer reported FAIL only because
`expect_files` resolved against its workdir, not the repo.

Finding, not a pass: the free observation fired on turn 4, but from turn 11 every
command returned the same authored line ("Kristin copies the prisoner numbers...") for
20 turns. The final facts did not show the copy-numbers advantage, 1C was never left,
and the provider logged 20 recoveries. The harness did not record why (reveal
selection, rejection, committed facts), so the cause is undiagnosed. Smoke 1 is kept
as evidence and is not replaced.

Smoke 2 (same design, same caps) is run only after the harness records per-turn
committed facts, reveal selection, rejection and recovery. Two unsuccessful iterations
on the same symptom stop the work for a contract review.
