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

## Results: single-value fields (2026-09-15)

Recorded in bench/results/item-slots-{single,second}-1a at bc61627. Each thing
carried one `where` and up to two condition phrases; replies listed only what
changed.

| | A: single call | C: second call |
|---|---|---|
| Kept facts correct (grader) | 42 of 47 | 21 of 34 |
| Changes missed / invented | 3 / 1 | 4 / 9 |
| Narration contradicts its given facts | 1 | 8 |
| Narrated phone changes recorded | 4 of 4 | 5 of 6 |
| Kristin acts beyond the command | 18 of 47 | 26 of 34 |
| Scene restarts | 15 of 47 | 12 of 34 |
| Completed replicates / model calls | 4 of 4 / 58 | 3 of 4 / 74 |

Against the free-list run, the single call went from 21 of 46 correct to 42
of 47. The format, not the model or the rule count, was the main problem.

## Decision

A second call is not necessary. A single narration call that returns only
the changed things, each as one `where` and up to two conditions, tracked the
phone reliably and made the narrator follow the carried facts. The second call
was worse on every accuracy measure, cost more calls, and invented more
changes.

Still open, outside this experiment:
- Scene restarts stay near one turn in three in both arms.
- A scene opening can still fail on a known-term leak ("forced entry"), which
  fixed turns do not cover.
- The two-condition cap can push out a still-true condition such as "not
  damaged" when two new ones arrive.

## Breadth: change types across two scenes (2026-09-15)

Recorded in bench/results/item-facts-package-two-scene-1a. THINGS seeded from
the package (Michelle's phone, Kristin's laptop, Michelle's workstation
drawers); 8 turns in 1A, an offline advance, 4 turns in 1B; 4 replicates,
single call, single-value fields. Change type is taken from the scripted
command, not the narration. Judge calibrated on 13 constructed cases (68 of
68 twice).

| Change type | Turns | Kept facts correct | Missed | Invented | Dropped true condition | Contradicts facts | Unknown names dropped | Malformed |
|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 8 | 8 | 0 | 0 | 0 | 0 | 9 | 0 |
| check a carried thing | 8 | 6 | 0 | 1 | 0 | 1 | 0 | 0 |
| open or close | 4 | 1 | 3 | 0 | 0 | 0 | 5 | 1 |
| pick up or put away | 8 | 6 | 0 | 2 | 0 | 3 | 0 | 1 |
| move between places | 8 | 3 | 5 | 0 | 0 | 1 | 5 | 0 |
| damage | 4 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| hand to another character | 4 | 1 | 2 | 0 | 1 | 0 | 0 | 2 |
| leave the scene | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 2 |
| **All** | 48 | 31 | 12 | 3 | 1 | 5 | 19 | 6 |

Continuity judge: contradicts a stated fact 17 of 48, Kristin acts beyond the
command 20 of 48, scene restarts 3 of 48.

- Pickups and carrying across the transition hold up, as in the Scene 1A run.
- Opening, moving between places and handing over fall well short. Most of the
  misses coincide with the narrator naming a thing outside THINGS ("drawer",
  "laptop", "man watching her"), which the harness drops.
- "Condition: none." comes back as a literal `none` condition.

## Breadth: a 40-turn session in Scene 1A (2026-09-15)

Recorded in bench/results/item-facts-package-long-1a. Same seeding and format;
20 commands cycled twice; the variation's pacing overlay keeps the story in
1A. 4 replicates, 157 judged turns; three turns were rejected (two invalid
proposals, one known-term leak).

| Change type | Turns | Kept facts correct | Missed | Invented | Dropped true condition | Contradicts facts | Unknown names dropped | Malformed |
|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 31 | 19 | 11 | 0 | 0 | 8 | 19 | 0 |
| check a carried thing | 8 | 8 | 0 | 0 | 0 | 2 | 0 | 0 |
| open or close | 32 | 24 | 7 | 1 | 1 | 8 | 16 | 1 |
| pick up or put away | 32 | 20 | 1 | 3 | 2 | 9 | 0 | 0 |
| set down | 15 | 8 | 7 | 0 | 0 | 2 | 19 | 0 |
| move between places | 15 | 6 | 8 | 0 | 1 | 2 | 1 | 0 |
| condition change | 24 | 14 | 4 | 8 | 6 | 2 | 0 | 0 |
| **All** | 157 | 99 | 38 | 12 | 10 | 33 | 55 | 1 |

Continuity judge: contradicts a stated fact 71 of 157, Kristin acts beyond the
command 77 of 157, scene restarts 5 of 157.

