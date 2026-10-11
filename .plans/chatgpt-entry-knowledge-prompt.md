# Brief for ChatGPT Desktop: fix two scene-entry knowledge lines that state a reveal too early

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the files named below yourself, then answer the task at the end. Cite a file and line for every claim. Story lines are yours to write; do not edit any file, and do not run billed calls.

## The problem

Each scene has one public "scene entry" knowledge item in `data/stories/continuity-initiative/knowledge.yaml` (ids `k_scene_1a_entry` ... `k_scene_3c_entry`, `source: {kind: scene_entry}`, audience public, player-visible). Its `statement` is scene framing that goes to the narrator as context for the whole scene (`storygame/runtime/knowledge.py`, search `scene_entry`; `storygame/runtime/cloudflare.py`). Its `aliases` are words the engine treats as known and public in that scene.

Two of these statements say something the plot has not yet staged when the scene starts. A review found them (decisions file: `.plans/disclosure-decisions.md`, section "Source conflicts"):

1. `k_scene_2c_entry` says "The purge clock is active and the group must act under pressure." Aliases: `purge clock`, `purge`. The plot makes the purge an issued order with a deadline only in 2C.2 (`data/stories/continuity-initiative/plot.md`, "Scene 2C.2 - The Purge Order", fact `purge_clock_started` in `knowledge.yaml`). At 2C entry the danger is a fear of a purge, not an active countdown.
2. `k_scene_2a_entry` says "The protagonists are entering the facility under false identities." Aliases: `false identities`, `facility entrance`. Scene 2A starts at Brandon's hideout (`plot.md`, scene 2A front matter and 2A.1). The false credentials are made in 2A.2 (fact `false_identities_ready`) and tested in 2A.3. At 2A entry they are planning, not entering.

Because the narrator reads the statement as true, it can narrate the later event in the opening turns, and the player skips the scene's own build-up.

## Decisions already made (do not reopen)

From `.plans/disclosure-decisions.md`:

- **purge clock:** narration may not present it as an active countdown before the purge order. Earlier fear of a possible purge is fine. It unlocks on `purge_clock_started` (2C.2).
- **false identities:** may be said early as a proposed cover. The credentials being ready is `false_identities_ready`. Passing the checks is later.
- **facility entrance:** may be said early. By 2A the facility is already found. Arrival, passing checks, and access to restricted areas must wait.
- General rule: custody is not secrecy, and an unlock follows a learned fact, never a scene number.

## Task

1. Rewrite `statement` (and `aliases` only if needed) for `k_scene_2c_entry` and `k_scene_2a_entry` so each is true at scene entry and matches the decisions above. Keep `id`, `entity_ids`, `audience`, `available_in_scenes`, `establishes` and `source` unchanged unless you give a reason from a file. The statement is narrator-facing: short sentences, one idea each, plain common words, at a 12th-grade reading level or lower. Do not use words like "authored", "grounding" or "segment".
2. Decide for each alias whether it stays in the public entry item. For `purge clock` and `purge` in 2C, check where else those words are declared (search `knowledge.yaml` for `purge_clock_started` and the aliases of the 2C reveals such as `k_sl_2c_b_r1`, and `world.yaml`). If the alias also belongs to a reveal that unlocks on `purge_clock_started`, say what happens to the word before the order if it leaves the entry item (it becomes guarded until then, which is the intended result) and whether anything in 2C.1 needs to say "purge" earlier (for example the entry text or the Rebecca offer). If removing it blocks a sentence the existing scene text needs, say so and give the alternative.
3. Sweep the other seven entry items (`k_scene_1a_entry`, `1b`, `1c`, `2b`, `3a`, `3b`, `3c`) against the plot. Report any that state a reveal before the plot stages it. Give a table: item, statement as written, the plot line that stages the event, verdict (ok / too early), and a rewrite only if too early. Do not rewrite items that are ok.
4. Check the scene `objective` lines in `plot.md` front matter for the same fault (2C: "Survive the purge clock and choose a combined mission"; 2A: "Enter the facility under false identities"). The objective is shown to the narrator and may be shown on screen (`cloudflare.py`, `_scene_entry` returns `objective`). Say whether each is a problem and, if so, give a replacement that is true at entry. Do not change anything else in the front matter.

## Constraints (check every one yourself)

1. **Prior art.** Read how earlier scenes word their entry items (for example `k_scene_1c_entry`, `k_scene_3a_entry`) and the decisions in `.plans/world-model.md` (W decisions) and `docs/world-model-grounding.md`. Recommend only proven techniques. If you propose something new, say so and say what you checked.
2. **No early secrets.** The new wording must not contain a protected term for a later reveal. The loader rejects authored prose that contains a guarded leak term (`storygame/story_package/loader.py`, `_validate_narration_term_traps`; `leak_terms` sections in `knowledge.yaml`). Check each new sentence against those lists.
3. **Grounding.** Every physical thing the wording names must exist in `world.yaml` and be placed (`docs/world-model-grounding.md`). Do not introduce a new place, thing or person.
4. **Entry text and bridges stay byte-identical.** Do not change any `entry_text` or `bridge_text`, except where item 2 shows a specific sentence cannot work without it. If so, quote the current line and give the smallest addition, and say plainly that it is a change to player-visible text.
5. **Do not touch** pacing lines, penalty lines, handoffs, or the Michelle message content.
6. **Player input** in any example you give is imperative and first-person-possessive for the player's own things ("Search the drawer.", "Check my laptop."), never "I search...", never "Wait.".

## Deliverables

- Paste-ready YAML for the two entry items (full item text, ready to replace the existing lines), with a one-line reason for each change.
- The alias decision for each of `purge clock`, `purge`, `false identities`, `facility entrance`, with the evidence for it.
- The sweep table from task 3 and the objective verdicts from task 4.
- A cheap offline check before any billed run, written as commands the repo already supports: load the package (does `load_story_package` pass?); run `uv run python scripts/disclosure_matrix.py --out-dir /tmp/dm` and compare the 2A and 2C rows for `purge clock`, `purge`, `false identities`, `facility entrance` in the early state with `.plans/disclosure-matrix.json`; run `TMPDIR=/tmp uv run pytest -q tests/test_leak_terms.py tests/test_narration_term_traps.py tests/test_knowledge_leakage_matrix.py tests/test_design_review_fixtures.py`. Say what result would make you drop the proposal.
- An honest limit statement: what offline checks cannot show (that the narrator stops narrating the later event in the opening turns), and the smallest live test that would (a blind-player run of 2A and of 2C, how many replicates, what to count; for example, how often the first three narrations mention the purge order or the passed identity check).
- If you conclude the entry item is the wrong place to fix this (for example the objective line is the real cause), say so and name the evidence. Do not propose a runtime change, a narrator rule or a matcher change.

Keep sentences short.
