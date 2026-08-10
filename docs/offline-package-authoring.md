# Offline package authoring

Story packages are authoring inputs, not a runtime authority. The engine
realizes an accepted package into canonical facts, and all later changes flow
through the normal proposal, validation, and fact-commit boundary.

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
