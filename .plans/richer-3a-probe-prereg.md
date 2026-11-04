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
