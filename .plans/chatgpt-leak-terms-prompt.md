# Brief for ChatGPT Desktop: the narration leak scan keeps rejecting ordinary words

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the whole brief, then answer the task at the end. Do not give generic advice about LLM games. Every claim you make must tie to the evidence below.

## How the game works (what you need to know)

- The player types an imperative command ("Open Michelle's message.", "Confront Rebecca about the broadcast controls."). Never first person.
- Each scene has **reveals** (called knowledge items): a short statement the player earns by an action. A reveal has `action_evidence` (words the player's command must contain), `requires` facts (an order), `delivery_text` (fixed authored text appended to the narration), and `must_convey` (groups of synonym phrases, one phrase from each group must appear in what is delivered).
- A reveal is **earned** when its action fires and its `requires` hold. Before that it is unearned.
- The narrator is a small model. It sees SCENE, THINGS, CONSTRAINTS. When no reveal is a candidate it improvises from SCENE and THINGS, and it uses natural everyday phrases.
- After the narrator replies, the engine runs the **narration safety scan** (`storygame/runtime/narration_safety.py`). It rejects the whole turn when the narration contains a phrase the scan treats as knowledge the player has not earned. The player sees a failed turn and must retype.

Hard rules (do not break them in your proposal):
- Facts are the sole mutable truth. The shared runtime is story-agnostic and LLM-proposal-first. No story-specific runtime branches, fixed action tables, hand-edited generated artifacts, or prose as canonical truth. No unvalidated provider output, no protected-knowledge leak, no fact change after rendering.
- Story and plot text is written in ChatGPT Desktop (you), then checked with the real loader and scan. Code changes are done by cheap worker models under a tool that runs an executed check.
- The engine must serve more than one story. A fix that names this story's nouns in code is not allowed.

## How the scan decides a phrase is a leak

Built in `storygame/story_package/loader.py`, used in `_validate_segments`:

1. `term_to_knowledge` maps a phrase to the reveals that own it. A phrase gets in from (a) every item **alias**, and (b) every **multi-word phrase in any `must_convey` group** of a reveal. Single words are not leak terms.
2. `entity_alias_to_entities` maps every entity name and alias (from `world.yaml`) to its entity.
3. A phrase in the narration is rejected when its owner is not earned, not grounded in the segment, and not named by an authored exemption. The exemptions that exist today: the phrase is in a staged handoff's text; or in the projected beat text; or in an earned reveal's statement (protected terms only, not known terms); or the entity is nameable in the scene (scene items, participants, places, things held).
4. Rejection codes: `narration_known_term_leak` ("mentions unavailable knowledge 'X'" or "unavailable entity 'X'"), `uncited_knowledge`, `protected_narration_leak`.

The scene frame text (the short "situation" line) does not contain any of the phrases below, so the scan has nothing that licenses them.

## The measurement

An LLM blind player plays each scene from the opening, three replicates, on a hosted staging copy. Rejected turns are counted. Latest run (main a773378, 2026-10-11, all nine scenes x3): every scene left by play 3/3 for the first time. Seven turns were still rejected by the scan, none ended a scene, each cost the player a retype:

| Phrase rejected | Scene | Count | What the player typed | Owner of the phrase |
|---|---|---|---|---|
| `encrypted message from michelle` | 2C | 2 | "Open Michelle's message." | `must_convey` phrase of `k_sl_2c_d_r1` |
| `michelle's encrypted message` | 2C | 1 | "Decrypt Michelle's encrypted message." (the player copied the wording the narrator had invented) | same |
| `rebecca's desk` | 2C | 1 | "Confront Rebecca about the broadcast controls." | alias of entity `rebecca_desk`, a 3B-only item |
| `escape route` | 1B | 1 | a park search | alias of `k_scene_3c_entry` |
| `archive crisis` | 2B | 1 | a records-archive search | alias of `k_bridge_2b_archive_crisis` |
| `coded message` | 2B | 1 | "Decode Michelle's coded messages." | `must_convey` of `k_sl_2c_d_r1`, `k_sl_2c_d_r2` |

Earlier runs also rejected: 3B `charles jenkins`, `los angeles surface`, 3A `dr. michelle`, 2A `detention level`, 2B `phase`, 1C `phase`, 2C `rebecca`, the surface gates (5 turns).

## What the evidence shows

I reproduced the 2C case offline with the real validator and no billed calls. Scene 2C, c_r1 earned, the purge clock not started (it fires at turn 3, and the story gates the Michelle reveal on it, so that gate is plot):

- "Kristin opens the encrypted message from Michelle on her laptop." is rejected.
- "Kristin opens Michelle's encrypted message ..." is rejected.
- "Kristin opens the coded message from Michelle." is rejected.
- "Kristin opens the message from Michelle ..." is accepted.

The word "encrypted" is in the story only inside that reveal's own phrases. No prompt line carries it. The narrator invented a natural phrase, and the scan rejected it because the reveal's synonym list had registered it as a protected term. The phrase carries no secret. The secret content is the maintenance route, Rebecca's secured office, and opening the cells, and other phrases already guard those.

The other five are the same pattern: a generic phrase got registered as a leak term by accident.
- Alias lists on **scene-entry and bridge items** that restate the statement ("escape route", "archive crisis", "purge clock", "false identities").
- Synonym lists in **`must_convey`**, where one single word already satisfies the group, so the extra multi-word phrases do nothing for coverage and only add leak terms.
- A **entity alias** natural for a place (Rebecca's desk) on an item that exists only in a later scene.

A full audit of every multi-word leak term against the package's own authored text (plot, statements, delivery, cue, fallback) found cross-scene overlaps that have not yet been rejected in play, so they are likely next: `dead drop` and `park bench` (owned by 1A, used in 1B), `enter the facility` (1C, used in 2A), `rebecca's office` and `transmit the evidence` (2C, used in 3B and 3C), `service corridor` (2A, used in 3B), `relay open` (3B, used in 3C), `dr. michelle` and `michelle mcgehee` (1A, used in 1B to 3C). Many same-scene hits are legitimate reveal terms, so the audit is noisy.

## What we already tried

- **Commit cbc427b8 (Sept 2026):** generic "Michelle's message / her message / message from Michelle / Michelle's note" were leak terms of two 2C reveals and rejected ordinary early phone talk. Fixed by adding "encrypted" to make them distinctive. That moved the collision but it is the origin of today's "encrypted message" rejections.
- **Rename the fiction** to remove a name collision: pick a scene-specific name instead of a bare common word ("desk").
- **Add a person to the scene's `participant_ids`** so the scan lets the narration name them (fixed 2C `rebecca`, 3B `charles`).
- **Declared things and placements** per scene so a thing is nameable where the story talks about it (surface gates).
- **Staged handoff / beat exemptions** in the scan code.
- **This branch:** (1) removed the two "encrypted message" phrases from the first `must_convey` group of `k_sl_2c_d_r1` (the single word "message" still satisfies the group; delivery text untouched; suite and ruff green; offline tests accept both wordings before the reveal and still reject the maintenance-route sentence). (2) A second Ringer task (offline tests pass, suite green, not yet measured live) drops the generic phrase for the other four: removes `coded message` from the `must_convey` groups of d_r1 and d_r2, drops the aliases `archive crisis` and `escape route`, and renames the `rebecca_desk` alias to "Rebecca's executive desk". Everything above is per-phrase work, found one run at a time, and it will not stop the next one.

## What I think (challenge it)

- Rejections come from the scan treating a **phrase list** as a secret. A reveal's secret is its content, not every synonym a human might write for it.
- Each live run costs money and finds one or two new phrases. Fixing by hand does not carry to a new story.
- The scan has an exemption for protected terms found in an earned statement but none for known terms. That asymmetry looks accidental. Fixing it would cover `archive crisis` in 2B (its entry statement is earned at scene start) but not the others.

## Task

Propose the smallest overall change that stops the scan from rejecting ordinary narration, **without letting protected knowledge leak early**, and that works for a story it has never seen. Rank by (expected rejections removed across all nine scenes) / (cost and risk). For each proposal:

1. Name the rejected phrases above it answers, and the likely next ones from the audit.
2. Say whether it is a **proven technique** from "What we already tried" or **new**. If new, say why no proven technique covers it, and name the one risk that would make it lose.
3. Say where it lives: story data (you will write the lines), loader or scan code (a worker will build it, story-neutral), or the test harness. If it is code, give the rule in plain words and the hermetic test that would prove it, without naming this story's nouns.
4. Give a **cheap offline check** before any billed live run. The offline replay above is the model: build the scene state, feed a narration, read the error code. Say what result would make you drop the idea.
5. Say what it does to the protection of real secrets: name a real leak the scan must still catch, and show the test that catches it.

Specifically answer these:
- (a) Which phrases should be leak terms at all? State a rule for deciding, for example "only a phrase that names the reveal's content", and show how it sorts `encrypted message from michelle`, `maintenance access route`, `rebecca's secured office`, `archive crisis`, `escape route`, `coded message`.
- (b) Should aliases on scene-entry and bridge items count as leak terms? Judge removing them as leak terms against what they are used for (recall matching of the player's words).
- (c) Should `must_convey` multi-word phrases be leak terms, or only the delivered text and statement? If not all, which?
- (d) What is the right fix for an entity alias that is natural in an earlier scene but names a thing placed only in a later scene (Rebecca's desk)? Compare renaming the alias, a scene-neutral exemption, and declaring the item earlier.
- (e) Should the scan stay a hard reject, or become a rewrite or retry for non-secret phrases? Weigh it against "no unvalidated provider output" and the cost of a retry.
- (f) Which one change would you do first, and why not the others?

Format: a short diagnosis (at most 10 lines), then the ranked list, then the first change as a paste-ready spec a worker could build, or a set of story lines I can paste. Keep sentences short. Do not propose rewriting the engine, switching the narrator model, or adding story-specific code.
