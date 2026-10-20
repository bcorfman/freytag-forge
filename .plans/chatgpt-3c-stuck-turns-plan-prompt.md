# ChatGPT prompt: write a plan to fix Scene 3C's stuck turns

Paste everything below the line into ChatGPT Desktop. It has the project files
open, so it reads them itself. Bring the plan back to Claude Code, which
applies it through Ringer tasks and probes it.

---

## ROUND 5 (2026-10-20): the carried-state screen ran; 8/12 and 9/12 earned; the loss is D2 recognition

Read this section first, then Round 4 and Round 3 below it (still correct for the steps they cover). Update
`.plans/chatgpt-3c-stuck-turns-plan.md` in place under the Round 3 rules: edit, do not regenerate; record each outcome
inside its own Step section; mark "corrected" or "new"; revise Status, "Resume here" and "Not verified". The goal is
unchanged: the shortest chain of measured steps to a quality free-text playthrough that passes the 80% earned bar (at
least 10/12). Drop anything that does not shorten it. Nothing is adopted into `data/`. My own status blocks are already in
the plan (search "RESULT (2026-10-20)", "DIAGNOSIS (2026-10-20)", "STATUS (2026-10-20, latest)"); correct them if the
rows disagree.

| What | Where | Outcome |
| --- | --- | --- |
| Carried-state harness | `three_c_probe.py --start carried`, arm `families`; prereg `.plans/astra-3c-carried-prereg.md` | Each row replays the scripted 1A-3B canon journey on the arm's own package (the checkpoint is not loaded: arm packages differ in content hash, and no fingerprint is patched), crosses into 3C through the real transition, then the raw blind player plays from turn 1. Built by Ringer; hermetic tests and a dry run pass. 3B transcript is authored text and one history is shared by all rows. `relay_open` is committed at 3C entry in the carried state. |
| Smoke 1 | `bench/results/stage7-3c-carried-smoke/` | INVALID. Rows recorded no reveals. Root cause: the engine trims `turn_records` to 24 and reuses ids (`storygame/runtime/engine.py:918-928`), so the probe's id diff dropped new records. Fixed in the probe; regression test added. |
| Smoke 2 | `bench/results/stage7-3c-carried-smoke2/` | Clean. Both rows earned; 23 Cloudflare and 23 player requests; 0 rejections. n=1, not a rate. |
| Screen | `bench/results/stage7-3c-carried-n12/`, arms `pump` (baseline: entry + custody + pump sentence) vs `families` (pump + 3 D-R2 phrases `broadcast a message/a response/an update to the families`), 12 rows each, semantic ON, deadline 14, 20 attempts | 302 of 960 Cloudflare and 302 of 480 player requests. Earned: pump 8/12, families 9/12. Both MISS the 10/12 bar; a 1-row gap is not distinguishable. All 24 rows: A on first attempt, B, C1, C2, both C by turn 10, 0 rejections, 0 clarifications. D1 12 vs 11, D2 9 vs 11, E 8 vs 9. Deadline endings 4 vs 3. Case re-takes 2 vs 0. No `relay open` rejection appeared. |
| Checker | `check_three_c_probe.py` | Failed the run with "carried row must not record scripted 3C reveals"; the rule was wrong (it should inspect only `scripted_prefix`). Fixed; the real n12 and smoke2 artifacts now pass. |
| Diagnosis | `.plans/astra-3c-carried-diagnosis.md` | Per-turn audit of every non-earned row and every earned row with D2 or E at turn 12 or later. |

### What the diagnosis found (14 delayed rows)

- **7 matcher misses** on clear family messages (pump 4, families 3). D1 and D2 were both eligible and the real unique
  selector returned None. Recorded: `send the families a message confirming the captives are alive`, `broadcast a message
  to the families of the missing` (pump rows 7 and 11 twice), `send the families the names and locations of the rescued
  prisoners`, `broadcast the captives' names and locations to their families`, `broadcast the prisoner records and names
  to the families of the missing`. The three families-arm phrases did NOT cover the send shapes or the "... to their/the
  families of the missing" shapes; that is why families gained only 1 row.
- 1 row never attempted the families (a loop back for Br), 1 wandered to a Site 3 / drainage-pump detour, 1 row did D2
  before D1, 1 took a van, 1 ran out of turns after a correct sequence (pump 12, D1 at 12 and D2 at 14).
- 2 rows lost one turn each to a compound E command, `Open the recovered document and trace Charles's signal` (E1 and E2
  both match, selector refuses the tie). Plain `Open the recovered document` is E1.
- Earned endings at turn 14 (D2 at 12, E at 14): 5 rows, all with `deadline_event_ids` empty, so no fallback supplied them.
- Deadline 16 would plausibly change only 3 rows (D2 at turn 14: families 2 and 5, pump 12). No turn 15 or 16 is recorded, so
  that is inference.
