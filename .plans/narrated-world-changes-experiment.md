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

Not run at 4 replicates. Brandon decided: a short omission rule first, carried
things decided by the match call, and whole-state scoring kept.

A 22nd calibration case (a correct capture after narration that says she picks
the phone up "from the table" while it was already in her hand) scored 158/158
in both judge passes, so the judge needs no wording change; the smoke turns it
marked not kept were ambiguous live narration, not a judge rule gap.

### Round 3 smoke after the omission rule and match-call carried (1d4e51d)

One replicate each. Keys stayed `where`/`condition` with no invalid entries.
Empty replies fell to 0 of 39 (40-turn) and 2 of 12 (two-scene). 40-turn kept
facts correct 29/39 (74%, from 19/39), with set down, move between places and
condition change all correct on this small sample; two-scene 5/12. The match
call fired 8 and 4 times; in 1B it reported Michelle's phone as carried, so the
phone stayed in THINGS after the scene change. It also over-refers: for "Check
that you still have Michelle's phone." it listed the laptop and the drawer as
referred, putting them in THINGS, and it returned untracked names such as
"drawer", "bench" and "Kristin" in `refers`, which the engine ignores. Both
Ringer smoke checks logged FAIL only because the live check still looked for the
superseded first rule line; the runs were valid. Smoke rows removed from the
ledger; the 4-replicate runs followed.

### Round 3 two-scene, 4 replicates (1d4e51d)

bench/results/item-facts-v3-two-scene-1a, 47 judged turns, whole-state scoring.
Round 2 rate is from the no-damage two-scene run (45 turns).

| Change type | Turns | Kept facts correct | Rate | Round 2 | Missed | Invented | Dropped true | Kept ended | State as place | Contradicts facts | Match calls | Things given (avg) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 8 | 7 | 88% | 7/8 | 1 | 1 | 1 | 0 | 0 | 0 | 4 | 2.1 |
| check a carried thing | 7 | 3 | 43% | 6/7 | 1 | 4 | 0 | 0 | 0 | 2 | 7 | 2.4 |
| open or close | 4 | 3 | 75% | 0/4 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 3.0 |
| pick up or put away | 8 | 2 | 25% | 5/8 | 0 | 5 | 0 | 1 | 0 | 7 | 5 | 3.2 |
| move between places | 8 | 5 | 62% | 2/8 | 3 | 2 | 0 | 0 | 0 | 0 | 5 | 3.0 |
| damage | 4 | 2 | 50% | 0/4 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 3.0 |
| hand to another character | 4 | 2 | 50% | 2/4 | 2 | 2 | 0 | 0 | 0 | 0 | 4 | 1.8 |
| leave the scene | 4 | 4 | 100% | 1/2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3.0 |
| **All** | 47 | 28 | 60% | 23/45 | 10 | 14 | 1 | 2 | 0 | 9 | 29 | 2.7 |

Continuity judge: contradicts a stated fact 10/47, Kristin acts beyond the
command 21/47, scene restarts 2/47. 33 match calls in all (29 before turns plus
end-of-run resolution).

- Opening, moving, damage and leaving the scene improved; only leaving the
  scene reaches 92%.
- **Pickups fall to 2/8, and the failure is a cascade from narration**, not
  capture alone: on "Look carefully at Michelle's phone." the narrator has
  Kristin pick the phone up, and on "Pick up Michelle's phone and put it in your
  pocket." all four replicates narrate "Kristin reaches into her pocket and pulls
  out Michelle's phone" while the reply reports the commanded result, "in
  Kristin's pocket". The judge marks those invented and contradicting.
- **The match call makes wrong semantic calls**: "Check who has Michelle's
  phone now." came back as `{"man": {"where": "on the bench"}}`, and the match
  call mapped "man" to Michelle's phone, moving the phone to the bench; it also
  keeps listing the laptop, the drawer and a note in `refers` for commands that
  mention only the phone, and once reported the laptop as carried.
### Round 3 40-turn, judge flake and interim numbers

The 40-turn run's narration completed (4 replicates, 155 accepted turns) but the
fact-tracking judge threw "invalid verdict" and the bench discarded the judging
of the whole billed run. Re-judging the saved turns one replicate at a time,
keeping every raw reply, showed the cause: GPT-5.4 returned one verdict FEWER
than the turns for two replicates (37 for 38, 38 for 39), omitting the last
turn, with the response complete and every field valid - not truncation. The
judge requires an exact count and throws. Fix: retry once on a count mismatch
and name both counts on a second failure.

