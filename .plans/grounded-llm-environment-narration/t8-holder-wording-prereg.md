# Holder-relation wording probe: preregistration (UNAPPROVED, nothing billed yet)

Status: harness built and tested offline 2026-10-25; waiting for Brandon's go before the one billed run.

**Question.** The T8 shadow sample rejected or left uncertain 4 of 10 true "held by the character" relations (memory card 3 of 5, laptop 1 of 5) while every place relation agreed with the hand labels. A held item's relation carries place and holder both set to the holder's full name, so the Jev question reads "(at place Kristin Schweitzer and held by Kristin Schweitzer)". Does dropping the place when it equals the holder, so the question reads "(held by Kristin Schweitzer)", fix it without letting a wrong relation through?

**This is a hypothesis.** The narrations name the character "Kristin", not "Kristin Schweitzer", so the full name may be the cause instead. If the wording arm does not fix it, the report's per-row scores are what we have to diagnose from; no third arm is pre-approved.

**Cases (frozen).** `scripts/ringer/environment_narration/holder_probe/cases.jsonl`, 25 single-relation cases, SHA-256 `7413a57476e59f35f399ba04a6934c38a7ce1022c4b617dc3135b0f953bcce7a` in `cases.lock.json`; `--run` refuses if it differs. Narrations are the real shadow-sample replies, copied verbatim (gitignored source `bench/results/environment-narration/shadow-sample/full/rows/rows.json`).
- 10 `positive_held` (label accept): the real holder relations, all hand-labelled true in the blind reading.
- 10 `wrong_holder` (label reject): same narration and thing, place and holder set to "Michelle McGehee". The narrations say Kristin holds the item.
- 5 `absent_thing` (label reject): the five "examine my laptop" narrations asked about Michelle's memory card; none mentions the card (checked by script).
The reject labels follow by construction. I read the ten positive narrations: each shows the item in the character's hands.

**Arms.** `current` (relation exactly as the product builds it) and `held_only` (place dropped when it equals the holder). Questions come from the product's own `_question_for`. Same thresholds as T7 (accept above 0.65, reject below 0.35), same Worker `/jev` route.

**Frozen T7 corpus.** The rewording applies only when place equals holder. `--check-corpus` shows 0 of 274 corpus relations change (they hold no place with a holder), so the T7 result stands unchanged and the corpus is not re-billed.

**Counts and cost.** 25 cases x 2 arms x 2 samples = **100 Jev requests**, fixed-seed order with the arms interleaved, no retries, no replacement samples. Estimated 31k input tokens, ceiling **$0.002** at 1.5x margin. Pass `--max-calls 100 --max-usd 0.01`. Stops after 3 consecutive unusable replies or on HTTP 429/5xx.

**Gate (held_only arm).**
- G1: at least 18 of the 20 positive samples are accept.
- G2: zero accepts among the 30 negative samples.
- G3: positive accepts at least equal to the `current` arm's.
The `current` arm's numbers are the "before" and are reported next to it.

**Limits.** The 10 positive cases are the ones that exposed the defect, so a pass shows the rewording fixes known failures, not that it generalizes; only a second shadow sample with a new preregistration can show that. The negatives are constructed, not natural. Single-relation requests, whereas the product batches several relations per request. One Jev version, two samples each (T7 samples agreed every time, so the effective n is smaller than 100). A pass permits changing the product rendering (a Ringer task, tests first); a fail leaves it as is.

**Command (after approval; run as one Ringer probe task, `run-holder-probe-live.json`).**
`(set -a; . ./.env; set +a; .venv/bin/python scripts/ringer/environment_narration/holder_wording_probe.py --run --confirm --max-calls 100 --max-usd 0.01 --out bench/results/environment-narration/holder-probe-rows.json)` then `--report --rows ... --out bench/results/environment-narration/holder-probe-report.md`.
