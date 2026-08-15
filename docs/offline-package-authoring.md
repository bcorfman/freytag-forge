# Offline package authoring

Story packages are authoring inputs, not a runtime authority. The engine
realizes an accepted package into canonical facts, and all later changes flow
through the normal proposal, validation, and fact-commit boundary.

## V2 compiled stories

Phase 2 introduces `storygame.authoring` alongside—not inside—the existing
package authoring pipeline. A `CompiledStory` is an immutable, versioned V2
session input with a stable story ID, characters, initial world state, protected
revelations, completion tags, and a Freytag beat graph with pacing thresholds.
It has no mutable facts and is not a V1 package projection.

The local compiler validates stable IDs, references, acyclic prerequisites,
crisis/climax/resolution presence, a dependent required climax, a resolution
that answers the central question, protection references, completion tags, and
strictly increasing pacing thresholds. Errors are typed and story-agnostic.
The four checked-in deterministic fixtures are in
`data/compiled_stories/v1/{mystery,fantasy,sci-fi,relationship}.json`.

Phase 0 records `CompiledStory` as a reduced immutable bridge—not the future
full causal Blueprint—and keeps its current Vale Mansion omissions explicit.
The authority map, quality-suite baseline, and success measures are in
[genre-blueprint authoring](genre-blueprint-authoring.md).

`CompiledStoryCompiler` accepts an injected transport only at its outer edge.
Live model compilation is intentionally disabled unless
`FREYTAG_ENABLE_LIVE_COMPILER=1`; CI and deterministic tests load the checked-in
fixtures instead. Phase 3 will bootstrap the standalone runtime from these
inputs. Until Phase 4, the current V1 package path remains the running product.

`storygame.story_packages` validates the offline authoring contract. A valid
package declares locations and their presentation, characters and role
contracts, items and custody, protected knowledge, clues and resilient
revelation paths, causal rules, beat requirements, and viable endings.

`build_story_package_from_world` projects the external world-package data used
by the engine into this offline contract. It is an evaluation projection only:
it does not introduce a second mutable world representation or modify a live
`GameState`.

Frontier-backed generators and critics are permitted only through
`author_story_package`, an offline workflow. Their output is untrusted until
local validation and the deterministic judge accept it. Recovery candidates
must declare the fact categories they modify; the validator rejects any change
outside that scope, so repairs stay targeted rather than replacing a whole
story.

`evaluate_package_playability` runs each frozen package through exploratory,
goal-focused, social, adversarial, avoidant, and chaotic scripted-player
styles. A run passes only when it reaches a declared ending and returns a
structured artifact. `evaluate_fixture_playability` applies that check to all
frozen evaluation fixtures.
