# ChatGPT Astra prompt: how people reach the narrator (THINGS, "may say this aloud") — one holistic plan

Paste everything below the line into ChatGPT Astra. It has the project files open, so it reads them itself. Bring the plan back to
Claude Code, which applies it through Ringer tasks (tests first) and probes it.

---

## Task

Scene 3A of the Continuity Initiative story (Python 3.12 / FastAPI / React engine, small Cloudflare narrator model) still has open
narration defects that look like one family: **the narrator is told about people in two thin ways, and both misfire.** Read the record,
establish the causes and evidence yourself, and write one plan that treats these together instead of as separate patches:

1. **Where people are told to the narrator.** The THINGS section lists items, groups and places, the protagonist, and a person only
   when the player's command names them. Michelle stands with Kristin for the whole of scene 3A but has no THINGS line unless the
   command says her name.
2. **What a person is told they may say.** The CONSTRAINTS section carries one line per speaker and statement,
   `<Name> may say this aloud: <statement>`, and the statement is an authored, third-person fact that is also shown in SCENE
   ("Kristin and Michelle have reunited."). Michelle often speaks that sentence about herself.

Write the plan to `.plans/astra-3a-things-and-speaker-lines-plan.md`. Edit it in place on later rounds; do not regenerate it.

## What to read first

- `AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md` (and the pages it links on
  what the narrator may be told about places and people), `docs/contributor-guide.md`
- `.plans/richer-3a-open-issues-plan.md` ("Where things stand" and the status log) and `.plans/richer-3a-probe-prereg.md`, in particular
  **Amendments 9 and 11 to 18** (each records the question, the arms, the rubric, the result and what was reverted). Check every
  result against the rows, not only against the counts.
- `.plans/chatgpt-3a-open-issues-prompt.md` (the earlier round; its tables of problems O1 to O10 and Brandon's standing positions still
  apply)
- The story package: `data/stories/continuity-initiative/` (`plot.md` scenes 1B, 2A, 2B, 2C, 3A; `knowledge.yaml`; `handoffs.yaml`;
  `world.yaml`)
- Code that builds the prompt: `storygame/runtime/item_facts.py` (`_view`, `_things_block`, `_thing_names`,
  `_referred_lines_for_command`, `_referred_entity_label`, `prepare_turn`), `storygame/runtime/cloudflare.py`
  (`_section_user_prompt`, `_speaker_constraint_lines`, `_character_lines`), `storygame/runtime/knowledge.py` (`project`,
  `_effect_item_ids`, `scene_hidden_ids`), `packages/worldkeeper/src/worldkeeper/model.py` (`alongside`, `together`, `place_label`,
  `place_text`, `companions`, `members`)
- `docs/world-model-grounding/prompt-inputs.md` (the rule that THINGS gives only what the command refers to; check how it was meant to
  treat people)

## The recorded evidence

All local and gitignored under `bench/results/richer-3a-probe/`. Frozen payloads replay with
`python -m bench.frozen_prompts replay <payload> --samples 12 --out <rows>` (billed, about 3.7 neurons per request); `capture` is free.

| Directory | What it is |
| --- | --- |
| `bio/` | Amendment 13: Kristin's bio loses its goal sentence. `frozen-candidate-c{4,5}.json` is the shipped prompt; `candidate-c{4,5}-rows.json` its 12 replies each (2026-11-06) |
| `d1v-bio/` | Amendment 14: the six "may say this aloud" lines removed (D1-V), retested under the new bio |
| `reunion-bio/` | Amendment 15: a world effect that hides the reunion statements from SCENE |
| `frame/` | Amendment 16: moving "Michelle is beside the captives." to the opening entry text |
| `c9bio/`, `radio/` | Amendments 10 and 17: the c9 radio hand-off repeat |
| `people/` | **Amendment 18, newest:** engine change that lists people who stand with the player in THINGS, plus the frame sentence removed. `frozen-candidate-c{4,5}.json`, `candidate-c{4,5}-rows.json` |

The engine change of Amendment 18 is kept as `scripts/ringer/3a-open-issues/present-people.patch` (reverted from the working tree).

## What was observed (facts from the record; verify each against the artifacts)

- Shipped 3A prompt at command 4 ("Enter the medical level."): THINGS holds only `- Kristin. Place: detention level. With Kristin:
  Brandon.` and `- medical level. This is a place.`. SCENE ends its frame with "Michelle is beside the captives." and carries the two
  reunion statements; CONSTRAINTS carries six "may say this aloud" lines for them.
- Amendment 16 (frame sentence moved to the entry text, opening probe, 12 per arm): missed. The candidate opening became a recognition
  scene (Michelle speaks a reunion line 1/12, radio cue lost 1/12, eye contact in 9/12 against 0/12).
- Amendment 13 stage B (new bio): Michelle acts in 12/12 c4 replies and says "Kristin and Michelle have reunited" aloud in 8/12.
  Amendment 14 (speaker lines removed): that recitation 8/12 to 0/12, but Kristin then voices the second statement (6/12), the
  narrator re-stages the opening picture (6/12), replies not strict JSON 3/12: missed. Amendment 15 (statements hidden from SCENE by a
  world effect): missed.
- Amendment 18 (engine lists people with the player in THINGS, frame sentence removed; c4 and c5, 12 replies each): the preregistered
  rule missed by one item (one c4 reply of 12 truncated, not strict JSON). No identity or staging failure came back (searching,
  stranger, rescue at 0/12; Michelle acts 12/12). The recitation did not change (10/12 against 8/12). Brandon now opens 9/12 c4
  replies; one reply invents a radio call; one has a `dialogue` segment whose text is `None`. Both changes were reverted.

