# Brief for ChatGPT Desktop: a narrow declaration for the 2C "copied JANUS files"

You advised on a pointer sentence for the 2C opening and proposed declaring the files as a world item. The sentence is fine. The declaration, as written, causes new narration rejections in other scenes. This brief gives you the finding and asks for a narrow declaration. Read the files named below yourself. Cite a file for every claim. Story and world data are yours to write; code is not.

## What I changed and what I found

Applied (Ringer run in progress, branch `2a-supervisor-pointer`): the 2C `entry_text` now ends "Kristin carried the copied JANUS files. She could check them now." and nothing else. I did NOT apply your `world.yaml` item or the 2C `item_ids` and `item_placements`.

Why: your offline check scanned the sentence in an early 2C state only. I scanned ordinary narration in all nine scenes against three scratch copies of the package:

- `base`: the repository as it is.
- `v1`: base plus the sentence only.
- `v2`: v1 plus your item `copied_janus_files` (name "copied JANUS files", aliases `[copied files, JANUS files, JANUS evidence]`), `item_ids: [copied_janus_files]` and `item_placements: {copied_janus_files: {parent: kristin}}` in scene 2C only.

Files (read them): `~/dev/ringer-work/2c-declare/packages/{base,v1,v2}/` (full story folders) and `~/dev/ringer-work/2c-declare/cmp.py` (the script; it bootstraps a state per scene, feeds fixed narration through the real `RuntimeEngine` with a stub provider and prints any case where a variant differs from base).

Result:

- `v1` behaves exactly like `base` in all nine scenes. It loads and passes the loader's term-trap check.
- `v2` adds `narration_known_term_leak` rejections, in every scene except 2C, for narration containing "copied files" or "copied JANUS files" (1A, 1B, 1C, 2A, 2B, 3A, 3B, 3C), and in scene 2B for "JANUS files" ("Kristin opens the JANUS files in the records archive." is accepted by base and v1, rejected by v2). 2B is where players read the JANUS files, and the 2B reveal wording uses "JANUS files" (`handoffs.yaml`, fact `janus_evidence`).
- Cause (check it yourself): an entity alias is a guarded name in every scene where the entity is not nameable. Read `storygame/runtime/narration_safety.py` (the entity-alias check and the nameable-in-scene rules), `storygame/story_package/loader.py` (`entity_alias_to_entities`) and `docs/world-model-grounding.md`. Entity name and aliases from `world.yaml` become guarded phrases, and an item is nameable in a scene only if it is in that scene's `item_ids`/placements, a participant, a place, or held. Also read the memory-style precedent in `.plans/scene-affordance-e2e.md` for "desk" (a later-scene name rejected in earlier narration; fix was a scene-specific name) and the surface-gates fix (declare and place the item in every scene whose text names it).
- Retraction: in my first scan, "JANUS evidence" was rejected in every scene including base. That is an artifact of my bootstrapped state (the seven 2B reveals that own that phrase were not earned in it). In a real run those reveals are earned by 2C. Do not treat that as a defect. The scan script's own `janus_evidence` fact does not stand in for earning them. If you test anything with the phrase, set up the earned state or say that the result is not meaningful.

## The tension

`docs/world-model-grounding.md` says every physical thing the story text names that a player could act on must be declared and placed. The 2C opening now names "the copied JANUS files". Declaring them with common-word aliases breaks narration elsewhere. I want the smallest declaration that satisfies the guide without new rejections, or a reasoned case that the files need no declaration.

## Task

1. **Is a declaration needed?** Use the guide and the W decisions in `.plans/world-model.md` (search "copied", "evidence", "W4", the 2C entries and the earlier decision to declare no things upfront in 2C). What happens today when a narrator reply names "the copied files" in 2C and no entity exists: the engine creates a narrated thing (see `docs/world-model-grounding.md`, "NEW NAMES", and `.plans/world-model.md`). Say whether that already covers it, and what it costs (for example the thing's place defaults to the most local container).
2. **If a declaration is needed, make it narrow.** Choose a `name` and `aliases` that do not occur in other scenes' authored text or in the commands and narration the blind players actually produce there. Check by searching: `data/stories/continuity-initiative/*.md`, `*.yaml` and the saved runs under `~/dev/ringer-work/l2-1c10272f/`, `l2-41240bb/`, `l2-a773378/` (narration is in `text`). Then say in which scenes the item must be placed so its aliases are nameable where the story uses them: at least 2B (where "JANUS files" is used), 2C, and any later scene where players or narration say "copied files" or "JANUS evidence". Compare with how persistent carried items are declared now (`memory_card`, `transit_card`, Kristin's laptop: check their `item_ids` and `item_placements` per scene in `plot.md`).
3. **Alias use for recall.** Entity aliases also decide which player words recall which things. State whether your aliases change what the match call maps for "copied files", "JANUS files" or "JANUS evidence" in commands that currently fire `k_sl_2c_c_r1`, `k_sl_2c_c_r2` or any 2B reveal.
4. **Offline proof across all nine scenes.** Extend the approach of `cmp.py`: for each scene, run ordinary narration that uses each alias you propose, plus the 2B and 2C phrases blind players really used, through base and your candidate. State the result as a table. Any new rejection in any scene means the candidate is dropped or changed. Also run the candidate through the loader (term traps) and the five commands from your first answer through the matcher. Do not write files into the repository; use temporary copies.
5. **What you cannot prove offline.** Say it, and name the smallest live check (a hosted 2B and 2C run, how many replicates, what to count).

## Deliverables

- Your answer to question 1 in at most six lines.
- If a declaration is warranted: paste-ready `world.yaml` item lines, and for each affected scene the `item_ids` and `item_placements` lines for `plot.md`.
- The all-scenes table.
- If no declaration is warranted: the evidence, and the one risk of leaving it undeclared.

Keep sentences short. Do not propose engine changes, scan exemptions, narrator rules or a regex.
