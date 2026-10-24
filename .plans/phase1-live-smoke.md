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

## Result of smoke 2 (2026-10-24)

Artifacts: `bench/results/phase1-slice-smoke-2/` (gitignored; local). Same loop,
now diagnosed from per-turn records: the transfer window closed at turn 5, no outcome was
earned, and at turn 11 (`handoff_after_turns`) the legacy handoff staged the incident's
advantage fact. The provider then replied with that fact's fallback text every turn
(`semantic_refusal`, no rejection, nothing committed, one recovery per turn). Cause:
`_activate_pacing` had no unresolved-incident guard on handoff staging. Fixed in step 8e
(guard plus `tests/test_incident_handoff_guard.py`). Smoke 3 re-runs the same design with
the fix, in `bench/results/phase1-slice-smoke-3/`. Open design question: a blind player has
no signal after the window closes that the recovery action exists.

## Result of smoke 3 (2026-10-24)

Artifacts: `bench/results/phase1-slice-smoke-3/` (gitignored; local). The handoff fix
worked: 0 recoveries, no repeated response beyond 2, `stuck_loop` false, no stale cue,
no rejection. The slice still failed as a game: 30 commands, final scene 1C, exit cause
`other`.

- The free observation fired on turn 2. The window closed on turn 5 (`transfer_window_missed`).
  The blind player never attempted either outcome and never found the recovery.
- The live narrator drifted off the world from turn 12: Kristin at her kitchen table,
  a "Project Nightshade" file, driving back with Michelle and Brandon, a keycard reader,
  a service elevator. None are declared in 1C. This is a grounding failure of the
  narrator, separate from the incident design.
- Diagnosis: the opportunities are not visible. Plan section 1 requires the player to see
  what can be attempted and what is at risk; nothing in 1C narration offers copying the
  numbers, asking Brandon, or the recovery. Decision needed from Brandon (see the step 8
  note in the phase 1 plan). Two smokes with the same symptom were diagnosed; no wording
  patch was attempted.

## Result of smoke 4 (2026-10-24)

Artifacts: `bench/results/phase1-slice-smoke-4/` (gitignored; local). Run on the package
with Brandon offering the moves (step 9, from `.plans/1c-brandon-offers-moves.md`).
One row, a raw blind player, no retries.

- Finished: 1C -> 2A -> 2B in 10 commands, `ended_by` `scene_2b`, exit cause `copy_numbers`.
- The player was in 1C for 3 turns: the dock check earned the facility proof, a look
  through the observation shaft confirmed the captives, and "Copy the prisoner numbers."
  earned the outcome and entered 2A. Both 2A entry variants appeared in the responses.
- 0 recoveries, 0 rejections, 0 dropped segments, no repeated response, `stuck_loop` false,
  no stale cue.
- What this does not show: one row; only the copy-numbers path; the missed window and the
  recovery invitation were not exercised; the secure-route path was not tried. The player
  did not read the transfer window as a deadline because it finished before turn 5.
  Not a rate. The preregistered keep rule (harness completes, no stale cue, no impossible
  handoff, no unexplained state loss) is met for this row.
- Still open: three `transfer_window_missed == false` prerequisites were rejected by the
  loader (it counts only reveals as producers of a fact); the 1C-A observation can still be
  earned after a miss (`test_invitation_report.py` records one unanswered invitation).

## Smokes 5 and 6: scripted prefixes (2026-10-24, before any billed call)

Question: do the two paths smoke 4 did not exercise work against the real narrator after
step 9b: the missed window with its recovery invitation (smoke 5) and the secure route
(smoke 6)? Same design, caps and keep rule as above; one row each, no retries, no pooling,
and never pooled with smokes 1-4 (different start: a scripted prefix).

- `--prefix missed_window` (smoke 5): five scripted commands that earn no outcome and let
  the window close on turn 5 (the commands of the missed-window journey in
  `tests/test_phase1_slice_playthroughs.py`). The raw blind player takes over from turn 6 and
  sees the verbatim recovery invitation. Scripted turns spend no player request.
- `--prefix secure_route` (smoke 6): three scripted commands: check the loading docks, look
  through the observation shaft, then "Ask Brandon about the transfer route." The raw
  player continues after the outcome. This forces the choice; it tests the path, not what a
  stranger would choose.
- Outputs: `bench/results/phase1-slice-smoke-5-missed/` and `-6-secure/`. Each row records
  its prefix and the number of scripted turns.
- Smoke 5 passes if the player takes the recovery (or a path to 2B) without a stuck loop,
  stale cue or false outcome; if the player does not find the recovery in 25 further turns that
  is a finding about the invitation, not a harness fault. Smoke 6 passes if the outcome
  commits through free text (`secure_route`), the 2A service-route variant shows, and the row
  reaches 2B.
