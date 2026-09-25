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

Facts use `wk_` predicates. Values are in `object`; `wk_axis` also uses `value`
for the axis name. Every library predicate has a non-null object.
