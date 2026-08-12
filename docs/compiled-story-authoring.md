# V2 compiled-story authoring

`storygame.authoring` is the Phase 2 offline boundary for V2 story input. It
does not read V1 world facts, proposals, policies, or runtime package contracts.
Its only model integration is an injected `CompilerTransport` with
`generate(prompt)`. Provider adapters remain transport concerns.

## Contract

`CompiledStory` is an immutable `compiled-story-v1` object. It contains:

- a stable story ID and version;
- premise, central question, genre, and initial world state;
- stable-ID characters;
- protected revelations released only after declared completion tags; and
- beats with Freytag phase, required dependencies/unlocks, completion tags,
  central-question resolution flag, and pacing thresholds.

Validation is local and fails descriptively before any session can use the
story. It rejects duplicate IDs, unknown beat or tag references, cycles,
missing crisis/climax/resolution phases, an independent climax, a resolution
that does not answer the central question, missing/duplicate completion tags,
and non-increasing pacing thresholds.

## Fixtures and optional compilation

Checked-in deterministic fixtures are versioned under
`data/compiled_stories/v1/` for mystery, fantasy, sci-fi, and relationship
stories. Load one with `load_compiled_story_fixture(genre)`.

For an offline authoring experiment, inject a transport into
`CompiledStoryCompiler` and set `FREYTAG_ENABLE_LIVE_COMPILER=1` before calling
`compile_live`. This explicit switch keeps model costs outside normal tests and
runtime execution. `compile` remains available for injected deterministic
transports used by authoring tests.

Phase 3 consumes these immutable inputs through
`storygame.runtime.bootstrap_runtime_state`. `RuntimeState` is the sole mutable
session authority; compiled stories remain immutable inputs.

The V2 `mystery` fixture is a declarative projection of the retained authored
Vale Mansion case: Detective Elias Wren, Daria Stone, Emma Vale's death, the
case file and ledger-payment clues, the groundskeeper accusation, and the
evidence-gated resolution. It is data, not a mystery-specific runtime branch.
The V1 package/fact runtime remains the production fallback until the V2 hosted
path has passed staging promotion and its observation window.
