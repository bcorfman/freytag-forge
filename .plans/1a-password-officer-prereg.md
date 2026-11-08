# Preregistration: scene 1A password and officer, source screens

Written 2026-11-08 BEFORE any billed request. Nothing billed. Plan: [1a-password-and-officer-plan.md](1a-password-and-officer-plan.md) (probe matrix).
**Status: Stage 0 (free freeze) done and re-frozen against the retimed 1A clock (2026-11-08). Awaiting Brandon's approval of the spend below before any request is sent.**

Baseline: HEAD `25f9b75e`, dirty tree retained (listed in `bench/results/1a-password-officer/provenance.json`, git-ignored, with package, variation and frozen-file hashes).
Freeze scripts: `scripts/ringer/1a-password-officer/{capture,replay}.py`; independent check `validate_freeze.py` (prints `1A FREEZE VALIDATION OK` only if every arm differs from its control by exactly the planned bytes). Frozen via Ringer task `1a-password-officer-prepare` (PASS).

These are **reconstructed** requests: canonical imperative commands through the real engine path (prefix turns use the harness stub reply, so no preceding narration reaches the prompt, as in the original). They are not captured production requests. The raw lowercase/vocative transcript is kept only as the `raw` stage.

## Comparisons (each independent; control = the unchanged frozen payload; system text, max_tokens and wire fields byte-identical in every arm)

| Stage | Endpoint (command) | Arms | Single edit vs control |
| --- | --- | --- | --- |
| officer | OFF6 `Greet the officer.`; OFF7 `Ask the officer where Dr. McGehee is.` | CTRL, BIO | BIO adds one CHARACTERS line: Officer Reyes's existing `world.yaml` bio (via a `### Officer Reyes` heading in `plot.md`, real loader path) |
| raw | RAW7 `Officer, do you know where Dr. McGehee is?` | BIO (control), ALIAS | ALIAS adds the exact alias `officer` to `patrol_officer`; the validated prompt gains the officer's THINGS line (`federal patrol officer. Place: at Michelle's workstation.`) on top of the bio line |
| walt | WALT `Ask the neighbor what he saw.` (after `Go outside.`) | CTRL, BIO | BIO adds Walt Pruitt's existing bio as one CHARACTERS line |
| password | PW `Type in the password.` (after turn on, unlock) | CTRL, SUB, ADD | SUB deletes the laptop placement line and the laptop mentions in the two ownership-rule lines; ADD inserts `- Michelle's phone showed a password prompt.` directly after the phone placement line (investigator-supplied probe line, **not** an existing fact, and not a licence to ship transcript recall) |

**Timing and re-freeze (2026-11-08).** The 1A clock was retimed after the first freeze (arrive 6, enter 7, leave 10; arrive/enter/leave are `trailing` events, so the narrator sees the world before the event). The arms were re-captured against that clock and the validator passes. Endpoint ids are historical: `OFF6` is command 8 (`Greet the officer.`), `OFF7` is command 9 (`Ask the officer where Dr. McGehee is.`), `RAW7` is command 9 (raw vocative). The filler turns 6 and 7 are neutral (`Turn on the phone.`, `Turn off the phone.`) because looking at the calendar and photograph earns knowledge that is then offered to the officer as a speakable line (see the plan); the original session never did that. In all officer prompts the officer is at `Place: at Michelle's workstation`, consistent with the engine state, so the mixed-state mismatch that motivated the ordering change no longer arises here. The turn-10 collision (question on the departure turn) is not an endpoint here; it would be its own frozen case.

**Alias cell dropped.** After the re-freeze, `raw-ALIAS-RAW7` is byte-identical to `raw-BIO-RAW7` (the officer is present, so the `officer` alias adds nothing to the prompt). Per the rule above, a cell with no prompt difference carries no comparison and is not billed; the alias is not adopted on this evidence (it matters only when the officer is absent). The raw stage therefore has no billed cells.

## Requests and spend

12 scored samples per arm per endpoint, plus one **unscored smoke sample** (sample 0) per cell. No retries, no replacements, errors kept as rows; no matcher, judge or capture calls. Each stage is run and reported before the next is billed, in the order officer, walt, password.

| Stage | Cells | Smoke | Scored | Stage total |
| --- | --- | --- | --- | --- |
| officer | 4 | 4 | 48 | 52 |
| raw | 0 (alias identical to bio, not billed) | 0 | 0 | 0 |
| walt | 2 | 2 | 24 | 26 |
| password | 3 | 3 | 36 | 39 |
| **all** | 9 | 9 | 108 | **117** |

