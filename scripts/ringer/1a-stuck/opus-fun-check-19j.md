**CHANGES NEEDED**

1. **`factory/line.py:488-491`: failed notices are only retried when `run` starts.** `_retry_owner_notifications` runs only at `step_number == 0`. In a long run that sleeps until the next wake and then keeps going, a notice that failed once is not retried until the process restarts. The ticket stays parked and the owner hears nothing. Item 3 meant a retry on every pass of the line. The retry should run on every loop iteration, or at least after every sleep. The 3-attempt cap already limits the cost. The tests only pass because each one calls `run(max_steps=1)` again. Unverified: whether `__main__` calls `run` only once per process, which would make this a real gap.

2. **`factory/tickets.py:284-290`: on the worker's choice to set `owner_wait` in `record_failure`, `record_failure` guesses the trigger instead of being told.** It decides from "the station is FUN_REVIEW and `fun_history` has at least 2 entries". The line is what knows that the second fun block ran out the ladder (item 1). If a ticket ever reaches its last rung at FUN_REVIEW with 2 or more history entries for another reason, it gets parked. Examples are a provider or timeout failure, or a later item-7 `retry` that resets `fun_rounds` but keeps `fun_history`. In that case it goes through the generic path, which never calls `_escalate_fun_impasse`. So it gets no notice until the next start-of-run retry. That retry then sends "blocked twice" for a ticket that did not end that way.
   - Narrowing the trigger is right: setting `owner_wait` on every set-aside would be wrong.
   - The fix: the line passes an explicit argument, such as `record_failure(..., owner_wait_reason="fun_review_blocked_twice")`, only from the fun-exhausted branch.

3. **`factory/line.py:432-433`: unverified that the second block always reaches set-aside.** If the second fun block can happen while the ticket is below OPUS_REFRESH, `record_failure` moves it up one rung and re-queues it. In that case:
   - no `owner_wait` is set, and no notice is sent;
   - but the lessons are still recorded as `fun_exhausted`.
   
   That would be a ticket that did end after two fun blocks with no owner notice. I can't see the branch condition, or whether the line forces the rung to OPUS_REFRESH first. Every test starts at `LadderRung.OPUS_REFRESH`. A test is needed with a second block at a lower rung.

4. **`factory/line.py:208-213`: the retry pass doesn't check `reply` or `reason`.** Any `owner_wait` dict with no `sent_at` gets a notice, even after the owner has answered or when the reason is something else. This is minor today, but it matters once item 7 is built.

5. **`factory/line.py:177-190`: the notice is sent, then saved.** A crash between the two lines sends it again on restart. Sending at least once is acceptable for a file notifier, but it is not exactly once. Restarts are otherwise sound: the send state lives only in the payload, and the save/load test confirms it is kept.

6. **`factory/line.py:136`: `reasons` that isn't a string is shown as empty.** It isn't joined like `failed_checks`. Unverified: whether the real fun-review payload stores `reasons` as a string. The test uses a string.

7. **`factory/line.py:190` and `:432`: unverified whether `_record_fun_lessons` saves its own copy of the ticket.** If it does, the later `self.queue.save(failed_ticket)` overwrites it.

8. **Places that can move a ticket out of SET_ASIDE that I can't see: unverified.** Examples are CLI requeue or retry commands, `open_followups`, preflight resets, and `_all_passed`. The three paths shown all skip a parked ticket before checking its status: `_next_ready` (`line.py:81-83`), `_next_wake` (`line.py:469-471`) and `TicketQueue.next_ready` (`tickets.py:243-245`).

**What matches the design:**
- Item 1: the call comes after the lessons are recorded.
- Item 2: `SET_ASIDE` with `return_after` +6h is unchanged.
- Item 3: a failure is logged, the error is cut to 200 characters, the line carries on, and attempts stop at 3, which the test confirms.
- Item 4: `notifier=None` still parks the ticket and writes no `owner_notice`. Unverified: that `__main__` passes the same notifier instance the breakers use. The test only checks the class name.
- Items 5 and 6: the subject is exact and every body value is cut to 160 characters. Rendering `{1|2}` as "1 or 2" and printing "none" for empty failed checks are both fine.
- Item 7: correctly not built.
- Item 8: all four tests are present, plus the test for the skip.
