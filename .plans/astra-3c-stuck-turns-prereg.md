# Preregistration: Stage 7 Scene 3C stuck-turn screens (DRAFT, not approved)

Written 2026-10-18 before any further billed 3C run. Follows `.plans/chatgpt-3c-stuck-turns-plan.md`
(Step 1; Steps 2 and 3 only if its bar is missed). Code under test: current `main`
`5633582d` plus the uncommitted free work in this tree (tests and probes only; no `data/` or `src/` change).
Brandon has not approved this document. Nothing billed runs until he does.

## What is already settled (free, no new claim needed)

- PR #667's phrases make D-R1 the unique match for recorded turns 12, 13, 14 in the state after D-R2
  (`tests/test_3c_cue_chain.py`, 13 pass). The all-ten ambiguity rows are unchanged.
- The D-R2-first and D-R1-first chains reach an earned end with no deadline ids
  (`tests/test_resolution_cascade.py`).
- The surface-group binding moves only the captives, only after both C parts and at the deadline, survives
  save/load, and moves no person (`bench/results/stage7-3c-surface-binding/report.json`).
  The binding is not adopted by this prereg.

## What the n=1 smokes showed (not rates)

- Smoke `stage7-3c-probe-smoke3`, fresh synthetic 3C entry, semantic fallback off: control and pre667 both
  ended by the deadline backstop (14 accepted turns). Neither reached D, so the smoke says nothing about #667.
  Control committed A-R1 on turn 12 and B-R1 on 13; pre667 committed A-R1, B-R1, C-R1, C-R2 by turn 12.
  Control had 5 rejections that nobody has read yet. Reading them is step 0 below.
- A-R1 does not match "send/transmit the evidence" (its object list has "evidence package" only). That is
  reported, not fixed here: the plan forbids expanding evidence again.
- Smokes 1 and 2 were harness bugs (a snapshot passed as state; entry facts missing). Both are fixed and
  pinned by real-engine tests.

## Step 0 (free, before anything billed)

1. Read the 5 control rejections in `bench/results/stage7-3c-probe-smoke3/rows.json` and record their causes.
2. Add the labelled post-turn-8 start to the probe (below) and pass its real-engine dry check: the reveal
   universe at start is exactly `[k_sl_3c_d_r1]`.

### Step 0 result (2026-10-18, free)

