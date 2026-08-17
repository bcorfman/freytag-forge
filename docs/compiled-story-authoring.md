# V2 compiled-story authoring

`storygame.authoring` is the Phase 2 offline boundary for V2 story input. It
does not read V1 world facts, proposals, policies, or runtime package contracts.
Its only model integration is an injected `CompilerTransport` with
`generate(prompt)`. Provider adapters remain transport concerns.

`CompiledStory` remains a reduced, immutable bridge fixture while the Phase-1
Story Blueprint contract is introduced. It does not encode a genre's full
causal solution or alternate realization routes. Its public API remains
available, and `compiled_story_as_blueprint` provides a one-way reduced
projection into `story-blueprint-v1` while consumers migrate; neither format
becomes runtime mutation authority. The authority map, Vale Mansion omissions,
and later success measures are documented in
[genre-blueprint authoring](genre-blueprint-authoring.md).

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

## Phase-0 source selection

The offline compiler has one immutable `NormalizedStorySource` boundary. An
explicit `--outline-id` selects exactly one entry from
`data/story_outlines.yaml`; an explicit `--story path/to/brief.yaml` selects
one standalone `freytag-story-brief-v1` document. The selectors are mutually
exclusive. Both paths validate the declared genre/profile locally and produce
stable source ID, source format, a SHA-256 content hash, and a deliberately
limited provenance path (inventory name plus ID, or brief filename).

A Story Brief requires `schema_version`, stable `id`, `genre`, `profile`,
`premise`, and `opening_public_boundary`. It may add `world_notes`,
`cast_notes`, `hard_truths`, `protections`, `ending_constraints`,
`dramatic_beats`, `possibility_library`, and `author_notes`. The hard-truth,
protection, and ending fields are compiler constraints; all note, beat, and
possibility fields are non-canonical creative direction. Extra top-level keys
are rejected. Open-ended metadata belongs only under `extensions`, whose keys
must be namespaced, such as `author.palette`.

`vale_mansion_rebuild` is an `authoring_only` raw inventory entry. It may be
selected by the offline source selector, but hosted bootstrap still loads only
reviewed `data/compiled_stories/v1/` fixtures. Candidate artifacts will live
under `data/story_blueprints/candidates/` as new versioned
`*.candidate.json` files; they never overwrite reviewed artifacts in
`data/compiled_stories/v1/`.

The existing Vale artifact is deliberately not source authority. Its absent west
gallery, prose-only upper gallery and long hall, unreachable evidence locations,
and unprovable solution graph are recorded as failures a later causal artifact
must reject rather than patch with narration.

Use Phase 0 to inspect a source without constructing a provider:

```text
uv run storygame-blueprint --outline-id vale_mansion_rebuild
uv run storygame-blueprint --story path/to/brief.yaml
```

`storygame.runtime.bootstrap_runtime_state` retains `CompiledStory` as its
public bridge input and can additionally receive a validated Story Blueprint.
The blueprint is realized into the runtime's fact-backed progression map; the
immutable inputs remain authoring data, never mutation authorities.

The V2 `mystery` fixture is a declarative projection of the retained authored
Vale Mansion case: Detective Elias Wren, Daria Stone, Emma Vale's death, the
case file and ledger-payment clues, the groundskeeper accusation, and the
evidence-gated resolution. It is data, not a mystery-specific runtime branch.
The V1 package/fact runtime remains the production fallback until the V2 hosted
path has passed staging promotion and its observation window.

## Blueprint compilation candidates

`CompiledStoryCompiler` remains the reduced-fixture bridge. Full causal
blueprints use the separate offline `BlueprintCompiler`, an injected genre
profile registry, and an explicit JSON-object transport request. It validates
the raw-outline ID/hash and all generic/profile semantics locally, runs
injected full-blueprint critics plus route-fairness review, and permits only one
repair/revalidation pass. It records a non-playable candidate envelope with
compiler provenance rather than overwriting a checked-in reviewed fixture.

Use `storygame-blueprint --live` only with
`FREYTAG_ENABLE_LIVE_COMPILER=1` and an injected `module.path:factory`
transport. This tooling command is outside normal gameplay and may make a paid
provider request.
