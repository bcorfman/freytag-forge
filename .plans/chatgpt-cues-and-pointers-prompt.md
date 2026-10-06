# ChatGPT Desktop prompt: missing cues and next-step pointers, Scenes 1C, 2A, 2C (2026-10-06)

Paste everything below the line into a FRESH ChatGPT Desktop chat with the
project open. Score the answer against the real matcher before applying it. If
it misses, fix this prompt and start a fresh chat; do not hand-edit the answer.

---

You have the whole freytag-forge project. Write new story text for the
Continuity Initiative package (`data/stories/continuity-initiative/`). Read
first: `AGENTS.md` ("Writing Narrator Rules", "Fixing a Scene"),
`docs/markdown-story-authoring.md` (cue_text, delivery_text),
`docs/world-model-grounding.md`, `storygame/runtime/candidate_matcher.py` (the
exact matcher, including `_SYNONYM_CLASSES`), and these files: `handoffs.yaml`
(entries for 1C, 2A, 2C), `knowledge.yaml` (`k_sl_1c_*`, `k_sl_2a_*`,
`k_sl_2c_*`), `plot.md` (Scenes 1C, 2A, 2C) and `world.yaml`. Do not edit
files; return text to paste.

## The problem

Players do the right thing in their own words, but the screen never tells them
the next move, so nothing fires. Two things are missing.

1. Three steps have no cue (the short hint shown to the player). A cue names a
   thing on screen and the move to try on it.
2. Many deliveries end without saying where to go next. A pointer is one short
   closing sentence at the end of a `delivery_text` that names the next thing
   to act on.

Each scene is a chain of steps. A step cannot fire until the step before it has.
The game now shows a cue only after the step behind it can be earned, so a cue
may safely name a thing from later in the chain.

## Rules to keep

- A cue or pointer names a thing and a move. It never states the fact the move
  reveals. Example: "A logistics computer hums by the service entrance." is
  fine. Saying the computer shows a national network is not.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` scene text uses. Do not invent a place, person, object or fact. If a
  sentence needs a thing that is not declared, say so and give your nearest
  alternative.
- The words in a cue and pointer must be words the next step's
  `action_evidence` matches, so the player's natural command fires it. Use the
  exact noun, such as "logistics computer", "transfer orders", "coded message".
  Copy the groups in your answer and check each against the matcher.
- A pointer is checked by the narration leak scan. It may NOT use a
  multi-word phrase that is an alias or `action_evidence` phrase of a LATER
  reveal (`the supervisor`, `coded message`, `restricted infrastructure
  corridor` were all rejected). Use single words, declared `world.yaml` names,
  or wording from the story that no reveal lists. A cue is exempt because it is
  handoff text. After you choose a pointer, say which later-reveal phrases you
  avoided.
- Write at an 8th-grade reading level. Short, common words. One idea per
  sentence. A cue is one or two sentences. A pointer is ONE sentence.
- Kristin is "Kristin" and Brandon is "Brandon" in 1C, 2A and 2C (he is named
  by then). Never write "you".
- Keep every existing sentence and key fact in a `delivery_text`. Add the
  pointer as a new last sentence only. The `must_convey` lists in
  `handoffs.yaml` must still hold.
- Only one reveal may match a command. Pointers must not make a command match
  two reveals.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. New cue_text for two facts (handoffs.yaml)

A1. `national_detention_network_known` (scene 1C, no `cue_text` today). The
    step is `k_sl_1c_c_r1`. Evidence groups now:
    `[read, search, inspect, check, access, use, open, activate, examine, look at]`
    and `[logistics computer, terminal computer, computer]`. The cue should point
    at the logistics computer (declared in `world.yaml` as id `logistics_terminal`,
    name "logistics computer", fixed in the freight terminal) and a move such as
    using or reading it. It must not state that the computer shows a network.

A2. `purge_clock_started` (scene 2C, no `cue_text` today). Steps: `k_sl_2c_b_r1`
    (checks the transfer orders; nouns `transfer order(s)`, `purge order(s)`,
    `purge schedule`, `Charles's order(s)`) and `k_sl_2c_b_r2` (checks the
    broadcast schedule; nouns `broadcast schedule(s)`, `broadcast plan(s)`,
    `selected survivor(s)`, `survivor list(s)`). Either fires the fact. Write one
    cue that names the transfer orders. It must not state that the purge is
    coming within hours.

### B. Pointer sentences (append to delivery_text in knowledge.yaml)

For each reveal below, write one closing sentence that names the next thing to
act on. The next step is given with its evidence nouns. Where one fact has two
reveals (r1 and r2), write a pointer for each.

1C chain (order: facility_proof, then captives_confirmed_alive, then the
network):
- `k_sl_1c_a_r1` and `k_sl_1c_a_r2` -> next: the observation shaft over the
  processing line (`k_sl_1c_b_r1`, `k_sl_1c_b_r2`). Nouns: processing line,
  processing area, observation shaft, prisoners, captives, uniforms.
- `k_sl_1c_b_r1` and `k_sl_1c_b_r2` -> next: the logistics computer
  (`k_sl_1c_c_r1`). Nouns: logistics computer, computer.

2A chain (false_identities_ready, then facility_perimeter_reached, then
restricted_corridor_access):
- `k_sl_2a_b_r1` and `k_sl_2a_b_r2` -> next: drive to the facility and show the
  credentials at the checkpoint (`k_sl_2a_e_r1`). Nouns: the facility,
  checkpoint, the guard, inspector credentials. This delivery fires on turn 1
  of the step and names no next place today.
- `k_sl_2a_e_r1` -> next: the supervisor who questions why the inspection was
  not scheduled, or the restricted infrastructure corridor (`k_sl_2a_c_r1`,
  `k_sl_2a_c_r2`). Nouns: supervisor, cooling, ventilation, restricted
  infrastructure corridor. Use plot.md Scene 2A.3.

2C chain (purge_clock_started, then evidence_ready_to_transmit, then
rebecca_office_required_for_broadcast):
- `k_sl_2c_b_r1` and `k_sl_2c_b_r2` -> next: the copied files (`k_sl_2c_c_r1`)
  or the argument about sending them (`k_sl_2c_c_r2`). Nouns: copied files,
  archive files, proof, evidence, sending the proof.
- `k_sl_2c_c_r1` and `k_sl_2c_c_r2` -> next: Michelle's coded message
  (`k_sl_2c_d_r1`). Nouns: Michelle's message, coded message, encrypted message.

Do not write pointers for `k_sl_1c_c_*`, `k_sl_2c_d_*` or any 2A `a` step; they
end a chain or are optional.

### C. plot.md

For each new cue in Task A, give one sentence for the matching plot.md scene
(1C.3 for A1, 2C.2 for A2) that carries the same fact, so plot and cue agree.
Say which paragraph it follows.

## Output

1. YAML or text to paste, per file and key, changed lines only. For deliveries,
   show only the new last sentence and the reveal id.
2. A table: every cue and pointer, the exact nouns it uses, and which next-step
   evidence group each noun matches, checked word by word against the matcher
   (apostrophe rule, synonym classes, negations, the one-match rule).
3. For each cue, five commands a player might type after reading it. At least
   two per cue must be ones that should NOT fire. Give the result for each.
4. Anything in this brief you could not satisfy, and why.

Other wordings will be tested after you answer. A sentence that is vague about
the move is as bad as one that gives away the answer.
