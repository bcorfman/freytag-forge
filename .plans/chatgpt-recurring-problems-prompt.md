# Brief for ChatGPT Desktop: the recurring problems that keep the game from being finished

You are advising on freytag-forge, an interactive-fiction engine with one shipped story ("The Continuity Initiative", nine scenes: 1A 1B 1C 2A 2B 2C 3A 3B 3C). A player types free text. A small non-reasoning Llama-class model narrates each turn. The engine, not the model, owns the world facts. Read the whole brief, then answer the task at the end. Do not give generic advice about LLM games. Every claim you make must tie to the evidence below.

## How the game works (what you need to know)

- The player types an imperative command ("Search the drawer.", "Open the surface gates."). Never first person.
- Each scene has **reveals** (called knowledge items): a short statement the player earns by an action. A reveal has `action_evidence`: groups of words. A command matches when it has a word from EVERY group (verb group + object group). **Exactly one reveal may match** a command. Two matches return none.
- A reveal belongs to a **storylet**. When one reveal of a storylet fires, the storylet is spent and its sibling reveals are no longer offered (`knowledge.py _candidates`: `item.source.storylet_id in state.fired_event_ids` is skipped).
- A reveal has `requires` facts (an order), `delivery_text` (fixed authored text appended to the narration), and a **cue** (`cue_text` in `handoffs.yaml`): one scene-description sentence shown to the player to point at the thing to act on. Cues are staged: shown only when the reveal's `requires` are met.
- Each scene has a timer (13 turns). At the timer the engine delivers the missing reveals as authored `fallback_text` and moves on. So a scene never hangs, but a scene that exits by timer means the PLAYER did not make the story move.
- The narrator sees a prompt with SCENE (the earned statements plus the scene frame), THINGS (the world entities and their places), CONSTRAINTS. It is told not to invent objects. It is a small model: rules must be at an 8th-grade level and one idea per sentence.
- The narrator only gets reveal material when a reveal is a CANDIDATE that turn. When no candidate matches the command, the prompt says "This turn has no candidates" and the narrator improvises from SCENE and THINGS.

Hard rules (do not break them in your proposal):
- Facts are the sole mutable truth. The shared runtime is story-agnostic and LLM-proposal-first. No story-specific runtime branches, fixed action tables, hand-edited generated artifacts, or prose as canonical truth. No unvalidated provider output. No fact change after rendering.
- Story and plot text is written in ChatGPT Desktop (you), then scored with the real matcher. Code changes are done by cheap worker models under a tool that runs an executed check.
- The engine must serve more than one story. A fix that names this story's nouns in code is not allowed.
- Narration is live (free-text input is the reason). Authored deterministic text is preferred over LLM generation where possible.

## The measurement

An LLM "blind player" plays each scene from the opening, three replicates in parallel, on a hosted staging copy. Each scene reports an exit cause: **play** (the player earned the transition) or **timer** (the 13-turn timer ended it). The bar is play exit in at least 2 of 3 replicates per scene. Rejected turns (the engine refused narration for an unavailable name) are counted too.

Latest run (staging 41240bb, 2026-10-10, all nine scenes x3):

| Scene | Play exits | Notes |
|---|---|---|
| 1A | 2/3 | the third player never tried the drawer |
| 1B, 1C, 2B, 2C, 3B | 3/3 each | |
| 2A | 2/3 | one timer, one rejection |
| 3A | 1/3 | main failure |
| 3C | ended 3/3 | all seven steps fired by play (it was 0/3 two days earlier) |

Three rejected turns in the run: 2A "detention level", 2B "coded message", 2C "rebecca's desk".

## The recurring problems (the pattern across many rounds)

