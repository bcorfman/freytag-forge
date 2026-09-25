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
