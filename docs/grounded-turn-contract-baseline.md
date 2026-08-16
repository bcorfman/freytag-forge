# Grounded turn contract

Phases 1–2 are complete as of 2026-08-16. Ordinary freeform proposals carry local typed `staging_claims`; no provider-side schema is trusted for semantics.

The four generic relation families are `custody`, `environment`, `access`, and `event`. Before a proposal is accepted, the normal turn pipeline applies its already validated effects to a clone and verifies every claim against that candidate's canonical facts. Claims with an unknown relation, insufficient IDs, duplicate or contradictory identity, unavailable entity, or off-scene location fail local validation. The source fact store remains unchanged.

Planner claim failures use the same two-request recovery budget as malformed JSON, contract, speaker, and disclosure failures. Exhaustion raises `ORDINARY_TURN_RECOVERY_EXHAUSTED`; it never returns an invented successful turn. This stage does not parse prose or require incidental atmosphere to be a fact. Phase 3 will add claim authoring guidance and retire the temporary phrase-based custody guard only after equivalent coverage is established.

The shared CLI, local web, and hosted-demo turn path receives this behavior below their separate deployment adapters. Focused deterministic coverage is in `tests/test_grounded_turn_contract.py`.

Phase 2 makes consequential conditions package data rather than prose luck. Every generated package declares a named room-condition transition, its bounded consequence class (`pressure`, `setback`, `cost`, or `opportunity`), affected routes, and any evidence-based recovery. Bootstrap realizes those declarations as canonical facts. The shared semantic-action boundary can apply only a currently declared transition or resolve only a declared block using held evidence. Package validation rejects unknown rooms, routes, evidence, malformed classes, and a fully blocked room without a recovery route. Mystery, fantasy, sci-fi, and relationship fixtures exercise the same contract.
