# Scene 3A: close the open issues without undoing the fixes

Status: plan prepared, 2026-11-04, against `richer-narration-3a` at `10d505fc`.
The request names `39761567`; the latest full experiment remains run4 at
`7c7f1f6d`. These are different provenance points. No implementation, live
probe, test run, PR, or promotion was performed for this planning pass.

## Resume here

1. Repair the evidence boundary and freeze the scoring rubric (step A).
2. Take the already-tested R wording into a controlled confirmation, then test
   the reunion and completed-event wording separately (steps B–D).
3. Resolve the proof question on its actual merits, not just whether the
   narrator says “spots” (step E).
4. Attempt further size reduction only behind the same quality gates (step F).
5. Run the combined qualification and open the 3A PR with explicit known items
   (step G). Continue 3B and 3C afterward; do not implement them in this patch.

The deliverable is a plan for Claude Code/Ringer. Code and tests are tests-first
Ringer tasks. The candidate story wording below is supplied here; workers must
not invent replacements when a test or probe fails. Edit this plan in place as
results arrive. A failed arm remains a failed arm, not a reason to weaken its gate.

## Status log (edit as results arrive)

**2026-11-04, step A, deterministic part: done, uncommitted on `richer-narration-3a`.**
Ringer run `3a-open-issues-stepA` (manifest `scripts/ringer/3a-open-issues/stepA-manifest.json`,
generator `stepA.py`). All three tasks were reported FAIL by Ringer because of *my check bugs*,
not worker faults: (t1) `git diff --numstat` was empty since the worker staged its edits; (t2) the
`.venv` symlink makes `worldkeeper` import from the main checkout, so `PYTHONPATH` must include
`$PWD/packages/worldkeeper/src` or a worktree's model.py edit is silently ignored; (t3) `grep -rl`
put `tests/shard_durations.json` in the pytest args; and the export line's `':!.venv'` pathspec
errors on the ignored symlink. Generator fixed; corrected checks re-run by hand inside the kept
worktrees (all pass), patches reviewed and applied.

* 1A source: frame sentence is now `The deadbolt is still thrown.` (knowledge.yaml, one line);
  updated the pins in `tests/test_1a_back_door_gap.py`, `tests/test_1a_kitchen_start.py`, and
  `tests/fixtures/place_feed/baseline_prompts.json` (the same one sentence, two prompts); new
  consistency test in `tests/test_richer_1a_fixes.py` (outward-splinters clue still in `k_sl_1a_a_r1`).
* Stale captives text: **root cause confirmed**: `World.place` kept the old `wk_place_text` when the
  new placement had no text, so 3A's captives kept 1C's "moving through the processing line below".
  Fix is in `packages/worldkeeper/.../model.py` (a text-less place clears the old text). Tests: worldkeeper
  unit tests plus a real 1C→(2C)→3A→1C revisit test in `tests/test_world_placements.py`. No `world.yaml`/plot change.
* Judge provenance: bench turn records now carry ordered `authored_segments`
  (handoff delivery actually appended, cue, complication, bridge, variant-aware entry text);
  `judge_turns` uses them and tags `story_text_provenance` = recorded|reconstructed (legacy records
  are not rewritten). Calibration cases (a)–(f) added; (a), (b), (f) failed before the change.
  Two restart-rubric sentences added to `bench/continuity-judge.mjs`, marked unproven.
  Note for review: `bench/core.py` now also records a turn whose narration is empty but whose
  proposal has segments (`if narration or proposal.segments or ...`).
* Integrated gate: `quick_suite.py` rc 0, `ruff check`/`format --check` clean, node judge tests 11/11.
  The full suite has not been run (reserved for the final pre-merge gate).

