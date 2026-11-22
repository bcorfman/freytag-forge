CHANGES NEEDED

My tool calls to open the files were refused, so I judged from the diff alone. Line numbers are approximate, worked out from the hunk headers. Items marked *unverified* depend on code that isn't in the diff.

1. **`factory/line.py` ~265–276, the final fun block may never reach the owner and may repeat.** On the second block, the code sets `ladder_rung = OPUS_REFRESH` and calls `record_failure(max_attempts=1)`. It never increments `fun_rounds`. If `record_failure` sets the ticket aside and later re-queues it, or the Opus refresh rung re-runs anything, the loop goes like this:
   - The fun review reuses the saved block, so it costs nothing.
   - `next_fun_round` is still 2, so the ticket fails again.
   - Each pass adds a duplicate entry to `fun_history`.

   My section (d) said "don't merge; send to the owner with both plans, both reasons, and the last fun_advice". Nothing here explicitly parks the ticket for the owner. `result.output` carries only the last reasons. Store `fun_rounds = 2` and send the ticket to an explicit owner/parked state, not a ladder rung. *Whether `record_failure` and `OPUS_REFRESH` actually re-queue is unverified.*

2. **`factory/line.py` ~194, a probe reject after a fun round drops the fun advice.** A probe reject pops `fun_feedback`. The planner then sees only the probe verdict and can drift back to the plain "not broken" fix. The fun review will block that again, which wastes the second and last round. When `fun_history` is non-empty, the probe-retry feedback should also carry the last fun_advice. Without it, the "re-check through probe" path can't keep both goals.

3. **`factory/stations/wiring.py` ~366–395, a fun retry only changes the planner arguments.** If the tree reset or revert of the blocked fix happens only for `probe_retry` elsewhere in wiring, a fun-retry plan would be applied on top of the blocked fix. *Unverified.* Confirm that `fun_retry` gets the same tree handling as `probe_retry`.

4. **`factory/stations/fun_review.py` ~73, the blank line is gone.** The `continuity_between_scenes` bullet used to end `?\n\n`. It now ends `?\n`, and the new bullet ends `\n`. The blank line before "Reply with ONE JSON object" should move to the end of the `delights_the_player` bullet. All other bullet, template and rule text matches my design word for word.

5. **`factory/stations/planner.py` ~35, a real line break splits sentence A.** `PLANNER_BRIEF` is a triple-quoted string, so "show a⏎character, or sharpen the stakes." now contains a newline mid-sentence. Elsewhere the file uses `\` continuations. Add one here. Sentence A otherwise matches, and B and C match exactly and sit in the right places.

6. **`factory/stations/fun_review.py` `_evaluate_review` / `line.py` feedback lines, an empty failed-checks list.** A block where every check is true (the "only moves words around" rule) produces an empty `Failed checks:` line. Write something like "Failed checks: none (blocked by the rule against only moving words)" so the planner knows why.

7. **`factory/stations/fun_review.py` `_saved_result`, an old record can burn a round.** Saved records aren't checked against `brief_hash` (I saw no check in the diff). An old seven-key record with the same diff hash would fail closed, because the missing `delights_the_player` counts as false. That is the right direction, but it uses up a fun round with empty advice. Re-review when `brief_hash` differs.

8. **Possible leak through `reasons`, *unverified*.** The planner gets `normalized_reasons`, which comes from `_review_reason(reasons, checks)`. If that helper prefixes the failing check's question text, the check questions leak to the planner. If it only adds the key name, it's fine. Check it.

9. **Wording or limits that aren't from my design.** None of these changes what the review judges:
   - `FUN_CHECK_LABEL` in `wiring.py` is glue text. It fits sentence C ("story editor"), so it's acceptable.
   - `_claim_evidence` caps the data at 8 groups × 12 phrases. It also silently drops the claim when `available_in_scenes` excludes the scene, which leaves the no-visible-text clause unanswerable. Log that case or include the claim anyway.
   - The evidence comes from the fixed tree, so it shows the new phrase alongside the existing ones. That's fine.

10. **Not built from section (d), and possibly out of scope for this round:**
    - The precedent record (the advice plus the passing fix as a proven fun technique, and the blocked fix as lost) is not in the diff.
    - The owner spot-check log is partly covered. `review.json` keeps the reasons from the latest review, but each new review of the ticket overwrites it. Only `fun_history` keeps the blocks.

**What matches section (d):**
- The planner gets the blocked plan, the failed check keys, the reasons and the fun_advice, and not the brief or the questions (subject to item 8).
- `fun_history` records each block.
- A block goes back through wiring, then the lint and the probe, before the next fun review.
- Fun rounds are counted separately from probe rounds.
- The Claim evidence section appears only for `edit_claim_evidence`.
- A missing check counts as a failure, because `failed_checks` uses `is not True` over `FUN_REVIEW_CHECKS`.
