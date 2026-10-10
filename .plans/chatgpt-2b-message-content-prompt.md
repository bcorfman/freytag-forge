Write new story text for the Continuity Initiative game. You cannot see the
game's files, so everything you need is below. Return text to paste. Do not
ask me questions.

## The problem

In Scene 2B, Kristin and Brandon are in the facility's records archive. One
step is reading Michelle's coded maintenance messages. After that step, a
player can type commands like "Examine Michelle's decoded maintenance message."
The story says what the messages SHOW (they show Michelle has organized
prisoners and is preparing an uprising), but it never says what a message
SAYS. A small AI narrator then invents the text of the message. In tests it
wrote lines like "The message reads: 'Echo-12, Prisoner 3142 reclassified.
Prepare for Phase 2.'" Those invented names, numbers and codes break the
story. Worse, the word "Phase" is secret story material (the final twist),
and the game rejects any turn whose narration says it. When we removed the
sentence below from the narrator's view, the invented text stopped. So the
sentence pulls the narrator toward writing message text, and it gives the
narrator nothing real to write.

Fix it with story text only. Give the message real wording that the narrator
can copy, so it does not invent any.

### What a first try showed (read this)

A first version described what the messages say in plain words ("Michelle's
coded maintenance messages say she is hiding vulnerable captives from
experiments. They show Michelle has organized prisoners for an uprising from
inside."). We tested it with the real narrator, 15 replies per case. It did NOT
help. In one case the narrator wrote a quoted message in 12 of 15 replies, up
from 2 of 15 before, and it added details the story does not have: "cell block
3", "sector 3", "0400 hours", "Project Elysium", a signature "-Shelly", and
"Prepare for Phase 2". A description invites the narrator to write a message
and dress it up. The two replies that stayed safe copied the statement's own
words and added nothing. So the fix is to hand the narrator the message's EXACT
words, short enough to copy whole.

## The text today

Scene 2B in the plot, sub-scene 2B.4 ("Michelle's Hidden Resistance"):

> The records reveal unusual equipment failures and corrupted prisoner files throughout the facility. Kristin recognizes phrases in the corrupted data that Michelle used in her private notes.
>
> Michelle has built a small covert network among prisoners and sympathetic workers. Using her access to a medical terminal, she has been:
> * Altering prisoner classifications
> * Delaying transfers
> * Hiding vulnerable captives from experimental programs
> * Sending coded messages through maintenance reports
> * Preparing prisoners for an organized uprising
>
> The records prove that Michelle is active inside, but they cannot yet show how far her hidden network reaches.

The game entry for the step (YAML). The `statement` is shown to the narrator
on every turn in 2B. The `delivery_text` is shown to the player when the step
fires:

```yaml
statement: 'Michelle’s coded maintenance messages show she has organized prisoners and is preparing an uprising from inside.'
delivery_text: "Michelle has organized prisoners. She is preparing an uprising from inside. Brandon's earlier messages are still open on the remote terminal."
```

The step fires when the player reads, opens, checks, reviews, examines or
inspects the maintenance reports, maintenance messages or coded messages.

## What to write

### A. The exact words of a message

Write the exact words of ONE decoded maintenance message, in quotation marks,
as one or two short sentences. The narrator will copy it whole when a player
reads it. It says only facts the story already holds (see Rules). Then write
the `statement` as: one plain sentence saying the coded maintenance messages
show Michelle has organized prisoners and is preparing an uprising from inside,
followed by one sentence that begins "A decoded message reads:" and gives the
quoted words. The quoted words must stand alone: no code names, numbers,
signature or place.

### B. The matching delivery text

Give the `delivery_text` with the message's quoted words added as one sentence
before "Brandon's earlier messages ...". Keep all three current sentences. Do
not remove that last sentence.

### C. The matching plot sentence

Give ONE sentence for sub-scene 2B.4 that carries the same content, and say
which paragraph it follows.

## Rules

- **Only facts the story already holds.** Use only what 2B.4 says: Michelle
  alters classifications, delays transfers, hides vulnerable captives, has a
  small network of prisoners and sympathetic workers, and is preparing an
  uprising. Say it in the words of a message Kristin can follow, because
  Kristin recognizes phrases Michelle used in her private notes.
- **No invented specifics.** No names, numbers, ID codes, call signs, dates,
  times, places, signatures or new objects, in the quoted words or anywhere
  else. The quoted message is the only quoted text. Do not sign it.
- **Never use the word "phase", "plan two", "second plan" or any stage
  numbering.** That is the secret twist of the whole story.
- **Do not reveal anything from later scenes.** The messages must not say
  where Michelle is held, give a route to her, mention Rebecca, Charles, the
  broadcast, the purge, the cells opening, or when the uprising will happen.
  A later scene reveals those. Here the messages only show that Michelle's
  inside network exists and is ready.
- **Do not say how far the network reaches.** The story says the records
  cannot yet show it.
- **Keep the current meaning.** The statement must still name the coded
  maintenance messages, the organized prisoners and the uprising. The delivery
  text must still end with the sentence about Brandon's earlier messages.
- **8th-grade reading level.** Short, common words. One idea per sentence.
  Never join two ideas with "and". A small model reads this, and it obeys the
  first half of a sentence and drops the second.
- Kristin is "Kristin", Brandon is "Brandon", Michelle is "Michelle".
  Never write "you".
- The delivery text must read as what the player just found, in the present
  tense, like the current one.

## Output

1. The new `statement`, ready to paste.
2. The new `delivery_text`, ready to paste.
3. The 2B.4 plot sentence, and which paragraph it follows.
4. A check list: for each rule above, one line saying how the text meets it.
   Include the "phase" check.
5. Three short answers a narrator could write if a player types "Examine
   Michelle's decoded maintenance message.", each copying your quoted words
   whole. Each must add no name, number, code, place or signature. If any
   answer needs one, fix the quoted words until none does.

Other wordings will be tested after you answer.
