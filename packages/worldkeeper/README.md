# worldkeeper

`worldkeeper` is a fact-backed world model for text adventures and narrated roleplay.
Kinds and declared entities are static schema; all changing state is in the backend.

```python
from worldkeeper import MemoryBackend, World, WorldSchema

schema = WorldSchema.from_data(
    {
        "entities": [
            {"id": "cottage", "name": "cottage", "kind": "area"},
            {"id": "ada", "name": "Ada", "kind": "character"},
        ]
    }
)
w = World(schema, MemoryBackend())
w.seed()
w.move("ada", "cottage")
assert w.area("ada") == "cottage"
```

Facts use `wk_` predicates. The fact encoding is:

Kinds may declare `fixed: true` or `fixed: false`. When an entity does not
declare its own flag, the nearest kind declaration supplies it; otherwise a
descendant of `furniture` is fixed by default.

- `wk_kind`, `wk_name`, `wk_owner`, `wk_parent`, `wk_relation`, `wk_status`,
  `wk_place_text`, and `wk_unplaced` store their ID or free text in `value`;
  their `object` is `None`.
- `wk_axis` stores the axis name in `object` and its pole in `value`.
- `wk_condition` stores the zero-based condition index in `object` and the
  phrase in `value`.
- `wk_companion` stores the leader ID in `object`; `wk_hidden` and `wk_moved`
  use the fixed object `"true"`.

All facts are built through `make_fact`, and predicates that are not prefixed
with `wk_` are ignored.

## Incidental props and facets

`IncidentalPolicy` supplies a per-scene pool of `PropTemplate` declarations,
existing-entity facet palettes, authored facet values, and bounded turn, scene,
game, and per-object facet limits. `World.check_embellishments` validates a
batch without changing facts; `apply_embellishments` validates the complete
batch and then commits it atomically. Props are ordinary `thing` entities and
traits are cosmetic facet values only.

Incidental provenance is recorded as `wk_incidental` with the entity as subject,
scene ID as object, and template name as value. Stored facets use `wk_facet`
with the entity as subject, facet as object, and value as value. Fixed props
also receive `wk_fixed` with object `"true"`. Provenance and allowance facts
are never retracted, so moving or disposing a prop does not restore capacity.
Template names must be eligible and unused, parents must be exact visible
allowed holders, and all props and traits in a batch must pass before any real
facts are changed. Facets must come from the applicable palette and cannot be
changed after being set; authored values take precedence and count toward the
facet limit.

Condition phrases that exactly match one approved palette value can be routed to that cosmetic facet; ambiguous or unapproved phrases remain free conditions, and refused facet changes are reported without consuming incidental allowances.
