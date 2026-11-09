# 1A: phone is picked up, then examined as still on the floor

Reported transcript (Brandon, 2026-11-08): `pick up the phone` narrates
"She bends down to pick up Michelle's phone."; the next turn `examine the
phone` narrates "bends down to examine Michelle's phone, which lies on the
kitchen floor." The phone should be in Kristin's hands on turn 2.

Question: after turn 1, does the world model hold the phone as Held by Kristin
(capture landed), and what does turn 2's THINGS line say?

Arms: one. Script `pickup-then-examine` (variation
`bench/variations/1a-phone-pickup.json`), scene 1A, current package.
Smoke: 2 replicates. If either shows the bug, run 10 replicates, no pooling.
Read per replicate: turn 1 narration, `item_facts_before/after` for the phone,
turn 2 `prompt_user` THINGS line, turn 2 narration.
Decision: place stays "on the kitchen floor" after turn 1 -> capture/state
cause; place is Held by Kristin but turn 2 narration still says floor ->
narrator/prompt cause. No fix is chosen before this reading.

## Run log

- Smoke 1 (`bench/results/1a-phone-pickup-smoke`): invalid arm. The variation
  had `fixed_turns: 1` and no `item_facts`, so only turn 1 ran and no state was
  recorded. Both replicates narrated turn 1 identically, including "it's
  locked with a passcode. She tries to guess the passcode, but it doesn't work."
  That contradicts the authored fact that Kristin knows Michelle's passcode, so
  it is a second defect to track, not yet diagnosed.
- Smoke 2: variation now matches the hosted shape (`runtime: true`,
  `item_facts` single_call seeded from the package, `fixed_turns: 2`), out dir
  `bench/results/1a-phone-pickup-smoke2`.

## Finding and decision (2026-11-08)

Smoke 2 reproduced the miss in 1 of 2 replicates. Replicate 1's reply was
`{"phone": {"held_by": "Kristin", "place": "Michelle's kitchen", "owner": "Michelle"}}`.
The echo rule in `ItemFactsProvider.apply_item_facts` (commit `fa3c837d`,
`tests/test_held_by_echo.py`) kept the phone in the kitchen; the final state
still had it "on the kitchen floor", so turn 2's THINGS line said so. The
engine's take step ignores pickup commands by design (`moves_thing` answers
false for them), so only the narrator's reply moves the phone.

Decision (Brandon, option 1): widen the existing per-item Jev question to also
ask `picks_up_thing` in the same request; record the picked-up ids on
`TakingResult.pickups`; `ItemFactsProvider.pickup_ids` is set per turn by
capture; for a flagged thing held by the protagonist, `held_by` beats the place
echo. Unflagged echoes (the lit lamp) are unchanged. Not in scope: a reply that
omits the picked-up thing entirely.

Ringer task: `scripts/ringer/pickup-holds/manifest.json` on branch
`pickup-holds-over-echo`. Baseline suites were green (435 passed) before it.
After it lands: rerun `bench/variations/1a-phone-pickup.json`, 10 replicates,
and read turn-2 THINGS and narration for every one.
