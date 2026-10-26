# T7 observation-verifier calibration: preregistration (unapproved)

Status: approved by Brandon and run 2026-10-25 (448 requests). Result: gate PASS; see the T7 section of the plan for the numbers and limits.

**Question.** Can Jev, asked one batched yes/no question per required relation about final narration, meet the T7 gate: zero observed false accepts on required relations and at most 5% false rejects?

**Corpus (frozen).** `scripts/ringer/environment_narration/verifier_corpus/cases-{a,b,c,d}.jsonl`, 224 cases, 274 relations (127 accept, 147 reject), 8 stories in 8 genres, 10 case types. Combined SHA-256 `1f18f4b41778876b7c5066a1a3d75e9db910d075e8c1ee337ab5b79b0641dc52`, locked in `corpus.lock.json`; `--run` refuses if any file changes. Labels were written by Luna workers and 16 random cases were hand-read by me (all agreed); no case was changed after reading. Story `d` uses the product scene's shape with fresh names.

**Arms and counts.** One arm: `observation-relation-v1` wording, thresholds accept > 0.65, reject < 0.35 (set before any scoring). 224 cases x 2 samples = **448 Jev requests**, interleaved in a fixed-seed order, no retries and no replacement samples. Route: the Worker `/jev` (model recorded per row from the response).

**Cost.** Ceiling $0.0083 at $0.042 per million input tokens (about 132k estimated input tokens, 1.5x margin). Pass `--max-usd 0.02 --max-calls 450`.

**Command (after approval).**
`set -a; . ./.env; set +a; .venv/bin/python scripts/ringer/environment_narration/verifier_calibration.py --run --confirm --max-calls 450 --max-usd 0.02 --out bench/results/environment-narration/verifier-rows.json`, then `--report --rows ... --out .../verifier-report.md`. Run through Ringer as one probe task. Stops after 3 consecutive unavailable/malformed replies, on HTTP 429 or 5xx.

**Gate (at the thresholds above).**
1. Zero false accepts over the reject-labelled relations, in both samples.
2. False rejects (label accept, verdict reject) at most 5% of accept-labelled relations, excluding `invention_unreported`. Also report the strict rate (uncertain, unavailable and reject all count), since the product would fail closed.
3. Report by category, story, model/version; every row listed; sample-to-sample disagreement; latency p50/p95.

**Stated limits.** 147 reject relations x 2 samples: zero false accepts still leaves a Wilson 95% upper bound near 2% per sample if samples are independent (they are not fully). `invention_unreported` rows only confirm the required relation; the verifier does not detect unreported inventions. One corpus, labels from one authoring pass. The post-hoc threshold sweep in the report is not the gate and must not be tuned and re-scored on this corpus; any change needs a new corpus and a new preregistration. If the gate fails, the verifier stays shadow-only and T8 proceeds without it as a guard.