1. **The player stalls after the first reveal of a scene.** Scenes 1C to 3B all stalled after their first reveal until we fixed them one by one. The player does not know the next step, or tries it in words the matcher does not accept, or tries a step whose reveal is already spent.
2. **Evidence words never fit what a player types.** Each scene needed several rounds of widening verb and object groups (2A, 1C, 2B, 2C, 3A, 3B, 3C, 1A). Every widening risks a double match (two reveals match, none fires), so each round is also a collision check. New wording keeps appearing the next run.
3. **Spent siblings are dead ends.** Example now: 3A reveal `k_sl_3a_b_r2` ("enter the medical level") fires the storylet; the sibling `k_sl_3a_b_r1` ("read the experiment records") is no longer offered. Two of three 3A players then typed "Examine/Read/Open the experiment records." up to nine times in a row. Nothing fires, and the narrator answers without any candidate. Same class as 3C where the C/D split was needed so one reveal did not consume the other.
4. **The small narrator invents and pulls.** With no candidate it invents (a paper note in 1A, "torn fabric" and a "silver thread" on the 1A door hinges, a made-up warehouse and oak tree, a medical terminal and patient records). Lines in SCENE pull it toward the wrong goal (two earned 2C lines pulled 3A players to Rebecca's office). The narrator often ignores the command and restates the scene.
5. **Leak and unavailable-name rejections.** A thing named in a later scene is rejected when narration mentions it earlier, and a thing placed only in some scenes is rejected in scenes that talk about it (the surface gates, 5 rejected turns). Each new scene or edit can reintroduce one.
6. **Each fix is measured by a full billed live run**, then the next scene shows a new problem. We close one scene and lose time re-finding the next. Small samples (3 replicates) make noise hard to tell from a real gap.

## What we already tried (synopsis, with outcome)

Engine and structure
- **Missed-obligation escalation**: an obligation ledger, timed expiry of optional storylets, a ranked Cue, state-matched Complications, a Deadline backstop. Built; used. It makes the timer deliver missing reveals as authored text. It does not make the player act.
- **Staged cues** (PR 520): a cue shows only after the reveal's `requires` chain is met. Fixed "last step shown first" in 3A/3B. Kept.
- **Cue-derived matching** (once a cue is shown, its named things count as accepted objects with a broad verb class): proposed as the whole-game fix. Dropped by the project owner (2026-10-06) in favour of per-scene wording ("option A"), because it could fire a reveal on loose interaction and had no precedent.
- **Bare-noun resolution and disambiguation** (a bare "terminal" resolves to the one thing of that name in the player's scene; two matches ask "Do you mean the archive terminals or the medical terminal?"): scoped and checked offline against 283 recorded commands. It would have fixed only a few 3B relay commands, not the 2B misses. Design decided (an Inform-style question, the answer spliced into the old command, pending state kept out of snapshots). Not confirmed built. Verify before relying on it.
- **3C cue chain** (PR 565): split storylets so C and D each need both parts, cues staged through the resolution chain, the loader rule that every resolution event's activation facts be guaranteed or produced earlier. 3C went from 0/3 to a chain of 4/5/7 steps and then to 7 of 7 in all runs after the verb widening (PR 566, 568).
- **Parallel L2 replicates, per-scene continuous run, opening retry, narration retry hint**: built for speed and robustness.
- **Reveal handoffs**, fixed authored `delivery_text`, and pointer sentences in deliveries to name the next step. Used scene by scene; this is the strongest proven fix.

Story and wording
- Per-scene **wording rounds** with ChatGPT Desktop (1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C): widen evidence groups, add cue sentences, add pointers. Each round scored offline with the real matcher (a command table with expected matches and every double match reported). Works, but one scene at a time, and each scene needed two to four rounds.
- **Declared things and placements** per scene (surface gates in 3A/3B/3C, drawer contents). Rename the fiction to remove a name collision. A later-scene bare common word is rejected earlier, so give scene-specific names.

Narrator
- **Narrator rules**: tried the go-into-a-place rule (1/15 vs 4/15 baseline, worse), the plain-corridor rule and the copy-refers rule (both worse). One won: "When the player talks to someone, that person answers." Rule: narrator rules come last.
- **Line removal** (take two earned 2C lines out of 3A's SCENE): cut the pull toward Rebecca's office in the narrator probe (check the plan for whether it was applied; 3A still stalled afterwards).
- **Replaying recorded prompts** with one arm per candidate cause (10 to 15 samples, read by hand) is the proven diagnostic. It found: 3A pull lines, 2C stance, 3B office entry.

The latest 3A probe (just run, 80 narrator calls): the recorded 3A prompts for "Examine/Read the experiment records." after the medical level was entered. Arms: A as recorded; B add the records reveal's statement line, copied unchanged; C add the plot sentence "The senior official waits among the government prisoners."; D both. Scoring by reading: **no arm made the narrator answer the command.** A (10/10 and 10/10) restated the scene ("Kristin looks around the detention sector... searching for any clues"), never reading records and never naming the official. B pulled the narration back to the reunion ("Kristin's eyes lock onto Michelle... relief and joy") in about 4 of 10 samples on one command and most of the 10 on the other. C changed nothing. D mixed both. Adding story material to SCENE does not fix a command that has no candidate and names nothing in THINGS.

## What the evidence suggests (my read, challenge it)

- The deterministic layer (matcher, reveal order, spent siblings, cues) is where agency is lost. The narrator layer then fills the gaps badly. Fixing the narrator with more lines and rules has mostly lost.
- Most stalls are "the player acts on a thing the story already told them about, in an order or form the reveal graph does not accept". The engine answers with an improvised paragraph and no state change, so the player cannot tell they were wrong.
- We fix by hand, one scene at a time, and it does not generalise to the next story.

## Task

Propose the smallest set of changes that would let us **finish**: every scene at 3/3 play exits with no rejected turns, and robust enough that a new story does not repeat the cycle. Rank by (expected gain across all nine scenes) / (cost and risk). For each proposal:

1. Name the problem number(s) above it addresses and the exact evidence it answers (for example the 3A records dead end).
2. Say whether it is a **proven technique** from the synopsis or **new**. If new, say plainly why no proven technique covers the case, and name the one risk that would make it lose.
3. State where it lives: story text (you will write it), engine or loader code (a worker will build it, story-neutral), or the test harness. If it is code, give the rule in plain words and the hermetic test that would prove it, without naming this story's nouns.
4. Give a **cheap offline check** before any billed live run (for example: replay the 283 recorded commands through the real matcher; list every command whose result changes; read each one). Say what result would make you drop the idea.
5. Say how it interacts with the one-match rule and the spent-sibling rule.

Specifically answer these:
- (a) What should happen when a player acts on a thing in a spent sibling's territory (the 3A records after the medical level)? Options to judge include: a deterministic engine reply naming the next step, keeping sibling reveals offered after the storylet fires (and what that does to facts), merging the two reveals into one, or something else.
- (b) What should the engine do when a command matches no reveal but names a thing the story has already shown? A fixed authored line, a nudge toward the next requirement, or leave it to the narrator? Weigh against "authored deterministic text over LLM generation".
- (c) Is there a story-neutral way to stop the narrator from restating the scene when a command has no candidate, other than a prompt rule? Judge it against the narrator rules that lost.
- (d) How should we decide a scene is done with 3 replicates per run? What sample size or scoring would separate a real gap from noise without paying for many more billed runs?
- (e) Which one change would you do first, and why not the others?

Format: a short diagnosis (at most 10 lines), then the ranked list, then the first change as a paste-ready spec a worker could build or a set of story lines I can paste. Keep sentences short. Do not propose rewriting the engine or switching the narrator model (unless there's no other alternatives), or adding story-specific code.