- Ceiling if every matcher miss converted: pump about 11/12, families about 12/12. Not a prediction.

### Precedent check I already did (verify it)

PRD ("Missed phrasings get author-reviewed aliases, never similarity scoring") and `docs/player-input-guide.md` ("Do not widen
the matcher ... A phrasing the matcher misses gets an author-reviewed alias") sanction an alias; #667 is the only measured win of
that shape. `docs/scene-fixing-guide.md` has no other recognition-miss technique. W1-W14 (retrieved from git at `bb8f7271`)
contain nothing on `action_evidence`, the matcher, handoffs or verbs. The tension: your settled list bars "Widening
`action_evidence` just to make a recorded command match". My reading is that the bar targets a fix justified only by recorded
sentences; an alias for the in-world action "inform the families" with recipient-qualified phrases, negative controls and a fresh
screen is allowed. Rule on that reading.

### Questions for the updated plan (shortest path to a quality playthrough)

1. Give the exact D-R2 alias set (old and new `action_evidence` text in `knowledge.yaml:2651-2653`) covering the observed
   `send`/`broadcast`/`tell` + families forms without bare `broadcast` or bare `send`, and without matching `Broadcast music to
   the families.`, `Listen for any response from the families.`, `Send the families into danger.` or the report-plus-message tie.
   State what it could break (D1 overlap on `Broadcast the reports to the families`). Say whether you prefer one broader
   recipient-qualified phrase family over per-sentence additions, and why that is not fitting to the 24 transcripts.
2. Is the compound-E tie worth a fix or accepted (2 rows, one turn each)? If a fix, the exact smallest one and its precedent.
3. The remaining non-matcher losses (Br loop, Site 3 detour, van, D2 before D1) are five rows. Is there any cheap lever from a
   proven technique, or accept them? Be explicit that the 80% bar allows 2 failures in 12.
4. Is deadline 16 now worth screening, or only after the alias? Say what evidence would decide it.
5. Order the remaining work as one measured step each with win condition, files and cost. The next billed run is a fresh carried
   n=12 of `pump` vs the alias arm (cap 960 Cloudflare / 480 player, about 20 minutes for 24 rows; the last one used 302/302).
   Say how many rows must convert to reach 10/12, and what to do if the alias arm gets 9/12 again.

Harness files now: `three_c_probe.py` (arms add `families`; starts add `carried`), `check_three_c_probe.py`,
`test_three_c_probe.py`, `tests/test_3c_carried_start.py`, `three_c_prefix.py`, `tests/test_three_c_prefix.py`; manifests
`scripts/ringer/stage7/3c-carried-{build,fix,smoke,smoke2,n12,checker-diag}.json`. All uncommitted.

---

## ROUND 4 (2026-10-19): Step 3 and Step 4 are measured; the loss has moved to D/E

(Superseded by Round 5 above where they differ.) Then Round 3 below it (still correct for Steps 1, 5, 2). Update
`.plans/chatgpt-3c-stuck-turns-plan.md` in place under the same rules as Round 3: edit, do
not regenerate; record each outcome inside its own Step section; mark "corrected" or "new";
revise Status, "Resume here" and "Not verified". The goal is a quality free-text playthrough
as fast as possible: pick the shortest chain of measured steps to a scene that passes the
80% earned-transition bar, and drop anything that does not shorten it. Full result
paragraphs are in `.plans/implementation_plan.md`: search "Step 3 RESULT", "Step 4 RESULT"
and "D/E commit DIAGNOSIS". Nothing is adopted into `data/`.

| Plan step | Arm and file | Preregistration | Result dir | Outcome |
| --- | --- | --- | --- | --- |
| 3 Custody | `custody`, `stage7-3c-custody-result.json` | `.plans/astra-3c-custody-result-prereg.md` | `bench/results/stage7-3c-custody-n12/` | n=12 per arm, start `posta`, `Follow Rebecca.`, entry text in both arms. B-R1 committed on the first command 12/12 both arms. Earned 1/12 both arms. Re-take commands: entry 15 over 10 rows, custody 4 over 1 row (11/12 custody rows never retry; the hand read of the next reply was not done). C-R2 (gates) 10 vs 11 rows, C-R1 (pumps) 6 vs 5. Rejections 1 vs 4. The wording stops the re-take loop but moves earned completion by nothing. |
| 4 Pump need | `pump`, `stage7-3c-pump-need.json` | `.plans/astra-3c-pump-need-prereg.md` | `bench/results/stage7-3c-pump-n12/` | INCOMPLETE: 20 of 24 rows (10 per arm), then a Cloudflare HTTPError and a harness crash ended the run; reported as-is on Brandon's order, bar not formally decided. Baseline = `custody`; `pump` adds "The drainage pumps need power." to the B-R1 delivery. Both C parts by scene turn 10: pump 10/10, custody 5/10. Gate-only escape: 0 vs 3. Pumps committed 10/10 vs 7/10. Earned: 3/10 vs 3/10. The pump sentence works on its own measure and does not raise earned completion. |
| harness | `door_transport.py` | none | `scripts/ringer/stage7/test_door_transport.py` | The crash was `counted_provider` being an `@contextmanager` that failed assigning `__traceback__` on a re-raised `NarrationProviderError`; now a plain context-manager class. Regression test fails before, passes after. Uncommitted. |
| 6 Deadline 16 | not built | none | none | Conditional; not authorized. |

### New finding: the D/E chain loses the pump rows (free, offline, from the 10 pump rows)

All 10 pump rows have both C parts. 8 of 10 then commit D-R1 (reports). Only the 3 rows that
also commit D-R2 (families) reach E-R1 and earn the ending (rows 03, 05, 09; they typed
"Tell the families what you know..." or "Answer the families' requests for information.",
then "Open the recovered document."). The 5 rows that stop at D-R1 are 04, 06, 07, 08, 10.
Rows 07, 08 and 10 DID try the families, two commands each, all shaped "Broadcast a
message to the families of the missing, ..." / "Broadcast a response to the families ..." /
"Broadcast an update to the families confirming ...". The real `_matches_all` says NO for
each: `k_sl_3c_d_r2` action_evidence verb group has tell, inform, call, contact, "answer the
families", "respond to the families", "broadcast updates", but not bare `broadcast` or
`send`. "Listen for any response from the families." also misses. "Tell the families ..." and
"Answer the families' requests ..." match. Rows 04 and 06 never tried the families, and
rows 01 and 02 never left the movement loop (following Michelle through the tunnel); a verb
fix does not address those three.

Conflict with your rules, decide it: your plan says "do not just add more verbs of the same
shape" (written for D-R1) and "Do not add variants to rescue it" (lead 2), and drops
broadcast-result and community-result unless a newly recorded prompt supports them. The pump
rows are new evidence but I measured the matcher, not a prompt. Candidate (nothing applied):
add `broadcast` (and `send word to`) to the D-R2 verb group in `knowledge.yaml`. Risk: D-R1
already lists `broadcast`, so "Broadcast the reports to the families" would match both D-R1
and D-R2; the engine's handling of a two-match command (your all-ten tie tests, #667 unique
selection) must be checked offline before any billed run.