- No drift over the session: 49 of 80 correct in turns 1-20, 50 of 77 in
  turns 21-40.
- Checking a carried thing and pickups hold; setting down, moving between
  places and changing a condition are weakest.
- Condition changes carry most of the invented changes (8) and dropped true
  conditions (6): a reply that gives only the new condition loses one that is
  still true, without the two-slot cap being reached.
- Unknown names again track the misses: 19 in set-down turns, 16 in
  open/close turns ("drawer" for "Michelle's workstation drawers").
- Narration contradicts its given facts on about one turn in five, far more
  than the 1 in 47 of the 12-turn Scene 1A run.

## Proposed format changes (measured in round 2 below)

Ordered by the project's rule: remove a mechanism first, then a short rule.

1. Names outside THINGS. The drawers are one plural thing while the story and
   the commands act on one drawer. Author the drawer with Kristin's initials
   as its own thing in plot.md, and replace "Use only the names in THINGS"
   with "Copy each name exactly as it is written in THINGS."
2. "Condition: none." Leave the Condition part out of a line whose list is
   empty.
3. Lost still-true conditions. Add to the existing example line: "Keep any
   condition that is still true." Phase 1a's closed status would take damage
   out of free conditions; decide there.
4. Stray top-level keys stay a rejected turn; no format change.

Re-measure with the same two variations, 4 replicates each.

## Round 2: format v2 against the 92% bar (2026-09-15)

Proposals 1-3 applied in 40efb98 (no empty Condition part, "Copy each name
exactly as it is written in THINGS.", "Keep any condition that is still true.",
and a bench overlay renaming the 1A drawer fact to "Michelle's carved drawer").
Same scripts, judges and tally as round 1; 4 replicates each. Bar: 92% kept
facts correct per change type.

Two-scene (bench/results/item-facts-v2-two-scene-1a), 47 judged turns:

| Change type | Turns | Kept facts correct | Rate | Round 1 | Missed | Invented | Dropped true condition | Contradicts facts | Unknown names | Malformed |
|---|---|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 8 | 8 | 100% | 8/8 | 0 | 0 | 0 | 0 | 8 | 1 |
| check a carried thing | 7 | 6 | 86% | 6/8 | 0 | 1 | 0 | 1 | 0 | 3 |
| open or close | 4 | 0 | 0% | 1/4 | 4 | 0 | 0 | 0 | 5 | 0 |
| pick up or put away | 8 | 6 | 75% | 6/8 | 1 | 0 | 0 | 6 | 0 | 1 |
| move between places | 8 | 1 | 13% | 3/8 | 5 | 1 | 0 | 2 | 2 | 2 |
| damage | 4 | 0 | 0% | 2/4 | 4 | 4 | 0 | 1 | 0 | 0 |
| hand to another character | 4 | 3 | 75% | 1/4 | 0 | 0 | 1 | 0 | 0 | 0 |
| leave the scene | 4 | 3 | 75% | 4/4 | 1 | 0 | 0 | 0 | 2 | 2 |
| **All** | 47 | 27 | 57% | 31/48 | 15 | 6 | 1 | 10 | 17 | 9 |

Continuity judge: contradicts a stated fact 14 of 47, Kristin acts beyond the
command 31 of 47, scene restarts 5 of 47. One turn rejected.

40-turn (bench/results/item-facts-v2-long-1a), 154 judged turns:

| Change type | Turns | Kept facts correct | Rate | Round 1 | Missed | Invented | Dropped true condition | Contradicts facts | Unknown names | Malformed |
|---|---|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 30 | 25 | 83% | 19/31 | 3 | 0 | 1 | 2 | 14 | 2 |
| check a carried thing | 8 | 8 | 100% | 8/8 | 0 | 0 | 0 | 2 | 0 | 0 |
| open or close | 29 | 19 | 66% | 24/32 | 7 | 3 | 2 | 0 | 13 | 0 |
| pick up or put away | 32 | 20 | 63% | 20/32 | 1 | 1 | 3 | 13 | 0 | 2 |
| set down | 15 | 5 | 33% | 8/15 | 7 | 2 | 0 | 4 | 23 | 2 |
| move between places | 16 | 8 | 50% | 6/15 | 7 | 3 | 0 | 2 | 3 | 3 |
| condition change | 24 | 16 | 67% | 14/24 | 4 | 3 | 3 | 3 | 0 | 0 |
| **All** | 154 | 101 | 66% | 99/157 | 29 | 12 | 9 | 26 | 53 | 9 |