## Claude Code's unverified readings (leads, not conclusions: confirm, correct or discard each yourself)

1. THINGS leaves people out because `_view` skips every character except the protagonist and `_referred_lines_for_command` adds a
   person only when the command names them; so the frame sentence is the one line that says where Michelle is at c4.
2. The kept engine rule's person line is built from the parent's name only (`Place: <area>`), while an item's `Place:` uses
   `world.place_label` (the story's own placement text when present). In the other scenes where the rule adds a person line, the story
   authors a placement text for that person that the line drops:
   - 1B: `brandon: {parent: los_angeles_park, text: watching Kristin in the park}`; the line reads
     `- the man watching Kristin. Place: Los Angeles park. State: conscious. If it changes, give "state": "unconscious".`
   - 2A: `shift_supervisor` "walking out from the facility gate with a tablet and the work order"
   - 2B: `shift_supervisor` "leading the audit sweep between the archive stacks", while the scene text says voices and footsteps are
     approaching; the line reads `- shift supervisor. Place: records archive.`
   - 2C: `rebecca` "standing between her guards in the command corridor"
   Michelle has no placement text in 3A (`michelle: {parent: detention_level}`).
3. The `State: ... If it changes, give "state": ...` sentence on a person who is only standing there looks like noise.
4. The 1B opening golden (`tests/fixtures/place_feed/baseline_prompts.json`, tested in `tests/test_place_scoped_feed.py`) pins the old
   THINGS block and fails on the kept rule. 1A is unchanged by the rule.
5. The speaker line is the template `f"{display_name} may say this aloud: {item['statement']}"` in `_speaker_constraint_lines`. The
   `statement` is the same authored third-person fact that SCENE shows, so the narrator is given facts it may voice, not quoted
   speech. Michelle's recitation of "Kristin and Michelle have reunited" (and of the bookkeeping sentence that follows) may come from
   that. Not tested: giving each speaker an authored utterance separate from the fact (a story-schema and loader change).
6. Removing speaker lines moved the content to another speaker (Amendment 14) rather than removing it; hiding statements from SCENE
   brought back the opening re-staging (Amendment 15, and Amendment 11 earlier). So the same sentences appear to do two jobs: tell
   the narrator what is true, and tell it what a person may say.

## Brandon's standing positions (follow them)

- Richness comes from the plot, not runtime embellishment. Invented details matter only if they are story-breaking.
- Manage the narrator prompt aggressively: only characters and things in the scene or referred to. "If you can keep the prior behavior
  and reduce the prompt size in a better way, then do that instead." He prefers safety over size. Deep-turn prompts are already over
  budget in 3A, 3B and 3C (open issue O8): do not raise a ceiling to make a test pass.
- "I also still want you to keep the feature limiting the speaker lines, even if it doesn't help in this case."
- The narrator is a small non-reasoning model: remove the mechanism that causes a defect before adding an instruction; a narrator rule
  comes last, and only if its probe arm wins. Never gate narration with keyword or regex scanning. Narrator rules are written at 12th
  grade level, plain words, one idea per sentence.
- Facts are the sole mutable truth; world-model logic is a `World` method in `packages/worldkeeper`; `storygame` only adapts. Shared
  runtime stays story-agnostic: no scene or character names in engine code.
- Recommend only techniques proven in earlier scene fixes (cite the file and section) and say what you checked. Anything new must be
  labeled "new, unproven" with the probe that would test it. Do not repeat an arm the record shows was rejected unless you say what is
  different now.
- Probes: one arm per candidate cause, 10 to 15 samples per arm, every narration read by hand, a rubric and win rule written before any
  billed request, same script and replicate count when re-running; known judge faults fixed first. A same-day control is needed when
  the saved control is from an earlier day: replies drift from day to day.
- Story text is written by you in this chat when a fix needs new wording: give the exact words for each story file edit. Code and
  tests go through Ringer, tests first; no code is written by you.

## What the plan must contain

1. For each of the two problems above and for each reading in the list: the cause you established from the artifacts (cite file, line or
   turn), whether it is a real defect under Brandon's rulings, and the proven technique from the record that fits it. If none fits, say
   so. Say whether the two problems share a cause.
2. A holistic design: how people with the player should reach the narrator (THINGS lines, CHARACTERS, SCENE, placement text), and how
   what a person may say should be written, so that Michelle is located without a frame sentence, the reunion is not recited, and the
   opening still identifies her without turning into a recognition scene. State what changes in the engine, in the story data, and in
   the schema, and which of those can be done without the schema change.
3. Every scene the engine change touches (1B, 2A, 2B, 2C, 3A and any other you find): what the narrator will now be told there, whether
   that is right for the scene's pacing and discoveries, and what must be checked before it ships. Include the 1B golden test.
4. Each step in order: exact files and lines, the tests, the free offline check (payload diffs cost no neurons), the probe (arms,
   samples, neuron cost at about 3.7 per request, rubric, win rule, preregistered before the run), and what the sample size does not let
   us claim. The Amendment 18 miss was one truncated reply out of 12: say how you would tell noise from a defect.
5. The shortest path to a pull request: which open items are acceptable as known items and which block it, and why.
6. A short list of what you would not do.

Do not write code, do not apply any change, and do not run any billed test. Mark every plot, knowledge, world or schema change as such
so Brandon can approve it before it is applied.