**2026-11-05, D1-V prepared, uncommitted on `richer-narration-3a`; billed replay NOT yet run.** Ringer run `3a-open-issues-stepD1V` (manifest `scripts/ringer/3a-open-issues/stepD1V-manifest.json`): both tasks reported FAIL from my check bugs (the flags check outran Ringer's limit; the decode check read `records` where the report says `rows`); checks re-run by hand in the kept worktrees all pass, patches applied, `quick_suite.py` rc 0, ruff clean.
* Change: `voiceable: false` added to `k_sl_3a_a_r1` and `k_sl_3a_a_r2` only (tests compare every other field to the frozen D1 copy `bench/frozen/continuity-pre-3a-d1v/`; one D1 test that pinned the six speaker lines now asserts they are gone, with SCENE and system unchanged). Variations `richer-3a-d1-control` / `richer-3a-d1v`.
* Offline payloads (zero neurons): exactly six speaker lines removed; saves 896 characters from c2 onward. Totals control to candidate: c4 5,406 to 4,510; c5 5,837 to 4,941; c7 7,048 to 6,152; c8 7,208 to 6,312; c9 9,443 to 8,547. c7-c9 still exceed 6,500, so O8 stays open.
* Offline decode of D1's saved replies (`bench/frozen_decode.py`, reports in `bench/results/richer-3a-probe/d1/decode-*.json`): the real decoder recovers segments from the three malformed c4 replies (samples 4, 5, 6) and the validator accepts all 24 rows per arm; self-custody proposals appear in 11/24 D1 rows (9/12 at c4) versus 1/24 control and are stripped, not committed. This answers the O9 D1 caveat for the offline decode only; it does not clear the narration quality of those replies.
* Preregistration: Amendment 9 in `.plans/richer-3a-probe-prereg.md` (win: 0/12 on reunion, stranger, recitation, malformed, self-custody, plan-exchange; c4 medical 12/12; c5 cake 12/12). **Result (same day): D1-V MISSED.** 48 requests, no errors. c4 recitation fell 8/12 to 2/12 and degeneration 3/12 to 1/12, but the medical lead stays 3/12 (the narrator re-describes Michelle from SCENE in 8/12), and c5, clean under D1, regresses to 7/12 cake question, 6/12 plan exchange, 2/12 malformed and 4/12 self-custody. D1-V is rejected; C stays the accepted state; D1 stays experimental; O2 and O3 stay open; D2 does not start. Details and rubric table: Amendment 9 result. The twelve replays are close to one deterministic path per prompt (the D1 control reproduced Amendment 8), so the effective sample is small. **Next: Brandon's decision on how to diagnose the recorded replies (no narrator rule).**

**2026-11-05, step A leftovers, offline part done (committed with the tools; judge calls only, no narrator neurons).**
* **Exit audit** (`bench/exit_audit.py`, Ringer run `3a-open-issues-stepA2`; report `bench/results/richer-3a-probe/candidate-run4-rejudge/exit-audit.json`, untracked). The nine commands played through the real engine with authored deliveries only (scripted narrator, so live narrator `item_facts` are NOT exercised). After c9 the engine is in 3B and the authoritative world has Kristin, Michelle and Brandon in `security_corridors`; the captives stay in `detention_level`, matching plot.md ("the prisoners hold the lower levels"). So the run4 c9 **missed-change** flags for Kristin came from the narrator's scoped item map, which is taken before the transition, not from a missing move. **Radio custody:** the c8 delivery and plot.md:797 say "Michelle hands Kristin the stolen radio", but no authored effect records it: `stolen_radio` stays at `detention_level`, holder none, at every command. Only the narrator's own `item_facts` proposals ever give it to Kristin (3 of 4 run4 replicates did at c9, 1 did not). That is an authored-versus-world mismatch, not fixed here: a fix means a world/plot change (an authored radio hand-off effect) that this plan does not authorize and that 3B/3C's use of the radio may need. **Decision for Brandon.**
* **Rejudge of run4** (`bench/rejudge_frozen.py`, Ringer run `3a-open-issues-stepA3`, bench/results `.../candidate-run4-rejudge/`): the judges ran again, with the corrected judge input, against the package at run4's own revision `7c7f1f6d` (64 judge calls: 4 continuity, 60 fact). All 36 turns are `reconstructed` (run4 predates recorded segments). Originals untouched. Continuity: acts-beyond 6 to 4, restarts 3 to 3 (different turns), contradictions 0 to 2; 12 of 108 continuity answers changed. Fact judge: missed change 3 to 4, one turn changed (r1/c1). **Read:** the two new contradictions (r2 and r3, c9) quote the narrator writing "Kristin takes the stolen radio from Michelle ... gives the signal" one turn after c8 did it. That is the O4 repeated signal, now confirmed independently of the old input. The c4 restarts (r2, r3) quote "She spots Michelle beside the captives ..." and the judge calls it a re-discovery despite the new "seeing someone nearby is not a restart" sentence, which keeps the O2 reading unsettled. **Limit:** there is no same-input control rejudge, so judge noise cannot be separated from the provenance effect; with 12 answers moving both ways, do not compare aggregate judge scores across runs. Provenance for run4 stays reconstructed.
* Still owed in step A (billed narrator calls): the 1A frame replay (12+12) and, optionally, the c1 captives replay. D2, E, F, G untouched.

**Step A, still open (all spend model/judge calls; not started):** rejudge frozen artifacts with the
corrected judge input; 1A frame replay (12+12, 88.8 neurons); c1 captives replay (12+12, 88.8 neurons,
now expected to pass deterministically, so a live replay may be skippable); inspect the serialized
post-transition tree for the c9 missed-change flags. **Update 2026-11-05:** B and C passed their recorded gates; D1 met its narrow gate but is not accepted. D2–G remain unrun. Each new billed experiment still needs its preregistration written first (this file and `.plans/richer-3a-probe-prereg.md`).

## Evidence checked and corrections to the supplied account

Read AGENTS, PRD, contributor and agent workflow guides, scene-fixing and
narrator-writing guides, world-model grounding and its scene/character/placement/
prompt-input details, player-input guide, the testing runbook's local and prompt
inspection entries, the complete 3A preregistration including Amendments 1–5,
the richer-narration resume list and richness rules, and game-reimagination
section 6 and Rounds 6–7. Checked the current 3A plot, knowledge, handoffs and
world declarations and the actual projection/formatting functions.

Artifact review included every run4 opening and turn; all 36 opening-only
samples; all proof turns in the isolating and format arms; all first medical
turns of c4-C/R/X and R openings; the earlier baseline/candidate/run2/run3
medical, proof, reader and exit turns; run3's official invention; all seven 1A
smoke turns; summaries and pertinent judge verdicts. This is targeted diagnosis,
not a claim to have independently rescored every historical turn. The report
helper truncates openings to 900 and turns to 700 characters; raw JSON was used
for decisive passages, complete run4 prompts and state fields.

Important corrections, before choosing a cause:

* `baseline/all-turn-records.json`, command 4, does not spot Michelle 2/4.
  Replicate 1 spots captives and replicate 3 an unnamed figure. First candidate
  command 4 spots captives once and Brandon three times; run2 spots captives
  twice and Brandon twice. Thus “older scene-staging behavior” is supported;
  “the same Michelle defect 4/4 in every earlier run” is not. Run3 spots Michelle
  once here; run4 does so four times. Do not pool these as the same event.
* `c4-{C,R,X}/all-turn-records.json` contains **nine turns per replicate**:
  the two-command script repeats `Free the captives.` / `Enter the medical level.`
  and ends with another freeing command. The first medical turn remains a valid
  comparison; later repeats are not independent confirmations or a nine-command
  rescue journey. Any future “two-turn” experiment must assert its actual request
  count and stop after turn 2. Historical cost estimates must not assume three
  narration requests per replicate for those artifacts.
* Run2's proof echo is in replicates **2 and 4**, not 2 and 3. The raw narration
  repeats the apology and wall sentence there. Run4's proof payload no longer
  repeats those sentences, but it still does not reliably ask the typed question.
* The 1A smoke is traceable: command 1 repeats a conflicting scene-frame sentence;
  command 5's flagged pocketing is the exact authored handoff, not narrator action.
* `bench prompt --help` confirms that this is a **fresh-entry** prompt tool,
  not a way to reconstruct commands 4–9. Use saved prompts or a faithful offline
  prefix. `--player-input` is the supported action flag. Help was checked locally.

Paths below are relative to the repository. “run4 r2/c5” means replicate 2,
the fifth scripted command in `bench/results/richer-3a-probe/candidate-run4/`.
Judge results are descriptive observations, not truth labels.

## O1–O10: findings, severity, and available techniques

| Item | Established evidence and causal limit | Disposition and technique |
| --- | --- | --- |
| O1: two reunions | Run4 opening r1/r3 already exchanges speech; all four c1 deliveries begin “Kristin finds Michelle alive”. The opening cue is `handoffs.yaml:368`; the discovery-and-conversation delivery is `knowledge.yaml:2408`. Seeing Michelle and later speaking are compatible, but presenting discovery again is not. The static frame fixes missing identity; removing it would restore the look-alike risk. | Real authored repetition; block readiness until the opening and earned conversation have distinct jobs. Use the subtractive delivery fix from richer-narration “Scene 2B / Delivery repeat” and 3A Amendment 1. The exact 3A replacement in C now has the sampled support below. Keep the reunion fact earned by an action; do not assert it merely because the opening model writes eye contact. **Update:** Amendment 7 / `c-{control-unplanned,candidate}/all-turn-records.json`: authored rediscovery 12/12 versus 0/12, quiet moment and medical lead once in 12/12, no echo/rejection; opening conversation 0/12 in each arm. C passes on the A-r1 path; A-r2-first live behavior remains untested. |
| O2: later re-spotting | Run4 c4 prompt repeats both A-r1 and A-r2 reunion statements in SCENE and per-speaker lines. c4 R/X failed to remove the behavior. Nested format caused the c5 wording shift in Amendment 4; that experiment does not establish the cause at c4/c8/c9. In c4-R r1/c2 the narrator literally gives another “brief, unhurried moment”; that is stronger than looking at someone. | “Spots Michelle” or walking over to her is ordinary staging under Brandon's ruling unless the passage actually redoes a discovery, reunion, or journey. Accept the bare verb; score repeated emotional meetings separately. No proven cure for this specific later-turn defect. Test a compact established-state statement (D), not SCENE deletion or a rule banning a word. **Update:** D1 frozen c4: emotional reunion 11/12 control versus 0/12 D1; c5 0/12 both. This supports the statement-family intervention in this state, not a general cure. D1 replaces it with recitation and malformed replies; adoption remains blocked pending D1-V below. |
| O3: Michelle dialogue | Run4 r2/c5 has Kristin ask “What's happening here?” and r4/c5 asks about plans/other sites; the appended answer is Saturday/circle/lemon cake. Even r1/r3 do not clearly ask about the cake. Old per-name arms include the fabricated “cake we had at the circle”; their calls-out score did not measure answer fidelity. Opening speech is a different endpoint: c4 C 9/12 versus R 0/12. | Harmless NPC greetings alone are not a story-breaking defect or a protagonist physical action. The unrelated question/answer and invented shared memory undermine this reveal's job: block proof acceptance on that endpoint. R is supported for the opening only. Source subtraction and concrete plot material have precedents; the proof-specific candidate in E is new, unproven. **Update:** B passes for opening speech (4/12 control versus 0/12 R). D1 c5 asks about cake in 10/12 versus 11/12 control; its samples 1–2 still ask about plans and supply unrelated dialogue. Ten direct cake questions are an improvement over control’s added plan exchange, not closure of O3. E remains conditional after D1-V. |
| O4: signal repeated | Run4 r1–r3/c9 repeats the signal already delivered on c8. In r1/c9, SCENE contains both C-r1 and C-r2 signal statements and each of three speakers receives them again. No candidates are offered; this is not a second earned handoff. `_committed_for` and `_established_for` project entries whose effects are established, including alternate realizations, not only the selected realization. | Real replay of a completed action; block readiness. The source feed is established; whether shortening that feed cures generation is not. Use the short-statement technique of richer-narration “1B probe fixes”, with the one-time action kept in delivery. D tests C-r1 and C-r2 together because leaving either leaves the same causal input. |
| O5: keypad | Run4 r2/r3 c7 invent a keypad. Current statement/delivery contains none; the old explicit gaze contradiction is absent. `world.yaml:435` declares a fixed checkpoint reader, with reader/card-reader aliases. The current placement only locates it. | Accept cosmetic keypad detail as a known item while it supplies no new code, capability, required input, or contradiction. Do not spend a blocking arm to suppress harmless nouns. No established causal explanation for the residual. Declaring a keypad or adding a prohibition would enlarge scope and could recreate the old contradiction. |
| O6: official line | Run3 r3/c8: “We can't risk a premature uprising. We need to wait for the signal from Dr. McGehee.” It precedes the authorized signal. No such line is authored; absence in run4 is not a cure. | Conditional caution before a signal is not inherently contradictory. Accept this isolated line if it neither blocks the typed action nor delegates the signal away from Kristin. Keep it in qualification scoring; invented authority that changes the plot fails. No proven fix specific to this occurrence. |
| O7: 1A smoke | `richer-1a-probe/smoke-trim`, c1 prompt SCENE says “The lock is splintered out of the wood.” Narration copies it. Plot 1A.1 describes outward frame splinters and a thrown deadbolt. c5's pocketing quote is in the prompt's “game will add this” delivery. Michelle is present in CHARACTERS in both prompts. | No evidence these two flags were caused by character trimming. The first is source disagreement, not proof of model regression; second is provenance misclassification. Apply the exact source correction in A and repair judge attribution before comparisons. Preserve actual authored acquisition. |
| O8: size | System prompt is 2,527 characters in the compared rows. Per-speaker repetition, not transcript memory, drives the tail. `_speaker_constraint_lines` at cloudflare.py:1622 preserves per-name form and present-or-named filtering. `_character_lines` at 1586 keeps present/named/brought-up scene participants. | Real budget problem. Preserve those behaviors. First shorten repeated story statements, then test semantic `voiceable: false` only for observations (F). The latter has 1B/1C precedent but is unproven in 3A and may reproduce the loss of useful speaker-line density. A passing entry budget test cannot close the deep-turn problem. **Update:** D1 saves 356 characters at each frozen endpoint: c4 total 5,762→5,406; c5 6,193→5,837 (system 2,527 unchanged). No c7–c9 measurement or budget closure follows, and these savings are not yet accepted. |
| O9: aggregate judges/facts | Raw counts below. Run4 missed-change is r1–r3/c9; invented-change is r2/r3/c1 and r4/c8. c1/c8 prompts show captives “moving through the processing line below”, although their before-place is detention level. That exact text is the **1C** character placement at plot.md:304. r2/r3 c1 after-place becomes processing line. | Do not dismiss all flags as noise or fix to their aggregate count. The stale placement is a concrete additional source problem; trace its selection in A. Exit records mix transition prose with scoped fact snapshots, so c9 flags alone do not prove final-world travel failed. Verify authoritative post-transition facts and radio custody separately. Correct provenance and then rejudge frozen artifacts; do not silently overwrite the originals. **Update:** D1 c4 samples 4–6 fail strict JSON parsing (0/24 control); samples 4–5 repeat item-fact keys and sample 6 is incomplete. Several parseable replies also put a person in their own custody. These raw proposals establish neither committed bad facts nor successful engine recovery. Replay through decoding/validation offline before claiming either. |
| O10: R | Exact three-line change is recorded in Amendment 5 part 3; direct R opening review confirms 0/12 Michelle speech but continuing eye contact. Its c2 still repeats reunions and spots Michelle 11/12. | Recommend R for the opening, not as an O2 cure. R has now been retained on the branch after B; merge adoption remains separate. Precedent: game-reimagination Rounds 6–7 (2A source rewording). B supplied the isolated opening confirmation. **Update:** Amendment 6 / `b-control.json`, `b-r.json` meet B’s gate: Michelle and cue 12/12 R, no look-alike/negative identity/weapon/reunion line. R is retained on the branch, not awaiting its initial opening test. Brandon whispers in 5/12 R openings and 13/24 C openings; panel inventions remain G watch items. |

The relevant projection boundary is `knowledge.py:238` (`project`):
`scene_hidden_ids` comes from `_effect_item_ids`, which identifies established
claims with world effects. `_section_user_prompt` skips those IDs only in
SCENE; speaker projection is separate. Do not add fake world effects to hide
a troublesome sentence. Do not hide grounding knowledge or whole scenes to
solve prompt size. Section 6's cue lifecycle is a contract, not evidence that
arbitrary scene-statement retirement has already been implemented or proven.

### Measured prompt size

Maxima over recorded accepted turns, per scripted command. Run3/run4 have all
nine commands in every replicate, so positional alignment is valid here.

| Command | run3 user | run3 system + user | run4 user | run4 system + user |
| --- | ---: | ---: | ---: | ---: |
| 1 | 2144 | 4671 | 2177 | 4704 |
| 2 | 2666 | 5193 | 3712 | 6239 |
| 3 | 2649 | 5176 | 3472 | 5999 |
| 4 | 2452 | 4979 | 3275 | 5802 |
| 5 | 2539 | 5066 | 3706 | 6233 |
| 6 | 2669 | 5196 | 3836 | 6363 |
| 7 | 3085 | 5612 | 5124 | 7651 |
| 8 | 3175 | 5702 | 5268 | 7795 |
| 9 | 4212 | 6739 | 7535 | 10062 |

Run2's maximum was 10,248. Run4 retains only 186 characters of tail saving
against that maximum (about 1.8%), despite meaningful earlier safe cuts. The
5,000 normal / 6,500 worst-case targets are not met on run4's c7–c9. Those are
characters, not tokens or a billing measurement. For the first candidate, one
proof turn was rejected: align comparisons by typed command, not array offset.

### Raw judge counts, before calibration

| Run | Turns | contradiction | acts beyond | restart | missed change | invented change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 36 | 0 | 4 | 0 | 2 | 3 |
| candidate | 35 | 0 | 0 | 0 | 1 | 1 |
| run2 | 36 | 1 | 3 | 0 | 3 | 3 |
| run3 | 36 | 0 | 1 | 3 | 1 | 2 |
| run4 | 36 | 0 | 6 | 3 | 3 | 3 |

These come from each `summary.json`. They are not independent samples of 36
players: turns share state within four replicates. Do not call 6 versus 1 a
measured causal regression without matched arms and corrected labels.

## Experiment contract for every step

Preregister in this file and `.plans/richer-3a-probe-prereg.md` **before** billed
work: SHA/package hashes, exact prompt diff, model/settings, entry facts, script,
actual stopping limit, sample count, request ceiling, human rubric, win/miss
rule, and output path. Use one candidate cause per arm. Freeze the control at
the predecessor to that step, not at an old run with several other differences.
Keep every failure and retry; do not replace bad samples or pool different arms.

Use 12 samples per diagnostic arm. For saved-prompt diagnostics, each arm gets
the same 12 frozen states (three repeats of each run4 replicate when appropriate).
Preserve the original system prompt. Read every generated narration plus its
appended delivery/cue/bridge, not merely the model lead-up or `item_facts`.
For end-to-end confirmations use identical scripts and replicate counts across
arms. Check the actual prompts differ as intended before interpreting output:
`invalid-fmt2cmd` is the warning against comparing identical empty speaker feeds.

Costs below are **narration-only estimates** at 3.7 neurons/request, including
openings where stated. Matcher/recovery calls and external judges add cost;
log actual requests separately. Do not copy the bench's 11-neuron projection
into a 3.7-neuron estimate or treat cached/request counters as total cost.
Twelve zero-failure samples do not establish a universal fix: a one-sided 95%
upper bound is about 22% even for independent identically distributed samples;
repeated prompts and correlated paths weaken generalization further. Four
replicates are compatibility evidence, not an 80% population success guarantee.

## A. Establish trustworthy scoring and state inputs first

**Files and exact boundaries.** Tests first in `tests/test_judge_input.py`,
`bench/continuity-judge.test.mjs`, and `tests/test_world_placements.py`.
Inspect/fix `bench/judge_input.py:11` (`_story_text`) and `:281` (`judge_turns`)
before changing judge instructions. `_story_text` currently reconstructs the
base candidate delivery and a transition bridge; it does not enumerate every
cue, delivery variant, or destination entry. That is a verified incomplete
provenance boundary, not evidence that every run4 verdict is false.

Preserve actual ordered authored segments at composition/recording and carry
them into the judge input; derive no runtime truth by searching prose. Use
existing segment metadata where available. Legacy records must be reconstructed
with their own package revision and variants or marked unclassifiable. Do not
subtract today's delivery string from yesterday's narration. Retain a narrator
repeat even if it matches a separate story segment word for word. The existing
judge's distinction between story/game/narrator passages is the precedent.

Calibration fixtures must distinguish: (a) authored 1A pocketing, no protagonist
fault; (b) narrator repeating a prior-turn signal, a real repeat; (c) ordinary
approach/spotting, no restart; (d) a second emotional reunion after the completed
one; (e) a new incorrect shared memory; (f) authored arrival and final custody.
If rubric clarification is still needed, add only these plain sentences to
`bench/continuity-judge.mjs:50`'s existing restart explanation:

> Seeing or approaching someone who is already nearby is not a restart.
> Repeating a completed reunion as a new meeting is a restart.

This clarification is **new, unproven** until held-out calibration passes. Do
not alter the physical-action metric to count every line of NPC speech; use a
separate human question/answer fidelity column.

**1A source correction.** In `knowledge.yaml:377`, replace only
`The lock is splintered out of the wood.` with `The deadbolt is still thrown.`
The replacement is unchanged plot text (plot.md:143). Retain the outward
splinters clue in its earned delivery. Add a source-consistency assertion to
the existing 1A story tests; do not rewrite the card acquisition to appease a judge.

**Stale captives placement.** Reproduce the c1 prompt from a real 1C→2C→3A
prefix and a thorough bench seed. Assert that 1C's placement text is not reused
after the group is placed in 3A. Trace the placement-text selector through the
world adapter; change the selector that incorrectly chooses another scene's
text, not the valid 1C placement. Exact implementation location remains a
diagnostic gate: no speculative patch to `world.yaml` is authorized by this plan.
If the fix reads only world state, implement a World method and tests in
`packages/worldkeeper`; storygame only adapts it. If it selects authored scene
text, keep it in the existing adapter. Inspect the serialized post-transition
tree before diagnosing the c9 missed-change flags; a scoped before/after map
cannot establish final location or custody.

**Win/miss and cost.** Offline fixtures must classify every named case correctly
and preserve the real repeat. Zero neurons for reproduction/tests. Rejudge
frozen artifacts after calibration (zero narrator neurons, external judge cost
recorded separately); retain original verdicts. If source disagreement persists,
do not compare aggregate judge scores. For the 1A frame correction, replay c1
control versus corrected prompt, 12 each: 24 requests = 88.8 neurons; require
0/12 lock/frame contradictions and no clue loss. If a placement fix is needed,
use 12 c1 prompt samples per arm, another 88.8, requiring 0/12 false processing-line
moves. Confirm authoritative state deterministically as well as reading prose.

## B. Confirm R, preserving the opening identity fix

Exact proposed story edits (three lines only):

* `knowledge.yaml:399`, 3A `pressure: Join the uprising`.
* `knowledge.yaml:3619`, `k_scene_3a_entry` statement:
  `Supporting the uprising is the immediate priority.`
* `plot.md:707`, 3A `objective: Join the uprising`.

Keep `knowledge.yaml:398`'s `Michelle is beside the captives.` unchanged.
Keep `handoffs.yaml:368`'s opening cue unchanged. Do not auto-complete
`michelle_reached`, `uprising_prepared`, or `detention_uprising_started`.

Tests: `tests/test_richer_3a.py` pins the three fields and unchanged opening cue,
fact prerequisites, and reveal IDs. Capture opening and all nine entry prompts
offline to catch changes in brought-up characters.

Probe: current control versus R, 12 openings each, 24 requests = **88.8 neurons**.
Win: no look-alikes, false “not Michelle”, invented weapons, or Michelle reunion
speech in R; no loss of visible Michelle or the radio cue. Eye contact is allowed.
Do not claim O1 or O2 solved from this. If it misses, keep current wording and
report the replication failure; do not adopt X, which failed the identity test.

## C. Give the opening and earned reunion different jobs

The opening establishes that Michelle is there; the action earns the private
conversation and the next lead. Keep the current cue and its lifecycle. In
`knowledge.yaml:2408`, replace only the first sentence of A-r1's delivery:

> Kristin joins Michelle beside the captives.

Full resulting delivery, so the worker has no editorial discretion:

> Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. For one unhurried moment the two of them talk to each other and nobody asks anything of either. Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait.

A-r2 delivery stays unchanged: its alternative action earns a conversation about
other sites. Keep fallback `handoffs.yaml:365` for now; it represents the actual
earned reunion and is not the opening cue. Test that fallback and alternate A-r2
paths do not duplicate the quiet moment in a single composed turn.

Tests: extend `tests/test_richer_3a.py` to verify no fact earned by cue display,
A-r1/A-r2 still establish the same facts, the dose explanation survives, and
consumed discovery cues do not recur after save/load/revisit. Use existing cue
lifecycle tests in `tests/test_discovery_continuity.py` rather than new runtime
flags. The 2B delivery-repeat technique is proven; Amendment 7 now supports this wording on the sampled A-r1 path.

Probe: B winner as control versus the one-sentence change, 12 opening+c1 pairs
per arm, **48 requests = 177.6 neurons**. Win: 0/12 rediscoveries on c1, no opening
conversation followed by a second full reunion, one earned quiet moment and the
medical-level lead in 12/12, no echo or rejection. A mere later approach is fine.
If the opening still performs the entire reunion, this arm fails: investigate
cue/display-time lifecycle under section 6 rather than deleting the identity fix.

**Result:** C passed its Amendment 7 gate (`f9b1b86a`, `aacad859`, result `41a63079`). The control was run before preregistration and accepted as the disclosed unplanned control, not a prospectively registered run. Both arms used 12 opening+c1 pairs. The mechanical removal of the authored discovery accounts for the 12→0 difference; neither arm’s lead-up independently rediscovered Michelle. Preserve the successful sentence. The candidate’s senior-official gaze in replicates 1, 4 and 6 is an attention mismatch, not a second reunion. Do not infer later-turn or alternate-path success.

## D. Shorten completed events at their source, one event family at a time

Do not remove SCENE statements. Keep the per-speaker format and filtering.
Do not change `must_convey`, `requires`, `establishes`, action evidence, delivery,
or leak ownership in this step. These are proposed **short established summaries**,
following 1B's short-statements/long-deliveries technique. Their 3A behavioral
effect now has narrow D1 evidence below; they are not a demonstrated tense trick or an accepted combined fix.

**D1, reunion summary arm.** Replace these two `statement` values:

* `knowledge.yaml:2379`, A-r1:
  `Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.`
* `knowledge.yaml:2410`, A-r2:
  `Michelle has explained that freeing this block means little without exposing the other sites.`

Both alternate realizations can be projected from the same established facts;
changing only A-r1 leaves A-r2's replayable quiet moment in the prompt. The
delivery still supplies that quiet moment once when earned. Do not expand these
statements with experimental details or the private proof.

Probe: frozen c4 and c5 prompts, control versus D1, 12 per endpoint per arm:
**48 requests = 177.6 neurons**. Win: 0/12 repeated emotional reunions at each
endpoint; c4 still leads into the medical delivery; c5 does not regress to
reintroducing Michelle as unknown. Record bare spotting separately, not as failure.
Require shorter measured payloads at both endpoints. Tests in
`tests/test_richer_3a.py` and `tests/test_knowledge_projection.py` verify the
alternate-realization projection and preserved grounding/reveal behavior.

**D1 result and decision:** Amendment 8’s preregistered gate was met: c4 reunion 11/12→0/12; c5 reunion/unknown identity 0/12 in both; c4 medical movement 0/12→3/12; both prompts shrink 356 characters. This is a weak relative movement gate, not adequate action completion: nine D1 c4 replies never head to the medical level, and two of the three that do are malformed. D1 remains experimental on the branch; do not use it as an accepted control for downstream adoption.

Corrections from the raw artifacts (`d1/{control,d1}-rows.json`, sample numbers are one-based):

* “Shelly” is supplied in CHARACTERS as Kristin’s authorized nickname; the 11 control c4 uses are not inventions. The repeated reunion is the defect.
* D1 c4 recites summaries in dialogue in samples 1–3, 6–9 and 12 (8/12). Control c4 sample 9 narrates coordination, rather than reciting it as dialogue: under that same dialogue rubric the control is 0/12, not 1/12. Control c5 sample 9 voices the other-sites content (1/12); D1 c5 samples 1–2 do so (2/12). Do not conflate narrative reuse with spoken recitation.
* D1 c5 samples 1–2 contain an invented plan exchange despite missing speaker tags; “Michelle only reacts” applies to the other ten. The control has a plan exchange in 12/12, but 11 then ask about cake: only sample 4 ends on the unrelated question. D1 therefore reduces extraneous conversation while increasing missing cake questions from 1 to 2. Control sample 10 also pauses before the authored “without a pause”; score that composed contradiction in E.
* A-r2’s delivery was not selected, but its summary already appears as established SCENE content and explicit speech permission in both frozen arms; committed prefix facts include the shared reunion/resistance facts. This is alternate-realization content being voiced, not demonstrated leakage of protected knowledge. Whether the conversation actually occurred is a separate fidelity concern. Do not fix this by hiding facts or pretending `voiceable: false` removes SCENE content.
* Strict JSON parsing fails for D1 c4 samples 4, 5 and 6; there are no transport errors. A replay of the wire payload does not exercise final composition, validation or committed world state. The claim that these turns “would survive” is unverified. The shortened statements are the controlled intervention; speaker permission is a plausible recitation mechanism, not yet an isolated cause of either recitation or malformed JSON.

**D1-V, isolated permission follow-up (new, unproven in 3A).** Retain the exact two D1 summaries above for this experiment. In `data/stories/continuity-initiative/knowledge.yaml`, add exactly `voiceable: false` at both `k_sl_3a_a_r1` and `k_sl_3a_a_r2`; change no other field. This supersedes F’s A-r2 carve-out for the experimental arm only: both completed-event summaries can be recited, so suppressing only A-r1 leaves the observed A-r2 input. Their authored deliveries and earned actions remain intact. The existing observation mechanism has the 1B/1C precedent cited in F; its application to A-r2 is a new hypothesis, not a proven cure or a runtime permission redesign.

Before spending, use tests-first Ringer tasks to pin unchanged SCENE/grounding, prerequisites, facts, deliveries and per-speaker formatting; check both alternative earned paths, and run saved malformed replies through the actual decoder and validator offline, recording rejection/recovery and fact effects. Use the existing quick-suite gate. Capture all nine prefixes to measure total payloads without a billed call.

Preregister D1 versus D1-V: same scripted prefixes as Amendment 8, c4 and c5, one frozen state per endpoint, 12 samples per endpoint per arm, **48 requests = 177.6 neurons**, no retries/replacements, errors retained. Freeze hashes, model/settings, payload diffs and output paths in the next amendment before the run. Only the six A-r1/A-r2 speaker lines may disappear at these endpoints; SCENE and system must match. Read every reply and its composed delivery. Win requires 0/12 repeated reunions, stranger introductions, summary-recitation dialogue, malformed replies and invalid self-custody proposals at each endpoint; c4 must head into the medical level in 12/12; c5 must ask about cake/calendar in 12/12, without an unrelated plan exchange, invented memory, hesitation contradicting delivery, or echoed answer. Payloads must shrink. These strengthened prospective gates do not retroactively change D1’s recorded win. A miss rejects D1-V; preserve the last accepted C state as the fallback, keep O2/O3 open and return to prompt diagnosis, not another narrator rule. No general reliability claim follows from twelve repeated frozen prompts.

**D2, uprising summary arm.** Only after a reunion variant clears the strengthened gate, freeze that accepted state as control and replace:

* `knowledge.yaml:2609`, C-r1:
  `The prisoners have seized checkpoints. The fighting route toward the command and broadcast levels is open.`
* `knowledge.yaml:2642`, C-r2:
  `The uprising has begun. The emergency-gate authorization is about to expire.`

Keep both signal deliveries and `handoffs.yaml:382`–392 byte-identical.
The signal must still be performed when first earned, never precommitted by
summary text. Test C-r1, C-r2, their prerequisites, the typed-input tie-break,
the expiry event, and one earned 3A→3B bridge.

Probe: c8 and c9 saved prompts, control versus D2, 12 per endpoint per arm:
**48 requests = 177.6 neurons**. Win: c8 delivers the authorized signal exactly
once in 12/12; c9 repeats neither radio transfer nor signal in 12/12 and still
leads upward with its bridge. Payload must shrink; any loss of the authorized
c8 action fails. D2 is not permission to remove the uprising or its deadline.

## E. Make the proof turn ask the actual question

First read the accepted D1-V c5 results and inspect D2’s c5 payload offline; if D2 changes that payload, the paired E probe below must check the resulting state. Original D1 fails question fidelity in samples 1–2, so it cannot waive E. If the question and proof now agree in all samples,
do not add text. If they do not, the next candidate is a delivery that concretely
binds the answer to the asked topic, without adding another narrator rule.

In `knowledge.yaml:2764`, replace the proof `delivery_text` with exactly:

> Asked about the lemon cake on the kitchen calendar, Michelle answers without a pause: Saturday, circled, K, lemon cake.

This uses the plot's actual answer rather than suggesting a remembered meal
“at the circle”. **New, unproven:** the more explicit answer may restore echo,
so it must beat the trimmed control before adoption. Keep `voiceable: false`,
the calendar/medical prerequisites, and the two `must_convey` groups intact.
Do not put the proof's content in placements, global context, or earlier turns.

Tests: the existing proof gating and `must_convey` assertions in
`tests/test_richer_3a.py`, plus an unearned-calendar case and a completed
question/answer fixture. Probe frozen c5, 12 control and 12 candidate:
**24 requests = 88.8 neurons**. Win: every composed turn addresses the cake or
calendar, no wrong question immediately answered by the proof, no invented
shared meal, no double answer, no false hesitation, no premature proof leak.
Harmless greetings do not fail. If both arms fail, no proven technique closes
this item yet: return to recorded-prompt diagnosis. Do not silently restore a
known echo or claim the old calls-out endpoint proves this question is answered.

## F. Reduce size only while preserving behavior

First measure D's exact payloads offline at every prefix. Shortened statements
are multiplied by the existing speaker lines, so quality repair can also save
characters without regrouping permissions. Do not forecast a numeric saving
before capture. Keep the no-candidate rule cuts, repeated-name placement cut,
and present/named/brought-up character selection byte-identical.

If c7–c9 still exceed 6,500, test the existing story-level observation mechanism:
add `voiceable: false` only to `k_sl_3a_a_r1`, `k_sl_3a_b_r2`,
`k_sl_3a_c_r1`, and `k_sl_3a_c_r2` in `knowledge.yaml` at their ID blocks
(2378, 2472, 2608, 2641 at this HEAD; resolve by ID after earlier edits).
These narrate actions rather than words for an NPC to recite. D1-V now tests A-r1 and A-r2 together before D2; carry their flags forward only if that arm wins. F then tests only the remaining listed observation flags against that accepted control, without retesting or silently reverting A-r2. Keep D-r1’s official authorization sayable. Do not
change speaker formatting or hide any corresponding SCENE statement.

Precedent: richer-narration “1B probe fixes” and “1C closeout” made observations
not voiceable. **Unproven in 3A:** Amendment 4 shows that fewer permission lines
can change behavior regardless of whose name they use. Therefore this is a
separate arm, never a cleanup silently bundled with D.

Tests: extend `tests/test_speaker_lines.py` and `tests/test_richer_3a.py` to
distinguish observations from genuine speech. Preserve synthetic cases with
multiple statements and present/absent/named speakers. Preserve
`tests/test_prompt_presence.py`, `tests/test_prompt_inert_lines.py` and the
typed-handoff tests. Extend `tests/test_prompt_budget.py` with offline scripted
deep states rather than raising its cap or pinning accidental exact lengths.

Probe c4, c5, c6 and c9, 12 per endpoint per arm, **96 requests = 355.2 neurons**.
Win: all D/E gates survive, no invented official or missed alias at c6, no
unauthorized speaker, and deep payloads decrease. Declare size closed only if
all c1–c9 are <=6,500 and entry/normal test targets <=5,000 remain satisfied;
list normal-turn exceptions rather than disguising the worst-case cap as target.
If the arm fails quality, reject it even if it meets size. Keep the safer larger
prompt and report O8 explicitly as unresolved; a draft PR can document it, but
merge requires a measured safe alternative or Brandon's explicit budget exception.

## G. Combined qualification and the PR

After each accepted candidate, run tests-first Ringer checks using the existing
runbook. The implementation manifest must run:

```sh
TMPDIR=/tmp uv run python scripts/quick_suite.py
uv run ruff check .
uv run ruff format --check .
node --test bench/continuity-judge.test.mjs
```

Include relevant heavy files with `--also` as the runbook directs, especially
canonical journey/transport/package tests affected by story changes. Confirm
installed Ringer supports `check_timeout_for`, then use `check_timeout_s: 900`.
Regenerate package-derived expectations with existing generators only; inspect
the diff, not blind pin replacement. Whole quick suite on the integrated branch;
full suite once at the final pre-merge gate. No pytest run was needed to write
this document. Existing prompt-inspection/local-check entries cover this work;
no new testing procedure or dated runbook results entry is required.

Final diagnostic qualification: freeze the immediate pre-fix control and combined
candidate, both the original nine imperative commands and original thorough
entry facts, **12 replicates each**, including opening. This is
**240 narration requests = 888 neurons**, plus matchers/recoveries/judges.
Read every turn, including Brandon’s opening whispers, invented panel readouts/countdown, C’s official-directed gaze, D1-style off-command planning, malformed output and proposed self-custody. Cosmetic staging is a watch item; invented operational information that changes player choices, omitted commanded movement, or invalid committed custody fails. Record raw parse failures separately from engine recovery. In a separate compatibility rerun, candidate-run5 uses the
historical **four** replicates and same nine commands, **40 requests = 148
neurons**, compared descriptively with run4, never pooled with the 12-replicate
experiment. The two replicate counts serve different purposes and must not be
called a matched run4 comparison.

Before running, verify variation configuration really executes those nine
commands once. Commands, in order:

1. `Free the captives.`
2. `Read the wrist tags.`
3. `Listen to the stolen radio.`
4. `Enter the medical level.`
5. `Ask Michelle about the lemon cake.`
6. `Ask the senior official about the gate codes.`
7. `Check the checkpoint reader.`
8. `Tell the prisoners to start the uprising at the checkpoints.`
9. `Lead the prisoners upward toward the command levels.`

Require 12/12 earned deliveries on their intended commands; 12/12 earned exits;
zero rejected turns, wrong identities, contradictory shared memories, replayed
reunions/signals, functional inventions, or restored echoes. Each four-replicate
compatibility run must also pass its observed cases. Match the corrected judge
version in both arms, and include human classifications alongside verdicts.
Check radio custody and scene/party state with actual final snapshots. If c1's
captives still acquire the old processing-line placement, qualification fails.

Re-run the original seven-command 1A smoke on the final code, one replicate as
before (8 requests = **29.6 neurons**). This is a smoke, not causal evidence;
the 12-per-arm A diagnostic supplies the targeted comparison. Offline check
1C/2B/3A-start character feeds, plus synthetic absent/named speaker cases.

The maximum listed narration estimate if every optional arm is needed is
**2,486.4 neurons**, including both A diagnostics, B–F, the added D1-V comparison (177.6), final 12-per-arm full
qualification, four-replicate compatibility rerun, and 1A smoke. B, C and D1 account for 120 recorded narration requests, approximately **444 neurons**; the maximum remaining listed estimate is **2,042.4 neurons**, including optional A/E/F work. This excludes judge/matcher cost (C candidate recorded 12 reply-judge calls despite the intended judges-off setup). It is a planning
sum, not a spend authorization or guaranteed bill. Stop after failed gates;
do not pay for downstream confirmations of a rejected candidate.

### Interaction and regression checklist

| Earlier fix | Why it stays safe / what must fail the next candidate |
| --- | --- |
| c5 per-speaker restoration (`c339081a`) | Preserve one line per speaker per statement and present-or-named limit. D1 changed contents and introduced recitation/parse failures; D1-V/F change counts, so explicitly test c4 movement, c5 identity **and** actual question fidelity, raw parsing and validated facts. Never substitute nested headers because their smaller size looks attractive. |
| Opening identity sentence (`7c7f1f6d`) | Keep the exact plot sentence and visible radio cue through B–G; any look-alike or “not Michelle” fails. R does not authorize its deletion. |
| Reader keypad contradiction | Keep keypad absent from statement, conveyance and delivery. Cosmetic reader detail is allowed; Brandon's action must not contradict first-pass success or create a code requirement. |
| Tags/radio/proof echo reductions | Preserve scoped imagery in existing placements, not new global Details. Compare lead-up with appended delivery; E is rejected if its explicit answer restores echo. |
| Proof acceptance and official/uprising handoff | Keep proof groups/prerequisites and `typed_input` tie-break. Assert exact official handoff with the runtime-appended display names. Required path and optional proof must still land on their own commands. |
| Safe prompt cuts | Preserve no-candidate rule removal, inert placement removal, and character relevance. Do not revive transcript/history (none is currently supplied). Measure total payload, not only user text or a fresh entry. |
| Rejected format/SCENE experiments | No named-speaker-only targeting, nested header, or generic SCENE dedup. D1-V tests the two reunion observation flags before D2; F tests remaining observations against the accepted state with regression gates, not a retry of those rejected transformations under a new name. |
| Cue and scene handoff lifecycle | Keep discovery distinct from conversation, and first signal distinct from active uprising. Do not remove earned knowledge/facts to silence text. No stale discovery cue after completion; no source-scene action after the destination bridge. |

Order matters: A fixes measurement and stale input; B changes only opening
pressure (B passed); C removes authored rediscovery (C passed); D1 has narrow benefits but is not accepted. Isolate D1-V’s two reunion speech permissions before D2; only a quality-gated winner proceeds to uprising summaries. E repairs remaining proof mismatch; F then tests the remaining observation flags for size; G measures their combination. A short prompt that reintroduces the old defects is a loss.

### Shortest honest path to opening the PR

A draft PR may be opened once the proposed patch is concrete and deterministic
checks pass, with unrun live gates and unresolved O8 plainly listed. For a PR
presented as ready to merge, O1's authored rediscovery, O3's wrong proof question,
O4's repeated signal, the stale c1 captives placement if reproduced, and reliable
measurement of O7/O9 block. The normal merge/staging procedure still applies:
follow `docs/railway-production-promotion.md`, merge only on Brandon's word,
wait for SHA-bound main CI staging, then verify staged E2E. Planning opens no PR.

Accept as known items: ordinary O2 approach/spotting; O3 harmless greetings;
O5 cosmetic keypad; O6 isolated caution that changes no outcome; and residual
historical judge flags that are demonstrably provenance errors. Do not classify
a full second reunion as ordinary approach or dismiss genuine custody/topology
errors. O10 can be closed as tested-and-adopted or tested-and-rejected; it is not
a required runtime feature. O8 remains a disclosed blocker to a budget-compliant
merge unless solved safely or explicitly excepted; do not sacrifice quality to
mark it green. No new source cause is yet proven for every symptom, so “all ten
fixed” is not an honest current status.

Keep later-scene obligations in the existing richer-narration resume list:
3B/3C replace the facility radio loop (“when it stops, everyone will know”);
the watched outbound channel requires the office broadcast; Brandon's reader
ease pays off on the climb; the supervisor on Rebecca's purge list still needs
its payoff. None justifies adding more 3A prompt material now.

## What not to do

* No regex/keyword narration gate, “spots” ban, transcript memory, or mutable
  continuity store beside facts.
* No undoing the opening identity sentence, speaker presence limit, proof
  prerequisites, leak protection, or typed-input handoff tie-break.
* No generic SCENE dedup, named-speaker-only filter, nested speaker headers,
  or 3B situation-line rewrite presented as a proven remedy.
* No new narrator rule until source candidates have failed and its isolated
  probe wins; no silent prompt truncation to meet a budget.
* No declaring a keypad, gun, or new place just because a model mentioned it;
  no global placement reset that breaks custody on revisits.
* No treating a fresh-entry budget check, aggregate judge count, or zero in
  four/twelve samples as proof of complete continuity or general reliability.

**2026-11-05, artifact-checked status update (B–D1).** B edit/preregistration `216e526e`, result `92664699`: gate met in 24 openings; retain R on branch. C edit `f9b1b86a`, preregistration `aacad859`, result `41a63079`: gate met in 48 requests, with the unplanned control provenance disclosed. D1 edit/harness/preregistration `4fb5c2d0`, result `3255b379`: 48 frozen replays meet Amendment 8’s narrow gate but do not justify adoption. The raw-artifact corrections and stronger next gate are recorded in D. Existing deterministic test outcomes above are historical reports, not rerun or independently verified in this document update. No billed requests or implementation changes were made in this update.

**Next:** keep the two D1 statements experimental, preserve accepted B/C, and preregister D1-V before any new paid work. Do not proceed with D2 on unaccepted D1 or treat F’s former A-r2 exception as settled. D2, conditional E, remaining F and G remain owed, along with A’s unrejudged artifacts, 1A replay and final-state audit. A failed D1-V returns to C as the accepted baseline and leaves the reunion/proof defects open.
