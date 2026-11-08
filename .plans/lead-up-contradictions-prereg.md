# Preregistration: lead-up contradictions, source probes 1A, 1B, 2A

Written 2026-11-07, BEFORE any billed request. Nothing billed. Plan: [lead-up-contradictions-plan.md](lead-up-contradictions-plan.md) steps 0-2.
**Status: Stage 0 done (free). Awaiting Brandon's approval of the rubric, the exact 1B wording, and the spend below.**

Baseline: HEAD `5fc12e79`, dirty tree retained. Frozen inputs are the live FINAL run's recorded prompts (`bench/results/shared-narrator/live/final-r1`), settings from the GU2 envelope. Hashes, dirty-diff and package-file fingerprints are in `bench/results/lead-up-contradictions/provenance.json` (git-ignored). Freeze script `scripts/ringer/lead-up-contradictions/freeze_inputs.py`; independent check `validate_freeze.py` (prints VALIDATION OK only if each arm differs from its control by exactly the planned lines). GU2's `package_hash` is stale metadata and is not used.

## Comparisons (each independent; control = the unchanged recorded FINAL payload)

| Id | Endpoint | Single edit | Payload sha256 (control → arm) | User chars delta |
| --- | --- | --- | --- | --- |
| 1A | c6 `Ask the senior official about the gate codes.` | add the senior official's `world.yaml` bio as the last CHARACTERS line | c6 control in `diff-report.txt` → `5148194a9a4e` | +213 |
| 1B | c4 `Enter the medical level.` | delivery's first sentence → "Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments." (other two sentences kept) | `74a5c4cf20ca` | +85 |
| 2A | c4 | delete the three "may say this aloud: …organizing…secret announcements…" lines | `aca414c1db03` | −388 |

Control payload hashes per endpoint are in `diff-report.txt`. System text, max_tokens and response_format are byte-identical in every arm. Each comparison draws its own same-day interleaved control (sample-major, endpoint, arm).

## Requests and spend

12 samples per arm, no retries, no replacements, errors kept as rows; no matcher, judge or capture calls. 1A, 1B, 2A: 24 requests each, **72 total ≈ 266 neurons (ceiling 324)** at the historical 3.7 / 4.5 per request (not verified current billing). The 2A ordinary-question safeguard (`Ask Michelle about the stolen radios.`, 24 more requests) is not frozen yet and is not in this scope. Replay script is not written yet; it will refuse without `--confirm` and cap requests per comparison. A 429 quota error stops the run and is kept as an error row. Order: 1A, 1B, 2A, each reported before the next is billed.

## Scoring

Sheets with arm labels removed and order shuffled; key kept apart until scores are written. Every reply read in full, malformed readable prefixes included; cite row and quote for every miss. Rows scored on the **composed** turn (lead-up plus exact delivery, delivery split once from the end).

- **Reproduction:** control needs ≥4/12 rows with the targeted failure to claim a causal win; otherwise report "not reproduced", no rerun. 1A target: invented jailer/clearance stance or an answer incompatible with the authority delivery (CONTRA). 1B target: composed prose never enters/traverses the medical level. 2A target: unrelated organizing stock speech.
- **Candidate improvement:** target ≤1/12 and ≥3 fewer than control. CONTRA, private/premature disclosure, invented authority, malformed or empty text, transport failure: 0/12. Relevant composed action ≥11/12 and not below control. Irrelevant stock speech recorded even when the action succeeds.
- **1B movement:** prose clearly enters the medical level ≥11/12, no substitute radio talk counted. A generation win licenses integration work only; persisted place is checked with the engine, not inferred from prose (FINAL c4 left Kristin at detention level).
- **2A:** cannot be called adopted without the ordinary-question safeguard (supported answer ≥11/12, never silence).
- No pooling across states, no gate changes after seeing output. A failed comparison is dropped or re-preregistered, not rerun until green.

## Ownership

1B text and the 1A/2A story edits (plot heading, `voiceable: false`) are ChatGPT Desktop proposals that Brandon approves; Claude Code builds only approved package changes, tests first, through Ringer.

## Result 1A (run 2026-11-07, 24 requests, 0 transport/decode errors; smoke row separate and unscored)

Rows: `bench/results/lead-up-contradictions/run-1A-rows.json`, blinded sheet `sheet-1A.txt`, key `key-1A.json` (single reader, Claude, scored before unblinding).

| Arm | Target failure (hostile jailer stance / denial contradicted by the authority delivery) | Borderline | Clean |
| --- | --- | --- | --- |
| C0 (FINAL) | **11/12** (S1, S2, S5, S7, S11, S16, S18, S20, S21, S23, S24) | 0 | 1 (S3) |
| 1A (bio line added) | **0/12** | 1 (S12 "I'm not sure I can trust you": wary, not a denial) | 11 |

Reproduction met (≥4/12). Improvement met (≤1/12, 11 fewer than control); CONTRA 0/12 in 1A even if S12 is counted as a miss (1/12). Lead-ups all pose the gate-code question (relevant action 12/12); no invented authority or malformed output. Caveat: 1A replies are near-identical (11 of 12 are one two-sentence opening), so 12 samples are strongly correlated. A generation win only; it licenses the ChatGPT Desktop PLOT proposal (`### Imprisoned senior official` heading with the existing bio), the early-reveal scope check, and live qualification.

## Result 1B (run 2026-11-07, 24 requests, 0 transport errors; blinded sheet `sheet-1B.txt`, key `key-1B.json`)

| Arm | Lead-up mentions the medical level | Stock organizing speech | Malformed |
| --- | --- | --- | --- |
| C0 | 0/12 | 12/12 | 0 |
| 1B (plot sentence) | 0/12 | 11/12 | **1/12** (S4: runaway duplicate `item_facts` keys, truncated) |