1. The 5 control rejections in smoke 3 were narration-guard rejections, not matcher faults: attempt 3
   `unavailable entity 'house'`; attempts 4 and 5 `protected knowledge 'janus selection'`; attempts 15 and 16
   `unavailable knowledge 'send the evidence'` (the narrator echoed the player's own command, the same shape as the
   plan's turn 13 case). Guards are left as they are, per the plan.
2. The probe now takes `--start post8`. Offline with a real engine, the reveal universe at the start is exactly
   `['k_sl_3c_d_r1']` in both arms, the scripted prefix commits A-R1, B-R1, C-R1, C-R2, D-R2 with turn index 8,
   and 15 hermetic tests pass. Not yet checked by hand: the 10-attempt cap for post8 rows and the smoke caps in
   `plan.json` (it shows 80 Cloudflare / 40 player for n=1, not the 60 / 20 in the table below); fix before approval.

## Live work, in the plan's order (Step 1)

Arms everywhere: `control` = current package; `pre667` = same package with the four #667 phrases removed
(`bench/variations/stage7-3c-pre667.json`, replacement matches exactly once). Same system prompt, model,
settings and raw blind player. Arms interleave row by row. Semantic fallback ON (as hosted) and recorded per row.

**Free first.** The 15-command matcher table (deployed vs current evidence, all-ten and state-appropriate and
recorded-eligible subsets) is `bench/results/stage7-3c-matcher-table/`. Win at this boundary (plan): current
selects D-R1 on turns 12, 13, 14 and deployed does not; no new matches elsewhere; the all-ten ambiguity on
12 and 14 is preserved.

**Live A: isolated recorded-command probes.** Labelled synthetic post-turn-8 state (A-R1, B-R1, C-R1, C-R2,
D-R2 committed by scripted reveals, turn index 8; a true replay is impossible because the bundles hold no full
save). Replay the recorded raw commands of turns 9 to 14 as SEPARATE one-command probes from that state, so
each is an independent "does this command commit D-R1 now" check. These raw texts are an explicitly labelled
raw-language check, not new player input. Per probe: committed reveals, status, rejection text. No player
model is used. Turns 13 and 14 are not forced after a successful turn 12.

**Live B: free-form continuation.** From the same post-turn-8 state, the raw blind player continues freely;
cap 10 attempts; stop at `story_complete`. This is what shows whether the scene can still end, so it is the
measure for the loop; A is a mechanics check.

**Live C: full fresh 3C screen.** Both arms, synthetic 3C entry (entry facts asserted), the raw blind player from
scene turn 1, 20-attempt cap, real deadline at 14 accepted turns. Record accepted turns separately from attempts.

**Smoke before screens:** one row per arm for each of A, B, C (A needs no player), read in full (narration plus
appended cues) before the 12-row screen. Run each screen at most once; one Ringer task per smoke or screen.

### Measures (engine data only, never narration text)

`committed reveal ids in order`, `d_r1_commit_attempt`, harness outcome (`earned_complete`, `deadline_complete`,
`no_complete`), rejections, clarifications, accepted turns, `deadline_event_ids`. Report rejections,
clarifications and deadline completions separately from earned completions; keep the raw "stuck" count beside
them. If provenance cannot be shown, mark unknown, never earned.

### Bar and stopping rule (the plan's)

Earned means `story_complete` with Phase Two earned through an eligible E reveal after A, B, both C parts and both
D parts, with no deadline event supplying any link. Required: at least 10 of 12 earned completions per the
requested 80% bar (9/12 is 75% and does not pass). Differences under 3 rows between arms read "not distinguishable
at n=12". Keep all rows and counts; no significance claim. Stop adding edits when the current package meets the
bar. If every arm fails, report that. Do not change the matcher, expand evidence, weaken the knowledge guard,
add an escape reveal, or disable the deadline.

## Spend ceilings (hard caps; harness stops on cap, quota, outage or malformed output; no replacement rows)

Measured from `stage7-3c-probe-smoke3`: 74 spend events over 33 attempts, so about 1.3 Cloudflare calls per
attempt (not split further in that file). Ceilings assume 3 Cloudflare calls per attempt, with Brandon to
correct if a dollar ceiling is needed:

| Run | Rows | Player attempts | Cloudflare requests |
| --- | ---: | ---: | ---: |
| A smoke (6 probes x 2 arms) | 12 probes | 0 | 36 |
| A (12 reps x 6 probes x 2 arms) | 144 probes | 0 | 432 |
| B smoke | 2 | 20 | 60 |
| B | 24 | 240 | 720 |
| C smoke | 2 | 40 | 120 |
| C | 24 | 480 | 1440 |

Player calls are billed outside the Worker; their per-token price is not in the repo, so they carry a
request cap only. Cloudflare dollar ceiling uses the 2A prereg's per-request figure (about $0.002 per request):
A at most about $0.86, B about $1.44, C about $2.88, smokes about $0.43 together. The Worker also enforces
`DAILY_BUDGET_USD`.

## Stop rules

Read every smoke row (narration plus appended cues) before the matching screen. Stop and report on malformed
output, quota or cap errors, missing evidence, premature disclosure, or a contradictory cue. One Ringer task
per smoke or screen, one attempt each, aborted attempts recorded. If a smoke shows a harness problem, stop and
ask Brandon; do not fix and relaunch on my own.

## Only if Live C misses the bar (Steps 2 and 3 of the plan, not authorized by this document)

Screen the one-statement rewordings (`3c-broadcast-result`, then `3c-community-result`) one at a time, adopting
and re-baselining before the next. The surface binding is screened separately as a world-consistency change.

## Not covered

Live effect of #667 in the full hosted game (an upstream 2C loop blocked that), a true historical replay,
whether the semantic model's turn-7 refusal was right, the turn-13 "remaining detention sites" guard, and
any whole-game 80% estimate.