Interim, from the two replicates that judged (78 turns):

| Change type | Turns | Kept facts correct | Rate |
|---|---|---|---|
| look (no change asked) | 15 | 10 | 67% |
| check a carried thing | 4 | 2 | 50% |
| open or close | 15 | 8 | 53% |
| pick up or put away | 16 | 7 | 44% |
| set down | 8 | 6 | 75% |
| move between places | 8 | 7 | 88% |
| condition change | 12 | 11 | 92% |
| **All** | 78 | 51 | 65% |

- **The opened-box example did not stop a state going in the place field.** One
  capture, `{"Michelle's carved drawer": {"where": "open"}}`, rode along for the
  rest of the scene: of 24 turns flagged `state_as_place`, 22 carry that same
  drawer entry. Under whole-state scoring that single error costs every later
  turn, and it is the largest single cause of the 40-turn rate.
- Condition change (92%) and move between places (88%) are the strongest types;
  pickups (44%) fail mostly through narration contradicting the given facts (9
  of 16).

### Round 3 40-turn, all four replicates (a84c90c)

bench/results/item-facts-v3-long-1a, 155 judged turns, whole-state scoring.
Round 2 rate is from the 40-turn v2 run (154 turns).

| Change type | Turns | Kept facts correct | Rate | Round 2 | Missed | Invented | Dropped true | Kept ended | State as place | Contradicts facts |
|---|---|---|---|---|---|---|---|---|---|---|
| look (no change asked) | 28 | 12 | 43% | 83% | 4 | 1 | 1 | 1 | 16 | 3 |
| check a carried thing | 8 | 2 | 25% | 100% | 0 | 0 | 0 | 0 | 4 | 4 |
| open or close | 31 | 8 | 26% | 66% | 11 | 14 | 4 | 6 | 20 | 9 |
| pick up or put away | 32 | 10 | 31% | 63% | 2 | 4 | 0 | 1 | 13 | 15 |
| set down | 16 | 6 | 38% | 33% | 2 | 2 | 4 | 2 | 8 | 0 |
| move between places | 16 | 9 | 56% | 50% | 1 | 0 | 0 | 1 | 9 | 1 |
| condition change | 24 | 17 | 71% | 67% | 3 | 4 | 0 | 1 | 9 | 1 |
| **All** | 155 | 64 | 41% | 66% | 23 | 25 | 9 | 12 | 79 | 33 |

Continuity judge: contradicts a stated fact 40/155, Kristin acts beyond the
command 52/155, scene restarts 13/155. 27 match calls across the run.

**One defect produces most of the loss.** Per replicate:

| Replicate | Kept facts correct | State as place |
|---|---|---|
| 1 | 9/38 (24%) | 21 |
| 2 | 24/40 (60%) | 24 |
| 3 | 4/39 (10%) | 34 |
| 4 | **27/38 (71%)** | **0** |

In replicates 1, 2 and 3 the same turn - "Open the drawer with your initials
carved into it." - returned the drawer's state as its place
(`{"where": "open"}`, once as `{"condition": ["open"], "where": "open"}`, once
under the short name "drawer" that the match call resolved). Under whole-state
scoring that single wrong entry fails nearly every later turn of the scene.
Replicate 4 never made it and scored 71%, the best 40-turn rate measured so far.

So the opened-box example (rank-1 rule, second attempt at this defect) did not
stop a state landing in `where`. No change type reaches 92%; the ceiling with
the defect absent is about 71%.

### Round 3 smoke with the place key (40c97d2)

Brandon's choice: ask for `place` instead of `where`, since "where is it now?"
invites "open". One replicate each.

| | Two-scene | 40-turn |
|---|---|---|
| Kept facts correct | 10/12 (83%) | 9/40 (22%) |
| State as place | 0 | 30 |
| Reply keys `place` / `where` | 14 / 0 | 36 / 0 |
| Invalid entries, empty replies | 0, 0 | 0, 2 |

The rename fixed the key itself: the narrator used `place` every time, never the
legacy `where`, and sent no invalid entries. It did not stop a state being the
ANSWER, but the remaining failure is now confined to commands that open or close
something:

