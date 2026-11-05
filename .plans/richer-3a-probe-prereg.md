# Preregistration: the richer scene 3A, the detention level

Written 2026-11-03 before any billed 3A run. Same method and instruments as `.plans/richer-2c-probe-prereg.md` (including the
1B value rule: presence is necessary but not sufficient; every added detail must do a job). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free).** `bench describe` runs on both arms (package hashes: baseline `5ab57e3e...`, candidate `7b6d8c45...`). Offline,
`tests/test_richer_3a.py` hands each scripted command to its intended reveal given the facts the earlier commands establish. Whole
quick suite on the branch: 4127 passed, 31 skipped; ruff clean. Both arms use `entry_state: thorough`. The thorough entry state earns
`broadcast_loop_confirmed`, `lemon_cake_calendar_read` and `committed_to_rescue` but NOT `held_transfers_seen` or `badge_craft_noted`
(checked offline), so the candidate arm sets `entry_facts` to those two (this exercises the variants of the wrist tags and the reader).
The frozen baseline does not declare them, so its arm cannot set them; it has nothing authored for tags, the radio loop, the proof or
the reader anyway.

## What changed in 3A (each addition has a job)
- **Wrist tags** (F, 3A.1): every captive's transfer date is a week old; Michelle held them one ticket at a time from the archive
  terminal. Pays off the 2B held transfers and the 2C cart tags, answers "who held them" and "why are they alive". With
  `held_transfers_seen` the tags carry the closing code. Declared thing: `wrist_tags`.
- **Loop in the radios** (G, 3A.1): Michelle's coded words ride inside the facility's own repeating message and change one word; the
  guards no longer hear it. Pays off the loops of 1A, 1B and 1C, answers how the captives came to trust a voice they could not see, and
  plants 3B/3C ("when it stops, everyone will know"). No new thing (uses `stolen_radio`); with `broadcast_loop_confirmed` it says "the same
  ninety seconds".
- **Michelle's private proof** (H, 3A.2): after the medical level, a question about the kitchen calendar; she answers "Saturday,
  circled, K, lemon cake" and apologizes for the birthday. Pays off the 1A calendar; the facility never saw that wall, so the player can
  stop doubting her after the false-recollection experiments. Needs the new fact `lemon_cake_calendar_read`, which `k_sl_1a_g_r2` now
  sets (the only existing entry changed). No new thing.
- **Checkpoint reader** (I, 3A.4): Brandon opens it on the first pass without looking at the keypad; Michelle's people watch him instead
  of the door. Pays off the 1B keypad and the 2A/2B badge checks (with `badge_craft_noted`: "the same ease he showed at the gate"), and
  plants his usefulness against their distrust. Declared thing: `checkpoint_reader`.
- F, G, H, I are optional, priority -1, not voiceable, short statements, windows 0/8/9 (every existing 3A storylet has earliest 0, so
  no forward-activation ordering is at risk).