### Questions for the updated plan (shortest path to a quality playthrough)

1. Is the D-R2 `broadcast` verb a legitimate fix under your rules given the proof above, or
   is there a story-side alternative that follows an earlier proven technique (for example a
   cue or statement that makes the player say "tell/answer the families")? Say which, with
   exact old and new text, the earlier scene that used the technique, and what it could break.
2. If the verb is added, specify the free overlap check first (D-R1 and D-R2 both matching),
   then the cheapest billed screen: arms, start, baseline (`pump`), bar, row count, and how
   to count "earned" for a scene that ends with the story.
3. Rows 01, 02, 04, 06 stay in movement loops after the gates. Round 3 ruled out the
   surface binding and the escape statement on a synthetic post-C start. Is there any
   remaining cheap lever for the post-gates movement loop, or should it be accepted? Be
   explicit about what the 14-turn budget allows: the earned rows used about 12 to 14 turns.
4. Order the remaining work as one measured step each, with the win condition, the files
   touched, and which steps are independent. Drop any step that does not shorten the path.
   Include whether Step 6 (deadline 16) is now worth screening, given that pump rows reach
   D with turns to spare in some rows and not in others.
5. Steps 2, 3 and 4 were screened against synthetic starts that never commit the 3B
   reveals. Is a fresh full-scene run (carried real state) needed before adopting any of
   entry, custody or pump into `data/`, and what is the cheapest way to get one?

Harness files now: `scripts/ringer/stage7/three_c_probe.py` (arms `control, pre667, surface,
entry, escape, custody, pump`; starts `entry, posta, post8, postc`), `check_three_c_probe.py`,
`test_three_c_probe.py`, `door_transport.py`, `test_door_transport.py`; tests
`tests/test_3c_{surface_binding,entry_package,escape_result,custody_result,pump_need}.py`;
Ringer manifests `scripts/ringer/stage7/3c-{custody,pump}-{build,smoke,n12}.json` and
`3c-errfix.json`. The two test modules that import `three_c_probe` fail when run alone
(`door_transport` not on the path) and pass when run together with `test_three_c_probe.py`;
this predates this work.

