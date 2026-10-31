# Verification

Part of [the world-model grounding guide](../world-model-grounding.md).

## Verifying

- **Tree properties are deterministic.** Test them with the real package and
  a synthetic second package, with no network. Every audit must work on a
  package it has never seen.
- **A prompt rule is only observable live.** A test that greps the prompt
  proves the prompt says it, not that the model obeys. Run a single-scene
  smoke first, and read its `item_facts_unplaced` and match-call resolutions.
