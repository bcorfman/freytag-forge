Part of [Markdown story authoring](../markdown-story-authoring.md).

Incidental props are optional harmless objects that can appear in a scene.
Declare them in the `props` list in `world.yaml`.
Each prop has an id, a name, one or more parent location or item ids, and an optional fixed flag.
The parents say where the object may be placed.
You may give a prop a small facet palette.
Each palette names cosmetic choices such as colors or finishes.

Scene front matter may contain `prop_pool`.
This tuple lists the declared props that may be used in that scene.
An item may also declare `facets` for cosmetic choices.
An item may declare `authored_facets` for values chosen by the author.
Authored facet values win over palette choices.

The allowances are one new object per turn, three new objects per scene, and twelve new objects per game.
At most three facet names may be declared on one prop or item.

Props are ordinary harmless things.
They have no clues, tools, openings, containers, or characters.
A prop name must not clash with any authored location, NPC, group, or item name or alias.

The loader checks prop ids, parent ids, names, scene pools, and scene availability.
It checks that facet names and values are present and non-blank.
It rejects duplicate facet values.
It rejects more than three distinct facet names, including authored facets.
It also rejects unknown scene props and props whose parents cannot occur in that scene.
