# Gameplay, model, and interaction safety

Part of [the contributor guide](../contributor-guide.md).

## Gameplay, model, and interaction safety

- Keep ordinary play LLM-proposal-first. Only `save`, `load`, `quit`, and
  `help` are parser control commands; normalize deterministic affordances via
  the shared proposal/commit contract.
- Let players attempt story moves freely. Validate bounded consequences,
  clarify ambiguity, and reserve confirmation for irreparable goal breaks; do
  not replace interpretation with a fixed command table.
- Validate all accepted state deltas before rendering. Narration, dialogue, and
  action segments cannot create uncommitted truth or leak observer- or
  speaker-protected knowledge.
- Treat provider responses as untrusted JSON-boundary input. Use an explicit
  typed structured-output adapter; normalize supported envelopes; parse and
  validate locally before commit. Provider JSON-object mode is syntax help, not
  semantic validation.
- A normal turn makes at most one narration inference request plus one shared
  recovery request for JSON-mode fallback, malformed output, or transient
  failure; a delayed duplicate of the same narration request (a hedge, sent
  only when the first has not answered) counts as that same request, and only
  one reply is used. The item-facts name-matching request has its own cap of
  two and does not share the narration budget. Exhaustion is a typed fail-closed
  error, never fabricated success. Target under ten seconds on the normal path.
- With `FREYTAG_OPENING_CHECK=1`, an opening check adds one Jev request per opening the command refers to, up to two per attempt.
- A guard retry may name a rejected term only when the player typed that term; otherwise rejection feedback remains generic.
- Generate NPC dialogue only from the addressed NPC's permitted current
  context. Reject parroting, wrong speakers, off-scene or role violations, and
  unavailable-model fallbacks rather than fabricating a response.
