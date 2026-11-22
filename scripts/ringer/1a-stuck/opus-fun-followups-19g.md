Reasoning:
- I couldn't read the code (the search tool was denied), so I've marked where I assumed a payload key name. In those places, use whatever key the station already writes.
- A fun pass only shows that the reviewer liked a fix. Players getting unstuck is the real test, so a winning lesson waits for `record_pass` (live playtest passed). A blocked lesson is recorded when its ticket ends, either by `record_pass` or by the fun ladder running out.
- One ticket proves nothing across the game. A lesson reaches the planner only after it shows up in at least 2 tickets in at least 2 different scenes. Before that it is stored but not shown.
- Lessons are written as fix kind + precedent technique + check key, never as the plan text. That way the planner learns the pattern and has nothing to copy word for word. It also keeps story and player text out.
- Runtime lessons go in untracked `factory/state/`, not in the curated repo file. They never ride in a PR, so the hands-off merge path doesn't change and the curated file's 20k test still holds.
- When the reviewer blocks the same ticket twice, the reviewer and planner disagree. Another 6-hour retry spends money without changing anything, so the ticket is parked for the owner. Whether to merge a blocked fix or drop the scene is a merge-policy question, and the owner decides policy.
- A notifier failure must never stop the line. Sends are idempotent through a payload key and retried a fixed number of times.

## FINAL

### Follow-up 1: record what a fun block taught

1. **New module `factory/lessons.py`.** It is plain code with no model calls.
   - `record_lessons(ticket, outcome)` is called from `record_pass` (outcome `"delivered"`) and from `record_failure` when the fun ladder is exhausted (outcome `"fun_exhausted"`). It writes nothing if `fun_history` is empty.
   - `render_lessons(path, cap=4000) -> str` builds the planner's text.
2. **Store.** Append one record per line to `factory/state/fun_lessons.jsonl`. It is untracked, never committed and never part of a PR. This file is the full record and is never trimmed.
3. **When records are written.**
   - Each `fun_history` entry gets one `"blocked"` record, at either ticket end.
   - The final plan gets one `"won_after_block"` record, only when the outcome is `"delivered"` (live playtest passed).
   - A fun pass whose live playtest fails writes the blocked records only.
4. **Record fields.**
   - Fields: `lesson_id`, `ticket_id`, `scene_id`, `outcome` ∈ {`blocked`, `won_after_block`}, `fix_kind`, `precedent`, `failed_checks` (list of check keys, empty for a win), `fun_round` (1-based), `recorded_at` (ISO).
   - `fix_kind` is the plan's typed kind, e.g. `claim-edit` (assumed key `plan["kind"]`).
   - `precedent` is the text after `"Precedent: "` in the plan's `reason`, up to the first period, cut to 80 characters, or `"none"`.
   - There are no plan, advice, reason, story or player text fields.
5. **No duplicates.**
   - `lesson_id = f"{ticket_id}:{fun_round}:{outcome}"`. The writer skips an id that is already in the file.
   - The payload key `fun_lessons_recorded: [lesson_id, ...]` is also set, so a returning ticket can never write twice.
6. **Grouping.**
   - A blocked lesson is keyed by `(fix_kind, precedent, check)`, one per failed check.
   - A won lesson is keyed by `(fix_kind, precedent)`.
   - For each key, count distinct `ticket_id` and distinct `scene_id`.
7. **"Proven" threshold.**
   - A key is proven when it has at least 2 distinct tickets and at least 2 distinct scenes.
   - Keys with fewer stay in the jsonl and are not rendered. (Within a single ticket, the planner already gets `fun_history`.)
   - Conflicts: if a block key's check also fails for the same `(fix_kind, precedent)` that has a proven win, render it as mixed with both counts, never as a rule.
8. **Rendered form.** A new evidence section `FUN REVIEW LESSONS (machine-recorded, proven across ≥2 scenes)`, one line per key:
   - `- Avoid: {fix_kind} via "{precedent}" tends to fail {check} ({n_tickets} tickets, {n_scenes} scenes).`
   - `- Works after a block: {fix_kind} via "{precedent}" passed fun review and live playtest ({n_tickets} tickets, {n_scenes} scenes).`
   - `- Mixed: {fix_kind} via "{precedent}": {wins} wins, {blocks} blocks on {check}.`