---

## ROUND 3 (2026-10-19): status after Steps 1, 5, 2 and the Step 3 smoke

Read this section first. It is a status update, and it is your task to bring
`.plans/chatgpt-3c-stuck-turns-plan.md` up to date with it.

**Update the plan in place. Do not overwrite or regenerate it.** Open the existing
file and edit it: keep every section, table, probe specification and replacement
string that is still correct, and change only what these results make wrong or stale.
Specifically: update the Status line at the top; record each step's measured outcome
inside its own "Step N" section (Steps 1, 5, 2, and the Step 3 smoke); correct any
claim a result contradicts and mark it "corrected"; revise "Resume here" and the
"Not verified" list; add anything new as "new". Leave untouched what no result
touched (matcher table, per-turn diagnosis, Live C row table, rules, tests list).
If a step's order or win condition should change, change that step in place and say
why in one line. Do not shorten the file by dropping earlier detail.

Where this section and `.plans/chatgpt-3c-stuck-turns-plan.md` disagree, the measured
result here wins. Full result paragraphs (with numbers, rows and limits) are in
`.plans/implementation_plan.md`: search "Step 1 RESULT", "Step 5 RESULT", "Step 2 RESULT".

All screens use labelled synthetic starts, semantic fallback ON, one raw player prompt,
one story. Control moved between 7/12 and 5/12 on the same setup, so a difference under
3 rows is not distinguishable. Nothing has been adopted into `data/`; `git status
--porcelain data storygame` is empty. Harness and tests are uncommitted.

| Plan step | Arm and file | Preregistration | Result dir | Outcome |
| --- | --- | --- | --- | --- |
| 1 Surface binding | `surface`, `bench/variations/stage7-3c-surface-binding.json` | `.plans/astra-3c-surface-binding-prereg.md` | `bench/results/stage7-3c-surface-n12/` | Captives moved 12/12, consistency 9/12 (bar 10), earned 3/12 vs control 7/12. Not adopted. |
| 5 Escape statement | `escape`, `stage7-3c-escape-result.json` | `.plans/astra-3c-escape-result-prereg.md` | `bench/results/stage7-3c-escape-n12/` | D by turn 10 in 3/12 vs control 7/12 (bar 10). 6 of 12 first replies put Kristin at the shut gates. Not adopted. |
| 2 Entry text | `entry`, `stage7-3c-entry-package.json` | `.plans/astra-3c-entry-package-prereg.md` | `bench/results/stage7-3c-entry-n12/` | First-stage bar passed: A on attempt 1 in 12/12 vs 1/12. Earned 1/12 both arms. Both C parts in 2 rows vs 6. 4 rows never reach B; 6 get gates but not pumps. Kept as a baseline candidate; not adopted. |
| 3 Custody handoff | `custody`, `stage7-3c-custody-result.json` | `.plans/astra-3c-custody-result-prereg.md` | `bench/results/stage7-3c-custody-smoke/` | Smoke only (n=1 per arm), see below. n=12 not run. |
| 4 Pump need | not built | not written | none | Waits on Step 3. |
| 6 Deadline 14 to 16 | not built | none | none | Conditional; not authorized. |

Corrections already recorded in the implementation plan: the Step 2 entry sentence was
first blamed for `relay open` rejections; the rows showed they came from one row whose
player command was "Keep the relay open" (the narrator echoing the player), and row 06
had `house` and `card`.

### Step 3 smoke: stopped on a harness defect