- turn 8, "Close the drawer." -> `{"Michelle's carved drawer": {"place": "closed"}}`
- turn 26, "Open the drawer with your initials carved into it." -> `{"place": "open"}`
- turns 6 and 7 were correct, handling `shut` as a condition, so the model only
  confuses the two when the command itself is to open or close.

That single entry costs the rest of the run under whole-state scoring: set down
0/4, move between places 0/4 and check a carried thing 0/2 are all collateral
from the drawer having no real place. The script composition explains the gap
between the two runs - one open/close turn in twelve (83%) versus eight in forty
(22%) - not a difference in the format.

Brandon chose the match-call normalisation (rank 2, the call already fires on
most turns).

### Round 3 smoke with place normalisation (225a3fe)

The match call now remembers each captured place and asks whether the text is a
place or a state; a state restores the previous location and becomes the
thing's condition. One replicate each.

| | Two-scene | 40-turn |
|---|---|---|
| Kept facts correct | 7/12 (58%) | 20/38 (53%) |
| Previous smoke | 10/12 (83%) | 9/40 (22%) |
| State left in a place field | 0 | 0 |
| Place fixes | 0 | 3 |
| Match calls per turn | 0.92 | 0.87 |

- **The defect it targeted is gone**: no state remains in any place field, and
  the drawer now keeps "in Kristin and Michelle's shared house" with condition
  `["closed"]` after "Close the drawer." The 40-turn run more than doubled.
- **But the fix misfires.** Of three corrections, one was right (the drawer) and
  two destroyed correct captures: asked about Michelle's phone at
  "on the kitchen counter", the match model answered "state", so the harness
  restored "in Kristin's hand" and made the counter a condition. That is why the
  two-scene replicate fell.
- **The question is also mis-keyed.** The model sometimes answers `places` by the
  place TEXT rather than the thing's name
  (`{"in Kristin's hand": "state", "on the kitchen counter": "place"}`); those
  answers match no remembered name and are silently ignored, wasting the call.
- Cost is now about two model calls per turn (one narration, ~0.9 match).
- The two-scene losses are otherwise narration faults, not capture: the narrator
  opens the drawer and reports nothing, says the phone was on a coffee table
  when it was in hand, or introduces a note it never reports.
- Known gap in the implementation: a place captured on a run's FINAL turn is
  never checked, because `resolve_held` returns early when nothing is held.

Next: tighten only the wording - key the answer by the thing's name, and
contrast "on the kitchen counter" (a place) with "open" (a state) - then
re-smoke before spending on four replicates.

### Round 3 smoke after the wording fix (ef03215)

| | Two-scene | 40-turn |
|---|---|---|
| Kept facts correct | 10/12 (83%) | 16/40 (40%) |
| Previous smoke | 7/12 (58%) | 20/38 (53%) |
| Place fixes | 0 | 1, and it was wrong |
| Answers keyed by text (ignored) | 2 of 11 | 7 of 38 |
| State left in a place field | 0 | 0 |
| Match calls per turn | 0.92 | 0.95 |

The wording fix worked on its target: mis-keyed answers fell from 17 of 31
before it to 2 of 11 and 7 of 38, and the destructive corrections nearly
stopped. The one correction the 40-turn run did make was still wrong -
`Kristin's laptop` at "in the truck" judged a state.

**But the defect moved rather than died.** With the narrator no longer putting a
state in the place field, it now gives a plausible WRONG PLACE instead: turn 6,
"Open the drawer with your initials carved into it.", returned
`{"place": "in front of Kristin"}`. The normalisation cannot catch that, because
it really is a place, and the drawer then keeps it for the whole run (turns 8,
26, 28, 35, 39). Worse, the open/closed state is now never recorded at all: after
"Close the drawer." the drawer's condition list is empty. Open or close scored
2/8, pick up or put away 1/8, set down 1/4, move between places 1/4.

Single replicates are noisy - the 40-turn figure moved 22%, 53%, 40% across three
smokes of successive fixes - so these are read as direction, not measurement. The
four-replicate run on this committed state is the measurement of record.

This is the case for the declared state axes candidate recorded under Phase 1a:
with `open|closed` declared for the drawer, "Close the drawer." has somewhere to
land that is not the place field, and a place answer that is not a declared state
value is simply left alone.

## Round 3 measurement: four replicates each (417e4f1)