At the historical 3.7 to 4.5 neurons per request (not verified against current billing): **about 430 neurons, ceiling about 530**. The replay refuses without `--confirm`, refuses an existing output file, and refuses samples outside 0 to 12. A 429 quota error stops the stage and is kept as a row; nothing resumes until 00:00 UTC. Smoke rows are read for usability only and never scored or pooled.

## Scoring (single reader, blinded)

Sheets with arm labels removed and order shuffled; key kept apart until scores are written. Every reply read in full, malformed prefixes included; cite sample and quote for every miss. Rows are scored on the **composed** turn (reply plus any delivery text the engine would append, exactly once). Prose is scored, not `item_facts`.

- **officer (OFF6, OFF7):** target failure = a person other than Reyes answers or is substituted (Mrs. Jenkins, Walt, Michelle, an invented neighbor), or Reyes's location or whereabouts claims are unsupported. Relevant action = Reyes responds to the address.
- **raw (RAW7):** same failure, plus whether the bare address reaches Reyes. The alias must not be read as making him physically present.
- **walt (WALT):** target failure = wrong witness identity, an incoherent account, or disclosure beyond the delivered sentence. Relevant action = Walt answers.
- **password (PW):** target failure = the laptop or the drawer is used, an unsolicited file search, or invented successful authentication or a known password. Relevant action = the phone is the target, or a genuine clarification is asked. Record correct target separately from action success.

## Win rule (fixed before any call)

- **Reproduction:** control (CTRL; BIO for raw) needs at least 4/12 targeted misses at that endpoint to claim a causal win; otherwise "not reproduced" and no rerun. A source-completeness repair may still be approved on authoring grounds alone, never called a causal win.
- **Improvement:** candidate at most 1/12 targeted misses and at least 3 fewer than control; relevant action or correct clarification at least 11/12 (silence is a miss).
- **Zero tolerance in the candidate, no worse than control on any safeguard:** wrong-speaker substitution, hidden knowledge leak, invented password knowledge or authentication, contradiction with the appended event, malformed or empty output, transport failure.
- No pooling across endpoints, no gate changes after seeing output, a failed comparison is dropped or re-preregistered rather than rerun until green. Highly similar replies are reported as correlated.

## Ownership

Story text is not applied by this preregistration. The `### Officer Reyes` and `### Walt Pruitt` blocks reuse existing `world.yaml` bios verbatim and the `officer` alias is a story-data edit; the arm packages live only in `bench/results/1a-password-officer/pkg/`. Brandon approves adoption after the results. The timing change and the compatibility-filtered reference design from the plan are not in scope here.

## Not covered

Officer timing (pre-departure action phase), the recency integration cases, the raw wrong-person regression for the other three bio arms, other scenes, hosted staging, other models, and live qualification.

## Result: officer stage (run 2026-11-08, 48 scored requests plus 4 smoke; 0 transport errors; blinded sheet `sheet-officer.txt`, key `key-officer.json`, scores `scores-officer.json`; single reader, Claude, scored before unblinding)

Rows: `bench/results/1a-password-officer/run-officer-rows.json`. Smoke sample 0 is separate and unscored. Targeted miss = wrong person or name substituted (W), invented unsupported event or whereabouts (I), or the officer acting as an ally who thanks Kristin and analyzes the scene (O). Malformed (M) = output the real contract parser rejects (verified: `parse_turn_proposal` with `item_facts` removed rejects exactly the 14 rows I scored M, no disagreements).

| Cell | Targeted (W/I/O) | Wrong name "Officer Jenkins" | Malformed (parser rejects) | Clean and parses |
| --- | --- | --- | --- | --- |
| OFF6 greet, CTRL | **8/12** (W 5, O 4, I 1; some overlap) | 5/12 | 8/12 | 0/12 |
| OFF6 greet, BIO (Reyes bio line) | **0/12** | 0/12 | 6/12 | 6/12 |
| OFF7 ask, CTRL | 3/12 (I: invented neighbor report, lab breach, "when we arrived" search story) + 1 borderline (S15, "I didn't see her leave") | 0/12 | 0/12 | 8/12 |
| OFF7 ask, BIO | 0/12 | 0/12 | 0/12 | 12/12 |