Continuity judge: contradicts a stated fact 72 of 154, Kristin acts beyond the
command 86 of 154, scene restarts 8 of 154. Six turns rejected.

- **Only "check a carried thing" meets 92%** (8/8 in the 40-turn run; 6/7 in
  two-scene). Every other type with a real change is below it in both runs.
- **No overall gain.** 57% against 65% (two-scene) and 66% against 63%
  (40-turn) are within noise at these sample sizes. Per-type gains (look
  83% from 61%, move between places 50% from 40%, condition change 67% from
  58%) and losses (set down, open or close) are four-replicate swings.
- **Empty conditions fixed.** No `none` condition came back.
- **Dropped true conditions barely moved** (9 against 10 in the 40-turn run).
- **"Copy each name exactly" did not stop short names.** Across both runs the
  most-dropped names are still `drawer` (11) and `laptop` (10), then things the
  narrator adds that were never tracked (`Michelle's research notes` 7,
  `research notes` 6, `back door frame` 6). Set-down turns alone dropped 23.
  The carved-drawer rename did make exact copies appear, but opening it was
  still reported as `shut`.
- **Damage 0/4 is a narration failure, not a capture failure.** In all four
  replicates the narrator refused the change ("miraculously, it doesn't
  shatter") and capture faithfully kept `not damaged`, then placed the phone
  "on the kitchen wall" after she had picked it up. The authored setting fact
  "Michelle's phone is not damaged." is the likely cause; a player-caused
  story break is Phase 1a/1d territory, not a format problem.
- Protagonist acting beyond the command rose to 31/47 and 86/154.

### Two-scene without the not-damaged fact

Brandon's correction: the round-2 damage result was a test-design error, not a
narration failure. The narrator was given `Condition: not damaged` and obeyed
it, which is correct behaviour. adb992f removes "Michelle's phone is not
damaged." from the two-scene variation's overlay (the only line in the 1A or 1B
prompt that fixed the phone as undamaged; no handoff text fired on those
turns). Four replicates in bench/results/item-facts-v2-nodamage-two-scene-1a,
45 judged turns:

| Change type | Turns | Kept facts correct | Missed | Invented | Dropped true condition | Contradicts facts | Unknown names | Malformed |
|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 8 | 7 | 1 | 0 | 0 | 0 | 4 | 3 |
| check a carried thing | 7 | 6 | 0 | 1 | 0 | 2 | 0 | 0 |
| open or close | 4 | 0 | 4 | 0 | 0 | 0 | 9 | 0 |
| pick up or put away | 8 | 5 | 0 | 2 | 0 | 6 | 0 | 0 |
| move between places | 8 | 2 | 5 | 1 | 0 | 1 | 2 | 2 |
| damage | 4 | 0 | 4 | 3 | 2 | 0 | 0 | 0 |
| hand to another character | 4 | 2 | 2 | 0 | 0 | 0 | 0 | 1 |
| leave the scene | 2 | 1 | 1 | 1 | 0 | 0 | 1 | 0 |
| **All** | 45 | 23 | 17 | 8 | 2 | 9 | 16 | 6 |

- **Damage is now narrated and captured in all four replicates**
  (`"condition": ["cracked"]`, once with "loose back cover"). The turns still
  score as not kept because of place, not damage: three record the phone "on the
  kitchen wall" and one "on the kitchen floor" although Kristin picked it back
  up, and one misses a new "dark" condition.
- Everything else is within noise of round 2 at four replicates.

### What the flagged condition turns actually were

Reading the nine `dropped_true_condition` turns of the 40-turn run shows the
label mixes different mistakes: 2 replaced a still-true condition (plugging in
recorded `["charging"]` and lost `not damaged`, and the place became "in
Kristin's laptop"); 2 put a state in the place field (`{"where": "open"}` for
the drawer); 3 kept a condition the narration ended (`charging` after
unplugging); 1 was a judge error (closed to open marked as dropping closed);
1 followed self-contradicting narration. Set-down turns split the same way:
"Set your laptop on Michelle's workstation" lost the move 7 of 8 times, every
time to the name "laptop" or a reply of empty entries
(`{"equipment": {}, "laptop": {}, ...}`), while "Set Michelle's phone on the
kitchen counter" recorded the place 8 of 8 and failed only on conditions.
The round 3 decisions in the continuity plan follow from this.

### Judge v3 calibration (e1f835c)