The measurement of record for round 3, on the committed state (place key, match
call for names/carried/places, normalisation). Smoke replicates are not quoted.

Two-scene, bench/results/item-facts-v3-place-two-scene-1a, 48 judged turns:

| Change type | Turns | Correct | Rate |
|---|---|---|---|
| look (no change asked) | 8 | 6 | 75% |
| check a carried thing | 8 | 4 | 50% |
| open or close | 4 | 3 | 75% |
| pick up or put away | 8 | 3 | 38% |
| move between places | 8 | 5 | 62% |
| damage | 4 | 0 | 0% |
| hand to another character | 4 | 2 | 50% |
| leave the scene | 4 | 3 | 75% |
| **All** | 48 | 26 | 54% |

40-turn, bench/results/item-facts-v3-place-long-1a, 156 judged turns:

| Change type | Turns | Correct | Rate | State as place | Invented |
|---|---|---|---|---|---|
| look (no change asked) | 29 | 16 | 55% | 14 | 7 |
| check a carried thing | 8 | 3 | 38% | 5 | 2 |
| open or close | 31 | 15 | 48% | 19 | 15 |
| pick up or put away | 32 | 12 | 38% | 14 | 10 |
| set down | 16 | 7 | 44% | 10 | 5 |
| move between places | 16 | 5 | 31% | 10 | 10 |
| condition change | 24 | 13 | 54% | 9 | 6 |
| **All** | 156 | 71 | 46% | 81 | 55 |

Continuity: contradicts a stated fact 57/156, acts beyond the command 64/156,
scene restarts 11/156. 140 match calls, about 0.9 per turn, so capture costs
roughly two model calls a turn.

**No change type reaches 92% in either run.** The best is 75% on three two-scene
types with four to eight turns behind each.

**The normalisation does not work, and the reason is structural.** 81 of 156
turns still carry a state in a place field. In replicate 1, 34 turns carried one
while the normalisation fired twice - and both times it was wrong, calling
`Kristin's laptop` at "in the truck" and at "on the passenger seat of her truck"
a state. The match call runs on the SAME 8B narrator model through
`CloudflareTurnProvider._request`, so the rank-2 semantic check is being
performed by the model that made the error in the first place. That is why
asking it to classify place-versus-state fails at scale while costing a second
call per turn.

**Round 3 did not beat round 2 on whole-state accuracy.** The 40-turn script
scored 99/157 (63%) in round 2 against 71/156 (46%) now; two-scene was 23/45
(51%) in round 2 against 26/48 (54%). The comparison is indicative, not clean:
the packages differ (carved drawer rename, the not-damaged fact removed) and the
judge gained two criteria, though `facts_after_correct` is defined as before.

Conclusion: further prompt wording has been tried three times against the
state-as-place defect (name both keys, opened-box example, rename to `place`)
and a semantic check once, without reaching the bar. The next move is the
declared state axes candidate under Phase 1a - deterministic, authored, and
needing no model call - not another bench round.

Judge note: the fact-tracking judge again returned fewer verdicts than turns even
with its retry, so the bench discarded the whole run's judging; re-judging the
saved turns one replicate at a time succeeded on all four (39/39, 40/40, 38/38,
39/39). Judging a replicate per call is the reliable shape.

## Round 4: binary state axes (d4ca5b2, 9fb31be)

Brandon's design, corrected twice by him during the build: an axis is EXACTLY
two opposite poles with optional aliases (`{"shut": ["closed"], "open": []}`),
because recording one pole implies the negation of the other; and an axis value
occupies a slot of its own, evicting only its opposite, because "lit" is not the
opposite of "open" and a lantern may be both lit and open. The match call's
place question, which measured 1 correct correction in 3, was deleted.

One replicate each after the axis-slot fix:

| | Two-scene | 40-turn |
|---|---|---|
| Kept facts correct | 4/12 (33%) | 31/40 (78%) |
| States left in a place field | 0 | 0 |
| Axis fixes (pole given as a location) | 0 | 0 |
| Canonicalisations observed | 0 | 1 |
| Match calls per turn | 0.42 | 0.15 |

- **The state-as-place defect is gone** in both runs, and capture now costs far
  less: match calls fell from about 0.9 a turn to 0.15-0.42 once the places
  question was removed.