**Greet (OFF6).** Reproduction met (8/12 at least 4/12). Improvement met (0/12 at most 1/12, eight fewer than control). Relevant action: Reyes answers in all 12 BIO rows. The preregistered zero-tolerance gate on malformed output is **not met** (6/12 in the candidate, 0 required); it is no worse than control (8/12) and is not caused by the bio. The gate is not lowered after seeing output. So the bio is a large, clean-direction improvement at this endpoint that cannot be called a win under the preregistered gate until the malformed output is addressed or the gate is re-registered by Brandon.

**Ask (OFF7).** Control shows 3/12 targeted misses (4/12 if the borderline row S15 is counted): **not reproduced under the strict reading** (needs at least 4). Candidate is 0/12 and 12/12 clean, with no malformed output, but no causal win is claimed. The Walt prompt did not enter this stage.

**New defect (outside the plan's two misses).** 14 of the 24 greet replies are rejected by the real parser: the second segment's keys are mangled (for example `"text":"…","},{":"kind","narration":"…"`), or `item_facts` runs away. It occurred only at the greeting command (0 of 24 at the question). The engine gets two narration attempts per turn (`TURN_NARRATION_ATTEMPTS = 2`), so the live failure rate per greeting turn is a question for a separate measurement. Cause not established. The wire payload is the production shape (same `response_format`), but reply-format behavior of the hosted model was not otherwise inspected.

**Caveat.** Both officer endpoints are reconstructed (neutral filler turns, canonical commands). Replies are strongly correlated (several rows are near-identical). A generation result only.

## Result: Walt stage (run 2026-11-08, 24 scored requests plus 2 smoke; 0 transport errors, 0 malformed; blinded sheet `sheet-walt.txt`, key `key-walt.json`, scores `scores-walt.json`; single reader, Claude, scored before unblinding)

Composed turn = reply plus the game's appended delivery sentence (identical in both arms: Walt at the fence, wife missing, the vans and the clipboard, "he is not sure what he saw", asks Kristin not to tell the patrol). Rows: `run-walt-rows.json`.

| Arm | Wrong witness or name | Incoherent account or disclosure beyond the delivery | Reply repeats the delivery's opening line (D) | Walt speaks his own "not sure what I saw / have not slept" before the delivery says it (P) | Clean |
| --- | --- | --- | --- | --- | --- |
| CTRL | 0/12 | 0/12 | **11/12** | 1/12 | 1/12 |
| BIO (Walt bio line) | 0/12 | 0/12 | 0/12 | **9/12** | 0/12 |

Preregistered target (wrong identity, incoherent handoff or early disclosure beyond the delivered sentence) is **not reproduced**: control 0/12 (needs at least 4). No causal win is claimed for the Walt block. Secondary observation, not preregistered as a gate: the control narrator restates the setup that the appended delivery says again (11/12); with the bio line, that restatement disappears (0/12) but Walt starts voicing his bio's traits ("I'm not sure what I saw", "I haven't slept in days") ahead of the delivery in 9/12, so the composed turn says it twice in a different way. Neither arm is clean. The bio is trait text that surfaces as dialogue; the Walt block is source completeness only and is not supported as a fix by this screen. 12 samples are strongly correlated (many near-identical replies).

## Result: password stage (run 2026-11-08, 36 scored requests plus 3 smoke; 0 transport errors; blinded key `key-password.json`, scores `scores-password.json`; single reader, Claude, scored before unblinding)

Rows: `run-password-rows.json`. Command `Type in the password.` after turn on and unlock, canonical, no preceding narration in the prompt.

| Arm | Laptop, drawer or file search | Invented successful authentication | Types or attempts the password (relevant action) | Walks over, picks up and examines the phone instead | Borderline |
| --- | --- | --- | --- | --- | --- |
| CTRL | **0/12** | 0/12 | 4/12 | 8/12 | 2/12 ("starts to dial Michelle's password") |
| SUB (laptop lines removed) | 0/12 | 0/12 | **0/12** | 12/12 | 0 |
| ADD (`Michelle's phone showed a password prompt.`) | 0/12 | **6/12** ("the phone unlocks with a soft click", "list of Michelle's contacts") | 12/12 | 0/12 | 0 |

**The original miss is not reproduced.** The laptop is never chosen and no file search appears in any of 36 rows, control included (0/12 against the 4/12 needed). So SUB cannot be called a win, and it is worse than control on the relevant action (0/12 against 4/12): with the laptop removed, the narrator never types at all. ADD fixes the relevant action (12/12) but fails the zero-tolerance gate on invented authentication (6/12), so the one-line context probe is not adoptable as written. What the control shows is a different, smaller problem: without any password context, the narrator does not treat `Type in the password.` as typing in 8/12 rows (it picks the phone up and examines it), which is an unfinished-action miss, not a wrong-device miss. A reference-memory design would not have changed these rows (the phone is already the target). Per the preregistered rule nothing here licenses the compatibility-filtered recency engine; its premise (device substitution) did not reproduce. 12 samples are strongly correlated.

## Preregistration: voiceability probe (written 2026-11-08 BEFORE any voice-stage request; Brandon approved 52 requests)

**Question.** When the player has earned Kristin's own reading of the kitchen walls, the officer's prompt offers it as a line he may say aloud. Does `voiceable: false` on `k_sl_1a_g_r2` (the documented use: "records what the player character did, so a present non-player character does not repeat it as speech") stop that, without making his ordinary answers worse?

**Frozen arms** (`frozen-voice-{CTRL,NOVOICE}.json`, validator OK, earlier frozen files verified byte-identical). Both arms have the Reyes bio line, so the only difference is voiceability. CTRL = Reyes-bio package; NOVOICE = same plus one line `  voiceable: false` after the k_sl_1a_g_r2 statement. The NOVOICE prompt equals CTRL minus exactly the line `- Officer Reyes may say this aloud: Kristin reads the kitchen walls as a life interrupted: ...`. Script: five phone commands, `Look at the wall calendar.`, `Look at the photograph.`, then VOICE8 `Greet the officer.` (command 8) and VOICE9 `Ask the officer where Dr. McGehee is.` (command 9). Reconstructed, canonical, not the original session.

**Spend.** 4 cells x (1 smoke + 12 scored) = 52 requests, about 190 neurons at the old 3.7 to 4.5 per request (not verified). No retries; smoke first and unscored; refuses re-billing.

**Scoring** (blinded, single reader, composed turn, real parser used for malformed). Miss types, each counted per row: VR = the officer says or paraphrases Kristin's reading (calendar, photograph, Saturday, lake, "life interrupted") or analyzes the kitchen scene as an ally; W = wrong name; I = invented unsupported event or whereabouts; MAL = rejected by the real parser; CH = replacement chatter (officer speech that ignores the greeting or the question and runs stock investigation talk).

**Win rule (fixed now).** At each endpoint: reproduction needs the control to have at least 4/12 VR; improvement needs the candidate at most 1/12 VR and at least 3 fewer than control; relevant action (the officer answers the greeting or the question) at least 11/12; the candidate must be no worse than control on W, I, CH and MAL, and CH must be 0/12 (the 2A attempt failed on this: removing speakable lines produced unrelated chatter). Malformed output is reported by cell and not pooled; a greeting-cell malformed rate that is again about half is recorded as the known separate defect, not as caused by `voiceable`. A failed comparison is dropped or re-registered, never rerun until green. A generation result only; adoption would also need the full-suite and live qualification.

## Result: voiceability probe (run 2026-11-08, 48 scored requests plus 4 smoke; 0 transport errors; blinded key `key-voice.json`, scores `scores-voice.json`; single reader, Claude, scored before unblinding; real parser used for malformed)

| Cell | VR (officer voices Kristin's reading / ally scene analysis) | Officer gives no reply to the greeting or question (RA) | Invented event (I) | Replacement chatter / role confusion (CH) | Wrong name | Rejected by the real parser |
| --- | --- | --- | --- | --- | --- | --- |
| VOICE8 greet, CTRL (line offered) | **0/12** | 6/12 | 3/12 | 0 | 0 | 0 |
| VOICE8 greet, NOVOICE | 0/12 | 1/12 | 0 | 0 | 0 | 0 |
| VOICE9 ask, CTRL | 0/12 | 0/12 | 0 | 0 | 0 | 1/12 |
| VOICE9 ask, NOVOICE | 1/12 (V12, plus I) | 0/12 | 1/12 | **1/12** (V40: roles scrambled) | 0 | 0 |

**Preregistered target not reproduced.** With the earned-knowledge speaker line in the prompt, the control officer voices Kristin's kitchen reading in **0/24** rows (needs at least 4/12 at an endpoint). So `voiceable: false` is not supported as a fix: the offered line is not what produces the wrong answers in these samples. The candidate also trips the zero-chatter gate at the question endpoint (CH 1/12, V40), and it is no better there (VR 1/12 against 0/12). No causal win; the story-data edit is not adopted.

**Exploratory, not preregistered as a gate.** At the greeting the control officer gave no reply in 6/12 rows (Kristin greets, or the reply truncates, and the officer never speaks; three of those rows also invent a "forced entry and overturned chair") against 1/12 for NOVOICE. If real, the offered line may be crowding out the officer's reply; this is one cell of 12 correlated samples and would need its own registered check before anyone acts on it. The greeting-cell parser rejections seen in the officer stage (6 to 8 of 12) did not recur here (0/24 at the greeting), although the prompts differ only by the earned reading turns; cause unknown.

Smoke sample note: the NOVOICE greeting smoke row (unscored) was a parser-rejected reply, the same defect class as the officer stage.

## Result: recovery request at the officer greeting (run 2026-11-08, 12 requests, approved; no smoke sample to stay within the approved count; 0 transport errors; rows `run-recovery-rows.json`)

Frozen request: the provider's own recovery request (`CloudflareTurnProvider._recover_malformed_response`: the greeting request with " Your last answer was not valid. Send back only JSON. ..." added to the system text; validator checks user text equals the frozen officer-BIO greeting request). Triggered by the recorded fused-segment reply (officer-BIO sample 1).

- **Parsed by the real contract parser: 12/12.** No rejected or invalid-JSON reply, so on these samples the live player would not hit the 502 `INVALID_PROPOSAL` path; the cost of a bad first reply is the extra model call (latency, neurons), not a lost turn.
- **Content: the officer answers in 1/12** (sample 2). In 11/12 the reply is Kristin approaching and greeting (or asking) and the officer never speaks, and in 8 of those the quoted greeting is left unterminated (the closing quote is missing mid-sentence). Read strictly, the recovery turn is usable JSON that leaves the greeting unanswered.
- Together with the first-reply rate (6 to 8 of 12 rejected at this command) and the earlier greeting rows with no officer reply, this is the more likely explanation for "the officer did not answer when greeted" than any bio or voiceability issue. It is a model-behavior pattern at this prompt, not a story-data fault; a fix would be a narrator-rule or provider-repair candidate with its own preregistered screen. 12 samples, strongly correlated; one scene; reconstructed request.

## Preregistration: live greeting check of the fused-segment repair (written 2026-11-08 BEFORE any request; Brandon: "then do the check" after #754 merged)

**Question.** Through the real provider and engine, does the repair merged in #754 change what the player gets when they type `Greet the officer.` in scene 1A: does the officer answer, how many model calls does the turn cost, and how often is the turn lost?

**Design.** Harness `scripts/ringer/1a-password-officer/live_greeting.py` (validated offline by `validate_live.py`: arms, order, request counting, hard cap, error rows, dry-run guard). Shipped package (Reyes bio included), eight canonical prefix commands (five phone commands, two neutral, then the greeting), the real `ItemFactsProvider` and `RuntimeEngine`. Arm ON = the code as merged; arm OFF = the repair switched off on the provider instance. Only narration-shaped requests (including the provider's recovery request) reach the real endpoint; matcher and capture calls are canned as in the earlier freezes. 12 samples, ON then OFF per sample (interleaved), no retries beyond the provider's own recovery, errors kept as rows.

**Spend.** One unscored smoke sample (up to 4 real requests), then up to 12 samples per arm. Hard cap **36 real requests in total** (smoke included, enforced in the harness and the run stops early if reached; completed samples are reported as they are). Expected: about 24 first-reply requests plus recovery requests (the earlier screens suggest roughly half of the greeting turns, mostly in OFF), so about 30. The old price estimate of 3.7 to 4.5 neurons per request puts the ceiling near 160 neurons (not verified against current billing).

**Scoring** (blind: arm labels removed, order shuffled, key kept apart; single reader, Claude; rows scored on the composed final text the engine returned; transport/turn errors are lost turns): per row, ANSWERED = the final text contains the officer's own response to the greeting (speech or a direct reply action); UNANSWERED = Kristin greets and the officer never responds, or the turn contains only scene narration; LOST = error row. Also recorded per arm: first-reply parser rejection rate, recovery-request rate, mean real requests per turn, wrong-person/name substitutions.

**Win rule (fixed now).** Reproduction: the OFF arm has at least 4/12 UNANSWERED or LOST. Improvement: ON has at most 1/12 UNANSWERED or LOST and at least 3 fewer than OFF; ON uses fewer real requests per turn than OFF; ON has no wrong-person substitution and no more LOST than OFF. A first-reply parser rejection rate that differs wildly between arms (they send the same prompt) is noted as noise. If OFF does not reach 4/12, report "not reproduced" with no rerun. A generation result on a reconstructed request only; not live qualification.
