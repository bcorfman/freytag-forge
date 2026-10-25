# T2 audit: what worldkeeper can say about what the player sees

Audited 2026-10-25 at `14f11314`, `packages/worldkeeper/src/worldkeeper/model.py`.

## What exists

| Query | Answers | Does not answer |
| --- | --- | --- |
| `is_visible(id)` | Exists, not hidden, not status `missing`, not inside a closed openable container (checked up the whole chain). | Who is looking. Where they stand. Whether a surface is see-through. Any difference between inside and outside a vehicle. |
| `is_shut_away(id)` | Hidden only because a container in its chain is closed. | Whether the container is see-through. |
| `given_with(id)` | Visible `on`/`under` children of a supporter. `in` children of a container, visible or shut away. | Observer; completeness of the list. |
| `together(a, b)` | Same area, or nested areas. | Line of sight. It is a reach test, not a sight test. |
| `holder`, `chain`, `parent`, `relation`, `contents`, `place_label` | Current custody and placement from facts. | Nothing missing for the first slice. |

Known gaps against the plan:

1. **No observer.** `is_visible` is a world property. The laptop on the passenger seat is "visible" from the driveway and from the cab alike. The planned "look through the window" row (outside view allowed, opaque view withheld) cannot be told apart from "enter the truck" by any current declaration.
2. **No search-scope completeness.** Nothing says a container holds only what the world lists. An empty `contents()` is the same fact for "searched, nothing" and "never described". The "search beneath the drawer after recovery" row needs a generic, open-world-by-default declaration.
3. **`given_with` mixes two jobs.** It returns shut-away container contents so an opening action can resolve. The projection must keep those apart as action-contingent, never as already seen.

## Minimum schema change (add only when a T3 test needs it)

Both are optional, package-level, story-agnostic, and default to today's behaviour:

- `view`: on an entity, a list of `{from: <area or entity>, blocked_by: <axis=pole> | null}`. A thing inside the entity may be seen from `from` unless `blocked_by` currently holds. No entry means no outside view.
- `contents_complete`: on a container or supporter, a boolean. Only `true` plus an empty known-contents list licenses an unqualified empty result. Absent means open world.

The engine never names a truck, laptop, or scene. T2 proves the need with the tests below; T3 builds the schema only for the tests that fail for want of it.

## Projection boundary decided for T3

`storygame/runtime/observation.py` is pure and story-agnostic. It takes a worldkeeper `World`, the observer id, a typed request, and the completed implicit actions, and returns an immutable `ObservationContext`. The typed request kind (`look`, `open`, `enter`, `none`) comes from the existing bounded intent proposal, never from a verb table. Public names only reach the narrator; ids stay inside.