- **But the axes barely fired.** Zero pole-as-location fixes in either run and
  one canonicalisation in 52 turns, so neither figure is evidence that axes
  work. The 40-turn 78%, the best measured all round, and the two-scene 33%,
  the worst, both come from elsewhere.
- **A rule I specified is actively harmful.** I wrote that a condition reply
  preserves the current axis value unless the reply itself names a pole. The
  narrator's way of saying a state ended is an EMPTY condition list -
  `{"drawer": {"condition": []}}` - so the stale pole survives and is charged
  against every later turn. In the two-scene run the drawer stayed `shut` after
  being opened for 7 of 12 turns, and the same reply shape kept the 40-turn
  drawer `open` after "Close the drawer."

Brandon chose: an empty list clears the axis value, so the state reads unknown
rather than stale (f461739). A non-empty reply naming no pole still preserves
the axis value; that asymmetry is deliberate and still open.

## Round 4 measurement: four replicates each (f461739)

bench/results/item-facts-v3-place-*, both judges clean (4 calls each).

Two-scene, 47 judged turns:

| Change type | Turns | Correct | Rate |
|---|---|---|---|
| look (no change asked) | 8 | 5 | 62% |
| check a carried thing | 7 | 5 | 71% |
| open or close | 4 | 4 | **100%** |
| pick up or put away | 8 | 3 | 38% |
| move between places | 8 | 6 | 75% |
| damage | 4 | 0 | 0% |
| hand to another character | 4 | 2 | 50% |
| leave the scene | 4 | 3 | 75% |
| **All** | 47 | 28 | 60% |

40-turn, 159 judged turns:

| Change type | Turns | Correct | Rate |
|---|---|---|---|
| look (no change asked) | 31 | 22 | 71% |
| check a carried thing | 8 | 6 | 75% |
| open or close | 32 | 19 | 59% |
| pick up or put away | 32 | 19 | 59% |
| set down | 16 | 9 | 56% |
| move between places | 16 | 14 | 88% |
| condition change | 24 | 16 | 67% |
| **All** | 159 | 105 | 66% |

Whole-state accuracy by round, same scripts:

| | Two-scene | 40-turn |
|---|---|---|
| Round 2 (format v2) | 23/45 (51%) | 99/157 (63%) |
| Round 3 (capture v3) | 28/47 (60%) | 64/155 (41%) |
| Round 3 (place key + normalisation) | 26/48 (54%) | 71/156 (46%) |
| **Round 4 (binary axes)** | **28/47 (60%)** | **105/159 (66%)** |

- **The 40-turn script is at its best measured value**, 66%, up from 46% and
  past round 2's 63%. Two-scene is level with its best, 60%.
- **State as place is gone**: 0 of 206 turns across both runs, against 81 of 156
  in round 3. Kept-ended conditions are 0 and 3.
- **Capture is cheaper**: 26 and 23 match calls for 47 and 159 turns, about 0.5
  and 0.14 a turn, against roughly 0.9 when the normalisation call existed.
- **But the axes themselves did little work**: 0 axis fixes in the two-scene run
  and 6 across 159 turns in the 40-turn run. Most of the gain comes from
  DELETING the failed normalisation and from an empty list clearing a stale
  pole, not from routing a pole out of the place field. The honest reading is
  that round 4 removed damage rather than adding capability.
- **No change type reaches 92%** except open or close in the two-scene run, 4 of
  4 turns, which is too thin to count. The best broad figures are move between
  places 88% (16 turns) and check a carried thing 75%.
- Damage is 0 of 4 again, all four missed. Pickups remain weak (38% and 59%)
  and are dominated by narration contradicting its given facts (5 and 14 turns).
- Continuity: contradicts a stated fact 12/47 and 54/159; scene restarts 2/47
  and 10/159.
- **Narrator initiative is not a failure** (principle 1: a narrated change
  belongs to the world whoever caused it; only a story-breaking change is
  refused). The useful statistic is whether its consequences were captured. The
  narrator acted unprompted on 25 two-scene turns, of which 15 kept facts
  correct and 7 missed the change, and on 68 forty-turn turns, of which 39 kept
  facts correct and 25 missed - about 58% captured, 32 changes silently lost
  across both runs. Every failing turn is listed in
  `bench/results/round4-failures.md`, which counts capture defects and narration
  that contradicts canon or its given facts, and annotates initiative as
  context.

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
