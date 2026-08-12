# V2 production acceptance scorecard

Each staging evaluation records the candidate SHA, model and prompt revision,
channel, numerator, and denominator for every measure below. The promotion gate
fails for typed errors, protected-revelation leaks, continuity failures,
incomplete coverage, or an identity mismatch. Human review assesses the
remaining qualitative measures before production promotion.

| Measure | Definition |
| --- | --- |
| Structured-output success rate | Decoded and locally valid first responses / model responses |
| One-call rate | Successful turns completed by one provider call / successful model turns |
| Repair rate | Turns that used the one permitted repair / model turns |
| Typed-error rate | Typed fail-closed errors / model turns |
| p95 turn latency | 95th percentile end-to-end turn duration |
| Premature-revelation rate | Protected-revelation violations / evaluated turns |
| Continuity violations | Invalid entity, custody, location, or beat findings / evaluated turns |
| Completion rate | Sessions reaching a valid ending / started evaluation sessions |
| User-facing session failures | Client-visible session creation, turn, load, or isolation failures / sessions |

Phase 5 records these values in the SHA-bound `staging-evaluation.json` workflow
artifact. See [the staging evaluation guide](phase-5-staging-evaluation.md) for
the automated gate and required human review.
