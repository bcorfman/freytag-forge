# Grounding a story in the world model

Read this before you add or place anything in a story package, or before you
write any prompt line that tells a model about places or things. Field syntax
lives in [markdown-story-authoring.md](markdown-story-authoring.md). The [world-model checklist](../.plans/world-model.md) tracks the remaining
conditional work and explains how to retrieve the historical decisions
(W1–W14) and their amendments from git.

The world model (`packages/worldkeeper`, adapted by
`storygame/runtime/world_model.py`) is a tree of typed entities held as facts.
Every thing, character and area has one parent. The engine owns that tree. The
narrator proposes changes by naming parents, and the engine resolves the names.
A name that resolves to nothing, or to the wrong entity, breaks the story
silently. So grounding means one thing: **every name a model may use for a
place, thing or person resolves to exactly the right entity, in the scene
where it is used.**

A group's scoped aliases name it only while the group is placed and in scene
scope. Plain words therefore stay free to name different people in other
scenes.

## Detail index

- [Scene places](world-model-grounding/scene-places.md): read this when setting a scene's area, naming sub-places, or handling new matched entities.
- [Things](world-model-grounding/things.md): read this when declaring, placing, or configuring physical things and their relations.
- [Characters and names](world-model-grounding/characters-and-names.md): read this when placing NPCs, setting companions or states, or choosing aliases and leak terms.
- [Placement payloads](world-model-grounding/placement-payloads.md): read this when checking what placement text and Details entries the shipped narrator receives.
- [Prompt inputs](world-model-grounding/prompt-inputs.md): read this when changing THINGS, PLAYER, rules, examples, or match-call material shown to a model.
- [Prompt outputs and judges](world-model-grounding/prompt-outputs-and-judges.md): read this when changing reply fields, world-change capture, or judge inputs.
- [Verification](world-model-grounding/verification.md): read this when testing tree properties or prompt behavior.