## Questions
- **Q1 Invented material.** Plain things resolved new, and specifics the narrator invents (what the tags say, who held the transfers,
  what the radios play, the proof's content, what the reader checks), old versus new 3A. The baseline has nothing authored for any of them.
- **Q2 Authored details delivered when earned (candidate).** F on command 2, G on command 3, H on command 5, I on command 7. Each lands
  on the command that asks for it. Record the turn each landed and whether any was refused or went to a different reveal.
- **Q3 No regression.** Required path: reunion (`k_sl_3a_a_r1`, command 1), the medical level (`k_sl_3a_b_r2`, command 4), the framed
  official (`k_sl_3a_d_r1`, command 6), the uprising (`k_sl_3a_c_r1`, command 8) and the bridge to 3B (command 9). Record per replicate
  the turn each landed and whether the scene was left by an earned transition.
- **Q4 Value.** For each detail: does it plant, pay off, deepen or set mood, or is it an inert prop? Is the narration better, flat or
  busier than baseline? Watch the known faults: the narrator or Brandon reciting statements as dialogue, the engine's delivery text
  repeating what the narrator just wrote (echo; the reader delivery says Brandon never looks at the keypad, the likeliest echo), the same
  image repeated, the narrator inventing what a thing shows, and Michelle's explanation ("I held them") appearing before the tags are read.

## Design
Arms `richer-3a-baseline` (frozen story from `e28473a1`, `bench/frozen/continuity-pre-richer-3a/`) and `richer-3a-candidate` (current
story, `entry_facts` held_transfers_seen and badge_craft_noted), script `richer-3a-detention` (nine imperative commands): `Free the
captives.` `Read the wrist tags.` `Listen to the stolen radio.` `Enter the medical level.` `Ask Michelle about the lemon cake.` `Ask the
senior official about the gate codes.` `Check the checkpoint reader.` `Tell the prisoners to start the uprising at the checkpoints.`
`Lead the prisoners upward toward the command levels.` 4 replicates per arm, both judges on, shipped transports, no retries, partial rows
kept, one opening request each. Projected cost at 11 neurons per turn, opening included: 10 turns x 4 replicates = 440 per arm, 880 in
all. Request cap 150 narrator and matcher requests per run; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or
`AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC. 3A pressure events fire at turns 8 and 9 (lockdown, code deadline); the uprising is command 8.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each detail, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (Q3) is a defect to fix before 3B.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500), and name any
  turn over 5,000.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
The transmit branch of 2C entering 3A (the thorough entry state chose rescue), the other order of commands, the 3A.2 experiments
detail beyond the proof, later scenes (the loop plants pay off in 3B and 3C), hosted staging, other models, wording tuning.

## Owed to other scenes (so the plants pay off)
3B/3C: the loop in the radios is the facility's own repeating message; the final broadcast must replace it ("when it stops, everyone will
know"), and every outbound channel is watched (2C monitor light), so the broadcast must be forced from Rebecca's office. 3B can use
Brandon's ease at readers when he opens doors on the climb. The supervisor on Rebecca's purge list (a payoff for the 2A alarm log) is
still not covered.

## Result (run 2026-11-03/04, branch `richer-narration-3a`, commit `0606fa9c`)
Outputs `bench/results/richer-3a-probe/{baseline,candidate}` (gitignored), 4 replicates each, none failed, 880 projected neurons. Every
turn of both arms read by hand (scratchpad reports, not in the repo). Replicates reported separately; the judge scores are not real signal
at 4 replicates (candidate 4.75 against baseline 3.0 of 7, `rewards_investigation` 4/4 against 0/4, but the gap is inside the interval). The
candidate had one malformed narration segment that the transport dropped and logged, and one rejected turn (below).

**Headline: richness is supported on the 3A path. 15 of 16 detail commands delivered on the command that asks for them, the baseline's
invented material around those four things is gone, and the existing path did not regress. Four defects are open: the keypad
contradiction in the reader reveal, echoes, one rejected proof turn, and a required-path flake that predates this change.**

- **Q1 Invented material.** Plain things resolved new: baseline 10 in 36 turns (wrist tags 2, checkpoint reader 4, prisoners 2, armored
  teams 2), candidate 5 in 35 (prisoners 2, armored teams 2, uprising 1), all of the candidate's on the uprising turn, none from the four
  details. What the narrator made up where nothing was authored (baseline): tags "encrypted" or "a mix of names, numbers, and codes" (3/4);
  the stolen radio speaking as "Phoenix-1" or "Dr. McGehee" with a location (4/4); a made-up shared memory of baking a lemon cake, which
  Michelle then dismisses with "no time" (4/4, so the baseline wrongly answers the question the proof exists for); the reader as "a metal
  box with a glowing screen" and, once, a keypad (4/4). Candidate: radio invention once (replicate 3: "Echo-1, Sierra-7, Bravo-3"), none
  for tags or the proof, and the reader problem below. The opening still invents an unnamed woman in the rows in both arms (baseline "a scar
  above her left eyebrow" 4/4; candidate "mouths 'not yet'" 3/4); same fault, older than this change.
- **Q2 Delivered when earned.** Wrist tags (command 2) 4/4; loop in the radios (command 3) 4/4; Michelle's proof (command 5) 3/4, the
  fourth turn REJECTED (`missing_knowledge_content`, "does not convey: Saturday": the narrator's own text omitted Saturday, so the player's
  command got no answer); checkpoint reader (command 7) 4/4. All three variants fired every time they were due (sensor fault 4/4, ninety
  seconds 4/4, "the same ease he showed at the gate" 4/4). No reveal went to a different entry.
- **Q3 No regression.** Reunion (`k_sl_3a_a_r1`) 4/4 and the medical level (`k_sl_3a_b_r2`) 4/4 in both arms. The framed official
  (`k_sl_3a_d_r1`, command 6) landed in 1 of 4 replicates in the baseline AND 1 of 4 in the candidate; the uprising (`k_sl_3a_c_r1`) 1 of 4
  in both arms. Both reveals were offered every time (D was in the offer in all eight rows); the engine found no unique authored handoff
  and the narrator did not pick them. The scene was left by an earned transition in 1 of 4 baseline replicates and 0 of 4 candidate ones,
  but both are the same flake (the one baseline exit is the one replicate where D and C both landed; the candidate's one replicate with
  both ran 8 commands because of the rejected turn). **This flake predates 3A and is not caused by it, but it means this script cannot
  measure the 80 percent exit bar.**
- **Q4 Value.** Wrist tags: strongest. It answers 2B's "who held the transfers" and "why are these people alive", pays off the 2C cart tags,
  and the baseline's fake "encrypted" text is replaced. Loop in the radios: pays off the loops of 1A to 1C, replaces invented radio
  voices, and plants "when it stops, everyone will know"; the narrator never contradicted it. Michelle's proof: does its job (the
  baseline invented the wrong memory); when it lands, Kristin's doubt is answered and the player is told why. Reader: pays off the
  badge checks, but see defect 1. Candidate narration is longer than baseline on those turns because the delivery text is appended.
  Narrator quirks seen: Michelle's reply "comes through the radio" in 3 of 3 proof turns although she stands beside the captives
  (minor); Brandon "standing in front of the reader" is fine.

### Open defects (cures known or proposed; nothing is changed yet)
1. **Keypad contradiction, reader reveal, 3/4.** The narrator's lead-up writes Brandon "with his eyes fixed on the keypad", then the
   delivery says "Brandon never looks at the keypad". Cause: the statement and delivery name the keypad, and the narrator also invents
   one on its own (baseline once). Proposed cure, subtractive: take "keypad" out of the statement, `must_convey` and the delivery
   ("The checkpoint door opens on the first pass. Michelle's people watch Brandon instead of the door."), keeping the 1B payoff only in a
   variant for a player who saw Brandon ignore the keypad if such a fact exists.
2. **Echo.** The narrator writes the revealed content, then the engine's delivery repeats it: wrist tags 2/4 (the date and the code),
   radios 1/4 (ninety seconds), proof 1/4 (the answer written out twice). Brandon asked for no echo in 1C and 2B. The cure used there
   was to move the repeated content into the thing's placement text or Details line and keep only what is new in the delivery; here
   that means the tags' placement carrying the shared date, with the delivery giving Michelle's line and the code. Needs a re-probe
   because the 1C data showed the cure leaves about 2 in 8.
3. **Rejected proof turn, 1/4.** `must_convey` for the proof is three groups ([lemon cake], [Saturday], [birthday]) and the narrator
   must say all of them. Proposed: two groups, [lemon cake] and [Saturday, birthday].
4. **Required-path flake (older than 3A).** The framed official and the uprising reveals hand off in 1 of 4 replicates in BOTH arms
   although they are offered. Worth its own diagnosis (run the exact turns offline and compare the candidate list with the matcher's
   result); it hides the exit bar and the earned-transition rate for the whole scene.

### Prompt lengths
Narrator prompt (system 2,527 plus user), longest per command: candidate 4,867 / 5,726 / 5,716 / 5,551 / 5,859 / 5,867 / 7,842 / 7,634 /
10,026 characters; baseline 4,825 / 6,057 / 5,557 / 5,524 / 5,805 / 5,867 / 6,545 / 6,714 / 8,473. 31 of 35 candidate turns and 32 of 36
baseline turns are over 5,000, so the line does not discriminate for a nine-command script: the user section carries the recent
narration, and the candidate's longer replies (delivery text appended) grow it by up to 1,500 characters by command 7. The static
budget test (`tests/test_prompt_budget.py`) passes. If that growth matters, compact what the narrator is shown of earlier turns; this
is not a 3A-specific change.

## Amendment 1: the probe fixes (2026-11-04, Brandon: "fix all the open defects first")
Each fix was compared with the plan and the earlier scene fixes before it was built. Tests first (`tests/test_richer_3a.py`
`test_the_probe_defects_are_cured_at_the_source`, `tests/test_handoff_typed_tiebreak.py`); quick suite 4133 passed, 31 skipped; ruff clean.

1. **Keypad contradiction.** The reader reveal no longer names the keypad (statement, `must_convey`, delivery, variant, plot prose). The
   narrator invented the stare from the statement. Precedent: the subtractive fixes of 1B and 2B (take the cause out, add no rule).
2. **Echo.** Same technique as the 1C door, the 1C pallets and the 2C monitor light (Amendment 1 of the 2C prereg, echo gone 4/4): the
   imagery moves into the thing's placement text and the delivery adds only what is new. The wrist tags' placement carries the shared date
   and "a week old"; the stolen radio's placement carries "tuned to the facility's own message, played on repeat"; the tags and radio
   deliveries give Michelle's line, the code and the coded words; the proof delivery summarizes ("gets every detail right: the day, the
   circle, the lemon cake") instead of quoting the answer. Also as in 2C, the three Details additions I had made to 3A.1, 3A.2 and 3A.4
   were removed (the probe's narrator prompt grew up to 1,500 characters over baseline; the imagery now costs prompt space only when the
   player asks). Expect a residual of about 2 in 8, as with the earlier echo fixes; zero needs the engine change the plan already
   records as needing Brandon's go (not showing quiet reveals' delivery text to the narrator).
3. **Rejected proof turn.** `must_convey` is [lemon cake] and [Saturday, birthday] (the 2B rule: ask the narrator for less, not more).
4. **Official and uprising flake (older than 3A).** Diagnosed offline: `assemble_turn_prompt` appends the display names the player's nouns
   resolved to ("gate codes" becomes "emergency override codes"); "override" then satisfied the verb group of the second official reveal
   (`k_sl_3a_d_r2`), two reveals tied on group count and no handoff was staged. The uprising reveal only failed because it needs the
   official's reveal first. Reproduced deterministically in `test_the_framed_official_hands_off_with_the_names_the_engine_appends`.
   Fix: `uniquely_matched_authored_handoff` takes `typed_input` and, only when a tie remains after the existing rules, prefers the
   matches that also fit the words the player typed (the same function and the same kind of change as the 1C closeout tie-break). Blast
   radius, measured over the whole story as 1C was (1,657 synthetic commands built from each reveal's own evidence, with the resolved
   names appended): 34 commands change, every one from no handoff to the one reveal the player's own words fit (1A "Search the overturned
   chair", 2B "Pull up the file", 3A "Warn the code", 3A "Listen to the radio"); none switches a handoff that already worked. Rejected
   alternative: delete "override" from the second reveal's verbs (one word, but it leaves the class open).

Re-probe not yet run. Proposed (needs Brandon's go, about 440 neurons): the candidate arm only, same script, as `candidate-run2`, not
pooled. Questions: echo on the tags, radios and proof; the reader contradiction; the proof turn rejected; the official on command 6 and the
uprising on command 8, and the scene exit on command 9 in at least 3 of 4 replicates; narrator prompt length against the first run.

### Amendment 1 result (candidate-run2, 2026-11-04, `bench/results/richer-3a-probe/candidate-run2`, 440 neurons, commit `69f229ff`)
4 replicates, none failed, 0 rejected turns, every turn read. Not pooled with the first run; the baseline is unchanged and not rerun.

- **Flake: fixed, 4/4.** The framed official (command 6) and the uprising (command 8) handed off in all four replicates (first run 1/4 in both
  arms), and all four replicates left the scene by the earned transition on command 9 (first run 0/4, baseline 1/4). The 80 percent exit
  bar is met for this script.
- **Rejected proof turn: gone.** 0 rejected turns; the proof landed on command 5 in 4/4 (first run 3/4).
- **Keypad contradiction: gone, 0/4.** The narrator describes the reader as "a small device beside the door at the top of the block"; the
  delivery adds only that it clears on the first pass and that Michelle's people watch Brandon. No lead-up contradicts it.
- **Echo: fixed for the tags, radios and reader; residual on the proof, 2/4.** Tags: the narrator writes the shared date from the
  placement text and the delivery adds the code and Michelle's line, nothing twice (first run 2/4 echoed). Radios: the narrator writes
  "the facility's own message on repeat" from the placement text and the delivery adds the ninety seconds and the coded words (first run
  1/4). Reader: no echo. Proof: replicates 2 and 3 write Michelle's answer ("I'm sorry I missed your birthday. The facility never saw
  that wall.") and then the delivery repeats those two sentences word for word (first run 1/3). Replicates 1 and 4 are clean.
- **Invented material.** Plain things new: 1 in 36 turns (`prisoners`, command 9, replicate 4; first run 5, baseline 10). The radio's
  broadcast content is still invented but now matches what the reveal says (a monotone voice reading orders); once an invented
  "Brandon whispers: we need to find Michelle" lead-up (harmless).
- **Prompt length.** Longest narrator prompt per command, in characters: 4,825 / 6,137 / 6,120 / 5,923 / 6,434 / 6,484 / 7,772 / 7,916 /
  10,248 (first run 4,867 / 5,726 / 5,716 / 5,551 / 5,859 / 5,867 / 7,842 / 7,634 / 10,026). Removing the Details additions did not shrink
  it: the growth is the conversation history that carries the longer replies, and the placement text adds a few hundred characters to
  the turns that name those things. The static budget test passes. Unchanged conclusion: this is not 3A-specific.

Remaining, open: the proof echo (2/4). Cure options, none applied: (a) drop "She says she is sorry she missed the birthday. The facility
never saw that wall." from the delivery and keep only "gets every detail right: the day, the circle, the lemon cake", leaving the
sentiment to the narrator (the narrator writes it anyway when it speaks for Michelle); (b) the engine change that keeps quiet reveals'
delivery text away from the narrator (needs Brandon's go and its own probe).

## Amendment 2: managing the narrator prompt, and the proof delivery trim (2026-11-04, Brandon's directions)
Brandon, on the prompt growth: "You are supposed to aggressively manage the context length"; "you only need to keep context about the
items/characters that are in the scene currently ... or those that the player refers to. The world state should be kept by worldkeeper,
but only needs to be accessed within the prompt for the characters/items that apply or are mentioned by the player or another NPC."
My earlier note that the growth was "conversation history" was WRONG: the prompt carries no history. The growth was the CONSTRAINTS block,
which wrote every sayable statement once per speaker present (3A, command 9: 3 speakers x 8 statements, 5,004 of 7,721 characters).

- **Proof delivery trimmed** (the echo cure Brandon chose): "Michelle answers without a pause and gets every detail right: Saturday,
  the circle, the lemon cake." The sorry and the wall inference moved to the statement ("...a question about the kitchen calendar that
  the facility never saw"). Tests in `tests/test_richer_3a.py`.
- **Speaker lines grouped** (`67dc6bb3`, `tests/test_speaker_lines_grouped.py`): each sayable statement is written once, naming every
  NPC who may say it ("A, B and C may say this aloud: ..."); no speaker is offered a statement they were not given. Same code comment
  and reasoning as the earlier protagonist skip. Full 3A state, eight reveals earned, same command: user prompt 7,668 to 5,253
  characters (-31%), CONSTRAINTS 5,682 to 3,267.
- **Characters by presence** (`94e37d2f`, `tests/test_prompt_presence.py`): CHARACTERS introduces the protagonist, and a scene
  participant only when it is placed in the scene (the check the speaker lines use) or the player's command names it (the existing name
  matching, now public as `named_entity_ids`). A character who is not a scene participant is still never introduced. Whole-story entry
  prompts (old to now): 1A 3,333 to 3,074; 1B 3,009 to 2,750; 1C 2,732 to 2,473; 2A and
  2C unchanged; 2B 2,925 to 2,666; 3A 2,890 to 2,736; 3B 2,674 to 2,337; 3C 2,547 to 2,254. Full 3A state now 5,099 characters
  (from 7,668). EARLIER IN THE STORY was already reference-keyed (it holds only earlier knowledge the command recalled; commit `522c00cd`).
- **Quality risk to check:** Michelle is a participant but not present in 1A, 1B, 1C, 2B, 3B and 3C, so her biography now reaches the
  narrator only when the command names her ("Search Michelle's drawer" does; "Search the kitchen" does not). The place-feed fixture and
  one transport test changed for this reason. The 3A candidate script names Michelle on commands 5 only. Quick suite 4138 passed,
  31 skipped; ruff clean.
- **Not changed, as designed:** a sayable statement that names an absent character does not pull that character's biography in (the
  statement already carries the name). The compaction of older in-scene statements was NOT built: Brandon's rule is about who is
  in the prompt, and the measured saving above came from removing duplicates, not from dropping knowledge.

Re-probe proposed (needs Brandon's go, about 440 neurons for 3A): candidate-only, same script, as `candidate-run3`, not pooled. Questions: the
proof echo; any change in the other deliveries (echo, rejected turns); Michelle introduced or not on the turns that do not name her
(any lead-in that does not know who she is); the exit rate; narrator prompt lengths against run2 (max 10,248). A one-replicate 1A smoke
is also worth running because Michelle is the story's driver there.

## Amendment 3: prompt size again, with no change to who the narrator knows about (2026-11-04, Brandon's directions)
Brandon, on the presence rule: "remember the goal of changing the prompt was to reduce the amount of characters used; if you can keep the
prior behavior and reduce the prompt size in a better way, then do that instead", then "my rules were about aggressively and dynamically
trimming the prompt down to items/NPCs/memories that are actually within the context window". The presence rule of Amendment 2 was
reverted (`cb44dc4c`), the safe cuts were built, and the rule came back in an amended form once Michelle's case was covered.

Measured first (3A deep state, 5,320 characters): fixed rules and speaker permissions were 3,217 (60%), the speaker lines alone 1,651 (31%),
Characters 986, scene text 1,080. THINGS placement lines were already scoped to the scene and hidden items (all nine entry prompts total
2,647 characters, only 202 of them for things apart from Kristin), so the item rule had little left to take.

- **Pick rules dropped on a turn with no candidates, placement lines that repeat the name dropped** (`99a48189`,
  `tests/test_prompt_inert_lines.py`): "When one or more offered candidates match ... randomly pick" and "Do not put a candidate's ID in
  grounding_ids" were followed by "This turn has no candidates", which cancels them (217 characters on every such turn). A turn that offers
  candidates reads exactly as before. One placement line read "splinters around the back door frame is around the back door frame."
  The moved pin: the quiet-turn assertion in `test_turn_prompt_matches_what_the_turn_actually_offers`, whose own docstring says a
  quiet turn must not invite a selection.
- **Each set of speakers named once** (`d823a662`, `tests/test_speaker_header_once.py`): a set with two or more statements gets one
  header "A, B and C may say these aloud:" and nested lines; a set with one statement keeps the one-line form. Two 1B/1C pins that looked
  for the one-line form now use `speaker_may_say`, which accepts both and still fails if an observation is offered to Brandon.
- **Characters: present, named, or brought up** (`3729577a`, `tests/test_prompt_presence.py`): a scene participant is introduced when
  present, when the command names them, or when the scene objective, a statement the player has earned, or a statement an NPC may say
  names them. Beat prose, the scene frame and the entry text do not count (they would bring back every participant a scene merely
  mentions). A character who is not a scene participant is still never introduced. Michelle is introduced in 1A by the objective; she
  drops out of 1C, 2B and 3A-start (no one names her) and comes back as soon as a command or statement does.

Entry prompts (old to now): 1A 3,333 to 3,044; 1B 3,009 to 2,790; 1C 2,732 to 2,254; 2A 3,260 to 3,041; 2B 2,925 to 2,447; 2C 3,071 to 2,852;
3A 2,890 to 2,517; 3B 2,674 to 2,118; 3C 2,547 to 2,035. Deep 3A state 5,320 to 4,430 (7,668 before Amendment 2). Quick suite 4147 passed, 31 skipped.

The Amendment 2 "not changed" note is superseded: a statement that names an absent participant now brings that character's biography in.
Still open: relevance-to-the-command trimming of earned statements was NOT built (every earned statement in 3A concerns people in the
scene, so an entity rule would remove almost none; it would need command or recency relevance and could cost narration quality).
The re-probe below now also checks the narrator on turns where a participant dropped out (1C, 2B, 3A start).

### Amendment 3 result (candidate-run3 and the 1A smoke, 2026-11-04, commit `ad5c9785`)
`bench/results/richer-3a-probe/candidate-run3` (440 neurons, 4 replicates, none failed, 0 rejected turns, every turn read; not pooled) and
`bench/results/richer-1a-probe/smoke-trim` (88 neurons, 1 replicate, 7 turns, 0 rejected, every turn read).

- **Prompt size, measured on the recorded prompts:** the largest user prompt per replicate fell from 7,721 / 7,498 / 5,946 / 5,946
  (run2) to 3,992 / 4,015 / 4,212 / 4,015 (run3), about 45% smaller at the tail. Entry turn 2,298 to 2,144.
- **Exit and handoffs:** scene left by the earned transition on command 9 in 4/4; the same eight reveals landed by handoff in every
  replicate as in run2. All eight deliveries were present and unrepeated in 4/4.
- **Proof echo cured: 0/4** (was 2/4 in run2). Every replicate says "Michelle answers without a pause and gets every detail right:
  Saturday, the circle, the lemon cake." once, with a lead-in that only has Kristin ask.
- **Participants that dropped out (Rebecca, Charles in 3A):** no turn missed them. Charles reaches the narrator only through
  delivery text (commands 6 and 9) and nothing misnamed him. Michelle is present in 3A, so the 1A risk was checked on the smoke instead.
- **1A smoke:** Michelle is introduced by the objective; the narrator never lost who she is (phone, tablet and bag, birthday calendar,
  memory card all landed, the neighbor beat delivered). Judge: 1 contradiction, 1 acts-beyond-command of 7 turns (not traced).
- **Open, found in this run (none caused by a known change; read before the PR):**
  1. *Re-spotting.* "She spots Michelle/Brandon" (as though newly seen) in 7 of 36 turns (baseline 0, first candidate 3, run2 2) and
     "looks around / stands in" openers in 15 of 36 (7, 7, 10). The continuity judge flagged scene restarts 3/36 (run2 0/36), each
     the narrator re-spotting a character already in the scene (replicate 1 command 9; replicate 4 commands 5 and 8). Could be this
     run's prompt cuts or noise at n=36; the cuts changed only the rules block, the speaker lines and Characters, so a one-change A/B is
     the way to tell.
  2. *Opening look-alike.* The opening narration invents "a woman with a scar above her left eyebrow" in all arms; in the candidate arms
     it then says "it's not Michelle" (run1 3/4, run2 2/4, run3 2/4; baseline 0/4) and the authored line "Michelle speaks into a stolen
     radio" follows. Present before today's cuts, so not from them.
  3. *Reader keypad.* The narrator invented "a keypad" on the checkpoint reader in 1/4 (run1 4/4, run2 0/4); minor invention.
  4. *Invented line.* Replicate 3 command 8: the official says "We need to wait for the signal from Dr. McGehee" before the authored line.

## Amendment 4 (2026-11-04): diagnose defect 1, re-spotting, before the PR
Brandon: "diagnose defect 1 first". Reading the recorded prompts first (free) changed the diagnosis. Amendment 3's line "none caused by a
known change" was wrong: between run2 and run3 **two** things changed, not one. (a) The proof delivery was trimmed (commit `089b1bc7`:
"…the day, the circle, the lemon cake. She says she is sorry she missed the birthday. The facility never saw that wall." became
"…Saturday, the circle, the lemon cake."), and (b) the prompt cuts of Amendment 3. Four of the seven "spots Michelle/Brandon" turns are
command 5 ("Ask Michelle about the lemon cake.") in run3, the proof turn, where run2 and the baseline wrote "Kristin calls out to Michelle…".
Run3's command-5 prompt is 2,488 characters against run2's 3,907; its lead-in is "Write only what leads up to it", and the narrator
wrote a stock look-around and "She spots Michelle" instead of the question. Michelle is already speaking into the radio in the opening.
Remaining three spots: command 4 once (baseline also opens "She spots a group of captives" here), commands 8 and 9 once each.

**Question.** Which change moved command 5's lead-in: the trimmed delivery (a) or the prompt cuts (b)?
**Arms, both 3A, first five commands of the probe script, 4 replicates, judges off, shipped transports, no retries, one opening each:**
- `diag-3a-pretrim`: today's code, story with the old proof delivery restored (`599288d8`'s `knowledge.yaml`). Isolates (a).
- `diag-3a-trim-oldcode`: code of `599288d8` (run2's), today's story (trimmed delivery). Isolates (b).
- Reference arms already run, not rerun: run2 (old code, old delivery) and run3 (today's code, trimmed delivery).
**Cost.** 6 requests x 4 replicates x 11 neurons = about 264 per arm, about 530 in all.
**Read.** Every command-5 narration and the openers of commands 1-5, by hand. Count command 5 leads that (i) have Kristin ask or speak to
Michelle, (ii) "spot" Michelle as if newly seen, (iii) a bare look-around. Decision rule, triage only: if `pretrim` returns to (i) in at
least 3 of 4 and `trim-oldcode` stays at (ii)/(iii), the trimmed delivery caused it, and the fix is at the source (give the proof turn a
lead-in worth writing without restoring the echo), not in the prompt rules. If the reverse, the cuts caused it and I find which.
If neither returns to (i), it is noise or both combined, and the one-change A/B continues on the cut that touches Characters or speakers.
Echo (the narrator's question repeating the delivery) is checked on the same turns.

### Amendment 4, part 2: result of the two isolating arms and the format test (2026-11-04)
`diag-pretrim` and `diag-trim-oldcode` (4 replicates each, 88 neurons each, nothing failed), command 5 read in every replicate:
- `diag-trim-oldcode` (run2's code, trimmed delivery): command 5 leads with Kristin calling out to Michelle in 4/4 ("Michelle, is that
  you?"), and the delivery lands once. So the trimmed delivery is **not** the cause.
- `diag-pretrim` (today's code, old delivery): 3/4 open with the stock look-around and "She spots Michelle across the way", 1/4 calls out.
  So the cause is today's code. The command-5 prompts differ only in Rebecca (dropped) and the speaker lines: one header with nested
  statements ("Dr. Michelle McGehee, Brandon Corfman and Imprisoned senior official may say these aloud:") against the old one line per
  speaker per statement. The grouping is the suspect; Rebecca is not in play on this turn.
Format test, 8 replicates per arm, today's code and story, a two-command script (`Enter the medical level.` `Ask Michelle about the
lemon cake.`), judges off, in a scratch worktree where only the speaker-line format is switched by an environment variable (not committed):
`nested` (today), `per_statement` (each statement once, all names before "may say this aloud", the format of `67dc6bb3`), and `per_name`
(the old one line per speaker per statement). Cost about 3.7 neurons a request, under 100 per arm. Read command 5 in each: calls out to
Michelle (i), "spots Michelle" (ii), bare look-around (iii). Decision rule: if `per_name` keeps (i) in at least 6 of 8 and `nested` does
not, grouping moves the lead-in. Then take the smallest format that keeps (i): `per_statement` first, since it saves most of the size.
The first format test was invalid and is discarded (kept under `invalid-fmt2cmd/`, about 570 neurons): the two-command script skipped the
earlier turns, so the prompt carried no "may say" lines and the three arms were the same prompt (identical lengths). Rerun with the first
five commands of the probe script and 6 replicates per arm; the speaker lines are checked in the prompts before anything is read.

### Amendment 4, part 3: result of the format test and the diagnosis of defect 1 (2026-11-04)
`bench/results/richer-3a-probe/fmt-{nested,per_statement,per_name}`, 6 replicates each, first five commands, 132 neurons each, none
failed, prompts checked (speaker lines present in all; format switch confirmed in the recorded prompts). Command 5, read in every replicate:

| format | command-5 prompt | calls out to Michelle | "spots Michelle" | bare look-around |
|---|---|---|---|---|
| nested header (today, `d823a662`) | 2,511-2,539 | 0/6 | 6/6 | 0 |
| one line per statement, all names before it (`67dc6bb3`) | 2,601-2,708 | 4/6 | 1/6 | 1/6 |
| one line per speaker per statement (run2's) | 3,102-3,673 | 6/6 | 0/6 | 0 |

Together with the isolating arms (`diag-trim-oldcode` 4/4 calls out, `diag-pretrim` 1/4), the old format gives 10/10 and the nested header
0/6 + 1/4 on the same turn. **Defect 1 is caused by my speaker-header change (`d823a662`), at least on command 5 (4 of the 7 spots);
the delivery trim and the removal of Rebecca are cleared.** Cause of the mechanism is not established; a plausible reading is that one
header with a list of nested statements reads as scene facts rather than as what Michelle may say, so the narrator stops letting her
speak first. The nested header saves about 100-170 characters over one-line-per-statement and 600-1,100 over the old format on this turn.
Not explained: the spots at commands 4 (1), 8 (1) and 9 (1) and the rise in "looks around" openers; these turns are checked again after
the fix. Not significant on its own: one-line-per-statement 4/6 against the old format's 10/10 (Fisher p about 0.14).
Mistake recorded: my first format test used a two-command script and was invalid (see above), costing about 570 neurons.

### Amendment 4, part 4: prototype of speaker trimming by who the command names (2026-11-04, preregistered before the run)
Brandon asked for another way to save characters, since the old format is large and the nested header causes the re-spotting. The old
format repeats the same three statements for Michelle, Brandon and the senior official (1,644 characters; the name prefixes are only about
400 of them; two of the three statements are also stated word for word in SCENE). **Prototype (scratch worktree, not committed):** if the
command names one or more speakers, list only their lines, in the old one-line-per-speaker form; if it names none, list every speaker's
statements once each with all names before it (the 4/6 format). **Arm** `fmt-targeted`: first six commands of the probe script, 6
replicates, judges off, about 160 neurons. Command 5 names Michelle; command 6 names the senior official.
**Read:** command 5 leads (calls out / spots / look-around), the speaker lines in the command 5 and 6 prompts (only the named speaker
listed), and command 6 for a speaker saying something unauthorized. **Decision rule (triage):** if command 5 calls out to Michelle in at
least 5 of 6 and command 5's prompt is within about 100 characters of nested's, build it through Ringer; if 4/6 or fewer, the old
per-speaker lines for Michelle are not what carries the behavior, and I report back.

### Amendment 4, part 5: result of the targeted-speaker prototype (2026-11-04) — failed the decision rule
`bench/results/richer-3a-probe/fmt-targeted`, 6 replicates, 6 commands, 132 neurons, none failed, 0 rejected. Command 5 (prompt 2,541-2,564,
only Michelle's three lines listed): calls out to Michelle 0/6, "spots Michelle" 4/6, bare look-around 2/6 (the decision rule needed 5/6).
**Michelle's own lines under her name are not what carries the old behavior.** The old format's 6/6 had six or nine lines (Michelle and
Brandon, sometimes the official too); one-line-per-statement had three lines and got 4/6; nested and this prototype had three lines and got
0/6. The behavior seems to track how many "may say aloud" lines the prompt carries, not whose they are. Also seen: on command 6 the
named-entity match listed Michelle and Brandon's lines instead of the official's in 3 of 6 replicates (the match missed "senior official"),
and in 1 of 6 the narrator invented a "Sector Commander". The prototype is dropped. Prototype code is not committed.

### Amendment 4, part 6: prototype of the old per-speaker format limited to present or named speakers (2026-11-04, preregistered)
Brandon: "Try the old format in 3 limiting the speaker lines." Prototype (scratch worktree, not committed): the old one line per speaker per
statement, but a speaker (never the protagonist) gets lines only if `_is_present` or the command names them, the same test the CHARACTERS
section already uses. Arm `fmt-presentonly`: first six commands, 6 replicates, judges off, about 132 neurons. **Read:** command 5 leads
(calls out / spots / look-around), the speakers listed in the command 5 and 6 prompts and their sizes (against the old format's
3,102-3,673 and nested's 2,539 on command 5), whether the official's lines appear when he is not present, and command 6 for invention.
Decision rule (triage): command 5 calls out in at least 5 of 6 and the command 5 prompt noticeably under the old format's; if so build
through Ringer.

### Amendment 4, part 7: result of the present-only prototype (2026-11-04)
`bench/results/richer-3a-probe/fmt-presentonly`, 6 replicates, 6 commands, 132 neurons, none failed, 0 rejected. **Behavior kept: command 5
calls out to Michelle 6/6.** **No size saved: the filter removed nothing.** The imprisoned senior official counts as present
(`_is_present` finds him in the scene's beat prose) in 5 of 6 replicates, so command 5's prompt is 3,673 characters, the same as the old
format; only replicate 2, where he was absent, was 3,102. Command 6 named the official correctly each time and no invented "Sector
Commander" appeared. Conclusion: limiting by presence cannot trim the 3A speaker lines, because everyone listed is in the scene.
The statements are the same three for every speaker, so size can only come from not repeating them or from fewer lines; the first
changes behavior in the tests so far. Untested: dropping from SCENE the beat statements that the speaker lines already carry verbatim
(about 300 characters on command 5).

### Amendment 4, part 8: SCENE-dedup prototype (2026-11-04, preregistered)
Brandon: "Scene-dedup test." Prototype (scratch worktree, not committed): the old one-line-per-speaker-per-statement format for every
listed speaker (the behavior-safe format), and any SCENE line that is word for word one of those speakers' sayable statements is
dropped from SCENE, since the speaker lines already carry it. Arm `fmt-scenededup`: first six commands, 6 replicates, judges off,
about 132 neurons. **Read:** command 5 leads (calls out / spots / look-around), the size of the command 5 prompt against the old format's
3,102-3,673 (expected about 300 less), whether anything the narrator needs is now missing (the scene frame or the objective reading
thin, the narrator treating the lines as optional), commands 4 and 6 for invention. Decision rule (triage): command 5 calls out in at least
5 of 6 and the prompt is about 300 characters smaller; then build through Ringer. Otherwise the old format stands as it is.

### Amendment 4, part 9: result of the SCENE-dedup prototype (2026-11-04) — not adopted
`bench/results/richer-3a-probe/fmt-scenededup`, 6 replicates, 6 commands, 132 neurons, none failed, 0 rejected. Command 5: calls out to
Michelle 5/6, the sixth a look-around that still speaks to her, no "spots Michelle" (the decision rule passed). Size as expected: 2,797
(six lines) and 3,368 (nine lines) against 3,102 and 3,673 in the old format, about 305 less. **But command 4 regressed: "She spots
Brandon standing nearby" in 5 of 6 replicates (the sixth "looks at Brandon"), against 1 of 6 in `fmt-presentonly`, which has the same
old format without the dedup** (Fisher p about 0.08). Removing the scene statements moved the re-spotting from Michelle on command 5 to
Brandon on command 4; the narrator seems to take SCENE statements as what has already happened. Not adopted.
Decision (Brandon, same day): build the old per-speaker format with speaker lines limited to speakers who are present or named by the
command, "even if it doesn't help in this case". Measured safe on command 5: 16 of 16 across the three old-format arms.

### Amendment 4, part 10: what was built (2026-11-04)
Commits `68972abb` (failing tests, `tests/test_speaker_lines.py`, replacing the nested-header tests) and `c339081a` (Ringer, one attempt,
44,033 tokens): `_speaker_constraint_lines(speakers, player_input)` writes one line per speaker per statement, "<name> may say this aloud:
<statement>", for speakers who are present or named by the command; the nested header and the grouping are gone. Quick suite 4145 passed,
32 skipped, ruff clean. The size saving of the nested header is given up (about 1,100 characters on command 5, speaker-heavy turns); the
other Amendment 3 cuts stay. Not yet re-probed: a full 3A run (about 440 neurons) to check commands 4, 8 and 9 and the openers.

## Amendment 5: defect 2, the opening look-alike (2026-11-04)
Cause read from the recorded opening prompt: SCENE and THINGS never say where Michelle is. SCENE says "Reach Michelle and join the
uprising" and "Reaching Michelle and supporting the uprising are immediate priorities", so the narrator searches and invents who it finds.
The plot sentence "Michelle is beside the captives." (3A.1) reaches the player only through the authored cue, after the narration. The
baseline and candidate prompts differ only in THINGS, so the extra THINGS lines are not the cause (baseline invented the scarred woman 4/4).
Probe (opening only, one request per sample, 12 per arm, every narration read; ~137 neurons; scratch scripts, not in the repo):
- A control (current candidate): invented woman 11/12 (scar 2, "determined look" 4, similar build 5 ...), "not Michelle" 8/12,
  "mouths 'not her'" 4/12, invented warnings from Brandon and a "countdown" on the reader 2/12. Michelle recognised correctly 1/12.
- B plot sentence added to the 3A scene frame unchanged ("... around the lower levels. Michelle is beside the captives."): Michelle
  found 12/12, look-alike 0/12, "not Michelle" 0/12, the cue not doubled word for word 0/12. New: Kristin reaches for a pistol or gun 3/12
  (no gun in the story), Michelle speaks an invented line ("Kristin, what took you so long?") 4/12, Michelle talks to a captive and then
  "speaks into a stolen radio" 3/12.
- C "immediate priorities" statement hidden from SCENE: "not Michelle" 1/12, but the invented familiar woman 12/12 (scar 4).
Read: B fixes the defect; C does not. B's costs are small invented details to watch in the full 3A re-probe (the pistol first).

### Amendment 5, part 2: full 3A re-probe on the rebuilt speaker lines plus the scene-frame sentence (2026-11-04, `candidate-run4`, 4 reps, 440 neurons projected)
Code at `7c7f1f6d`. Every turn read by hand; judge counts in brackets are run4 against run3.
- **Defect 2 fixed in the full run:** Michelle found in 4/4 openings, no look-alike, no "not Michelle" (run3 2/4, run2 2/4, first run 3/4),
  no scar. Invented opening line "Kristin, what took you so long?" 2/4. Gun or pistol in 1 of 40 turns (baseline 4 of 40), none in openings.
- **Command 5 re-spotting fixed:** 0/4 (run3 4/4) after the one-line-per-speaker rebuild. Replies on command 5 still add invented Michelle
  dialogue in reps 2 and 4 (the judge flags both as acting beyond the command).
- **Not fixed, predates today's changes:** on command 4 ("Enter the medical level") the narrator searches for Michelle and "spots" her 4/4 (first
  candidate 4/4, run2 4/4, baseline 2/4); judge restarts_scene on command 4 in reps 1 and 4. Command 8 spots Michelle 2/4, command 9 1/4
  (run3: 1/4 and 1/4). Keypad invented on the reader in 2 turns (run3 1, first run 4, baseline 1).
- **New cost of the sentence:** the opening now shows Kristin already reaching Michelle (eye contact, 2/4 a spoken line), and the command 1
  delivery ("Kristin finds Michelle alive...") then reunites them a second time, 4/4. The judge did not flag it (restarts_scene is on
  commands 4 and 9 only).
- Judge: acts_beyond_command 6/36 (run3 1, run2 3, baseline 4): 3 on command 9 (takes the radio and gives the signal, authored in the
  command 8 delivery), 2 on command 5, 1 on command 4. restarts_scene 3/36 (run3 3). contradicts_stated_fact 0/36.

### Amendment 5, part 3: does the 2A rewording fix the re-spotting? (2026-11-04, `bench/results/richer-3a-probe/c4-{C,R,X}`)
Hypothesis from the record (2A: SCENE said the phrase three times; rewording pressure, entry statement and objective took rejections from
7/12 to 0/12): SCENE tells the narrator to "Reach Michelle" three times after the reunion, so it keeps looking for her. Probe: two-command
script ("Free the captives." then "Enter the medical level."), 12 replicates per arm, judges off, every narration read.
Arms: C control; R pressure "Join the uprising", entry statement "Supporting the uprising is the immediate priority.", plot objective
"Join the uprising"; X entry statement hidden from SCENE only.
- **Re-spotting on command 2 is not caused by those lines.** "She spots Michelle beside the captives..." C 12/12, R 11/12, X 12/12. The
  narrator rewords the committed statement "Kristin reaches Michelle alive, ... directing prisoners through stolen radios and coded
  announcements" and the cue "Michelle shows Kristin the medical level". Second meeting ("rushes to Michelle", relief, "unhurried moment",
  eyes meet) C 7/12, R 8/12, X 4/12 (not a reliable difference).
- **R does improve the opening:** invented Michelle line ("Kristin, what took you so long?" or speech) C 9/12, R 0/12, X 1/12; pistol C 0, R 0,
  X 4/12; Brandon whispers a line that follows SCENE ("they're tightening security") R 4/12. Reunion delivered on command 1 in 12/12 of every arm.
- Brandon's standing ruling applies to commands 4, 8 and 9: Kristin stepping up to a character she is already near is ordinary staging, not a
  restart ([[approaching-a-nearby-character-is-not-a-restart]]); the run4 `restarts_scene` flags on those commands are that pattern.
Not adopted yet: R (needs Brandon's go). Not fixed: the opening-plus-command-1 double meeting (authored cue and delivery both place Michelle).

## Amendment 6: step B of the open-issues plan, confirm R on the opening (2026-11-04, written BEFORE the billed run)
Plan: `.plans/richer-3a-open-issues-plan.md` step B. Code at the commit that adds this text (step A is `7f2b6ff1`).
- **Question:** does R (pressure "Join the uprising", entry statement "Supporting the uprising is the immediate priority.", plot objective
  "Join the uprising") keep the opening free of the invented Michelle line, without losing the identity fix, in a fresh confirmation?
- **Arms (one candidate cause):** control = the story at `7f2b6ff1`, frozen in `bench/frozen/continuity-pre-3a-r/` (variation
  `richer-3a-b-control`, package/variation hash 53b5191274f3 0761a1cf8590); R = the current story with only the three R lines changed (variation
  `richer-3a-b-r`, hash 1cab61efc1b7 0761a1cf8590). Same code, same model/settings, same `thorough` entry state with `held_transfers_seen`, `badge_craft_noted`.
  The opening prompts differ only in the three R lines: `bench prompt` shows the pressure and entry-statement lines; the objective line ("Kristin Schweitzer's objective is to join the uprising.") appears in the provider-path prompt dump of the step B test (before/after dumps diffed offline); the CHARACTERS name set is the same. The probe records the exact prompt of every sample, and the orchestrator diffs them before reading any narration.
- **Probe:** opening only, 12 requests per arm, 24 narration requests (~88.8 neurons at 3.7/request; no matcher or judge calls), no retries,
  failures kept, no replacement samples, run once as a Ringer task (`scripts/ringer/3a-open-issues/stepB-probe-manifest.json`) writing
  `bench/results/richer-3a-probe/b-control.json` and `b-r.json` with the exact prompt of every sample. Request cap: 24.
- **Rubric (human, every narration read, control and R scored by the same rules):** (1) Michelle visible and identified, (2) look-alike or
  invented woman, (3) "not Michelle", (4) invented weapon, (5) Michelle speaks a reunion line (a harmless captive greeting is not this),
  (6) radio cue lost or doubled word for word. Eye contact is allowed. Record other invented details but they do not decide.
- **Win:** in R, 0/12 of (2)-(5) and no loss of (1) or of the radio cue. Miss: any of them. If it misses, keep the current wording and
  report the replication failure; do not adopt X. A win does NOT claim O1 or O2 solved (the c1 double reunion and the c4 re-spotting are
  separate steps C and D); 12 zero-failure samples bound a failure rate only to about 22% (one-sided 95%).
- Control rates are recorded for comparison but are not a pass criterion.
