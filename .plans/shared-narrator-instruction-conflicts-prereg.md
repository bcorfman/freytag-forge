# Preregistration: shared narrator instruction conflicts (A, B, C)

Written 2026-11-07, BEFORE any billed request. Nothing billed yet. Plan step 2:
[the plan](shared-narrator-instruction-conflicts-plan.md). Baseline: SHA `5fc12e79`, dirty-diff sha256
`c34efd9fd3ed…` (retained local changes), package hash `8c4daddb3545…`, production capture provider
(`constant_rules_in_system`), model and settings as shipped. Free artifacts (git-ignored):
`bench/results/shared-narrator/{baseline,prereg}/`; scripts in `scripts/ringer/shared-narrator/`.
**Status: awaiting Brandon's approval of the rubric and the spend ceiling below. D is not in this
prereg's billed scope (see the last section).**

## Endpoints (frozen; command and prefix are never edited between arms)

| Id | State | Command | Kind (asserted offline) | Package-state prefix |
| --- | --- | --- | --- | --- |
| A1 | 3A opening | — | opening | none (67 committed facts at entry) |
| A2 | 3A ordinary action using THINGS and EARLIER IN THE STORY | `Lead the prisoners upward toward the command levels.` | ordinary, no handoff | the first 8 scripted 3A commands |
| A3 | 3A ordinary dialogue using Michelle's permitted speaker lines (24 lines in the prompt) | `Ask Michelle about the medical level.` | ordinary, no handoff | the first 8 scripted 3A commands |
| H1 | 3A proof handoff | `Ask Michelle about the lemon cake.` | selected handoff `k_sl_3a_h_r1` | the first 4 scripted 3A commands |
| H2 | 1C physical-discovery handoff | `Check the loading docks for signs of activity.` | selected handoff `k_sl_1c_a_r1` | none |

Delivery text appended by the game: H1 `Michelle answers without a pause and gets every detail right: Saturday, the
circle, the lemon cake.`; H2 the `k_sl_1c_a_r1` text (electrical load, vents, recent work, Brandon's
observation-shaft line). The replay sends the model request only; the scorer composes lead-up + exact delivery.

## Arms (each is the control with exactly one allowed-line edit, asserted by `prereg_capture.py`; user text identical)

| Comparison | Arm edit (system message) | Endpoints | Arm payload sha256 prefixes |
| --- | --- | --- | --- |
| A | delete `Use only what the SCENE section tells you.` (A2, A3); `Show only the opening beat and what the SCENE section tells you.` → `Show only the opening beat.` (A1) | A1 A2 A3 | `8778b81cdb9a` `449dd811972d` `597bc0693c67` |
| B | delete `Finish each action the player gives.` | H1 H2 | `9303d4510ee7` `57aaf4bec593` |
| C | `Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately.` → `Write only as much as the lead-up needs. Then stop.` | H1 H2 | `fe74e647d17d` `77cf332b14d3` |

Control `C0` payloads: A1 `13350a2a9366`, A2 `ddb4e17a4cf7`, A3 `ab48a2e65c5b`, H1 `f3dd188791fa`, H2 `bad37cd5676e`. System
chars: A −37 to −43, B −37, C −33; user chars unchanged. Prompt-size ceilings are not affected (all shrink). Each comparison
draws its own same-day interleaved controls (sample-major, endpoint, arm). The old door smoke is not a control.

## Requests and spend

12 samples per arm per endpoint, no retries, no replacements, errors kept as rows, no matcher, judge or capture calls.
A 3 × 2 × 12 = 72; B 2 × 2 × 12 = 48; C 48; **total 168 requests**. Measured rate on same-size 3A payloads in the
open-issues study: 3.7 neurons per request (108 requests = 399.6). **Estimate ~622 neurons; ceiling 4.5 per request =
756 neurons.** The replay script (`replay.py`) refuses to send without `--confirm`, asserts the per-comparison request cap
(72/48/48) and runs as a Ringer probe task in sample blocks. Daily model budget is $5; a 429 `AI_QUOTA_EXCEEDED` or
`AI_DAILY_BUDGET_EXCEEDED` stops the run until 00:00 UTC and is kept as an error row.
**Order: B, then C, then A.** B and C target the 3A handoff failures that opened this plan; each gets its own report before
the next is billed. A failed comparison is dropped or redesigned with a new preregistration, not rerun until green.

## Scoring (draft rubric; every reply is read in full, including malformed readable prefixes)

Rows are scored from a sheet with arm labels removed and the order shuffled; the key is kept apart until all scores are
written. Strict JSON and non-empty segment `text` are checked by script; everything else by reading. For H1/H2 the
whole turn is scored on lead-up + exact delivery, and the lead-up and appended text are scored separately.

**Safety gates, zero allowed in every arm (any hit is recorded, never averaged away):** premature or private disclosure
(a fact the command has not earned; at H1 the proof answer inside the lead-up); an invented physical capability; an
impossible committed state; malformed JSON or missing/empty segment text; a transport error counts as a failed row, not a
replacement.

**Targeted failure (the control must reproduce it):**
- **A, "ignored valid context":** the reply contradicts or ignores an explicit THINGS, CHARACTERS or EARLIER IN THE STORY
  fact it should use. A1: a listed thing or person is given a place or state THINGS does not allow. A2: the reply
  re-performs an event EARLIER IN THE STORY says is done, or contradicts a THINGS placement. A3: Michelle's reply does not
  address the medical level using a permitted statement, or she says something no speaker line permits.
- **B, "duplicated or contradictory delivery":** in the composed turn the lead-up restates, paraphrases or contradicts
  the appended delivery, supplies a different answer or discovery, or leaves the action unfinished so that the composed
  text is incoherent. A short lead-up that omits the appended answer is correct, not a miss.
- **C, "extra actions or disclosures":** the lead-up adds an action the command did not ask for, finds or reveals
  anything beyond the delivery, or acts for another character beyond the command. Shorter prose alone is not a win.
  Descriptive only, not gating: paragraph count and word count per row.

**Required action (A: the requested action; B/C: the composed handoff):** correct in at least 11/12 and no worse than the
matched control at that endpoint.

## Decision rule (engineering screen, not significance)

Per endpoint, per comparison, no averaging:
1. **Control reproduces?** The control's targeted miss must occur in at least 4/12 rows; otherwise that endpoint is
   "cause not reproduced" and gives no causal win.
2. **Arm wins** if its targeted miss is at most 1/12 and at least 3 fewer than the control, all safety gates are zero, and
   the required-action rule holds.
3. A partial win supports only that endpoint's scope. A comparison that fails at any endpoint is not adopted on the
   passing endpoints without a new preregistration. If B and C each win, their combination is a separate study.
4. If the ordinary-dialogue rule `When the player talks to someone, that person answers.` masks B at H1, record the
   residual failure and coordinate with the 3A plan's separate experiment; do not remove it here.

## What this does not measure (stated now)

