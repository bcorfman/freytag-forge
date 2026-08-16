# Grounded turn-contract Phase 0 baseline

Recorded 2026-08-16. This audit establishes the boundary that Phase 1 will
close; it does not introduce a second mutation authority or change ordinary
turn behavior.

## Proposal and rendering entry points

| Surface | Opening path | Ordinary turn proposal and commit path | Current material-prose check |
| --- | --- | --- | --- |
| CLI | `StoryDirector` bootstrap via `build_bootstrap_response_payload` | `cli.run_turn` → `LlmFreeformProposalAdapter` → `resolve_freeform_roleplay_with_proposals` → `execute_turn_proposal` | Temporary held-item phrase guard, plus structural fact/policy validation. |
| Local web (`storygame.web`) | Shared bootstrap helper with an injected `StoryDirector` | `execute_turn` → shared `cli.run_turn` path | Same shared V1 behavior. |
| Hosted demo (`storygame.web_demo`) | Shared bootstrap helper with independent session, credentials, and backend configuration | `execute_turn` → shared `cli.run_turn` path | Same shared V1 behavior; deployment remains independent. |
| Freeform adapter | Not used for opening | Parses Cloudflare output into `DialogProposal` and `ActionProposal`, retrying once on local validation failure | `_dialogue_conflicts_with_held_item_custody` is a vocabulary-specific temporary guard. |
| Opening agents | `StoryDirector` and bootstrap agents parse a separate opening plan before facts are realized | Opening prose follows its own structured proposal, commit, and coherence sequence | Bootstrap-only presentation validation. |
| Story Director | Builds/replans bootstrap context; it is not the ordinary-turn narrator | May replan before freeform proposal; accepted prose never mutates facts | No material narration claim contract. |
| V2 standalone runtime | Independent `RuntimeState` bootstrap | `RuntimeEngine.turn` parses `TurnProposal`, validates a clone, then atomically replaces state | `narration_claims` are typed fact mutations, not yet the Phase-1 staging-relation contract. |

## Existing validation classification

| Check | Classification | Why |
| --- | --- | --- |
| `ValidatedFactCommitter`, predicate policies, semantic actions, consequences, and triggers | Structural fact validation | Validates canonical operations and invariants before commit. |
| Proposal parsing, provider-envelope normalization, and recovery budget | Structural boundary validation | Treats model output as untrusted but does not compare material prose with candidate facts. |
| `_dialogue_conflicts_with_held_item_custody` | Temporary prose guard | Regexes identify a few custody phrasings; Phase 3 retires it. |
| Targeted-speaker, player-echo, code-artifact, and document-disclosure checks | Presentation/dialogue validation | Protects speaker, role, and dialogue contracts, not general physical state. |
| Opening coherence/fact-parity and output-editor review | Presentation-only/bootstrap validation | Outside the normal material-claim boundary; cannot establish runtime truth. |

## Measured gap and deterministic specifications

`tests/test_grounded_turn_contract_baseline.py` injects a provider response for
custody, environment, access, and event contradictions. Each specification
requires the ordinary-turn recovery budget to exhaust and the original fact
set to remain unchanged. They are strict expected failures in Phase 0 because
no typed `staging_claims` field reaches a candidate-state validator. Phase 1
must remove the marker rather than add phrase matching. The examples have no
story-specific runtime meaning: they establish relation-family coverage only.

## Provider-call and latency baseline

A successfully parsed V1 freeform ordinary turn makes one provider request.
Parser, contract, targeted-dialogue, disclosure, and temporary custody-guard
failures get one shared retry, so the maximum is two; exhaustion raises
`ORDINARY_TURN_RECOVERY_EXHAUSTED` before commit. Deterministic affordance
normalization can avoid a provider request only when it constructs the same
proposal/commit contract.

The latest frozen in-process measurements record ten stub-model calls across
the local-web surface in 268.9 ms and ten across hosted demo in 11.7 ms. They
measure orchestration, not network inference; provenance is in the
[evaluation baseline](evaluation-baseline.md). CLI, local web, and hosted demo
share the ordinary freeform adapter and recovery contract; the two web
adapters retain independent credentials and backends.

## Phase 0 exit evidence

The audit covers every deployment adapter and makes no implementation decision
from a mystery item, weather name, access object, or fixed event. The remaining
gap is represented by relation-based deterministic specifications for Phase 1.
