# T9h drain replay: J1c causal check preregistration

2026-10-30. This preregistration and `scripts/ringer/environment_narration/drain_replay/cases.jsonl` are frozen before any score is collected. No billed replay has been run while this document is written.

## Question

Does J1c's scene context transfer to the real drain narrations? The check is limited to the scene-level relation for the storm drain at Los Angeles park. It tests location evidence, not condition or action safety.

## Frozen cases and traceability

There are six frozen cases. Cases 1 and 2 are verbatim first verifier attempts from the recorded rejected drain turns. Case 3 is a minimal edit of case 1 that removes the drain mention. Cases 4 and 5 are location-invalid controls: remembered and elsewhere. Case 6 is the recorded ON-smoke reply that says the drain is slightly ajar; it is location-valid but has `condition_policy` `problematic`.

Every case records its source file, replicate, stable turn id, stored turn index, and attempt id. The historical rows did not provide a separate attempt UUID, so `enforce_attempts[0]` is the recorded attempt id; edited controls identify their source attempt and edit in the attempt field.

The cases file SHA-256 is:

```text
26e10622abfe7d3e3aa4fa42bf1ad9f6b80a69d795896199f40dd3714264fd62
```

The probe embeds this digest as its cases lock. `--validate` must report a lock mismatch after any case-file edit.

The asked relation is unchanged for every case: thing `storm drain`, place `Los Angeles park`, holder `null`, scene-level `true`. J1c's scene is `Los Angeles park` and its starting places are `{"storm drain": "Los Angeles park"}`. The question text, criteria, and strict thresholds are those of the existing relation verifier: accept strictly above 0.65 and reject strictly below 0.35.

## Design and safety limits

The probe replays six cases under two arms, five samples per arm: 60 Jev calls total.

- V0 sends exactly `{\"narration\": ...}`.
- J1c uses `ObservationVerifier(scene_state=True)` and sends the resulting `{\"narration\": ..., \"scene\": \"Los Angeles park\", \"starting_places\": {\"storm drain\": \"Los Angeles park\"}}`.
- The estimated cost is approximately $0.001-$0.002.
- `--max-calls` is capped at 60 and `--max-usd` is capped at $0.005. The probe refuses before any request when the planned count or estimated ceiling exceeds the supplied cap.
- Spending requires both `--run` and `--confirm`, the required Worker environment, and a new output path. Existing rows are never overwritten.
- The run stops on the first quota, HTTP 429, or HTTP 5xx signal and preserves the partial rows. It does not rerun or replace samples.

## Pass rules

V0 is reported only. Its expected role is to reproduce the recorded uncertainty; it is not a gate.

For each location-valid case whose `condition_policy` is not `problematic`, J1c must accept at least 4 of 5 samples. For the three location-invalid cases, J1c must accept 0 of 5 samples. Case 6 is reported separately as `location accepted / condition not judged`; it is never required to be rejected by a relation-only judge.

A partial run fails the report even if the rows collected so far meet the applicable per-case counts. Missing samples are not silently treated as rejects.

This cannot qualify action safety. In particular, a J1c location accept does not judge opening, lifting, entering, initial open-state claims, contents, or other drain conditions. A fake transport or stub proves payload wiring and threshold handling only; it proves nothing about model judgment.
