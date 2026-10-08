Write new story text for the
Continuity Initiative package (`data/stories/continuity-initiative/`). Read
first: `AGENTS.md` ("Writing Narrator Rules", "Fixing a Scene"),
`docs/markdown-story-authoring.md` (cue_text, delivery_text),
`docs/world-model-grounding.md`, `storygame/runtime/candidate_matcher.py` (the
exact matcher, including `_SYNONYM_CLASSES`), and these files: `handoffs.yaml`
(the five Scene 2B entries: `janus_evidence`, `brandon_janus_role_known`,
`brandon_claimed_reform_motive`, `michelle_resistance_known`, and the 2B part
of the chain), `knowledge.yaml` (`k_sl_2b_*`), `plot.md` (Scene 2B) and
`world.yaml`. Do not edit files; return text to paste.

## The problem

In live play of Scene 2B, players open the archive and search for Michelle's
file. That fires `k_sl_2b_a_r1`. Then the screen does not say what to do next.
Players keep opening Michelle's records (her transfer record, her patient
record, her location) and the narrator invents people and details to fill the
gap, such as a doctor and a transfer site. The story has none of those. Players
never reach Brandon's development records, the security logs, the maintenance
reports, or the corrupted files on the medical terminal, which are the real
next steps.

Fix it with story text only. A pointer is one short closing sentence at the end
of a `delivery_text` that names the next thing to act on. A cue is the short
hint shown to the player before a step can fire.

Scene 2B is a chain. `k_sl_2b_a_r1` and `k_sl_2b_a_r2` (fact `janus_evidence`)
have no requirement. Everything else needs `janus_evidence` first:
`k_sl_2b_b_r1`, `b_r2`, `b_r3` (Brandon's role, motive, and that Kristin was
bait) and `k_sl_2b_c_r1`, `c_r2` (Michelle's resistance). The bridge needs
`janus_evidence` plus two of `brandon_janus_role_known`,
`brandon_claimed_reform_motive`, `michelle_resistance_known`. The game shows a
cue only after the step behind it can be earned.

## Rules to keep

- A cue or pointer names a thing and a move. It never states the fact the move
  reveals. "A report on Brandon sits in the development records." is fine.
  Saying the records prove Brandon helped write JANUS is not.
- Use only things the story already has: names in `world.yaml` and nouns the
  `plot.md` Scene 2B text uses. Do NOT invent a person, doctor, place, record
  type, transfer, date, code or fact. The story has no doctor, no transfer
  record and no hidden location in 2B. If a sentence needs a thing that is not
  declared, say so and give your nearest alternative.
- The words in a pointer must be words the next step's `action_evidence`
  matches, so the player's natural command fires it. Current groups:
  - `b_r1`: verbs search, read, open, check, review, show, find, examine,
    inspect; nouns development record(s), Brandon's record(s), Brandon's file,
    earlier messages, original JANUS records.
  - `b_r2`: verbs ask, confront, question, speak to, talk to; Brandon; nouns
    why he helped write, helped write, development records, earlier messages.
  - `b_r3`: security log(s), access log(s) plus Michelle's evidence, Charles,
    hidden network, Brandon's network.
  - `c_r1`: medical terminal, patient record(s), prisoner file(s), warning
    message, delayed transfer(s), corrupted records.
  - `c_r2`: maintenance report(s), maintenance message(s), coded message(s).
  Copy the groups in your answer and check each against the matcher.
- A pointer is checked by the narration leak scan. It may NOT use a multi-word
  phrase that is an alias or `action_evidence` phrase of a LATER reveal
  (`the supervisor`, `coded message` and `restricted infrastructure corridor`
  were rejected in earlier scenes). Use single words, declared `world.yaml`
  names, or wording from the story that no reveal lists. After you choose a
  pointer, say which later-reveal phrases you avoided. A cue is exempt because
  it is handoff text.
- Write at an 8th-grade reading level. Short, common words. One idea per
  sentence. A cue is one or two sentences. A pointer is ONE sentence.
- Kristin is "Kristin" and Brandon is "Brandon" in 2B. Never write "you".
- Keep every existing sentence and key fact in a `delivery_text`. Add the
  pointer as a new last sentence only. The `must_convey` lists in
  `handoffs.yaml` must still hold.
- Only one reveal may match a command. A pointer must not make a command match
  two reveals.
- Test commands follow AGENTS.md "Writing Player Input": imperative, verb plus
  object, no first person, no "do not", no waiting.

## Tasks

### A. Pointers (append to delivery_text in knowledge.yaml)

For each reveal, write one closing sentence that names the next thing to act
on. Aim the pointers so a player who follows them reaches the bridge.

- `k_sl_2b_a_r1` (Michelle was picked by JANUS) -> next: Brandon's name in the
  development records, or the medical terminal. Do not point at more of
  Michelle's own file; the file has nothing more to give.
- `k_sl_2b_a_r2` (Kristin was left behind on purpose) -> next: the security
  logs, or Brandon.
- `k_sl_2b_b_r1` and `k_sl_2b_b_r2` -> next: the medical terminal, or the
  maintenance reports.
- `k_sl_2b_b_r3` -> next: the medical terminal.
- `k_sl_2b_c_r1` -> next: the maintenance reports.
- `k_sl_2b_c_r2` -> next: Brandon's earlier messages, or the development
  records, whichever is not yet read.

Do not point at the same thing from every delivery. Spread the next steps so a
player is not sent in a circle.

### B. Cue_text check (handoffs.yaml)

The four 2B cues exist. For each, say whether its nouns match the evidence
groups above. Where a cue names a thing the evidence does not match, or names a
move that does not fire the step, give a replacement cue (one or two
sentences, a description, not a command). Keep a cue that already works.

- `brandon_janus_role_known`: "Brandon's hands stop over a record on the archive
  terminal. He goes quiet as he reads the next line."
- `brandon_claimed_reform_motive`: "Brandon's earlier messages about the project
  remain open on the remote terminal."
- `michelle_resistance_known`: "The medical terminal shows corrupted prisoner
  files and delayed transfer notices."
- `janus_evidence`: "Selection files fill the archive terminals. Government and
  financial records sit open beside them."

### C. A real answer for Michelle's file

Players who open Michelle's file again after `k_sl_2b_a_r1` get an invented
answer. Write ONE sentence for the `k_sl_2b_a_r1` delivery or the `janus_evidence`
`fallback_text` that closes the file ("Her file holds nothing more.") in the
story's own words, without a new fact. It may be the same sentence as the
pointer in Task A. Say which.

### D. plot.md

If any pointer or cue adds wording that Scene 2B in `plot.md` does not carry,
give one sentence for the matching sub-scene (2B.1 to 2B.4) so plot and text
agree. Say which paragraph it follows. If none is needed, say so.

## Output

1. YAML or text to paste, per file and key, changed lines only. For deliveries,
   show only the new last sentence and the reveal id.
2. A table: every cue and pointer, the exact nouns it uses, and which next-step
   evidence group each noun matches, checked word by word against the matcher
   (apostrophe rule, synonym classes, negations, the one-match rule).
3. For each pointer, five commands a player might type after reading it. At
   least two per pointer must be ones that should NOT fire. Give the result for
   each.
4. Anything in this brief you could not satisfy, and why.

Other wordings will be tested after you answer. A sentence that is vague about
the move is as bad as one that gives away the answer.