9. **Cap and eviction.**
   - The cap is 4,000 characters for the rendered section only, separate from the curated file's 20,000 cap. That puts the evidence at about 21k at most.
   - Sort order: Avoid lines first, then Works, then Mixed. Within each group, sort by n_scenes descending, then by newest `recorded_at`.
   - Drop lines from the end until the section fits, then add `- ({k} more lessons not shown)`.
10. **Planner prompt.** Add one sentence: "Fun review lessons describe patterns, not fixes; never repeat an Avoid pattern for a scene unless your reason names the lesson and why this scene differs."
11. **Tests.**
    - Writing is idempotent across a set-aside return.
    - No winning record is written without `record_pass`.
    - Records carry no text fields beyond the ones listed.
    - The 2-ticket/2-scene threshold works.
    - The section stays at or under 4,000 characters, and eviction order is correct.
    - The curated file's 20,000-character test is unchanged.

### Follow-up 2: escalation to the owner

1. **Trigger.** In the line, at the point where the second fun block runs the ladder past OPUS_REFRESH into `record_failure`, call `self._escalate_fun_impasse(ticket)` after `record_lessons`.
2. **Park the ticket.**
   - `record_failure` behaves as before: status `SET_ASIDE`, `return_after` +6h, so the existing tests still pass.
   - It also sets the payload key `owner_wait = {"reason": "fun_review_blocked_twice", "since": iso, "reply": None}`.
   - The re-queue step skips any ticket where `owner_wait` is set and `owner_wait["reply"] is None`, so the ticket stays parked.
   - Add a test for the skip.
3. **Send exactly once.**
   - Send only if the payload has no `owner_notice["sent_at"]`.
   - On success, set `owner_notice = {"sent_at": iso, "attempts": n}`.
   - On an exception, log it, set `owner_notice = {"sent_at": None, "attempts": n, "error": str(e)[:200]}` and carry on. The line never raises.
   - At the start of each line pass, retry tickets that have `owner_wait` set and no `sent_at`, while `attempts < 3`.
4. **Wiring.**
   - Signature: `FactoryLine(queue, state, handlers, provider_for, check_breakers, notifier: Notifier | None = None)`.
   - When `notifier is None`, `owner_wait` is still recorded and `owner_notice` is not set, so existing construction keeps working.
   - `factory/__main__.py` passes the same notifier it already builds for the breakers.
5. **Subject.** `factory: scene {scene_id} needs your call (fun review blocked twice, {ticket_id})`
6. **Body template.** Each `{...}` value is cut to 160 characters.
   - `{stuck_summary}` is the ticket's existing description of what was stuck (assumed key). If it is missing, use `"see ticket"`.
   - Each plan line uses `{fix_kind}` and the plan's `reason` without its "Precedent: " prefix.
   ```
   Scene {scene_id}, ticket {ticket_id}.
   Stuck: {stuck_summary}
   Fix 1 (blocked): {fix_kind_1}: {reason_1}
     Failed: {failed_checks_1}. Reviewer: {reasons_1}
   Fix 2 (blocked): {fix_kind_2}: {reason_2}
     Failed: {failed_checks_2}. Reviewer: {reasons_2}
   Last advice: {fun_advice_2}
   Nothing was merged. The ticket is parked and will not retry until you answer.
   You may: (1) merge fix {1|2} anyway, (2) let it retry with a note for the planner, (3) drop this scene's ticket.
   ```
7. **State an owner reply would need** (no reply channel designed here).
   - `owner_wait["reply"]` ∈ {`"merge_fix_1"`, `"merge_fix_2"`, `"retry"`, `"drop"`}, plus an optional `owner_wait["note"]`.
   - `merge_fix_N` sends `fun_history[N-1].plan` to station 9 with `owner_approved: true`.
   - `retry` clears the fun rounds for the ticket and gives the note to the planner.
   - `drop` closes the ticket.
8. **Tests.**
   - The notice is sent once across a set-aside return.
   - A notifier exception doesn't stop the line, and the retry stops at 3 attempts.
   - `notifier=None` sends nothing and still parks the ticket.
   - The body has both plan lines and the last advice.

NOT NOW:
- Promoting proven lessons into the curated `stuck_turns.md`. That stays a hand step for the owner, done in a normal PR.
- Expiring lessons on age, or after a later stuck regression in the same scene.
- A "resolved" follow-up message.
- The reply channel itself.
- Lessons from fun passes that had no block first.
- Using a model to word the lessons in plainer language.
