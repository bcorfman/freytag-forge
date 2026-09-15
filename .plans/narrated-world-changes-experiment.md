# Narrated world changes: single call or second call

## Why

Every change the narration shows the player is part of the world until something
changes it again, unless it would break the story. Today nothing the narration
says reaches the engine's state. If Kristin picks up Michelle's phone, the next
prompt still says the phone is on the kitchen floor in five places. The narrator
obeys, the phone jumps back to the floor, and the player sees the world forget.

The 2026-09-14 Scene 1A trial (bench/results/continuity-1a-*-entry-text-cut)
shows this directly. Kristin picked up the phone on 31 of 31 "look at the phone"
turns across both arms. Most turns the continuity judge marked as contradictions
had the phone back on the floor after an earlier pickup.

The loop the game needs is: narrate, capture the world changes, check them
against the story, regenerate when the narrator caused a story-breaking change
(or warn the player when their own command did), commit, and carry the new
facts into the next prompt. This experiment answers only the first open
question in that loop: can the 8B model capture the changes reliably, and does
it need a second call to do it?

## What history does and does not show

Three earlier designs had the 8B return world changes in the same call as the
narration: the V1 grounded turn contract (to 2026-08-16), the V2 `operations`
contract (2026-08-16 to 08-25), and the 2026-08-25 TurnProposal with fact
operations (removed 2026-08-28). Each bundled the changes with many other jobs -
dialogue speaker, intent classification, disclosure keys, beat completion tags,
copying authored route operations - under long, abstract rule lists, and asked
for abstract identifiers (legal claim tuples, JSON state paths, realization IDs)
rather than plain facts about things. None recorded how accurate the returned
facts were. So history cannot tell a model that cannot do this from a model that
was overloaded and asked for the wrong shape.

## The experiment

One bench-only harness, no game-engine change. Three arms, each 4 replicates of
12 fixed turns of the Scene 1A phone-bag-door script.

| Arm | Narrator call | Fact capture |
|---|---|---|
| A. Single call | Today's prompt, plus a THINGS section and one task line | The narrator returns `item_facts` next to its segments |
| B. Single call, fewer rules | As A, with the CONSTRAINTS rule list cut to the essentials | Same as A |
| C. Second call | Today's prompt, plus the THINGS section | A separate 8B call reads THINGS, the command and the finished narration, and returns `item_facts` |

### Facts in, facts out

- **THINGS section.** The prompt lists each tracked thing with its facts as plain
  phrases, for example `Michelle's phone: not damaged, on the kitchen floor`.
  The seed comes from the variation. Nothing hidden from the player is listed
  (no memory card).
- **Returned facts.** `item_facts` maps every listed thing to its full, updated
  list of short phrases. A thing the turn did not change keeps its phrases.
- **Carry forward.** After an accepted turn, the harness replaces the THINGS
  facts with the returned ones. Unknown names are dropped and recorded; a missing
  or malformed reply keeps the previous facts and is recorded. A rejected turn
  changes nothing.
- **One source for mutable facts.** Authored lines that fix a tracked thing's
  place or condition - the scene-1A placement and setting-fact rules and the
  phone's place in the scene frame and beat text - would contradict the carried
  facts after a change. The harness stops sending the placement and setting-fact
  rules, and all three arms share variation overrides that remove those phrases
  from the frame and beat text, so THINGS is the only place they appear.

### Rules the narrator sees

Written at an 8th-grade reading level in the existing CHARACTERS, SCENE,
CONSTRAINTS, PLAYER layout, with THINGS added. Arms A and B add one task line to
the system prompt and an output example that includes `item_facts`. Arm B's rule
list is the smallest set that keeps today's safety behaviour: answer the player,
use only the SCENE and THINGS sections, do not invent objects or clues, a
character says only what they may say, never write IDs, and the ownership rule.

### Measurement

- **Fact-tracking grader (new, GPT-5.4).** For each turn it sees the facts
  before, the command, the narration, and the facts after, and answers per turn:
  are the facts after correct for what the narration showed; was a real change
  missed; was a change invented; does the narration contradict the facts it was
  given. It also records which changes the command asked for and which the
  narrator added, because the full loop treats those differently.
- **Continuity judge (existing).** Restarts and acting beyond the command, to
  catch prose that gets worse under the extra task.
- **Calibration first.** Before the arms run, the grader is scored against a
  handful of hand-labelled turns built from recorded narration, as the
  continuity judge was.
- **Reading.** A spot check of transcripts and returned facts in every arm.

### What decides it

- If arm A or B tracks facts about as accurately as arm C without worse prose,
  the second call is not necessary, and the full-loop design uses a single call.
- If only arm B holds up, the rule list is the problem, and consolidating rules
  comes before the loop design.
- If only arm C holds up, the loop needs a second call and its extra latency and
  cost.
- If none holds up, the capture step needs a different design before anything
  else is built.

Four replicates per arm is a small sample. A clear gap is actionable; a narrow
one means more replicates, not a decision.

## Results: free phrase lists (2026-09-15)

Recorded in bench/results/item-facts-{single,single-minimal,second}-1a at
ac478d6. Each thing carried a free list of short phrases.

| | A: single call | B: single call, 6 rules | C: second call |
|---|---|---|---|
| Kept facts correct (grader) | 21 of 46 | 24 of 45 | 28 of 41 |
| Narrated phone changes recorded | 2 of 15 | 2 of 10 | 6 of 14 |
| Changes missed / invented | 22 / 6 | 17 / 8 | 10 / 7 |
| Things left out / unknown names added | 96 / 30 | 32 / 39 | 7 / 1 |
| Narration contradicts its given facts | 5 | 4 | 11 |
| Model calls | 52 | 52 | 93 |

- The first wording ("change a thing's facts only when your story changes
  that thing") recorded no pickups in any arm; the recorded run used the
  rewritten wording with a lantern example.
- A single call barely captures changes, and cutting the rules to six did not
  help, so rule overload is not the explanation.
- The second call is better but not reliable. Its errors come largely from the
  list format: a thing held two locations at once ("on the kitchen floor" and
  "in Kristin's hand"), contradictory conditions coexisted, locations were
  dropped, and trivia accumulated. The narrator also sometimes ignored carried
  facts, placing a held phone on a table.
- The fact-tracking grader scored 20 of 20 on five constructed cases, twice,
  after its cause wording was tightened.

## Next: single-value fields

Each thing carries one `where` phrase and up to two `condition` phrases, and a
reply lists only the things the story changed. A new `where` replaces the old
one, so a thing cannot be in two places, and omitted things stay as they were,
so the model no longer has to copy everything back. Rerun a smoke and then 4 x
12 for arms A and C.

## Steps

1. [x] Build the harness through Ringer (dfe3828, d8b71f8).
2. [x] Calibrate the fact-tracking grader on hand-labelled turns (8a79a2b).
3. [x] Smoke run, then rewrite the change wording (ac478d6).
4. [x] Full run with free phrase lists (f3c7401).
5. [ ] Switch the harness to single-value fields; smoke, then 4 x 12 for A and C.
6. [ ] Report the comparison and the decision, then write the full-loop plan
   (capture, story-break check, regenerate or warn, commit, carry forward).