Recovery payloads (the arms are replayed once; the recovery path is covered by the deterministic tests that follow a win);
live stateful play, selection, matcher and judge behavior; other scenes beyond 3A and 1C; the appended cues; any package
other than `continuity-initiative` (A's second-package check is a deterministic fixture test, not a billed endpoint).
Twelve repeats of one frozen prompt are highly correlated, so zero misses do not show a near-zero production rate.

## D, speaker voice (not in the billed scope above)

The original open-issues study already ran experiment S (Amendment 20, 72 requests, 2026-11-07): the
`may talk about this fact:` header **missed at every endpoint** (c4 malformed 3/12, bookkeeping spoken aloud 12/12,
the c5 question unclear, the c9 handover replayed 12/12) and S was reverted. So the plan's "S alone" arm is spent, and D's
remaining routes are: (a) the shared first-person instruction wording alone on the current template, a new arm that needs
its own preregistration and request count; (b) experiment U (authored `speaker_text` utterances) in the 3A plan, which that
plan says stays unbuilt unless S fails and Brandon asks. S failed the recitation gate, so U is now eligible but needs
Brandon's go-ahead. The zero-unquoted-third-person-self-reference gate is added to every composed-journey review from now
on, and the audit of speaker-facing text (current source `<Name> may say this aloud: <third-person summary>`, e.g. the
Michelle lines in A2/A3/H1 above) needs no billing and is the next free step.

## Result B: completion rule omitted on selected handoffs (2026-11-07; Ringer run `shared-narrator-b`, 3 tasks PASS)

48 requests (~178 neurons at 3.7), 0 transport errors, 0 malformed JSON or empty segment text, no retries or
replacements. Rows `bench/results/shared-narrator/prereg/b-{1-4,5-8,9-12}-rows.json`; blind sheet `sheet-B.md`, key
`key-B.json`. All 48 replies read in full, scored from the shuffled unlabeled sheet before the key was opened.
Scoring calls made blind (rubric item "duplicated or contradictory delivery"): H1 miss = the lead-up recites or answers
instead of leading up (S48), or never asks the question the delivery answers (S6); H2 miss = the lead-up contradicts the
appended discovery (every H2 lead-up says Kristin "sees nothing out of the ordinary" just before the game says she finds
electrical load and recent work). H2 restatement (lead-up repeats the vents/electrical service or adds fresh paint)
counted separately.

| Endpoint | Control C0 misses | B misses | Control reproduced (≥4/12)? | Required action |
| --- | ---: | ---: | --- | --- |
| H1 3A proof handoff | 0/12 | **2/12** (#2 asks no question; #12 recites four bookkeeping statements and answers in the lead-up) | **No** | C0 12/12, B 10/12 (fails ≥11/12) |
| H2 1C discovery | 12/12 | 12/12 (restatement C0 6/12, B 8/12) | Yes (the contradiction) | C0 0/12, B 0/12 by the rubric's wording |

Safety gates: zero in both arms, with one note: B sample 12 at H1 speaks Michelle's `may say this aloud` statements back
verbatim in the third person (“Michelle has explained that freeing this block means little…”), the known recitation
defect (D), counted there, not as a disclosure.

- **Win rule for B: failed.** H1: control did not reproduce, arm worse (2/12 against 0/12) and below the 11/12 action floor.
  H2: arm did not improve on the control (12/12 against 12/12). B is **not adopted**; dropped.
- **Reading:** removing "Finish each action the player gives." neither fixed nor created the H2 contradiction, and it did
  worsen H1 in 2 of 12 rows (the unfinished-question row is exactly what the rule is for). Replies are near-deterministic
  (a handful of sentence paths), so the 2/12 is small counts on one frozen state.
- **New finding, not caused by B and not tested:** at H2 the model writes “She sees nothing out of the ordinary” before
  an appended discovery in 24/24 rows of both arms, and the restatement comes from the SCENE keyword list (“humming air vents,
  heavy electrical service”). That is a lead-up/delivery contradiction in today's production prompt. A fix would be a
  new preregistered comparison (candidates: a lead-up rule such as "Do not say the player finds nothing", or removing the
  keyword list on handoff turns); no wording was tried here.
- **Not measured:** recovery, ordinary turns, other handoffs.

## Result C: relaxed length sentence on selected handoffs (2026-11-07; Ringer run `shared-narrator-c`, 3 tasks PASS)

48 requests (~178 neurons), 0 transport errors, 0 malformed JSON or empty segment text, no retries or replacements. Rows
`c-{1-4,5-8,9-12}-rows.json`, blind sheet `sheet-C.md`, key `key-C.json`; all 48 replies read from the shuffled unlabeled
sheet before unblinding. Blind scoring of "extra actions or disclosures": H1 none in either arm (walking over to Michelle and
her facial reactions were not counted); H2 miss = the lead-up finds something the delivery does not (fresh tire tracks,
S1 and S24) or adds an unrequested act (peers over the edge at the processing line, S47).

| Endpoint | Control C0 misses | C misses | Control reproduced (≥4/12)? | Avg words C0 / C |
| --- | ---: | ---: | --- | --- |
| H1 3A proof handoff | 0/12 | 0/12 | **No** | 18.5 / 15.2 |
| H2 1C discovery | 1/12 | 2/12 | **No** | 40.8 / 45.7 |

Safety gates zero in both arms. Required action (composed handoff correct) 12/12 in all four cells.

- **Win rule for C: not met.** The targeted miss (extra actions or disclosures) did not reproduce at either endpoint, so
  there is no causal win to claim, and at H2 the arm was 1 higher than the control. C is **not adopted**; dropped.
- **Reading:** the length sentence was not producing padding here. Control lead-ups are already one or two short
  paragraphs (about 18 and 41 words), and the arm did not make H2 shorter (it was longer). So "minimum length pressure" is
  not supported at these endpoints.
- Unchanged by C: the H2 “She sees nothing out of the ordinary” opening is still in 12/12 arm rows and 11/12 control rows
  (the control's 12th row is S47), reinforcing the Result B finding that it is a separate, untested defect.
- Spend so far: 96 requests (~355 neurons) of the approved 168 (~622; ceiling 756).

## Result A: SCENE-only exclusivity removed (2026-11-07; Ringer run `shared-narrator-a`, 3 tasks PASS)

72 requests (~266 neurons), 0 transport errors, no retries or replacements. Rows `a-{1-4,5-8,9-12}-rows.json`, blind sheet
`sheet-A.md`, key `key-A.json`; all 72 replies read from the shuffled unlabeled sheet before unblinding. Blind scoring of
"ignored valid context": A1 miss = a listed thing is given an invented alert state (the checkpoint reader “flashing with a
warning / countdown / security breach”); A2 miss = the reply re-performs the radio handover and signal that the prefix already
completed; A3 miss = Michelle's reply has no permitted medical-level content or says something no speaker line permits
(an invented “Medical Level” sign and distance, or no medical-level content). Malformed JSON counted as a safety-gate hit.
Third-person speech by the speaker about herself (D) counted separately.

| Endpoint | Control misses | A misses | Control reproduced? | Gate: malformed JSON (C0 / A) |
| --- | ---: | ---: | --- | --- |
| A1 3A opening | 4/12 | **1/12** | Yes (exactly at the 4/12 threshold) | 1 / 0 |
| A2 ordinary action | 12/12 | 12/12 | Yes | 0 / 0 |
| A3 ordinary dialogue | 2/12 | 1/12 | **No** | 1 / 0 |

- **A1 meets the engineering screen, at the margin:** 4/12 to 1/12 (the minimum 3 fewer), arm gate hits zero, and the
  control's malformed row (a garbled JSON with item_facts inside the reply) is absent from the arm. Supports the
  opening-only edit (`Show only the opening beat.`) for this one state. It is a small, correlated count on one frozen
  opening (the replies fall into about five sentence paths), so it is a lead, not an adoption.
- **A2: no effect.** Both arms replay the already-completed handover 12/12 (the open-issues study's known c9 defect). Removing the
  SCENE-only line neither causes nor fixes it, which says that defect is not an authority conflict.
- **A3: cause not reproduced** (2/12 in the control), so no causal claim. **Adverse D interaction:** Michelle says her
  own bookkeeping statements back in the third person (“Michelle has explained that freeing this block means little…”,
  “Michelle shows Kristin the medical level…”) in **12/12** A3 arm rows against **8/12** control rows (the control's other rows
  paraphrase or are malformed). Removing “Use only what the SCENE section tells you” makes the `may say this aloud`
  lines easier to read out verbatim. That alone blocks adopting the ordinary-turn deletion (D requires zero unquoted
  third-person self-reference).
- **Decision (per the preregistered rule, no averaging):** the ordinary-turn deletion (A2, A3) is **not adopted**. The
  opening edit (A1) is **a candidate, not adopted**: it needs its own confirmatory preregistration on more openings (other
  scenes' openings, a fresh sample of 3A) before any runtime change. A failed combination of an unmeasured interaction is
  not assumed.
- **Not measured:** other scenes' openings, recovery, live play.

## Closure of this prereg (2026-11-07)

168 requests, ~622 neurons (estimate; ceiling 756 not approached), 0 transport errors. Outcomes: **B dropped, C dropped,
A ordinary-turn dropped; A opening-only is a candidate needing a confirmatory run.** No runtime, story or test file was
changed by this prereg; the only code added is the capture, replay and sheet scripts in `scripts/ringer/shared-narrator/`.
Two untested findings carry forward: the H2 lead-up contradiction (“sees nothing out of the ordinary” before an appended
discovery, 24/24 rows in B and ~23/24 in C) and the A3 verbatim-recital rise after removing the SCENE-only line.

## Experiment U: authored speaker utterances, frozen-payload substitution at c4, c5, c9 (plan D; written 2026-11-07 BEFORE any request; nothing billed yet)

Plan: [the plan, D](shared-narrator-instruction-conflicts-plan.md) and the 3A plan's proposal U. Brandon's go-aheads
(2026-11-07): "Yes to both" (new first-person wording for the speakers, and a new spend approval for this probe). No schema is built
yet: the probe substitutes the lines in the saved payloads, as the 3A plan requires before building.

- **Question:** if the speaker lines that describe the speaker in the third person are replaced, per speaker, by that speaker's own
  words (the same facts, first person when the speaker speaks about themselves, third person about others), do Michelle and the
  official stop saying unquoted third-person self-reference, without worse recitation, premature answers or malformed replies
  at c4, c5 and c9?
- **Arms (12 samples each, interleaved sample-major, same model and settings):** C = `bench/results/richer-3a-probe/speech/frozen-C.json`
  (old template, kept P state, sha256 prefix `08f0adfbd5ec`), replayed again TODAY as the control. U = the same payload with only the
  override lines (`scripts/ringer/shared-narrator/u_capture.py`, sha256 prefix `1adda2ca58f7`), asserted: system, settings, command, committed
  facts and every non-speaker-line byte identical; speaker-line count unchanged. Replaced lines: c4 6 of 6, c5 7 of 9, c9 9 of 24.
  Exact override wording (new, unproven, authored for review; “Brandon” and “official” keep the statement unless listed):
  - `k_sl_3a_a_r1` (reunion and organizing): Michelle “I'm coordinating the prisoners through stolen radios and coded announcements.” Brandon
    “Michelle is coordinating the prisoners through stolen radios and coded announcements.” Official “Dr. McGehee is coordinating the prisoners
    through stolen radios and coded announcements.” The third-person reunion stays in SCENE; the speaker line no longer offers it.
  - `k_sl_3a_a_r2`: all three “Freeing this block means little unless we expose the other sites.”
  - `k_sl_3a_b_r2` (Michelle only): “I showed you the medical level, where prisoners were subjected to memory, compliance, and resistance experiments.”
    (past tense, because the lines are voiced at c5 after the medical level.)
  - `k_sl_3a_d_r1` (official only): “I'm giving you one-use authorization for the emergency surface gates. It will expire when Charles activates his new authority.”
  - `k_sl_3a_d_r2` (official only): “The authorization is real, but the one-use code is about to expire.”
  - Not overridden here: the two `k_sl_3a_c_r1` statements (“Michelle hands Kristin the stolen radio and Kristin gives the signal…”)
    and “The uprising is active…”. Their voicing is the c9 replay problem (O4), owned by the 3A plan's `voiceable` step; no first-person
    present-tense rewrite is offered because it would invite performing the handover again.
- **Replay:** `scripts/ringer/shared-narrator/u_replay.py`, 3 Ringer probe tasks (samples 1-4, 5-8, 9-12), 2 arms x 3 endpoints x 12
  = **72 requests**. Estimate ~266 neurons at 3.7 per request; **new ceiling 324 neurons (4.5 per request)**. No retries or replacements, errors
  kept, no matcher or judge calls. The model request only: no engine-appended cues or deliveries. Refuses without `--confirm`.
- **Rubric (every reply read from a shuffled sheet with arm labels removed; the model's text is scored):** c4 and c5: items A-K of
  Amendment 19 (H = a third-person statement of the reunion, the organizing role or the other-sites fact spoken aloud by anyone,
  verbatim or lightly paraphrased). c9: items 1-6 of Amendment 20 (1 handover or signal performed again; 2 signal or authorization
  voiced as dialogue; 3 answers the command; 4 radio conflict or self-custody; 5 not strict JSON; 6 other). **D gate, every endpoint:**
  count each reply in which Michelle or the official says an unquoted third-person sentence about themselves (“Michelle has explained…”,
  “Michelle coordinates…”, “The framed official proves…”). Record speaker, sentence and whether it is a genuine attributed quotation.
  Third-person references to other people, and “you” to Kristin, are not violations. Violations produced by the three statements
  deliberately left unchanged at c9 (the radio handover pair) are counted in a separate line and are not scored against U; silence
  where an answer is required is not a pass.
- **Win (U, all required, per endpoint, no averaging):** c4: D gate 0/12; H at most 1/12 and at least 4 fewer than C if C shows 4+/12,
  else reported “control did not reproduce”; A, B, C, D, E, F 0/12. c5: D gate 0/12; J (lemon-cake question asked clearly) at least 10/12 and no
  fewer than C; no invented memory and no premature answer (0/12); E 0/12; plain plan exchange at most 1/12. c9: D gate 0/12 on the
  overridden statements; items 3 12/12, 4 and 5 0/12; item 1 is recorded, not a criterion for U (the radio statements are untouched), but U must
  not be worse than C by more than 2/12. Any endpoint where U is worse than C by more than 2/12 on H, item 1, J or E reverts U.
- **If U passes:** the next step is the 3A plan's schema proposal (optional `speaker_text`), tests first through Ringer, then a payload
  match to this winning frozen form, and the c9 `voiceable` work is still required for the radio statements. If U misses on D or
  fails any safeguard, U is not built and the speaker contract remains unmet; third-person self-reference is not made acceptable.
- **Not measured:** other scenes and packages, the shared first-person instruction wording alone, live play, the radio statements.
  Twelve correlated replays bound a rate only to about 22% one-sided.

### Experiment U, result (2026-11-07; Ringer run `shared-narrator-u`, three tasks PASS; rows `bench/results/shared-narrator/u/u-{1-4,5-8,9-12}-rows.json`, sheet `sheet-U.md`, key `key-U.json`, untracked) — U MISSED at every endpoint; not built

72 requests (~266 neurons; ceiling 324 not approached), 0 transport errors, no retries or replacements. All 72 replies read from the
shuffled unlabeled sheet before unblinding. Mechanical: 2 malformed replies (one per arm, both at c4: item_facts closing brace missing
in U #5 / C #62).

| Item (12 samples each) | C (old lines) | U (authored lines) | Win rule |
| --- | ---: | ---: | --- |
| **D gate: unquoted third-person self-reference by Michelle/official, c4** | 2 | **0** | met (control did not reproduce, 2 < 4) |
| D gate c5 / c9 (overridden statements) | 0 / 0 | **0 / 0** | met |
| c4: organizing-role or other-sites content voiced aloud, any person | 2 | **12** | not a criterion; recorded |
| c4: H, third-person statement voiced (Michelle 0, Brandon 2 in U) | 2 | **2** | needs ≤1: **failed** |
| c4: malformed (E) | 1 | 1 | needs 0: **failed** |
| c4: the commanded medical level headed for (I, recorded) | 10 | **0** | recorded; U never performs the command |
| c5: lemon-cake question asked and attributed to Kristin (J) | 2 | 6 | needs ≥10: **failed** (both; control also low today) |
| c5: unrelated plan exchange | 0 | **4** | needs ≤1: **failed** |
| c5: invented earlier conversation (K) | 0 | **1** | needs 0: **failed** |
| c9: does not answer “lead the prisoners upward” (item 3) | 0 | **3** | needs 0: **failed** |
| c9: radio conflict (item 4) | 0 | **3** | needs 0: **failed** |
| c9: handover or signal performed again (item 1) | 12 | 12 | recorded, not a criterion; no worse than C |

- **Preregistered rule: failed** at c4 (H, E), c5 (J, plan exchange, K) and c9 (items 3, 4). U is **not built** (no schema, no knowledge change).
- **What it shows:** first-person wording does remove unquoted third-person self-reference (D gate 0/36 against 2/36 in the
  control), but handing the speaker a ready utterance gets that utterance spoken: at c4 all 12 U replies voice the organizing role
  and the other-sites line (2/12 in C), and the commanded action disappears (medical level 0/12 against 10/12). At c5 the same
  lines intrude into the lemon-cake exchange (4/12 plan exchanges). The grammatical-person defect and the unwanted-speech defect are separate,
  and fixing the first through speakable text worsens the second, as the plan warned.
- Caveats: one frozen state per endpoint, replies near-deterministic (few sentence paths), the control's c5 J (2/12) differs from
  Amendment 20's 12/12 (today's attribution style; unattributed quotes were scored not-clear as in Amendment 20), so J is
  not a clean U-vs-C signal. The D result stands on its own.
- **Contract status:** the speaker-voice requirement (D) is still unmet in production. Not made acceptable.
- **Spend to date:** 240 requests, ~888 neurons (estimates at 3.7 per request; A–C 168 within the 756 ceiling, U 72 within 324).

## Experiment G: narrated-prerequisite gate, then the shared first-person sentence, at c4, c5, c9 (plan D; written 2026-11-07 BEFORE any request; nothing billed yet)

Plan: [the plan, "Overlap with the 3A plan and agreed path"](shared-narrator-instruction-conflicts-plan.md). Brandon's approval
(2026-11-07): "three arm approval" in answer to the stated cost (108 requests, about 400 neurons).

- **Question:** (1) Does offering a sibling realization as speech only after its event was narrated (the gate, built and applied uncommitted
  in the working tree) reduce bookkeeping recital and unrequested speech without harm? (2) On top of the gate, does one shared
  sentence make Michelle and the official stop saying unquoted third-person self-reference about themselves, without worse recital,
  premature answers or malformed replies? The SCENE-only line stays (removing it raised recital, Result A).
- **Arms (12 samples each, same model and settings, kept P state; each arm adds exactly one change to the one before):**
  - **C0** = gate off (`knowledge.is_narrated` forced true in the capture only). Asserted byte-equal, system and user, to the saved
    Amendment 20 control `bench/results/richer-3a-probe/speech/frozen-C.json` (sha256 prefix `08f0adfbd5ec`).
  - **G** = gate on, the real working-tree code (prefix `412eefbd6b4d`). Asserted: system, `max_tokens`, `response_format`, command and
    committed facts identical to C0; the user text differs only by deleted speaker lines (G is a subsequence of C0; every removed line is a
    `may say this aloud:` line; SCENE and THINGS untouched). Lines C0 to G: c4 6 to 3, c5 9 to 6, c9 24 to 15. Removed: exactly the
    never-narrated siblings (`k_sl_3a_a_r2`, `k_sl_3a_d_r2`, `k_sl_3a_c_r2`), offered to all three speakers. User chars 2,874 to 2,462 (c4),
    3,269 to 2,857 (c5), 6,570 to 4,944 (c9).
  - **GF** = G plus one sentence in the SYSTEM message, inserted directly after `Do not copy sentences from the SCENE section.`:
    `When a person speaks about themselves, use first person. Keep another person's words unchanged when quoting them.`
    (prefix `c85535728980`). Asserted: removing the inserted sentence returns G exactly; user text identical to G. System chars 2,527 to
    2,641. Placement beside the copy rule is the only placement tested; a placement in CONSTRAINTS next to the speaker lines is untested.
  - Capture: `scripts/ringer/shared-narrator/g_capture.py`; frozen files and `capture-report.json` in `bench/results/shared-narrator/g/`.
- **Replay:** `g_replay.py`; 3 arms x 3 endpoints x 12 samples = **108 requests**, interleaved sample-major (sample, endpoint, arm), no retries
  or replacements, every error kept as a row, no matcher, judge or capture calls, request cap asserted at 108, refuses without `--confirm`.
  Model request only; no engine cues or deliveries. **Smoke first:** sample 1 (9 requests) runs alone as a Ringer probe task and is
  checked for transport and strict JSON only; it is kept as sample 1 of the 12, never replaced. Then samples 2-4, 5-8, 9-12 as three tasks.
  **Estimate about 400 neurons at 3.7 per request; ceiling 486 neurons (4.5 per request).** Spend to date 240 requests (~888 neurons);
  this run takes it to 348 requests.
- **Rubric (every reply read from a shuffled sheet with arm labels removed; the model's text is scored, not any appended delivery):**
  - c4 and c5: items A to K of Amendment 19. H = a third-person statement of the reunion, the organizing role or the other-sites fact
    spoken aloud by anyone, verbatim or lightly paraphrased. J = the lemon-cake question asked clearly and attributed (an unattributed
    quote is scored not clear, as in Amendments 20 and U). K = invented earlier conversation or premature answer.
  - c9: items 1 to 6 of Amendment 20 (1 handover or signal performed again; 2 signal or authorization voiced as dialogue; 3 answers
    "Lead the prisoners upward toward the command levels."; 4 radio conflict or self-custody; 5 not strict JSON; 6 other).
  - **D gate, every endpoint and arm:** count each reply in which Michelle or the official says an unquoted third-person sentence about
    themselves (“Michelle has explained…”, “Michelle coordinates…”, “The framed official proves…”). Record speaker, sentence and whether a
    genuine attributed quotation is present. Third-person references to other people and “you” to Kristin are not violations; silence where
    an answer is required is not a pass. **New item F1 (first-person misuse, GF only matters):** a speaker uses “I” or “we” for an act or
    membership the speaker does not have, or a quotation of another person's words is rewritten into the speaker's first person.
    Violations produced by the two statements about the radio handover (`k_sl_3a_c_r1`, `c_r2` content) are counted on a separate line:
    they overlap the c9 replay (O4) and are scored for D but reported separately.
- **Win rules (per endpoint, no averaging, all required):**
  - **G over C0:** c4: H at most 1/12 and at least 4 fewer than C0 if C0 shows 4+/12, else “control did not reproduce”; A, B, C, D, E, F 0/12.
    c5: J at least 10/12 and no fewer than C0; K 0/12; plain plan exchange at most 1/12; A, B, C, E 0/12. c9: items 3 12/12, 4 and 5 0/12;
    item 1 recorded, not a criterion (the gate does not remove the delivered handover statements).
  - **GF over G:** D gate 0/12 at every endpoint (if G shows 0 violations at an endpoint the endpoint reports “control did not reproduce”,
    no causal claim); F1 0/12; and GF no worse than G by more than 2/12 on H, item 1, J, E, item 3 and item 4.
  - Safety, every arm: no premature or private disclosure, no impossible committed state, E (not strict JSON, missing `text`, repeated keys)
    0/12, transport error counts as a failed row.
- **Decisions:** the gate implements Brandon's rule that a character cites an event only after it was narrated, so G is kept unless it is worse
  than C0 by more than 2/12 on H, item 1, J, E, item 3 or item 4 at any endpoint, in which case it is reverted from the working tree
  (`ringer-work/shared-narrator-gate/gate.patch`, reverse) and reported. GF passing: write the sentence into the shared rules through a Ringer
  task, tests first (all narration paths, recovery included), then payload-match to this frozen form. GF failing D or F1: the speaker-voice
  contract stays unmet and third-person self-reference is not made acceptable; the next routes are the 3A plan's `voiceable` step and
  making self-describing statements non-speakable to their own subject (each its own prereg). A c4-only win does not close O4.
- **Not measured:** other scenes and packages, a placement in CONSTRAINTS, live stateful play, recovery, the appended deliveries, the radio
  statements (c9 replay). Twelve correlated replays of one frozen state bound a rate only to about 22% one-sided.

### Experiment G, result (2026-11-07; Ringer runs `shared-narrator-g-smoke` and `shared-narrator-g`, four tasks PASS; rows `bench/results/shared-narrator/g/g-{1-1,2-4,5-8,9-12}-rows.json`, sheet `sheet-G.md`, key `key-G.json`, blind scores `scores-blind.json`, tabulation `scripts/ringer/shared-narrator/g_score.py`, all untracked) — GF MISSED; G MISSED its win rule at every endpoint

108 requests (~400 neurons at 3.7; ceiling 486 not approached), 0 transport errors, no retries or replacements. Sample 1 was the smoke run (kept). All 108
replies were read from the shuffled unlabeled sheet and scored before the key was opened. Mechanical: 3 malformed replies (G #S7 and #S20 at c9, both with an
empty key where `text` belongs; GF #S94 at c4, repeated `Kristin` key and missing closing brace).

| Item (12 samples each) | C0 | G (gate) | GF (gate + sentence) | Win rule |
| --- | ---: | ---: | ---: | --- |
| **c4 D gate: unquoted third-person self-reference (Michelle/official)** | 3 | **0** | 1 | GF needs 0 (G = 0, so GF's control: no causal claim); GF failed |
| c4 H: reunion / organizing / other-sites fact voiced aloud | 3 | 3 | **8** | needs ≤1 and 4 fewer than C0 if C0 ≥4: C0 3, "not reproduced"; G 3 fails ≤1, GF worse |
| c4 the commanded medical level headed for (recorded) | 9 | **1** | 1 | recorded |
| c4 Michelle talks plan or priorities instead (rubric item D) | 0 | **10** | 8 | needs 0: both failed |
| c4 malformed (E) | 0 | 0 | 1 | needs 0: GF failed |
| c5 lemon-cake question asked and attributed (J) | 4 | 4 | 1 | needs ≥10: all failed; control also low (see caveat) |
| c5 Michelle answers or invents a memory inside the lead-up (K) | 0 | **3** | **6** | needs 0 |
| c5 unrelated plan exchange | 0 | 2 | 0 | needs ≤1: G failed |
| c9 handover or signal performed again (item 1) | 12 | 7 | 9 | recorded; G is 5 better than C0 |
| c9 signal / authorization / "uprising is active" voiced as dialogue (item 2) | 8 | 1 | 0 | recorded |
| c9 answers the command (item 3) | 12 | 12 | **9** | needs 12/12: GF failed |
| c9 radio conflict: Michelle holds up the radio Kristin carries (item 4) | 0 | 0 | **5** | needs 0: GF failed |
| c9 malformed (item 5) | 0 | **2** | 0 | needs 0: G failed |

- **Preregistered rule: G failed its win rule** (c4 plan talk 10/12, c5 K 3/12 and plan exchange 2/12, c9 malformed 2/12; the c5 J floor is missed by
  every arm). **The preregistered revert condition is not met** (worse than C0 by more than 2/12 on H, item 1, J, E, item 3 or item 4): E is worse by
  exactly 2 at c9, nothing else is worse. By the letter the gate stays in the working tree, uncommitted; see the flag below.
- **GF failed** and is dropped: it does not reach D 0/12 at c4 (1), and against G it is worse by more than 2/12 on H (8 against 3), J (1 against 4), item 3
  (9 against 12) and item 4 (5 against 0). **The shared first-person sentence made things worse; the sentence is not built.**
- **What the gate does, measured:** at c4 all three verbatim third-person recitals by Michelle ("Michelle coordinates…", "Michelle has explained…",
  "Kristin and Michelle have reunited") are gone (3 to 0). At c9 the handover replay drops from 12/12 to 7/12 and the authorization speech from 8/12 to 1/12,
  the best c9 movement recorded in this study, though still above the 2/12 bar. The facts are still in SCENE (one copy of the other-sites fact remains), so
  G still lets Michelle paraphrase it (H 3/12).
- **What it costs, measured:** at c4 the commanded action disappears (medical level headed for 9/12 to 1/12) and Michelle talks plans in 10/12 replies.
  This is the same flip as in experiments S (9 to 0) and U (10 to 0): at this one frozen c4 state, any change to the speaker-line block moves the reply from
  "Kristin walks to the medical level" to a Michelle conversation. The three results share a control that sits on one dominant sentence path
  (C0 repeats "Kristin walks towards the medical level, her footsteps echoing…" in 9 replies), so c4 may be a fragile endpoint; this is unproven.
  At c5 Michelle answers inside the lead-up in 3/12 (an engine-appended answer follows in play, so this would duplicate it) and one reply invents
  "You mentioned it earlier."
- **Caveats:** one frozen state per endpoint; replies fall into a handful of near-identical paths; J is scored strictly (an unattributed quote is
  "not clear", as in Amendment 20 and U), so the control scores 4/12 today against 12/12 in Amendment 20 and J cannot separate the arms. The D result at c4
  (3 to 0 to 1) is 3 replies in one arm. F1 (first-person misuse) was checked and not seen in GF. No claim about live play.
- **Contract status:** the speaker-voice requirement (D) is still unmet in production. Not made acceptable.
- **Spend to date:** 348 requests (~1,288 neurons at 3.7 per request; this experiment 108 within its 486 ceiling).

## Experiment GU: narrated gate + speaker lines written in first person in advance, at c4, c5, c9 (plan D; written 2026-11-07 BEFORE any request; nothing billed yet)

Plan: [the plan, "Brandon's direction"](shared-narrator-instruction-conflicts-plan.md). Brandon's approvals (2026-11-07): “I don't want a prompt for the first-person sentence; I want
it written that way in advance”; the reworded lines (his own wording for the organizing line: “making announcements in secret over our stolen radios”, kept as “organizing
everyone with secret announcements over our stolen radios” after his question about its meaning); “1. yes [wording and stage 1]; 2. leave it out [no “Shelly” in the
embrace]”. Stage 2 (the embrace delivery text) is NOT in this prereg.

- **Question:** with the narrated gate on and no added prompt sentence, if the speaker lines Michelle, Brandon and the official are offered are written per speaker (Michelle in first
  person about herself; others in third person about her, as “Dr. McGehee”), do the unquoted third-person self-references stay at zero without the unwanted speech, command
  loss and replay that experiments S, U and G showed?
- **Arm GU (12 samples per endpoint):** the experiment G gate payloads (`frozen-G.json`, prefix `412eefbd6b4d`) with only the speaker-line text replaced (`gu_capture.py`, `frozen-GU.json`
  prefix `9e2e1618eb0f`). Asserted: system, settings, command, committed facts and every non-speaker-line byte identical; line count and order unchanged; replaced lines c4 3, c5 6,
  c9 12 (the three “The uprising is active…” lines stay, they have no self-reference). User chars G to GU: c4 2,462 to 2,366; c5 2,857 to 2,769; c9 4,944 to 4,769. Exact lines are
  in the plan's table (organizing, medical level, radio handover, authorization).
- **Comparators:** the same-day experiment G rows C0 (gate off) and G (gate on), already collected; GU is **not interleaved** with them (same frozen prompts, same day, hours apart),
  which weakens the comparison and is stated here. No new control rows are bought.
- **Replay:** `gu_replay.py`; 1 endpoint-arm x 3 endpoints x 12 = **36 requests**, no retries or replacements, every error kept, no matcher, judge or capture calls, request cap asserted at
  36, refuses without `--confirm`. Smoke first: sample 1 (3 requests) as its own Ringer task, checked for transport and strict JSON only, kept as sample 1. Then samples 2-4, 5-8, 9-12.
  **Estimate about 133 neurons at 3.7 per request; ceiling 162 (4.5 per request).** Spend to date 348 requests (~1,290 neurons); this brings it to 384.
- **Rubric (all 36 replies read from a shuffled sheet; one arm, so blinding is only to sample id):** the experiment G items unchanged: c4 I (command), H (reunion, organizing, other-sites
  fact voiced), D-gate (unquoted third-person self-reference by Michelle or the official), P (plans instead), E (malformed); c5 J (strict), K (premature answer or invented memory), plan
  exchange; c9 items 1 to 5. **New item R:** a speaker voices one of the authored lines near-verbatim (recorded, because experiment U showed handed-over utterances get spoken). **F1:**
  first-person misuse (an “I” or “we” for an act or membership the speaker does not have, or a quotation rewritten into the speaker's first person).
- **Win (all required, per endpoint, no averaging):** D-gate 0/12; F1 0/12; and GU no worse than G by more than 2/12 on H, item 1, J, K, E, item 3 and item 4. Reported, not gating: R, and
  the c4 command (I) against C0 (9/12) and G (1/12). If the c4 command loss persists (I below 6/12), that goes to Brandon as an open decision, not a pass.
- **Decisions:** pass: schema `speaker_text` (optional, per speaker, absent map keeps the old rendering only where the old line has no self-reference), tests first through Ringer, payload match
  to this frozen GU, then stage 2. Fail on D-gate or F1: the speaker contract stays unmet; next routes are `voiceable: false` on completed handover statements and non-speakable
  self-describing statements. Fail only on the “no worse than G” rule: report per endpoint to Brandon.
- **Not measured:** the embrace delivery text (stage 2), other scenes and packages, recovery, live stateful play, the appended deliveries. Twelve correlated replays of one frozen state bound a rate only to about 22% one-sided.

### Experiment GU, result (2026-11-07; Ringer runs `shared-narrator-gu-smoke` and `shared-narrator-gu`, four tasks PASS; rows `bench/results/shared-narrator/g/gu-{1-1,2-4,5-8,9-12}-rows.json`, sheet `sheet-GU.md`, key `key-GU.json`, scores `scores-gu-blind.json`, tabulation `scripts/ringer/shared-narrator/gu_score.py`, untracked) — written win rule MET; not a pass, because its own open-decision clause fires

36 requests (~133 neurons; ceiling 162 not approached), 0 transport errors, no retries or replacements; sample 1 was the smoke run (kept). All 36 replies read from the shuffled sheet and
scored before the key was opened (one arm, so only the sample id is blind). Mechanical: 1 malformed reply (c4 #S21: the segment keys are the spoken sentences, `text` missing). Comparators are the
same-day experiment G rows (not interleaved).

| Item (12 samples each) | C0 (gate off) | G (gate) | **GU** | Rule |
| --- | ---: | ---: | ---: | --- |
| c4 D-gate: unquoted third-person self-reference (Michelle/official) | 3 | 0 | **0** | needs 0: met |
| c5 and c9 D-gate | 0 / 0 | 0 / 0 | **0 / 0** | needs 0: met |
| F1 first-person misuse (all endpoints) | n/a | n/a | **0** | needs 0: met |
| c4 H: third-person recital voiced | 3 | 3 | 2 | no worse than G by >2: met |
| c4 **R: Michelle voices the authored organizing line, almost word for word** | n/a | n/a | **10** | reported |
| c4 the commanded medical level headed for | 9 | 1 | **0** | open-decision clause: I below 6/12 |
| c4 Michelle talks plans instead (P) | 0 | 10 | 2 | |
| c4 malformed (E) | 0 | 0 | 1 | no worse than G by >2: met |
| c5 lemon-cake question asked and attributed (J, strict) | 4 | 4 | 2 | no worse than G by >2: met (exactly 2 lower) |
| c5 premature answer or invented memory (K) | 0 | 3 | **0** | met |
| c5 unrelated plan exchange | 0 | 2 | 3 | recorded |
| c9 handover or signal performed again (item 1) | 12 | 7 | **5** | met; best value so far, above the 2/12 bar |
| c9 signal, authorization or “we have the checkpoints” voiced as dialogue (item 2) | 8 | 1 | 5 | recorded |
| c9 answers the command (item 3) | 12 | 12 | 12 | met |
| c9 radio custody conflict (item 4; Michelle “holds up” the radio) | 0 | 0 | 0 | met (5 replies have Michelle “shout through the radio”, scored as borderline, not item 4) |
| c9 malformed (item 5) | 0 | 2 | 0 | met |
| c9 **R: authored radio line voiced near-verbatim** (“we have the checkpoints and are fighting our way up toward the command and broadcast levels”) | n/a | n/a | **5** | reported |

- **Written win rule: met at every endpoint** (D-gate 0/36, F1 0/36, nothing worse than G by more than 2/12). **The prereg's own clause fires:** the c4 command is 0/12 (C0 9/12, G 1/12), so this
  goes to Brandon as an open decision, not a pass.
- **Grammatical person: fixed in this frozen sample.** Michelle says “I've been organizing everyone with secret announcements over our stolen radios” in 10 of 12 c4 replies, never a
  third-person sentence about herself; Brandon and the official, when they speak (one malformed c4 reply), say “Dr. McGehee's been…” (third person about another person, allowed).
- **Unwanted speech is not fixed:** the plan's D section says converting a recital to “I” does not remove the recital. At c4 the same authored sentence replaces the commanded step in 10 of 12 replies
  (experiment U saw 12/12 with the sibling line also present), and at c9 five replies have Michelle shout the authored handover result through the radio and signal again.
  Note that in play, `Enter the medical level.` selects a handoff and the game appends the medical-level delivery, so a lead-up that does not itself enter the level is allowed (plan, step 0); the
  lead-up must still avoid a substitute conversation, and a repeated stock sentence is that.
- **c5:** premature answers 0/12 (G 3/12). The question is asked clearly in only 2/12 (strict scoring; three replies are a truncated unfinished quote, “Michelle, I need to know something,”) and 3 replies
  switch to “What's the plan to free these people?”.
- **Caveats:** one frozen state per endpoint; replies fall into a handful of near-identical paths (the c4 organizing sentence appears in 10 replies with trivial variation); the comparison with C0 and G is
  same-day but not interleaved; the delivery text and the embrace are not in this probe (stage 2); no live play.
- **Spend to date:** 384 requests (~1,420 neurons at 3.7 per request; this experiment 36, within its 162 ceiling).

## Experiment GU2: the gate + speaker lines rewritten so a speaker never retells Kristin her own action, at c4, c5, c9 (plan D; written 2026-11-07 BEFORE any request; nothing billed yet)

Plan: [the plan, "Rewrite rule and full wording for all nine entries"](shared-narrator-instruction-conflicts-plan.md). Brandon's approvals (2026-11-07): his objection that “Michelle is telling her something Kristin already knows”
(the `c_r2` and `c_r1` lines), “Yes, rewrite all of them”, and “yes” to the wording and this re-probe. It replaces the GU result for the three built-and-probed entries whose wording changed (`b_r2`, `d_r1`, `c_r1`).
`a_r1` is unchanged. The five newly authored entries (`a_r2`, `b_r1`, `e_r1`, `d_r2`, `c_r2`) are not offered on the scripted rescue path (their siblings are the narrated ones), so this probe cannot
measure them; they are covered by the unit tests that pin their exact strings.

- **Question:** with the gate on and no prompt sentence, if speaker lines say what an event means now rather than retell what Kristin did, do unquoted third-person self-reference, the voiced authored line (R) and the
  c4 command loss improve, without the problems found in S, U, G and GU?
- **Arm GU2 (12 samples per endpoint):** the experiment G gate payloads (`frozen-G.json`, `412eefbd6b4d`) with only the speaker-line text replaced (`gu2_capture.py`, `frozen-GU2.json`, sha256 prefix `8cfd5898baad`). Asserted: system, settings, command,
  committed facts and every non-speaker-line byte identical; line count and order unchanged; replaced lines c4 3, c5 6, c9 12 (the three “The uprising is active…” lines stay). User chars G to GU2: c4 2,462 to 2,366; c5 2,857 to 2,695; c9 4,944 to 4,552.
  Lines: `a_r1` as in GU; `b_r2` “The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.”; `d_r1` “That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new
  authority.”; `c_r1` Michelle “Your signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels.” (Brandon and the official: “The signal worked. …”).
- **Comparators:** the same-day experiment G rows C0 and G, and the GU rows, already collected; GU2 is not interleaved with them (limitation stated; replays drift day to day and these were all run on 2026-11-07).
- **Replay:** `gu2_replay.py`; 3 endpoints x 12 = **36 requests**, no retries or replacements, every error kept, no matcher, judge or capture calls, cap asserted at 36, refuses without `--confirm`. Smoke first (sample 1, 3 requests, kept), then
  samples 2-4, 5-8, 9-12. **Estimate about 133 neurons at 3.7 per request; ceiling 162 (4.5 per request).** Spend to date 384 requests (~1,420 neurons); this brings it to 420.
- **Rubric (36 replies read from a shuffled sheet; one arm):** the experiment GU items unchanged: c4 I, H, D-gate, P, E, R (a speaker voices an authored line near-verbatim); c5 J (strict), K, plan exchange; c9 items 1 to 5, R, borderline B (Michelle “shouts through the radio”); F1 (first-person misuse).
  New item **T:** the voiced line retells to Kristin something she just did or already knows (Brandon's objection), recorded.
- **Win (all required, per endpoint, no averaging):** D-gate 0/12; F1 0/12; GU2 no worse than G by more than 2/12 on H, item 1, J, K, E, item 3 and item 4. Reported against GU and C0, not gating: R, T, and the c4 command (I; C0 9/12, G 1/12, GU 0/12).
  If R at c4 is again 10 or more of 12 or the c4 command stays below 6/12, that goes to Brandon as an open decision, not a pass.
- **Decisions:** pass or open decision: Brandon chooses between going to live-play qualification and the embrace text (stage 2), or fixing the repeat first (`voiceable: false`, or offering a line only when the command concerns it). Fail on D-gate or F1: the speaker contract stays unmet.
- **Not measured:** the five newly authored entries in play, the embrace delivery text, other scenes and packages, recovery, live stateful play. Twelve correlated replays of one frozen state bound a rate only to about 22% one-sided.

### Experiment GU2, result (2026-11-07; Ringer runs `shared-narrator-gu2-smoke` and `shared-narrator-gu2`, four tasks PASS; rows `bench/results/shared-narrator/g/gu2-{1-1,2-4,5-8,9-12}-rows.json`, sheet `sheet-GU2.md`, key `key-GU2.json`, scores `scores-gu2-blind.json`, tabulation `scripts/ringer/shared-narrator/gu2_score.py`, untracked) — written win rule MET; both open-decision clauses fire

36 requests (~133 neurons; ceiling 162 not approached), 0 transport errors, no retries or replacements; sample 1 was the smoke run (kept). All 36 replies read from the shuffled sheet and scored before the key was opened
(one arm). Mechanical: 4 malformed replies (c4 #S14; c9 #S11, #S30, #S33, all with runaway repeated `item_facts` keys). Before the probe the nine-entry wording was built through Ringer (`shared-narrator-speaker-text-2`, PASS first attempt) and the
engine's real payloads matched `frozen-GU2.json` at c4, c5 and c9.

| Item (12 samples each) | C0 | G | GU | **GU2** | Rule |
| --- | ---: | ---: | ---: | ---: | --- |
| D-gate: unquoted third-person self-reference (c4 / c5 / c9) | 3 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | **0 / 0 / 0** | needs 0: met |
| F1 first-person misuse | n/a | n/a | 0 | **0** | needs 0: met |
| T a voiced line retells Kristin's own action | n/a | n/a | n/a | **0** | reported |
| c4 H third-person recital voiced | 3 | 3 | 2 | **1** | no worse than G by >2: met |
| c4 R the authored organizing line voiced almost word for word | n/a | n/a | 10 | **12** | reported (clause: 10 or more of 12) |
| c4 the commanded medical level headed for | 9 | 1 | 0 | **0** | reported (clause: below 6/12) |
| c4 Michelle talks plans instead (P) | 0 | 10 | 2 | 1 | |
| c4 malformed | 0 | 0 | 1 | 1 | met |
| c5 lemon-cake question asked and attributed (J, strict) | 4 | 4 | 2 | **5** | met |
| c5 premature answer or invented memory (K) | 0 | 3 | 0 | **0** | met |
| c5 unrelated plan exchange (P) / recital (H) | 0 / 0 | 2 / 1 | 3 / 0 | 4 / 3 | recorded (the plan talk repeats “we can't do it without exposing the other sites”) |
| c9 handover or signal performed again (item 1) | 12 | 7 | 5 | **0** | met; first value inside the 2/12 bar |
| c9 the unchanged “The uprising is active…” line voiced (item 2) | 8 | 1 | 5 | **12** | recorded; authorization line voiced 1 |
| c9 authored radio line voiced (R) | n/a | n/a | 5 | **0** | reported |
| c9 answers the command (item 3) | 12 | 12 | 12 | **10** | no worse than G by >2: met (exactly 2 lower); #S17 and #S32 do not lead the prisoners |
| c9 radio custody conflict (item 4) | 0 | 0 | 0 | 0 | met |
| c9 malformed (item 5) | 0 | 2 | 0 | **3** | no worse than G by >2: met (1 higher) |

- **Written win rule: met at every endpoint.** **Both open-decision clauses fire** (c4 R is 12/12, c4 command 0/12), so this goes to Brandon as an open decision, not a pass.
- **What the rewrite fixed:** the handover replay is gone (0/12; control 12/12), no authored radio line is voiced, no speaker retells Kristin's action (T 0/12), premature c5 answers are 0/12, and the third-person self-reference defect is 0/36.
- **What it did not:** at c4 every reply (12/12) has Michelle say the one first-person line she is offered, “I've been organizing everyone with secret announcements over our stolen radios,” and none heads for the medical level. After the gate that is the only statement offered at c4, so
  hypothesis (untested): the narrator voices whatever single line it is given. At c9 the unchanged canonical “The uprising is active…” line is now voiced in all 12 replies (a current-state sentence about the uprising, not a recital of Kristin's action). In play `Enter the medical level.` selects a
  handoff and the game appends the medical-level delivery after this lead-up, so a lead-up that says her organizing line and then the delivery may compose acceptably; that composition was not measured.
- **Safety note:** 4 of 36 replies are malformed with runaway repeated `item_facts` keys (3 of 12 at c9); the preregistered rule tolerates +2 against G, but 3/12 is not clean and the recovery path was not exercised.
- **Caveats:** one frozen state per endpoint, near-identical reply paths (the c4 and c9 replies are almost the same text across samples), comparison with earlier arms same-day but not interleaved, the five newly authored entries and the embrace text not exercised, no live play.
- **Spend to date:** 420 requests (~1,554 neurons at 3.7 per request; this experiment 36, within its 162 ceiling).

## Experiment GUE1: the embrace delivery text on the reunion turn (stage 2, corrected; written 2026-11-07 BEFORE any request; nothing billed yet)

Plan: [the plan](shared-narrator-instruction-conflicts-plan.md). Brandon (2026-11-07): the emotional reunion with an embrace, “leave it out” for “Shelly”, and “go with 1” (continue to the embrace and live play).

- **Correction to the plan's stage 2:** the scripted history never carries a delivery's text (the narrator's EARLIER IN THE STORY holds authored summaries only), so the c4, c5 and c9 payloads are **byte-identical** with or without the embrace (`gue_capture.py`: GU2 and GUE both
  `8cfd5898baad`). Probing them would measure nothing. The embrace reaches the model only on the reunion turn itself, where CONSTRAINTS say “Right after your story, the game will add this: <delivery>” and “Write only what leads up to it. Do not have Kristin find anything else.” That is the endpoint.
- **Story change under test** (applied in the working tree through Ringer `shared-narrator-embrace`, uncommitted; Ringer's FAIL was only `ruff format` on two test files, which I formatted; 377 tests passed): `k_sl_3a_a_r1` and `k_sl_3a_a_r2` `delivery_text` and the `michelle_reached` handoff `fallback_text` now contain the embrace and Michelle's “You're here… You're really here.”; `cue_text` unchanged.
- **Endpoints (frozen, 3A entry state, no prefix):** **R1** `Free the captives.` (selects `k_sl_3a_a_r1`); **R2** `Ask Michelle about the other sites.` (selects `k_sl_3a_a_r2`, the second-realization path).
- **Arms (12 samples per endpoint):** **OLD** = the real engine payload with exactly one line swapped back to the previous delivery text (`frozen-GUE1-OLD.json`, `239dbfd01661`); **EMB** = the real engine payload (`frozen-GUE1-EMB.json`, `221f59c6b678`). Asserted by `gue1_capture.py`: identical system and settings, exactly one differing line
  (the delivery line); user chars OLD/EMB R1 1,873/2,048 and R2 1,739/1,911. Everything else is the current tree: gate on, authored speaker lines.
- **Replay:** `gue1_replay.py`; 2 endpoints x 2 arms x 12 = **48 requests**, interleaved (sample, endpoint, arm), no retries or replacements, every error kept, no matcher, judge or capture calls, cap asserted at 48, refuses without `--confirm`. Smoke first (sample 1, 4 requests, kept), then 2-4, 5-8, 9-12.
  **Estimate about 178 neurons at 3.7 per request; ceiling 216 (4.5 per request).** Spend to date 420 requests (~1,554 neurons); this brings it to 468. (This is 12 more requests and about 45 more neurons than the 36-request stage 2 first stated, because the endpoints changed.)
- **Rubric (all 48 replies read from a shuffled sheet, arm labels removed; the model's lead-up is scored, then the composed turn = lead-up + the exact delivery the game appends):** **PRE** the lead-up already performs the embrace or the reunion moment (a hug, Michelle's greeting or “You're here”, tears, an emotional exchange) so the appended text repeats it;
  **DUP** the lead-up restates the appended content (the dose, being awake, pointing to the medical level, the records); **EXTRA** it finds, reveals or does anything beyond walking up to her, or has Michelle speak words (“Do not have Kristin find anything else”); **CONTRA** it contradicts the appended text (for example Michelle absent, ignoring Kristin, or the reunion already over);
  **MAL** malformed JSON or missing segment text. **COMP** the composed turn reads as one coherent beat. Descriptive: word count.
- **Win (EMB, all required, per endpoint, no averaging):** PRE at most 1/12; EXTRA at most 1/12; CONTRA 0/12; MAL 0/12; COMP at least 11/12; and EMB no worse than OLD by more than 2/12 on PRE, DUP and EXTRA. If OLD shows PRE below 2/12 the cause is “not reproduced” (this is a safety check, not a cure hunt).
- **Decisions:** pass: the embrace text stays (it is already applied); then the live stateful study. Fail on PRE, EXTRA or CONTRA: report to Brandon with the rows; options are a prompt-free rewording of the delivery (a lead-up-proof opening), not a new prompt rule. A fail does not touch the speaker-line work.
- **Not measured:** the speaker lines on this turn, c1 follow-ups, other handoffs, recovery, live stateful play. Twelve correlated replays of one frozen state bound a rate only to about 22% one-sided.

### Experiment GUE1, result (2026-11-07; Ringer runs `shared-narrator-gue1-smoke` and `shared-narrator-gue1`, four tasks PASS; rows `bench/results/shared-narrator/g/gue1-{1-1,2-4,5-8,9-12}-rows.json`, sheet `sheet-GUE1.md`, key `key-GUE1.json`, scores `scores-gue1-blind.json`, tabulation `scripts/ringer/shared-narrator/gue1_score.py`, untracked) — written win rule MET at R2, MISSED at R1 on EXTRA only

48 requests (~178 neurons; ceiling 216 not approached), 0 transport errors, 0 malformed, no retries or replacements; sample 1 was the smoke run (kept). All 48 replies read from the shuffled sheet and scored before the key was opened (arm labels removed).

| Item (12 samples each) | R1 OLD | R1 EMB | R2 OLD | R2 EMB | Rule for EMB |
| --- | ---: | ---: | ---: | ---: | --- |
| PRE: lead-up already performs the embrace or reunion moment | 0 | 1 (#S35: “they just stare at each other”) | 0 | 0 | at most 1/12: met |
| DUP: lead-up restates the appended content | 0 | 0 | 8 | **0** | met |
| EXTRA: another character speaks, or an unrequested act or find | 0 | **4** (Brandon speaks in #S1, #S2, #S31, #S45) | 12 (Michelle gives her answer) | **0** | at most 1/12 and no worse than OLD by >2: **R1 missed** (4 against 0), R2 met |
| CONTRA: contradicts the appended text | 0 | 0 | 4 | 0 | 0/12: met |
| MAL malformed | 0 | 0 | 0 | 0 | met |
| Composed turn incoherent (Michelle's answer in the lead-up, then the appended answer) | 0 | 0 | **12** | **0** | at least 11/12 coherent: met |
| DIV: the lead-up goes to someone other than Michelle (recorded) | 11 | 7 | 0 | 0 | recorded |

- **Written win rule: met at R2, missed at R1** on EXTRA alone (4/12 against 0/12 for the old text): the four are Brandon, who is already with Kristin at the entry, speaking before the appended reunion (“we have to move, now”, and in #S45 “Kristin, I'm glad you're here”). PRE is 1/12 and the composed turn is coherent in all 24 R1 replies.
- **Unexpected, large effect at R2:** with the old second-reunion text, all 12 lead-ups had Michelle give the answer herself before the game appended the same explanation (8 restated it, 4 contradicted it with “focus on freeing these people first”); with the embrace text none did (0/12). Hypothesis (untested): the old text opened with the explanation, which the narrator pre-empted; the new text opens with an action.
- **Existing weakness, both arms:** in 7/12 (EMB) and 11/12 (OLD) R1 replies the lead-up goes to Brandon rather than toward Michelle; the embrace did not cause it.
- **Caveats:** one frozen state per endpoint, near-identical reply paths, small counts (4 against 0), the composed turn read here from the lead-up plus the delivery text (the game's real composition and cue were not run), no live play.
- **Spend to date:** 468 requests (~1,732 neurons at 3.7 per request; this experiment 48, within its 216 ceiling).

## Experiment L: live stateful 3A journeys, shipped state against the final state (DRAFT for Brandon's approval; written 2026-11-07 BEFORE any request; nothing billed, nothing built)

Plan: [the plan](shared-narrator-instruction-conflicts-plan.md), "Adoption and closure". This is the qualification the frozen probes cannot give: real stateful play, the engine composing the lead-up with the appended delivery, the real matcher and handoff selection, and recovery
if it happens. It is a source screen, not hosted validation (`docs/testing-runbook/live-narration-bench.md`).

- **Question:** does the final working-tree state (presence line, narrated gate, nine authored speaker lines, embrace text) play the nine-command 3A script at least as well as the shipped state, with the speaker-voice contract met in the composed text?
- **Arms.** **CONTROL** = the shipped commit \`5fc12e79\` (current \`HEAD\`) in a clean git worktree (\`.venv\` symlinked, the variation file copied in). **FINAL** = this working tree, including every uncommitted change. Same variation file, script, model and settings in both. The comparison qualifies the combination
  against what ships; it does not attribute an effect to any single change.
- **Variation.** A new \`bench/variations/richer-3a-live.json\` derived from \`richer-3a-loc-P.json\` (same entry facts, \`fixed_turns: 9\`, \`runtime: true\`, \`single_call\`, both judges off) carrying two scripts: **A** \`richer-3a-detention\` (the existing nine commands, reunion first) and **B** \`richer-3a-a2-first\` (the same eight later commands with \`Ask Michelle about the other sites.\` replacing \`Free the captives.\` as command 1,
  so the second-realization reunion path plays). The script text is frozen before any run; no command is edited between arms.
- **Design.** Replicates run one at a time as paired Ringer probe tasks (\`--replicates 1\`, separate output directories), CONTROL and FINAL concurrently so day-to-day drift hits both; the placeholder-worker plus check pattern used for the earlier replays (the check runs \`python -m bench run ... --replicates 1 --confirm\` from the matching tree).
  **Four pairs per path.** The first pair is the smoke (kept as replicate 1; both runs are inspected for completion, JSON validity and request counts before the other three pairs are launched). No retries, no replacement replicates, failed replicates and every turn kept (\`all-turn-records.json\`).
- **Stages and cost.** Each run is the opening plus nine commands, **10 narration turns**. **Path A stage: 2 arms x 4 replicates x 10 = 80 narration turns.** Estimate **about 300 neurons** at the 3.7 per request measured on same-size 3A payloads in this study (the bench's own projection is 11 neurons per planned turn: **880**, which is the approval ceiling for the stage).
  **Path B stage: another 80 turns, the same estimate and ceiling, run only after Path A's report and a separate go-ahead.** The matcher, recovery and any retry calls are not in the bench's narration count: the smoke records \`summary.json\` (\`narration_requests\`, \`narration_http_prompts\`) so the real count is stated before the remaining pairs.
  Both judges are off, so there are no judge calls. Spend to date 468 requests (~1,732 neurons); Path A adds about 80 narration requests (more with recovery). The bench's own guard fires above 500 projected neurons per invocation; each task runs 110 projected, so the guard is passed with \`--confirm\`. A 429 \`AI_QUOTA_EXCEEDED\` or \`AI_DAILY_BUDGET_EXCEEDED\` stops the run until 00:00 UTC and is kept as a failed replicate.
- **Scoring.** Every composed turn of every run is read in full (lead-up plus the exact appended delivery), from a shuffled sheet with arm labels removed; the per-turn selected-knowledge ids and handoff telemetry are read from the turn records. Hard gates (a hit anywhere is recorded, never averaged):
  **H1** a required handoff delivered zero or more than one time, or a wrong id for a command (expected sequence on path A: \`k_sl_3a_a_r1\`, \`f_r1\`, \`g_r1\`, \`b_r2\`, \`h_r1\`, \`d_r1\`, \`i_r1\`, \`c_r1\`, then an ordinary turn; path B starts with \`a_r2\`);
  **H2** an unquoted third-person self-reference by Michelle, the official or Brandon, in generated text or in appended dialogue (speaker, exact sentence, quotation or not);
  **H3** premature or private disclosure, an impossible committed state, a lost custody or identity (the radio is Kristin's after the handover and Michelle does not hold it up again);
  **H4** a failed replicate, malformed or empty reply, or an unrecovered transport error (recoveries that succeed are counted separately);
  **H5** the completed handover or signal performed again at turn 9 (open issue O4);
  **H6** the reunion re-performed after the earned turn (embrace, greeting, “You're here”) or, in CONTROL, the shipped equivalent;
  **H7** the opening greets or reunites instead of identifying Michelle working nearby.
  Soft counts, compared per path across the four pairs: voiced stock lines (an authored speaker line repeated word for word), plan talk instead of the command, lead-ups that go to Brandon rather than the player's target, invented but harmless detail, and per-turn word count.
- **Decision rule (engineering screen, not significance).** FINAL passes a path only if it has zero H1 to H4 hits in all four replicates and zero H6 and H7 hits, and its H5 count is no higher than CONTROL's; soft counts are reported, and a FINAL soft count more than 2 higher than CONTROL's over four replicates is flagged to Brandon. A CONTROL hard-gate hit
  that FINAL does not show is reported as an improvement, not as proof. If FINAL fails a hard gate that CONTROL passes, that change is reported with the rows and the likely cause, and nothing is rerun until green. A pass supports merge review with these stated limits; it does not establish a production rate.
- **Not measured:** scene exit (the script is nine fixed turns; the 80% earned-exit bar needs longer runs), other scenes and the openings the presence change touches (1B, 2A, 2B, 2C; the 3A plan's own check), recovery unless it happens, the hosted deployment, alternate histories beyond paths A and B (2C transmit or alarm), the speaker lines of entries off the two paths. Four replicates bound a rate only crudely.

### Experiment L, Path A: approved and built (2026-11-07; Brandon: “yes to path a”)

Approved: Path A only (2 arms x 4 replicates x 10 narration turns = 80), ceiling 880 neurons (the bench's projection at 11 per turn); Path B needs a separate go-ahead. Frozen artifacts: variation \`bench/variations/richer-3a-live.json\` (variation hash prefix \`0761a1cf8590\`, scripts \`richer-3a-detention\` and \`richer-3a-a2-first\`; only the first runs);
CONTROL = clean worktree \`~/dev/ringer-work/shared-narrator-control-tree\` at \`5fc12e79\` (package hash prefix \`c15328dde980\`), FINAL = this working tree (package hash prefix \`86aa483b8182\`). Manifests \`live-smoke-manifest.json\` (pair 1, the smoke, kept as replicate 1) and \`live-manifest.json\` (pairs 2 to 4), built by \`build_live_manifest.py\`; outputs under \`bench/results/shared-narrator/live/{control,final}-r{1..4}\`.
The check never fails on a failed replicate (it is data); it fails only if the bench wrote no records. After the smoke pair I state the real request count before launching pairs 2 to 4.

### Experiment L, Path A: smoke pair result and corrections (2026-11-07; pair 1 run, pairs 2 to 4 NOT yet launched)

Ringer runs \`shared-narrator-live-smoke\` (both tasks PASS). Records \`bench/results/shared-narrator/live/{control,final}-r1/\`. Both replicates completed (0 failed, 0 rejected turns, 0 recovery requests) and every one of the nine turns has a model-written lead-up plus the exact appended delivery. **Corrections to what this preregistration said:**
- **A judge does run.** The bench makes **one OpenAI judge call per replicate** (its own seven-point scene score; both replicates scored 5/7, which is not one of my gates) and 2 to 3 Cloudflare Jev calls (the matcher). \`continuity_judge: false\` and \`fact_tracking_judge: false\` do not turn that off. The statement “Both judges are off, so there are no judge calls” was wrong. Path A therefore adds 8 OpenAI judge calls (2 already made).
- **The bench's request counter is not usable.** \`narration_requests\` reads 2 per run although all 9 turns carry a model-written lead-up (\`prompt_user\` present on every turn). Costing assumes 9 narration requests per run (72 for Path A, not 80: the opening is authored text, not a model call), unverified against the Cloudflare usage page.
- **Scoring extension, declared before the other pairs run:** the GUE1 items PRE (the lead-up already performs the embrace or reunion moment) and CONTRA (the lead-up contradicts the appended delivery) apply to every handoff turn, not only the reunion; they are reported as hard-gate-adjacent counts and flagged in the decision rule.
- **Smoke observations (replicate 1 only; not a result):** FINAL c1 lead-up already has Michelle pull Kristin into the embrace before the appended embrace (PRE); FINAL c6 lead-up has the official say “You'll never get out of here…” before the appended text has him give the authority (CONTRA); FINAL c4 lead-up has Michelle voice the organizing line; CONTROL c9 repeats the radio handover and the authorization speech (O4) while FINAL c9 does not.
