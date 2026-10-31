# T9h faithful-path prose re-sample (preregistration)

Status: FROZEN before any billed call of this re-sample (2026-10-30). Brandon's authorisation: "yes" (2026-10-30), to
re-sampling the opening and pre-find states through the repaired harness. This is a **new registration**. It does not
reopen frozen stage 2 (still FAIL, artifacts byte-pinned) and does not authorise stage 3.

## What and why

The diagnostic arm screen (`t9h-stage2-diagnostic-prereg.md`) sampled only the find state. Stage 2's P1a failure was in
the opening and pre-find states, so those must be re-sampled before anyone says the bench prose is sound. The repaired
`hidden_bench_prose_probe.py` is used unchanged: HEAD package (P0) versus the working-tree package (P1), three states
(opening, prefind, find), 10 samples each = **60 calls**, through the world-aware request path with no injected text.
P0 is now the real request the HEAD package produces, a diagnostic control that is not gated.

## Budget and rules

Ceiling 60 calls and $0.06 behind `local_worker.mjs --max-usd 0.06`. The probe's own estimate counts input tokens only
and was about 8 to 10 times too low in both earlier billed runs; the planning estimate is about $0.04 (stage 2 spent
$0.0388). Billed once, no rerun after a partial result, no replacement samples, stop on 429, 401/403, 5xx or the cap.
Fresh output directory `bench/results/environment-narration/t9h-resample/`.

## Labelling and gates

Claude labels blind from sheets that hide arm and payload, the labels hash frozen before the join. Opening and pre-find
rows are read from the raw sheet. Find rows are read from the **composed view** (narrator text plus the engine-appended
delivery, shown separately), which is a post hoc inferred composition and not an accepted game turn. The probe's seven
labels are used with these rubrics:

- `names_clue_object`: the text names the transit token, the number sequence or the photograph.
- `describes_photograph_content`: the text says what the photograph shows or its details.
- `states_route_or_identity`: the text reveals the transport route, the photographed man's face or who he is.
  Naming Brandon is recorded in the notes, not here.
- `claims_nothing_under_bench`: **true only when the text says the space beneath the bench is empty or holds nothing.**
  "No obvious clues", "no visible signs" or an unfinished inspection does not count.
- `moves_fixed_bench`: true when Kristin lifts, tries to lift, or moves the bench or seat (attempts count; strict).
- `conveys_all_three_objects_and_keeping`: the complete find text (narrator plus appended delivery) shows all three
  objects and Kristin keeping them.
- `invents_fourth_object`: any object beyond the three declared clues appears.

Gates are the probe's own `report()` arithmetic, unchanged: **P1a** zero of the five prohibited labels in the 20 P1
opening and pre-find samples; **P1b** at least 9 of 10 P1 find samples convey all three and keeping without
route/identity; **P1c** zero invented fourth objects in the 30 P1 samples. P0 is reported, not gated.

A pass here is evidence only that, under the faithful request path, these states did not show the registered defects in
60 samples. It is not a stage pass, proves no rate, and does not change the recorded stage 2 FAIL. Premature Brandon
naming and unsolicited Brandon speech, which the probe has no label for, are counted by hand in the report notes.