The edit changes only the constant delivery sentence, so it cannot change what the model writes. In both arms the lead-up stays in the detention sector and never travels, and 1B composed turns therefore enter the medical level only through the authored delivery text ("leads Kristin through a medical level…"), 12/12 by construction. Persisted place was not checked; no row puts Kristin in the medical level (all `detention level`, or the nonsense `held_by: Kristin`), so the c4 state defect stays open. **Preregistered gate failed:** malformed output must be 0/12 in the candidate (1/12 here, and 0/12 in control). The gate is not lowered after seeing output; 1B is not adopted. A re-preregistration (or a decision that the one-sentence restoration is worth taking on authored-text grounds alone, with the state fix) is Brandon's call.

## Result 2A (run 2026-11-07, 24 requests, 0 transport errors, 0 malformed; blinded sheet `sheet-2A.txt`, key `key-2A.json`)

| Arm | Stock organizing line | Lead-up mentions the medical level | Invented dialogue (not a permitted line) | Malformed |
| --- | --- | --- | --- | --- |
| C0 | **11/12** (all but S7) | 0/12 | 0/12 (S7 voices the "freeing this block" statement) | 0 |
| 2A (three lines deleted) | **0/12** | 2/12 (S5, S6: Kristin says she will go; neither enters) | 12/12 (generic "we need a plan / get them out" exchanges; S6 runs 11 segments) | 0 |

Reproduction met; the targeted stock speech is gone (11 → 0, bar ≤1 and ≥3 fewer). But the lines were replaced by other unrelated chatter that does not answer "Enter the medical level": relevant action is 0/12 in both arms (not lower than control, but not the ≥11/12 the rubric asks), and the model now invents speech it was not given. So 2A removes the invitation without producing relevance, as the plan warned ("a new command-relevance filter is a separate engine design"). The ordinary-question safeguard (`Ask Michelle about the stolen radios.`, 24 more requests) is not run, so the `voiceable: false` flag is **not adopted**.

## 1A source change applied (2026-11-07, uncommitted)

Ringer task `add-senior-official-heading` (PASS, attempt 1): `plot.md` gains `### Imprisoned senior official` with the existing paragraph under Principal Characters (diff is exactly that block). New `tests/test_senior_official_bio.py`; focused suites pass. Pin edits: `tests/test_richer_3a.py` (3A opening character-name set includes the official) and `tests/test_prompt_presence.py` (later-character absence assertion changed from `Charles` to `Charles Jenkins`, since the official's bio now contains the word "Charles").

**Early-disclosure inventory** (`bench/results/lead-up-contradictions/official-bio-inventory.md`): his bio is now in CHARACTERS on **all nine** 3A turns, including c1-c5, before the c6 handoff where he gives out his one-use authority. The bio's last clause ("has kept one piece of emergency authority out of Charles's hands") therefore reaches the narrator before that is earned. The 1A probe only tested the bio at c6. Open: probe a narrowed `narrator_bio` (clause removed) at c6, and decide whether early exposure matters. Not done.

## Comparison 1A2 (preregistered 2026-11-07 BEFORE any billed request; approved by Brandon)

Question: does the 1A win survive without the plot-fact clause? Endpoint c6, same frozen FINAL payload. Control = the 1A arm (full bio line); arm 1A2 = that line replaced on its own line by `- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant.` (drops only "and has kept one piece of emergency authority out of Charles's hands"; the `narrator_bio` rule: plot facts earned at c6 do not belong in a story-wide bio). 12 samples per arm, 24 requests, about 89 neurons (ceiling 108), same-day interleaved, no retries or replacements. Scoring and gates as 1A (blind sheet; hostile-jailer / denial contradicted by the delivery = CONTRA). **Adopt** if 1A2 has CONTRA ≤1/12, 0 malformed, and not more than 1 more miss than the same-day control. If the same-day control does not reproduce its own 0/12 (≥2/12 misses), report instead of adopting. On adopt, apply the same text to world.yaml `narrator_bio` (via Ringer) and re-run the pins/inventory; on fail, the next candidate is a traits-only bio ("exhausted and observant"), separately preregistered.

### Result 1A2 (run 2026-11-07, 24 requests, 0 transport errors, 0 malformed; blinded sheet `sheet-1A2.txt`, key `key-1A2.json`)

| Arm | Hostile jailer / denial (CONTRA) | Mentions the authority | Malformed |
| --- | --- | --- | --- |
| 1A (full bio, same-day control) | 0/12 | 0/12 | 0 |
| 1A2 (authority clause dropped) | **0/12** | 0/12 | 0 |

The same-day control reproduced its 0/12; 1A2 meets the adopt rule (CONTRA ≤1, no malformed, no worse than control). Replies are near-identical (3 distinct texts in control, 4 in 1A2; "exhausted but observant", "caution and desperation"), so the 12 samples are strongly correlated, and 1A2 is a generation result only. **Adopted:** `narrator_bio` loses the clause. The earlier 1A/C0 comparison still stands (hostile 11/12 without any bio).

### 1A2 applied (2026-11-07, uncommitted)

Ringer task `trim-senior-official-bio` (PASS, attempt 1): `world.yaml` npc `senior_official` `narrator_bio` now ends "He is exhausted and observant." (one-line hunk). `tests/test_senior_official_bio.py` gains the lasting rule (bio equals the package text and never names "authority"). Inventory regenerated: the bio is still carried on c1-c9 but names nothing earned at c6. Focused suites pass. Together with the `plot.md` heading, 1A is complete for generation; the live qualification (nine-command Path A, both reunion orders) is not run.
