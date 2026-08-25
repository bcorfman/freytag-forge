# V2 evaluation scorecard

This is the metric schema for an expanded staged evaluator. The current
`v2-staging-evidence-v1` workflow artifact records SHA, API URL, runtime, and
its verification slice—not these numerators. Historical V1 evidence is
comparison-only; normal tests remain deterministic and provider-free.

| Measure | Record |
| --- | --- |
| Structured-output success | Locally valid first responses / model responses |
| One-call and repair rates | One-call successes / successes; repaired turns / model turns |
| Typed-error rate | Fail-closed errors / model turns |
| p95 turn latency | End-to-end milliseconds at p95 |
| Protected-revelation rate | Leaks / evaluated turns |
| Continuity violations | Invalid identity, custody, location, or beat findings / evaluated turns |
| Completion rate | Valid endings / started sessions |
| User-facing failures | Client-visible session, turn, load, or isolation failures / sessions |

Compare the SHA-bound staging report with the
[acceptance matrix](v2-acceptance-matrix.md) and the
[release baseline](release-baseline.md) before production approval.