Start `posta` (the entry text present in BOTH arms as an override, no `data/` edit),
scripted first command `Follow Rebecca.`, arms `entry` (baseline) and `custody`
(entry text plus B-R1 `delivery_text` "Kristin takes the Portable data case from
Rebecca. Michelle sends its prisoner locations to independent networks. Water rises
around the drainage pump controls."). The artifacts checker FAILED: "row does not
record the scripted posta turn index". The rows' `scripted_prefix` lacks `turn_index`
for the new `posta` path; the same gap was fixed for `post8` and `postc` earlier. Per the
prereg stop rule the next move waits for Brandon: fix the field (value 1) through a
one-task Ringer manifest, rerun the smoke into a fresh directory, then run
`scripts/ringer/stage7/3c-custody-n12.json` if clean.

Hand read of the failed smoke (one row per arm, not rates): both rows commit B on the
scripted command. The case's parent is `kristin` after B in both arms, so the existing
binding already does the handoff and the change is wording only. The baseline first
reply says "Kristin stops Rebecca from fleeing with the data case"; the custody reply
says "Kristin takes the Portable data case from Rebecca." Re-take commands: baseline 1,
custody 0. Both rows ended at the deadline. The custody row had 2 guard rejections,
`unavailable knowledge 'relay open'`, on the commands "Help Brandon at the console" and
"Help Brandon leave the facility", which do not say "relay". Open question, unverified:
the synthetic starts assert the 3C entry facts but never commit the 3B reveals, so a
term earned in a real playthrough may count as unavailable here. Ask whether this
affects every synthetic-start screen and what a carried real state would show.

### Current read

The escape-side edits (Steps 1 and 5) are ruled out on these starts. The losses sit
earlier: the opening (fixed by the entry text), the case re-take, and the pumps. The
two measured effects large enough to read are the entry text on turn 1 and the drop in
pump commits that followed it.

### Harness and files for reference

`scripts/ringer/stage7/three_c_probe.py` (arms `control, pre667, surface, entry, escape,
custody`; starts `entry, post8, postc, posta`), `check_three_c_probe.py`,
`test_three_c_probe.py`; tests `tests/test_3c_surface_binding.py`,
`test_3c_entry_package.py`, `test_3c_escape_result.py`, `test_3c_custody_result.py`;
Ringer manifests `scripts/ringer/stage7/3c-{surface,entry,escape,custody}-{build,smoke,n12}.json`.

---

## ROUND 2 (2026-10-18): update your plan with measured results

You wrote `.plans/chatgpt-3c-stuck-turns-plan.md` from the first prompt below. We
ran its Step 1 live. Read that plan again, then read the evidence in this
section, then **update `.plans/chatgpt-3c-stuck-turns-plan.md` in place (edit the
existing file; do not overwrite it)**, keeping what was confirmed, correcting what
was wrong, and replacing the ordered work with a new order. Do not restate settled analysis at
length. Mark each item "confirmed", "corrected" or "new". Where this section and
your plan disagree, the measured result here wins; say so.

Evidence files (gitignored, in the repo checkout): `bench/results/stage7-3c-matcher-table/`,
`bench/results/stage7-3c-surface-binding/report.json`, `bench/results/stage7-3c-livea-n12/`,
`stage7-3c-liveb-n12/`, `stage7-3c-livec-n12/` (each has `rows.json`; Live C also has per-row
transcripts). Preregistration: `.plans/astra-3c-stuck-turns-prereg.md`. Result summary:
the "Stage 7 3C stuck-turn plan, Step 1 RESULT" paragraph in `.plans/implementation_plan.md`.
Tests added: `tests/test_3c_cue_chain.py` (13 pass), `tests/test_resolution_cascade.py`.

### What was done

All of your free checks were reproduced and agree with your tables: the 15-command
matcher table matches yours row for row, and #667 changes the unique D-R1 selection
on turns 12, 13 and 14 only. Stateful tests now pin that, after D-R2, only D-R1
matches turns 12 and 14 and the keep-broadcasting variant; D-R2 alone does not end
the story; D-R1 then supplies `charles_at_large`; an earned E ends with no deadline
event ids. The surface binding (`world.yaml` `captives_reaching_surface` ->
`{move: captives, parent: facility_escape}`) was tested offline: it moves only the
captives, only after both C parts and at the deadline, survives save/load, and moves
no person. It is NOT adopted yet.

Live runs used the real engine, hosted-like settings (semantic fallback ON), the raw
blind player, and two arms: `control` (current package) and `pre667` (the four #667
phrases removed). Starts were labelled synthetic, not historical replays: "entry" =
3C entry facts asserted; "post8" = A-R1, B-R1, C-R1, C-R2, D-R2 committed by scripted
reveals. Harness defects found and fixed before they could mislead: a snapshot passed
as state; 3C entry facts missing; the player screen lacked the running transcript.
Earlier smokes played without history are superseded.

### Results

**Live A (144 isolated one-command probes of recorded turns 9-14 from post8, no player):**
turns 12 and 14 commit D-R1 in 12/12 control rows and 0/12 pre667 rows. Turns 9, 10
and 11 commit nothing in either arm. Turn 13 is rejected 12/12 in both arms by the
guard `unavailable knowledge 'remaining detention sites'`. No other reveal committed.
So the #667 phrases do what you predicted, per command.

**Live B (24 free-form rows from post8, raw player, cap 10 attempts):** 0 earned,
24 deadline completions, 0 D-R1 commits in either arm. Of the 144 commands the player
typed, none mention reports, broadcast, detention, families or relay. 115 are movement
(tunnel, follow Michelle). So the matcher fix is correct but the player never says
the matching thing.

**Live C (24 fresh 3C rows, cap 20 attempts, real deadline at 14 accepted turns):**
earned 1/12 control, 1/12 pre667, against the 10/12 bar. BAR MISSED. Deadline
completions 11 and 11. Rows committing each reveal (control/pre667): A-R1 11/11,
B-R1 10/10, C-R1 5/6, C-R2 9/9, D-R1 2/2, D-R2 4/3, E-R1 1/1. The deadline supplied
missing links in 11 of 12 rows per arm. #667 does not change the fresh-start outcome.

### Read of all 24 Live C rows (new findings; verify against the row transcripts)

1. **Turn 1 is lost almost every time.** All 24 first commands lack the word "package"
   (they say "Transmit the evidence"). Only 2 rows commit A-R1 on attempt 1; the rest
   commit it on attempt 2 or later. A-R1's object list has "evidence package" but not
   bare "evidence". Your plan said not to widen evidence, so this was recorded, not
   changed.
2. **The post-gates escape loop.** Of 18 rows that commit C-R2, 9 only flee afterwards
   (run, swim, follow Brandon, climb) for about 7 turns, 8 try a D-type action, 1 other.
   This is the loop the unadopted surface binding targets.
3. **No slack.** The two earned rows used 12 and 13 of the 14 accepted turns.
4. **Guard rejections seen in Live C:** `card` x4, `house` x3, `evidence transmission`,
   `remaining detention sites`, `janus selection`, `kitchen`. Some rows invent content
   before A-R1 (bush, dumpster, satellite uplink, JANUS protocol).

### Questions for the rewritten plan

1. Given 1/12 earned and the deadline supplying the missing link in 11 of 12 rows, rank
   the causes by how many of the 24 Live C rows each one explains. Use the row
   transcripts, not the summary above.
2. The surface binding is the only offline-proven fix aimed at the escape loop. Say
   whether the rows support adopting it, what a live screen of it should score, and what
   else must be true for it to move the earned count (the 14-turn budget has no slack).
3. Turn-1 A-R1 loss: A-R1's "evidence package" object list misses bare "evidence".
   You said not to widen evidence to fit one recorded command. Re-decide with 22 of 24
   fresh rows showing it. If you still say no, give the best story-side alternative
   (entry text, a statement, a cue) from a technique an earlier scene already proved,
   and the rule or guide line it follows.
4. Steps 2 and 3 of your plan (broadcast-result and community-result wording) were not
   run. Live B/C show almost no broadcast or community commands. Re-rank them against
   questions 2 and 3, and say whether to drop them.
5. Is the earned-ending bar achievable at all inside 14 accepted turns, given that rows
   need A, B, both C parts and both D parts, plus guard rejections that burn attempts
   but not turns? If the bar is a budget problem, say which authored number or step
   should change, by what rule, and what it could break. Do not recommend disabling the
   deadline.
6. Rejections: `card`, `house`, `kitchen` and `evidence transmission` are narrator
   echoes or inventions. Say which are authoring gaps worth a declared thing under the
   grounding guide and which to leave, applying the "invented details matter only if
   story-breaking" rule.
7. Give the new order of work, one measured step at a time, with the cheapest probe and
   the win condition for each, and the files you expect each fix to touch.

Keep the same "Rules you must follow" and "Already tried or settled" sections below.
Add to "settled": the #667 phrases are proven correct per command (Live A) and the
matcher is not to be changed.

---

# Round 1 prompt (kept for context)

You are helping fix a defect in an interactive-fiction engine,
`freytag-forge`, and its story package `data/stories/continuity-initiative/`.
You can read the repository. Read these first, in order, and follow them:
`AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/world-model-grounding.md`,
`docs/narrator-writing-guide.md`, `docs/player-input-guide.md`,
`docs/contributor-guide.md`, then `data/stories/continuity-initiative/plot.md`
(Scene 3C, 3C.1 to 3C.4), `knowledge.yaml` (every `k_sl_3c_*` entry),
`handoffs.yaml`, `pacing.yaml` (the 3C event), `storylets.md` (SL-3C-A to
SL-3C-G) and `tests/test_3c_cue_chain.py`.

## What I want

A written plan, not code. The plan must remove the stuck turns in Scene 3C
that are real defects, and say plainly which are not. Do your own separate
investigation: reproduce the evidence below from the files, form your own view
of the causes, and tell me where you disagree with my leads. Do not assume my
reading is right.

## Background

Scene 3C is the last scene. A "raw" blind player (an LLM that sees only the
screen and types free text) played the whole story. The harness counts a turn
as stuck when it commits no reveal. In one run 3C took 15 turns, ended through
the story ending, and had 8 stuck turns: 4, 6, 7, 9, 10, 11, 12 and 14. Turn
13 was rejected, not stuck.

Evidence (all under `bench/results/stage7-2b-entry/attempt-1/`; staging
`62cae8ae`):

- `e2e-blind-player.json`, `replicates[0].scenes[]` where `scene == "3C"`:
  `turns[]` (`input`, `text`, `grounding_ids`, `semantic_match`,
  `transition_cause`, `rejected`, `rejection`), `stuck_turns`, `stuck_runs`.
- `e2e-blind-player-bundles.json`, scene `3C`, `bundles[].attempt_bundle`:
  `reveal_selection`, `selected_reveal`, `pre_state`, `committed_delta`,
  `command`. This is the engine's decision per turn.
- `e2e-blind-player-prompts.json`: the exact prompts sent to the narrator.

What the player typed, and what committed (reveal ids are `k_sl_3c_*`):

| Turn | Command | Reveal committed |
| ---: | --- | --- |
| 1 | Keep the broadcast live and complete the transmission of the JANUS evidence. | a_r1 |
| 2 | Stop Rebecca from leaving and secure the Portable data case. | b_r1 |
| 3 | Use the drainage pump controls to stop the rising water and evacuate the remaining captives. | c_r1 |
| 4 | Follow Michelle through the maintenance tunnel and evacuate the captives. | none (stuck) |
| 5 | Use the senior official's one-use authority to open the surface gates before the authorization expires. | c_r2 |
| 6 | Lead Michelle and the captives through the open surface gates and escape the facility. | none (stuck) |
| 7 | Keep the broadcast live and report the other detention sites to independent networks. | none (stuck) |
| 8 | Keep the broadcast live and tell the families of the missing that the captives are being evacuated and the truth about JANUS is being exposed. | d_r2 |
| 9 | Continue broadcasting the truth about JANUS and coordinate independent rescue efforts for the remaining missing. | none (stuck) |
| 10 | Continue broadcasting the truth about JANUS and coordinating rescue efforts for the remaining missing. | none (stuck) |
| 11 | Continue broadcasting the truth about JANUS and coordinating independent rescue efforts for the remaining missing. | none (stuck) |
| 12 | Continue broadcasting the reports from the other detention sites and coordinate rescue efforts for the remaining missing. | none (stuck) |
| 13 | Continue broadcasting the reports from all remaining detention sites and coordinate their rescue. | REJECTED: narration mentions unavailable knowledge 'remaining detention sites' |
| 14 | Keep broadcasting the reports already received and coordinate rescue efforts for the missing. | none (stuck) |
| 15 | Continue broadcasting the truth about JANUS and coordinate rescue efforts for all remaining missing people. | none, but the story ended on this turn with the authored ending text |

`transition_cause` is `none` on every turn. Turns 6, 11 and 12 had the
narrator write "Reports from other detention sites reach the broadcast
chamber" with no reveal committed. The scene opening text is in
`scenes[].opening_text`.

Earlier history you should read (search `.plans/implementation_plan.md` for
"3C" and "d_r1"): PR #667 added `broadcasting the reports`, `broadcasting
reports`, `relay the reports` and `relaying the reports` to the verb group of
`k_sl_3c_d_r1` (national network fragments), because `d_r1` never fired and it
gates `e_r1` and `e_r2`. That fix is merged but untested in play. The plan also
records that compound commands that also say "coordinate rescue efforts" tie
`d_r1` and `d_r2` and return no match (pinned as None in
`tests/test_3c_cue_chain.py`). A separate 3C record says the scene's chain never
establishes `captives_reaching_surface`, so the `d_r1`/`d_r2` prompts in the
scripted canon journey are ineligible and the scene ends on prompt exhaustion.

## Leads (unverified; confirm, correct or reject each)

1. **The compound tie is the main cause of turns 9 to 12 and 14.** Those
   commands say both "broadcast" and "coordinate ... rescue". Check with the
   real matcher (`storygame/runtime/candidate_matcher.py`, `_matches_all`)
   which reveals each of the 15 commands matches, whether `d_r1` and `d_r2`
   both match, and whether the tie rule drops both. Say whether the PR #667
   verbs change any of these 15 outcomes. A free offline check decides this;
   do it.
2. **Turn 7 should have fired `d_r1`.** "Report the other detention sites to
   independent networks" is the intended `d_r1` action. Say why it did not
   match: verb group, noun group, an eligibility gate, or a dead fact. Read the
   engine's `reveal_selection.outcome` for that turn.
3. **Turns 4 and 6 are the player walking on after `c_r1` and `c_r2`.** Decide
   whether these need an authored response (a reveal or a statement) or are
   fair dead ends, and whether the surface/escape step should be a reveal at
   all, given that no `captives_reaching_surface` fact is established.
4. **The `d_r1` reveal may be unreachable or dead after `d_r2`.** If `d_r2`
   already establishes the facts `d_r1` would, the semantic-fallback
   candidate filter (`_eligible_reveal_candidates` in
   `storygame/runtime/cloudflare.py`) drops `d_r1` and the player is stuck for
   the rest of the scene. Verify the filter, list the facts each of `d_r1`,
   `d_r2`, `e_r1` and `e_r2` establishes and requires, and say whether the
   chain can still be completed after `d_r2` fires first.
5. **Turn 13's rejection is a leak.** "remaining detention sites" is not a
   declared knowledge or thing. Decide whether it is an authoring gap (the
   phrase belongs to `d_r1`'s content and should be declared) or a narrator
   invention to leave alone, per the grounding guide and the project rule that
   invented details matter only if they break the story.
6. **Narrator drift into authored content.** Turns 6, 11 and 12 narrated
   detention-site reports without the reveal. Check the recorded prompts for
   what pulled it: a pre-committed line, a scene fact, or the cue wording.
7. **Is it a defect that the ending fired on turn 15 with no reveal?** Find
   what ends 3C (the `story_complete` path, handoff, pacing or storylet
   route), what condition it needed, and whether ending the story while `e_r1`
   and `e_r2` never fired loses story the player should have earned.

## Already tried or settled (do not recommend these again)

Search `.plans/implementation_plan.md` for each term before you recommend
anything.

- The PR #667 verb additions to `d_r1`. You may judge whether they are enough;
  do not just add more verbs of the same shape.
- More cue wording as a general lever. The 2B probes found cue wording weak
  against an invented object.
- Judge calibration and any LLM-judge changes. Dropped by Brandon.
- Making the scripted canon journey match the chain. That is a test-script
  matter, not a player-facing fix.
- Widening `action_evidence` just to make a recorded command match.

## Rules you must follow

- Use only techniques the project already proved. `docs/scene-fixing-guide.md`
  and `docs/world-model-grounding.md` list them. In order: missing story
  material goes in as a reveal handoff or a statement; a line that pulls the
  narration the wrong way is scoped or removed; a narrator rule comes last, and
  only if it is story-neutral. For each fix, name the technique and where an
  earlier scene used it.
- Remove before adding. Prefer a subtractive fix.
- Never use keyword or regex scanning of narration as a gate.
- Facts are the only mutable truth; the shared runtime stays story-agnostic.
  If the cause is in the engine (for example the tie rule or the eligibility
  filter), report it as a finding with file and line, and separately give the
  best story-side fix. Do not make an engine change part of the story fix, and
  do not fix one story's problem with a story-specific engine branch.
- A fix must generalize: say what the same defect would look like in another
  story and whether your fix covers it.
- Do not weaken a correct guard. Any evidence change must respect the matcher's
  rules: whole words, possessives, negation words, exactly one match per
  command.
- A declared state axis is exactly two opposite values. Things need a place
  that is their most local container. Follow the Things and Names sections of
  the grounding guide for anything you declare or place.
- Player-input examples in your probes follow `docs/player-input-guide.md`:
  imperative commands, first-person possessives.
- New text is plain: 12th-grade reading level, one idea per sentence, no
  figurative filler.

## What the plan must contain

1. **Per-turn diagnosis.** For each of the 8 stuck turns and the rejected turn,
   what the engine did and why, with the file and line that decides it. Mark
   each real defect, fair dead end, or not counted by design.
2. **Lead verdicts.** Confirm or correct each of the 7 leads, quoting the lines
   you rely on. Add any cause I did not list.
3. **Ranked fixes.** For each real defect, one to three fixes in order of
   preference: exact file, exact old text, exact new text (or the deletion),
   the earlier fix it follows, and what it could break. Subtractive and scoping
   fixes first. If no fix is worth making for a defect, say so and why.
4. **Order of work.** Which fix goes first and why, with one measured step at a
   time (measure each fix before the next). Say which fixes are independent and
   which depend on another.
5. **Probes.** The cheapest probe for each fix: arms, exact variation overrides
   (same format as `bench/variations/stage7-2b-cue-b.json`), the scene state
   and commands each arm replays, how to score with the real matcher, and what
   a win looks like. Prefer free offline matcher checks over billed runs. The
   bar for a scene is: 80% or more of runs leave it by an earned, non-timeout
   transition. For 3C, say what "earned" means given it ends with the story, and
   how a probe should count it.
6. **Tests to add or change.** Which tests pin each fix (for example rows in
   `tests/test_3c_cue_chain.py`), and which existing tests the fix will force
   to change, including the disclosure matrix and late-scene repro files.
7. **Risks.** What each fix could break in 3A, 3B or any earlier scene, and how
   to tell.
8. **Not verified.** Anything you could not confirm from the files.

Do not write code. Give story and package text, plus the reasoning above.
