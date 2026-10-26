# Holder-relation wording probe: preregistration (UNAPPROVED, nothing billed yet)

Status: revised 2026-10-25 after Brandon said the full name is "definitely most of the issue": short names are now used in the product's observation path (commit `4a319773`) and the probe has three arms. Brandon approved running it once the fixes were done ("You can run it when you're done with the fixes"). Run result: see the plan.

**Question.** The T8 shadow sample rejected or left uncertain 4 of 10 true "held by the character" relations (memory card 3 of 5, laptop 1 of 5) while every place relation agreed with the hand labels. A held item's relation carries place and holder both set to the holder's full name, so the Jev question reads "(at place Kristin Schweitzer and held by Kristin Schweitzer)". Does dropping the place when it equals the holder, so the question reads "(held by Kristin Schweitzer)", fix it without letting a wrong relation through?

**Two causes, three arms.** The narrations say "Kristin", the old relation said "Kristin Schweitzer". Brandon's rule: short names everywhere. The arms separate the causes: `full_both` (recorded relation, the before), `short_both` (short names, place and holder both set; what the product now builds) and `short_held_only` (short names, place dropped when equal to the holder). If `short_both` passes, no wording change is needed. Short labels come from the world file (shortest of aliases and name), so the wrong-holder cases render "Shelly", the shortest alias of Dr. Michelle McGehee (a nickname only Kristin uses); they are still false, but less natural negatives.

**Cases (frozen).** `scripts/ringer/environment_narration/holder_probe/cases.jsonl`, 25 single-relation cases, SHA-256 `7413a57476e59f35f399ba04a6934c38a7ce1022c4b617dc3135b0f953bcce7a` in `cases.lock.json`; `--run` refuses if it differs. Narrations are the real shadow-sample replies, copied verbatim (gitignored source `bench/results/environment-narration/shadow-sample/full/rows/rows.json`).
- 10 `positive_held` (label accept): the real holder relations, all hand-labelled true in the blind reading.
- 10 `wrong_holder` (label reject): same narration and thing, place and holder set to "Michelle McGehee". The narrations say Kristin holds the item.
- 5 `absent_thing` (label reject): the five "examine my laptop" narrations asked about Michelle's memory card; none mentions the card (checked by script).
The reject labels follow by construction. I read the ten positive narrations: each shows the item in the character's hands.

**Arms.** See above. Questions come from the product's own `_question_for`. Same thresholds as T7 (accept above 0.65, reject below 0.35), same Worker `/jev` route.

**Frozen T7 corpus.** The rewording applies only when place equals holder. `--check-corpus` shows 0 of 274 corpus relations change (they hold no place with a holder), so the T7 result stands unchanged and the corpus is not re-billed.

**Counts and cost.** 25 cases x 3 arms x 2 samples = **150 Jev requests**, fixed-seed order with the arms interleaved, no retries, no replacement samples. Estimated 47k input tokens, ceiling **$0.003** at 1.5x margin. Pass `--max-calls 150 --max-usd 0.01`. Stops after 3 consecutive unusable replies or on HTTP 429/5xx.

**Gate (each short arm separately).**
- G1: at least 18 of the 20 positive samples are accept.
- G2: zero accepts among the 30 negative samples.
- G3: positive accepts at least equal to the `full_both` arm's.
The `full_both` arm's numbers are the "before" and are reported next to it.

**Limits.** The 10 positive cases are the ones that exposed the defect, so a pass shows the rewording fixes known failures, not that it generalizes; only a second shadow sample with a new preregistration can show that. The negatives are constructed, not natural. Single-relation requests, whereas the product batches several relations per request. One Jev version, two samples each (T7 samples agreed every time, so the effective n is smaller than 150). A `short_both` pass keeps the product as built. Only a `short_both` fail with a `short_held_only` pass permits changing the wording (a Ringer task, tests first).

**Command (after approval; run as one Ringer probe task, `run-holder-probe-live.json`).**
`(set -a; . ./.env; set +a; .venv/bin/python scripts/ringer/environment_narration/holder_wording_probe.py --run --confirm --max-calls 150 --max-usd 0.01 --out bench/results/environment-narration/holder-probe-rows.json)` then `--report --rows ... --out bench/results/environment-narration/holder-probe-report.md`.
