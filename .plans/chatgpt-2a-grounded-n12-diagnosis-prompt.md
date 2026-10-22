# ChatGPT prompt: diagnose why the grounded 2A arm earns the 2B reveal less often than control (N=12 screen)

Paste everything below the line into the ChatGPT Desktop thread used for the 2A
door work. It has the repository. Bring the answer back to Claude Code, which
applies any change through a Ringer task. Claude Code believes part of this is
a mechanics question (when the 2B reveal becomes eligible and matches), not only
a writing one; please say which parts are which.

---

The slotted-face edit (plot.md `setting_facts` lines 362-365 replaced by one
line, "The cooling-service archive panel has a slotted face.") was screened once
at N=12 per arm, live, with a blinded review. Artifacts:
`bench/results/stage7-door-grounded-n12-slotted/` (`results.json`,
`verdicts/`, `review-summary.json`, `prompts/`). Preregistration:
`.plans/astra-2a-grounded-route-prereg.md`. The grounded arm does NOT win.

## Result (12 rows per arm)

| Measure | Control | Grounded |
|---|---|---|
| earned_by_command_2 (mechanical, from the saved reveal ledger) | 6 | 2 |
| invented_access_object | 12 | 5 |
| reached_archive_without_new_credential | 7 | 8 |
| declared_panel_used | 9 | 3 |
| contradictory_delivery | 4 | 3 |
| premature_disclosure | 0 | 0 |

Keep rule needs grounded earned >= 10, archive reached >= 10, invented <= 2, and
earned >= control + 3. Invention fell sharply (the thing the edit targeted);
earned did not.

## Evidence about earned (per row, from `continuation.turns`)

Command 1 is `unearned` with nothing eligible in all 24 rows. All reveal
activity is on command 2. Per row (command 2: eligible beats / matched beat):

- Control earned (6): reps 2, 3, 7, 8, 10, 11, all `k_sl_2b_a_r1` eligible AND
  matched. Control rows eligible for `a_r1`/`a_r2` but not matched: reps 4, 5,
  6, 9, 12. Control rep 1 was eligible only for `b_r1..b_r3`, not matched.
- Grounded earned (2): reps 1 and 10, both `k_sl_2b_b_r1` (the "development
  records" beat) eligible and matched.
- Grounded rep 11: `b_r1` eligible AND matched but not earned (status
  `unearned`). Grounded reps 4, 5, 7, 9: command 2 had NOTHING eligible at all
  (`eligible == []`). Grounded reps 2, 3: `b_r1..b_r3` eligible, nothing matched.
  Grounded reps 6, 8, 12: `a_r1`/`a_r2` eligible, nothing matched.
- Grounded players mostly skipped the panel and went straight to the archive
  terminals ("Search the archive terminals for Michelle's selection file...",
  "Examine the terminals and search Michelle's selection file."). Only 3 of 12
  used the panel. Control players mostly opened a "hidden/access panel".
- Evidence phrases for `k_sl_2b_a_r1` are verbs (search/read/open/check/review)
  plus objects ("michelle's selection file", "selection file", ...). For
  `b_r1` the objects are "development record(s)", "Brandon's record(s)", etc.
  (the full evidence table is in `results.json` -> `continuation.turns[*].evidence`).

Differences between the arms by design: grounded uses the new route-neutral
bridge and the revised package (`data/stories/continuity-initiative/`); control
uses `bench/frozen/continuity-pre-2a-panel/` with the old bridge. The screen is a
replay of a recorded 2A prompt, with the THINGS panel line patched in as a
best-case assumption (`things_assumption`); the hosted match call was NOT run.

## What I need diagnosed

1. **Why does grounded make `a_r1` eligible less often at command 2, or make
   command 2 eligible for nothing at all?** Read the eligibility / entry rules for
   the 2B beats (the storylet and transition code and `plot.md` for 2B). Is
   eligibility driven by a fact the old bridge or the old panel path set, and the
   new route-neutral bridge no longer sets it? Rows with `eligible == []` on
   command 2 (reps 4, 5, 7, 9) are the clearest cases.
2. **Is "earned" even a fair comparison?** Control players phrased the panel
   command and then searched selection files; grounded players searched directly.
   Does the evidence-phrase table match "Search the terminals for Michelle's
   selection file" (rep 5, 9) as it should? Several grounded searches look like
   `a_r1` matches by wording but were not eligible or not matched. Say whether
   the matcher, the eligibility gate, or the player wording is the cause, row by
   row for reps 2-9, 11.
3. **Rep 11:** `b_r1` eligible and matched but `unearned`. What gates `earned`
   after a match, and why did it not fire?
4. **Writing vs mechanics.** For each cause you find, say whether it is (a)
   authored story text (plot.md bridge, setting_facts, 2B entry), (b) engine
   mechanics (do not propose engine changes silently; flag them for me), or (c)
   the screen design (replay + best-case THINGS) rather than the story.

## Constraints (same as the earlier rounds)

Read `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`,
`docs/scene-fixing-guide.md` and `docs/contributor-guide.md`. Facts are the sole
mutable truth; shared runtime stays story-agnostic; subtract before adding;
narrator rules last; no regex or keyword gates; 12th-grade, one idea per
sentence for any narrator text. Recommend only techniques already proven in the
plan's W decisions or earlier scene fixes, and name the precedent; if you
invent, say so. Do not propose reading more than the N=12 rows (the prereg says
N is not extended after seeing results).

## Output

A short diagnosis per question above, ranked by how many of the 24 rows each
explains, then exact old/new text for the smallest fix that is authored story
material, or a clearly labelled engine question if the cause is mechanics. No
file changes; I apply them through Ringer.
