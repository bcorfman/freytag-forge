# V2 migration acceptance scorecard

Phase 0 establishes these measures for comparison; it does not turn V1 deterministic replay into a V2 release requirement. Each V2 staging evaluation records its numerator, denominator, deployed SHA, model/prompt revision, and channel. Production promotion compares the tested SHA with this baseline and the documented Phase 5 promotion gate.

| Measure | Definition | V1 comparison evidence | V2 target record |
| --- | --- | --- | --- |
| Structured-output success rate | Decoded and locally valid first responses / model responses. | Not measured: V1 uses proposal contracts rather than the V2 `TurnResult`. | successes / responses |
| One-call rate | Successful turns completed by one provider call / successful model turns. | Not measured as a V2 metric; V1 stub ordinary-turn call counts are recorded in the evaluation baseline. | one-call successes / successes |
| Repair rate | Turns that used the one permitted repair / model turns. | Not measured as a V2 metric. | repaired turns / model turns |
| Typed-error rate | Typed fail-closed errors / model turns. | V1 recovery exhaustion is covered by frozen regressions; no comparable aggregate rate is captured. | typed errors / model turns |
| p95 turn latency | 95th percentile end-to-end turn duration. | In-process V1 stub timings only; not provider/network latency. | milliseconds at p95 |
| Premature-revelation rate | Protected-revelation violations / evaluated turns. | V1 hidden-information leak checks are frozen; no aggregate rate is captured. | violations / evaluated turns |
| Continuity violations | Invalid identity, custody, location, or beat continuity findings / evaluated turns. | V1 artifact categories are frozen; no aggregate rate is captured. | violations / evaluated turns |
| Completion rate | Sessions reaching a valid ending / started evaluation sessions. | V1 package playability evaluates endings; no aggregate rate is captured. | completed sessions / started sessions |
| User-facing session failures | Client-visible session creation, turn, load, or isolation failures / sessions. | V1 hosted-demo E2E covers the paths; no aggregate rate is captured. | failures / sessions |

Historical V1 deployment evidence is retained in the
[release baseline](release-baseline.md) and is comparison-only. A future
credentialed measurement must state its request budget; the normal test suite
continues to use deterministic fixtures.