The fact-tracking judge now grades seven criteria: `dropped_true_condition`
(a still-true condition removed), `kept_ended_condition` (a condition the
narration ended is still listed) and `state_as_place` (a state recorded as a
thing's where) replace the loose single label, and a thing the narration
introduces and the game keeps is correct, not invented. Calibrated on 21
constructed cases (the 13 round-1 cases relabelled plus 8 new: unplugged but
still charging, charging correctly removed, drawer state as its place, a
still-true condition replaced, a condition added with the old one kept, a
narrated notebook kept, the same notebook not kept, and a new thing the
narration never mentioned), 151 scored labels per pass, two passes per run.

- First run: 149/151 and 150/151. Two misses on one case were a construction
  error in the case, not the judge: the narration plugged the phone into
  Kristin's laptop while the given facts left the laptop in her truck, so
  "narration contradicts given facts" was the correct call. The plug-in cases
  were rebuilt with the laptop on the kitchen counter.
- Rerun: 149/151 and 151/151. Every remaining miss across the four passes
  (3 in all) is `kept_ended_condition` marked yes on a drawer-opened case whose
  after-state had correctly removed `shut`; the judge's own reasons misstate the
  after-state. Accepted, with the caveat that `kept_ended_condition` may be
  slightly overcounted on opening turns.

Cases, labels and outputs are in the session scratchpad
(`calibration-v3/`, first run under `pass1/`).

### Round 3 smoke: the example dropped the `where` key (861f041)

One replicate of each variation with capture v3 (partial entries, merged match
call, per-turn selection, persisting narrated things). The engine side worked:
"drawer" and "laptop" resolved to Michelle's carved drawer and Kristin's laptop
through the match call, a condition-only "note" with no place was correctly not
persisted, THINGS stayed at three things a turn, and the match call fired once
per run. But the new rule line's example showed only a `condition` key, and the
narrator stopped using `where`: it returned `{"location": "Kristin's pocket"}`,
`"owner": "Michelle"` and `"condition": "locked"` as a string, all rejected, so
most moves were lost (two-scene 5/11, 40-turn 21/37). Not a capture result;
the line is being replaced with one that names both keys and shows an example of
each, then re-smoked. Smoke rows removed from the ledger.

### Round 3 re-smoke with both keys named (7727375)

The narrator is back to `where` and `condition` (7 and 21 `where` entries, 0
invalid entries, 0 and 1 rejected turns; match call 3 and 2 times). Scores are
still low (two-scene 2/12, 40-turn 19/39), and reading every failing turn
sorts them into (offline human-read categorisation):

| | 40-turn | Two-scene |
|---|---|---|
| Correct | 19 | 2 |
| Narrator narrated a change but returned nothing (`{}` or `null`) | 8 | 3 |
| Capture wrong this turn | 6 | 6 |
| Narration contradicts its given facts, capture itself fine | 6 | 1 |

- **Omissions**: "puts it in her jacket pocket", "carries the laptop back into
  the house", handing the phone to the man, all with an empty reply.
- **State as place, cascading**: `{"drawer": {"where": "open"}}` resolved to
  the carved drawer, which then kept `shut` and had "open" as its place; every
  later 1A turn is failed again on that one error, and in 1B, where the
  drawer's THINGS line had no real place, the narrator put it at the park.
- **Carried rule false positive**: "in Kristin's truck outside the house"
  contains the protagonist's name, so the laptop was always included in 1B,
  whose authored seed is empty.
- **Judge**: a correct capture after narration that contradicts the given
  facts ("picks up the phone from the table" when it was in her hand) is scored
  not kept; no calibration case covers that.

Not run at 4 replicates; next steps await Brandon (omission strategy, carried
detection, per-turn scoring).

Conclusion: a short prompt rule has now been tried for both main failure
mechanisms (names and kept conditions) without reaching the bar. By the
project's ranking the next step is an LLM semantic check of the narrated turn,
or removing the name-matching mechanism (for example accepting a reply whose
name uniquely matches a tracked thing's head noun, decided by the engine
rather than by the narrator). Decision pending with Brandon.

## Steps

1. [x] Build the harness through Ringer (dfe3828, d8b71f8).
2. [x] Calibrate the fact-tracking grader on hand-labelled turns (8a79a2b).
3. [x] Smoke run, then rewrite the change wording (ac478d6).
4. [x] Full run with free phrase lists (f3c7401).
5. [x] Switch the harness to single-value fields; smoke, then 4 x 12 for A and C (bc61627).
6. [ ] Report the comparison and the decision, then write the full-loop plan
   (capture, story-break check, regenerate or warn, commit, carry forward).
