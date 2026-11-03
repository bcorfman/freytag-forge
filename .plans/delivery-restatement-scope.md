# Scope: the delivery text saying what the narrator just said

Status: scoped 2026-11-02, nothing built. Asked by Brandon after the 1B and 1C probes ("scope it next").

## What was observed
In 1B (picnic) and 1C (pallets) the narrator writes the scene fact, then the engine's authored delivery text repeats it in nearly the
same words ("...shrink-wrapped by the loading doors. ... Pallets of bottled emergency water stand shrink-wrapped by the loading doors.").

## What the engine already does
On a turn where a reveal is delivered, the narrator prompt already says: "Right after your story, the game will add this: <text>.
Write only what leads up to it. Do not have Kristin find anything else." The narrator still restates. A stronger rule is the kind of
fix his memories say loses on a small model, so this scope does not propose one.

## Measured across every recorded bench row (188 result files, 462 delivered reveals found in the narration)
- Narrator already said 40% or more of the delivery text's content words: 79 of 462 (17%). 60% or more: 14.
- Two entries account for 59 of the 79: `k_sl_3c_d_r1` (30) and `k_sl_1b_a_r1` (29). In both the player's command already names the
  result ("Compare the number sequence with the transit token", "Read the reports of facilities surrendering"), so the narrator's
  lead-up overlaps the delivery because the ACTION is the reveal. That is not a defect to remove; it is how an action leads to its result.
- The fixable kind is a delivery sentence that restates the placement text or the name of a thing the player can already see. A scan of
  all 72 authored deliveries for sentences at least 60% covered by their reach entities' names and placement text finds exactly three:
  `k_sl_1a_g_r2` (the refrigerator photograph, 0.78), `k_sl_1b_f_r1` (the dog leash, 0.86), `k_sl_1c_e_r1` (the pallets, 0.67).
  Those are the repeats seen in the probes. 1A and 1B/1C authoring created them; the older scenes are not affected.

## Options (recommend only what the repo has proven)
1. **Authoring rule plus a deterministic audit check (recommended).** Source-level, subtractive, and it generalizes across stories
   (audits must). Rule for `docs/markdown-story-authoring/knowledge-and-disclosure.md`: a delivery sentence must add what the placement
   text, thing names and the player's own command have not said; never open with the placement text. Add an `audit_package` check
   `delivery_restates_scene` (the scan above, threshold 0.6, sentence of 4 or more content words, reach-entity names plus
   placement text of the entry's first scene) so a future scene cannot reintroduce it. Then edit the three sentences.
2. **Engine: do not show the narrator the delivery text.** Removes the restatement cause but loses the lead-up the narrator uses to
   avoid contradicting the delivery (and PRD allows the reveal turn to see it). Unproven; would need a billed A/B across scenes. Not recommended now.
3. **Engine: move or trim the appended text after generation.** Post-hoc text surgery on prose; his rule is never regex over prose. Rejected.
4. **Stronger prompt rule.** Rules lose on this narrator. Rejected.

## Proposed work (tests first, all through Ringer)
1. Acceptance tests (new file `tests/test_delivery_restatement.py`): the audit flags a synthetic package entry whose delivery sentence
   restates a placement text; does not flag a delivery whose overlap is only with the player's command words; does not flag the current
   package after the three edits; reports exactly the three ids on the current package before the edits (so the check is not vacuous).
2. Engine task: `storygame/audit.py` check plus a short subsection in the authoring doc (kept short; the doc is already near its word limit
   so use the existing progressive-disclosure layout).
3. Story task: rewrite the three sentences so each adds something new (for example the pallets: start at "The county label is on every
   bottle..."; the leash line moves to a different image or is cut; the refrigerator photograph line keeps only what is not in the placement text).
4. Verify with one candidate-only rerun per affected scene (1B, 1C; 1A only if it is probed again). Cost about 150 neurons each, only on Brandon's go.

## Not covered
Narrator pre-announcing a result because the command already contains it (3C d_r1 pattern) and the leftover where Brandon recites
older observational statements in other scenes (a separate whole-game sweep of `voiceable: false`, proposed in the 1C result).
