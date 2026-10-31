# Worldkeeper boundary round 1

The parity probe bootstrapped `RuntimeState.bootstrap(load_story_package(Path("data/stories/continuity-initiative")))`, built the adapter World, and compared the new helpers with their legacy functions on `kristin`, `mcgehee_home`, `michelle_drawer`, and `memory_card` (plus several package entities). It passed for every comparison below.

## `World.descendants`

Replaces the containment walks in capture and observation. Observation is the ordering authority: both direct children and deeper children are breadth-first in `World.contents` order. Capture returned a set and used stack-pop traversal, so its order was not observable; membership matched on the real acyclic package. The new method is cycle-safe and excludes the root if malformed state points back to it; this resolves observation's missing cycle guard while preserving valid-world membership.

## `World.contains`

Replaces traversal's `_contains` and the item-facts parent climb. The legacy traversal arguments were `(entity_id, ancestor_id)`; this method intentionally uses `(ancestor_id, entity_id)` and preserves self-containment, `None` termination, and cycle-safe parent walking.

## `World.under_contents`

Replaces the direct world query in `_observation_underside_is_exhausted`. It is direct-only, filters exactly relation `under`, and keeps `World.contents` order; `on` and `in` children are excluded.

## `World.open_state`

Replaces capture's `_focus_open_state`. It returns only `open` or `closed`, and returns `None` for `None`, unknown, non-openable, non-container, or unsupported-axis values. The declared package matched the legacy helper. Requiring `is_openable` also makes the requested world gate expressible as `open_state(focus_id) == "closed" and world.sees(observer_id, focus_id)`; command kind and model `opens` remain storygame concerns.

## `World.is_item`

Replaces observation's `_is_item`, retaining `is_a` ancestry semantics and false for unknown IDs. Containers, supporters, furniture, and vehicles remain excluded even through custom-kind ancestry.

## `World.observable_items`

Replaces observation's `_candidate_ids`. The real-package probe matched for absent, unknown, area, container, supporter, item, and unrelated focuses. It preserves sorted `entity_ids` order for area scopes and the new breadth-first descendant order for containment scopes; hidden and unplaced entities retain the legacy candidate behavior.

## `World.required_observations`

Replaces observation's `_required_ids`. The probe matched item, container, absent, and unknown focuses. Under requests remain direct-only and require `sees`, while normal container/supporter requests use all descendant IDs and visibility filters.

## `World.moved_since`

Extracts the pure parent-change portion of capture's `_moved_unrelated`; exclusion construction remains storygame-specific. The legacy function returns sorted unique names. This method returns the corresponding IDs sorted by `(World.name(id), id)` so the caller can map them back with `candidate_world.name(id)`; on real IDs `('kristin_laptop', 'memory_card', 'michelle_phone')` mapped to exactly the legacy name tuple. It preserves the thing-kind filter and both non-`None` parent guards.

## `WorldSchema.related_areas`

Replaces narration safety's package-location walk with declared schema area entities. It includes the requested area, all ancestors, and all descendants as a `frozenset`, with cycle-safe ancestor handling. The real package matched the legacy validator for sampled locations.

## `WorldSchema.area_ancestors`

Replaces narration safety's `_location_ancestor_ids`; it excludes the requested area and returns a `frozenset`. The real package matched the legacy validator and preserved nearest-to-farthest membership semantics (the set makes order immaterial).

`WorldSchema.from_data(world_schema_data(package))` was checked against every `package.world.locations` entry: all declared location IDs were present and every parent matched (`True`).

## Optional helpers

All optional world-only helpers were separable and were added and tested:

- `World.current_seat` preserves the declared `seat_for` check from `seat_before_use`.
- `World.reachable_from_seat` returns the same names and entity ordering used by `stand_before_leave`; visibility, seat/vehicle exceptions, holder checks, and cycle-safe chains are world-only.
- `World.takeable_items` extracts the sorted candidate IDs from `take_before_put`, with package item `fixed` bits represented by `fixed_ids`.
- `World.fixed_visible_items` extracts the sorted candidate IDs from `refuse_fixed_move`, including the explicit `scope_ids` override.
- `World.visible_vehicle_seats` preserves visible vehicle filtering and sorted visible seat IDs from `board_vehicle`, using the same declared-seat data as `World.seats`.

The visible seat selected by round 2 is confirmed to be `sorted(world.seats(vehicle_id))[0]`, matching `board_vehicle`'s sorted seat list. The companion filter in `_fact_move_overrides` remains a storygame client comprehension over `world.companions` and `world.parent`.

No optional helper was skipped.

## Verification

The new boundary tests cover ordering, unknown/`None` values, cycles, hidden and unplaced entities, under/on/in relations, nested areas, seats, and companions. The requested package pytest, legacy `tests/test_world_model.py`, Ruff check, Ruff format, and `check_round1.sh` are the final gates; no storygame callers were changed in round 1.
