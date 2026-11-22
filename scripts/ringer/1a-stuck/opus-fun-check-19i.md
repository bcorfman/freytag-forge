CHANGES NEEDED

1. **`.gitignore` (not in the diff) / `factory/state/`**: The session's git status lists `?? factory/state/`, so the lessons directory is untracked but not ignored. Any broad `git add` in the deliver path would put `fun_lessons.jsonl` into a PR, which breaks design item 2 in practice. Add an ignore entry. Whether deliver ever stages broadly is unverified.
2. **`factory/lessons.py:~50` (`_precedent`)**: The planner prompt says to write `Precedent: none; list checks and the reason it does not apply`. For that case the code stores everything up to the first period, so reason prose goes into the record (breaks item 4). It also splits the common "none" key into one-off keys that never reach the threshold. It doesn't cut at a newline either. Fix: when the value starts with `none`, store `"none"`, and cut at the first `.`, `;` or newline.
3. **`factory/line.py:98-106` (`_record_fun_lessons`)**: Only `record_lessons` is inside the try. `ticket.payload` and `self.queue.save(ticket)` sit outside it, so a writer-side error can still stop the line. Two cases are unverified:
   - If `record_pass` or `record_failure` return `None`, the line crashes.
   - If they return a stale copy rather than the stored ticket, `save` overwrites the status or set-aside fields they just wrote.
   The `except Exception: return` also logs nothing, so lost lessons are invisible.
4. **`factory/stations/fix_plan.py:675-684` and `lessons.py` `_read_records`/`render_lessons`**: Records are only checked for key presence, not types. One bad line (say a list `ticket_id` or `fix_kind`) raises `TypeError` (unhashable) inside `render_lessons`. That error reaches `build_evidence` with no guard and fails the fix-plan station. Either check the types when reading or wrap the render call.
5. **`lessons.py` `_candidate_records` (`enumerate(history, start=1)`)**: `fun_round` is the list index, not a stored round number. If `fun_history` is reset or trimmed when a set-aside ticket returns after the Opus refresh, the new entries reuse old ids like `T:1:blocked`. The dedupe check then drops them without a word. Unverified whether history is append-only. The separate `payload["fun_rounds"]` counter suggests the index and the real round can differ.
6. **`lessons.py:~54-56` (`_plan_values`) / `_failed_checks`**: Three keys are assumed: `plan["kind"]`, `entry["plan"]` and `entry["failed_checks"]` (all unverified).
   - If a check key is wrong, every blocked record gets an empty `failed_checks` and nothing ever renders, with no error.
   - If `kind` is wrong, every plan becomes `"unknown"`. Unrelated plans from different tickets and scenes then merge under one key, which can pass the threshold and render a false Avoid line.
   Don't record or render `unknown`.
7. **`line.py:~145` (`open_followups`)**: Unverified. If follow-up tickets copy the parent's payload, including `fun_history`, each child writes the parent's blocks again under its own id. That creates a fake second ticket toward the threshold. `fun_lessons_recorded` doesn't help, because the ids carry the child's ticket id.
8. **`line.py:309` (exhaustion)**: Unverified whether the round that just failed has been added to `fun_history` before `record_lessons` runs. If it's added later, the final block is never recorded.
9. **`line.py:143-144` (delivered)**: The win is gated correctly on a live-playtest pass plus `merge_to_main`. Still unverified:
   - whether any other caller of `record_pass` exists (e.g. a manual approval), which would skip lessons;
   - whether `payload["plan"]` at that point is still the plan that passed fun review.
10. **`lessons.py` `_store_path` / `fix_plan.py` path logic**: The writer and the reader each work out the path separately from their own file's location. If the line and the fix-plan station run in different checkouts or worktrees, they use different files (unverified). A station's `payload_updates` could also redirect writes through `fun_lessons_path`. Put the path in one shared function.
11. **`line.py:322` (live-playtest failure)**: This passes `"fun_exhausted"` for a playtest failure. The result is correct (blocked records only), but the label is misleading. Live-playtest failures that go through the generic `else` branch (no turns) record nothing.
12. **`lessons.py` `render_lessons`, Mixed rule**: A proven win plus an unproven block renders as Works. I accept that; my design text was ambiguous. Proven block plus proven win → Mixed, and proven block plus unproven win → Avoid, both as designed.
13. **`lessons.py` `render_lessons`, cap loop**: Two cosmetic issues:
   - The first loop tests against the `omitted+1` marker, so it can drop one extra line when the count gains a digit (e.g. 9 to 10).
   - If every line is dropped, the header plus marker can exceed a very small cap.
   Neither matters at 4,000. Sort order (Avoid, then Works, then Mixed; within each, most scenes first, then newest) and the "N more lessons not shown" line are correct.
14. **`lessons.py` render lines**: A `"` inside a precedent breaks the `via "…"` quoting. Minor.
15. **My design, item 9**: My total was wrong. 20,000 + 4,000 is about 24k of evidence at most, not 21k.
16. **Unverified**:
   - All tests from item 11 (none shown).
   - Whether the planner prompt actually serializes `evidence["fun_lessons"]`.
   - Whether the curated file's 20,000-character test is unchanged.
   
   The planner sentence matches item 10 word for word. The record fields match item 4 exactly, apart from finding 2.
