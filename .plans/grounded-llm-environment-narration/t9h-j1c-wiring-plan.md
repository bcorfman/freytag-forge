# T9h route E: wire J1c into the observation verifier (plan, DRAFT 2026-10-29, nothing built)

Status: DRAFT for Brandon's approval. Source of the rule: `t9h-j1-scope-prereg.md` (J1c passed F1 to F3, 620 requests). This plan builds the product change behind a flag and sets up the enforced run that decides whether it fixes the drain miss. A passing screen does not qualify enforcement.

**What changes.** When a required relation's place is the scene's own location (the thing's immediate parent is the scene's `location_id`) and nobody holds it, the verifier's request state gains `scene` and `starting_places` (J1m). Every other request stays exactly as today. Questions are never changed.

## Design (from reading the code, 2026-10-29)

- `storygame/runtime/observation.py`: `build_observation_context` gets an optional `scene_location_id`. `ObservedThing` gets `scene_level: bool = False`, true when `world.parent(thing) == scene_location_id` and the thing has no holder. `ObservationContext` gets `scene: str | None`, the label of the scene's location. The comparison is by entity id, not by the display string, so "Los Angeles park" against `los_angeles_park` cannot silently miss.
- `storygame/runtime/observation_verifier.py`: `Relation` gets `scene_level: bool = False`; `relations_from_context` copies it. `ObservationVerifier(..., scene_state=False)` and `verify(narration, relations, *, scene=None)`: with the flag on, a scene, and at least one scene-level relation, the state is `{"narration", "scene", "starting_places": {thing: place}}` with entries only for the scene-level relations; otherwise exactly `{"narration": ...}`. `VerifierReport` records whether the scene state was sent, so the enforced run can be read per turn.
- `storygame/runtime/item_facts.py` `_observation_context` passes the current scene's `location_id` (it already reads `scene.metadata.location_id` elsewhere). `storygame/runtime/capture.py` passes `context.scene` at both `verify` calls (enforcing and shadow).
- `storygame/web_demo.py`: a new flag `FREYTAG_OBSERVATION_SCENE_STATE=1` builds the verifier with `scene_state=True`. A separate flag, so the enforced run can compare it with the current verifier on the same deployment. Default off; nothing changes when unset.

## Two untested product conditions (found while reading the code)

1. **The scene value.** Scenes have no title field (`SceneMetadata` has `scene_id`, `location_id`, `objective`, text). The screens sent a title ("Keeper's Yard") or a story name. The product would send the location's label ("Los Angeles park"). The fresh held-out titles were close to their place strings, but this is not what was measured.
2. **Mixed batches.** The fresh cases were single-relation requests. A real turn can batch a scene-level relation with specific-place ones, and `starting_places` then holds only the scene-level entries.

Step 2 below measures both for about $0.005 before the product change is built.

## Steps (each code change through a Ringer task, tests first, ruff after; focused tests between steps, the full suite once at the end)

1. **This plan approved.** Brandon's decision.
2. **Wiring probe (free build, tiny billed run, its own preregistration and go).** Reuse `j1_scope_probe.py` and the locked fresh cases: (a) the 30 scene-level cases with `scene` set to the location label (`scene_place` without "the", capitalised as the product labels it) instead of the title; (b) 12 mixed-batch cases built from fixed pairs of locked cases (one scene-level, one specific-place; positive/negative combinations written down before any score), each asked V0 and J1c-as-the-product-would-send-it. About 5 samples each, under 300 requests, ceiling under $0.01. Gate: the same F1 and F2 numbers as the scope screen on (a), and zero negative accepts with every positive pair member accepted at least as often as under V0 on (b). A failure stops the plan here and changes the design, not the gate.
3. **Product change behind the flag (Ringer build task).** Tests: the drain relation (thing `storm drain`, parent the scene's location) sends `scene` and `starting_places`; a drawer-contents relation sends exactly the V0 state and the same question; a held relation is never scene-level; flag off sends V0 for every relation; a mixed batch carries only the scene-level entries; the question text is identical with the flag on and off; the report records `scene_state`. Existing `tests/test_observation_*.py` and `tests/test_web_demo_observation_enforce.py` stay green. A story-data test over the compiled continuity-initiative package counts, per scene, the items whose parent is the scene location (reported, not asserted), which answers the free check at no extra cost.
4. **Enforced-run preregistration (new document, then Brandon's go).** A fresh enforced stage run under the staging rules (`docs/railway-production-promotion.md`; E2E against the hosted demo only; never merge to main mid-run): route E (1B) with the flag on, the route C/D regression, and the current verifier beside it. Gates to be set in that document from the T9h confirmation preregistration (G1 unsuccessful turns, call budget) plus a drain-specific gate on `inspect the storm drain`. It also checks that the `scene_state` flag was sent on the drain turn. This run, not the screen, decides whether the drain miss is closed.
5. **Update the active plan after each step.**

## Risks stated up front

- F2 passed by one case (the tin kettle stayed uncertain at 0.55 to 0.62). A real scene-level thing may behave the same and stay rejected; J1c lifts the drain case in the probes, it does not guarantee every scene-level thing.
- The unrelated-move guard (route E's other failure, the hidden items picked up on `search the park bench`) is a separate cause and is not touched here.
- Two areas with the same label would not matter (ids are compared), but the `scene` string is a label, so two scenes in one area share a scene value.
