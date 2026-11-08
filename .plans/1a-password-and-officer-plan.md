# Scene 1A: password reference and officer response

Status: **proposal for Brandon's review**, 2026-11-08. Investigation complete;
no story or engine changes applied, no billed probes run. Inspected HEAD:
`25f9b75efb7cb3dda30acafa47cb600442573a5a`. Existing untracked input artifacts
were preserved. Edit this plan in place on subsequent rounds.

## Status update (2026-11-08, same day)

Stage 0 of the probes is done and free: Ringer task `1a-password-officer-prepare` froze the 11 arm payloads and the
guarded replay (`scripts/ringer/1a-password-officer/`), and an independent validator confirms each arm differs from
its control by exactly the planned bytes. The preregistration is [1a-password-officer-prepare](1a-password-officer-prereg.md)
(`.plans/1a-password-officer-prereg.md`): now 117 requests after the re-freeze dropped the alias cell, about 430 neurons (ceiling about 530). **Nothing billed; awaiting
Brandon's approval of that spend.** Findings from the freeze: the Reyes and Walt bio lines do appear in the CHARACTERS
section for every officer and Walt endpoint, and the `officer` alias adds the officer's THINGS line to the raw vocative
request.

## Timing trace (2026-11-08, free; `.plans/1a-password-and-officer/trace_timing.py`)

Question: is the officer present or departed when the turn-7 narrator request is built? **Both, in different parts of
one request.** Evidence, canonical and raw scripts agree:

- Event timeline (`turns_since_entry` = turn number; scene entered at 0): patrol arrives outside at turn 4, enters the
  kitchen at 5, **leaves at 7**, returns at 9 (`pacing.yaml`; `home_search_narrows_1a` at 8). The officer is in the
  kitchen at the requests for turns 5 and 6 only. Player turns with him present: **two** (turns 6 and 7 are the
  greeting and the question; turn 7's own event removes him).
- `RuntimeEngine._turn_active` increments `turn_index`, then calls `capture.before_turn(command)`, and only afterwards
  `_activate_pacing(...)`, then the narrator provider. `before_turn` runs `prepare_turn` →
  `_referred_lines_for_command` → `_person_line` against the world **before** this turn's pacing events fire. Spy
  output at turn 7: `PERSON_LINE ... parent 'kitchen' place_text "at Michelle's workstation" turn_index 7`.
- The engine world at the request is already post-event (`officer_parent='patrol_staging'`, facts
  `patrol_departed`), so the SCENE/CHARACTERS material and the appended "The patrol pulls away from the curb." are
  post-event, but the **THINGS lines for command-referred people are pre-event**. The narrator is told the officer is
  at Michelle's workstation, answers as him, and the departure sentence is appended after. So the two stories I told
  earlier ("departed before narration" and "still present in the frozen payload") are both true; they describe
  different parts of one request. Neither alone explains the original wrong-person answer, which is still unreproduced
  (the stub replay cannot show it).
- Consequence for the plan: proposal 3's "align event order" is real but narrower than first written: the defect is a
  **phase mismatch inside one request** (referred lines before events, everything else after), not a missing departure.
  Candidate fixes to be probed: (a) run `_activate_pacing` before `capture.before_turn`, or (b) build the
  referred-person lines after pacing. Either changes when the delivery-visible world is read for every scene, so it
  needs the arrival/deadline/handoff trace listed above, tests first, and a before/after prompt comparison on the
  other scenes' recorded requests. Not applied.

## Scene 1A feels hurried (Brandon, 2026-11-08)

The numbers agree. Scene 1A has `min_turns: 9, nudge_after_turns: 10, handoff_after_turns: 13`, but the patrol clock
runs: arrives 4, enters 5, leaves 7, narrows search 8, returns 9. The player gets two turns with the officer and the
neighbor and kitchen details compete with a clock that has mostly finished by turn 9. The player in the transcript
spent the first three turns on the phone, which is exactly the "lot to investigate" he describes. The plain-words
options, to be chosen by Brandon, then probed one at a time:
1. **Slide the whole patrol clock later** (for example arrive 6, enter 7, leave 10, narrows 11, return 12, still
   inside the 13-turn ceiling). Cheapest; changes only `pacing.yaml`.
2. **Keep arrival where it is but let the officer stay longer** (leave 9) and keep return at 11 to 12, so the player
   has time for the neighbor outside before the patrol closes in.
3. **Trigger the patrol from player progress** (for example after the card is found) instead of the clock, with the
   clock as a backstop. A bigger engine/authoring change; not a proven technique here, so it is the last option.
Checks needed before choosing numbers (not done): the 1A storylets' `earliest/target/latest` windows, the
Walt/neighbor handoff eligibility, the card-challenge chain (`officer_presses_1a` at 5 requires `card_challenged`), and
the memory rule that optional storylet targets must not precede later gated ones. A scene-length change also touches
the 120-turn story budget in the plot. The corrected phase order above is independent of this and should be settled
first or alongside, since a later patrol arrival does not fix the stale referred lines.

## Ordering change and 1A clock: plan (Brandon said yes to both, 2026-11-08; nothing applied)

### A. Event order: make the whole request see one world (engine, Claude Code through Ringer, tests first)

Facts from the code, not yet changed:
- `_turn_active` runs `capture.before_turn` (reference match, referred-person lines, `_match_payload`) **before**
  `_activate_pacing(realize_complications=True, defer_guarded_events=True)`. `_referred_lines` is cached text from
  `prepare_turn` (item_facts.py:2027) and is inserted into THINGS unchanged (item_facts.py:570). `_referred_lines_for_command`
  is deterministic (no model call); the model-call part of `prepare_turn` is the match request.
- A trailing path already exists: after commit, `_finish_turn` calls `_activate_pacing(realize_complications=True)` again and
  appends a verbatim complication text after the story. `defer_guarded_events` already skips events guarded by an
  `equals: false` predicate in the pre-narration pass so they fire in that post-commit pass.
- The mismatch is not specific to the patrol: any pacing event or storylet effect that moves an entity (world.yaml
  `on_assert` moves) is read pre-event by the referred lines and post-event by everything else.

Two candidate orders, to be chosen with Brandon:
1. **Everything post-event** (rebuild `_referred_lines` after pacing). The narrator would be told the officer is gone
   while the player just addressed him, then "The patrol pulls away" is appended: a departure the narration cannot show.
   It also drops him from the referred lines (`together_or_unplaced` fails), so he gets no bio line.
2. **Everything pre-event for events that carry authored trailing text (recommended).** A per-event authored flag
   (working name `trailing: true`) makes the pre-narration pass skip the event, exactly like the existing guarded-event
   deferral; the post-commit pass fires it and appends its verbatim text. The player's question is answered by the officer
   who is still there, then the authored departure follows. Arrival events work the same way (the narrator no longer
   mentions the officer before "the front door opens"). Story-agnostic: the engine only reads the flag; the story decides
   which events trail. Start with `patrol_arrives_1a`, `patrol_enters_1a`, `patrol_leaves_1a` only.

Costs and risks to measure before and after, on recorded requests from every scene: events consumed by the same-turn
projection (storylet activation, cue staging, reveal eligibility, handoff candidates) shift by one turn for trailing
events; `officer_presses_1a` needs `patrol_in_house` and `card_challenged`, and moving `patrol_enters_1a` to trailing
delays the press by one turn unless its own flag is also trailing. Tests first (failing now):
(a) a trailing event's moves do not show in the same turn's THINGS/SCENE/CHARACTERS, and its text is appended once;
(b) the next turn sees the post-event world; (c) rejected or clarified turns leave the event unfired and uncounted;
(d) save/load and snapshot rollback mid-turn; (e) a non-trailing event behaves as today (golden check on every scene's
pacing events); (f) package loader accepts/rejects the flag and the authoring doc names it. Not a regex, no prose parsing.

### B. 1A clock (data edit, probed separately; Brandon chose option 1, slide the clock later)

Checked against `storylet-routes.yaml` and `pacing.yaml` (earliest/target/latest):
`SL-1A-C The Welfare Check Feels Like a Search 4/6/7` is the patrol-pressure storylet and would expire (latest 7) before a
patrol that arrives at 6. `SL-1A-I The Neighbor at the Fence 4/5/10` and `SL-1A-D 0/8/9` need no change. `SL-1A-G` waits on
`patrol_in_house = false`, which a later entry only widens. `pacing_event_review` also lists `pressure_1a` at 4.
Proposed first candidate (pacing.yaml `at_turn`): arrives 6, enters 7, `officer_presses_1a` stays gated on its facts,
leaves 10, `home_search_narrows_1a` 11, returns 12; scene ceilings (`min 9, nudge 10, handoff 13`) unchanged, so no change
to the 120-turn budget. Required companion edits: SL-1A-C window moved to about 6/8/9, `pressure_1a` reviewed,
and the tests that pin turns 4, 5, 7, 8, 9 (`tests/test_1a_patrol.py`, `test_1a_officer_press.py`, `test_scene_relative_pacing.py`,
`test_pacing_handoff.py`, `test_canon_journey.py`, `test_scene_progression_phase4.py`). The plot's 1A rhythm row ("evade a
widening patrol search") still describes it. Gap to confirm by play, not by assertion: after return at 12 the player has one
turn before the handoff at 13, tighter than today (4 turns). If that is too tight, shorten the stay instead (leave 9, narrows
10, return 11) as the fallback. Probe it as its own measured change (fast, canonical and slow scripts; an earned
transition in at least 80 percent of runs per the scene bar), not combined with the ordering change.

**Status (2026-11-08, after Brandon's yes): steps 1 and 2 done, uncommitted.** Ringer run `trailing-pacing-events`:
`tests/test_trailing_pacing_events.py` (11 tests; red first: 2 controls green, 9 feature tests red; one test tightened by
hand so it fails for the right reason) then `implement-trailing-events` PASS on attempt 1. Change: `PacingEvent.trailing`
(`models.py`, default false, not serialized when false), one condition in the pre-narration pass of
`RuntimeEngine._activate_pacing` (`engine.py`), one paragraph in `docs/markdown-story-authoring/pacing-and-incidents.md`.
Focused suites (new tests, 1A patrol/officer press, markdown package, relative pacing, handoff, canon journey, phase 4,
roleplay contract): 174 passed. No story data changed; no shipped event is trailing yet. Step 3 (free, temp copy with the
three patrol events trailing): at the turn-7 request the officer is still in the kitchen (`place 'at Michelle's workstation'`)
and the departure text is appended after the story; turn 8 sees `patrol_staging`; the arrival is likewise one request later
(turn 5 request: officer outside by the front door, entering text appended). Full-suite and other-scene golden
comparison are still to run at the end; the bench `_handoff_id` helper calls `_activate_pacing()` without the deferral,
so a trailing event would fire early in a bench prefix; only matters once an arm uses a trailing event.

**Status (2026-11-08, later): 1A clock retimed per Brandon, uncommitted.** Brandon's decisions: keep arrive 6, enter 7,
leave 10; narrow 11, return 13; 15-turn scene; raise the story cap to 122. `pacing.yaml`: arrive/enter/leave carry
`trailing: true`; `officer_presses_1a` at 7; narrows 11; returns 13; scene 1A window min 13, nudge 14, handoff 15
(the loader requires every event's `at_turn` <= `min_turns`, so the earliest exit from 1A is now turn 13). SL-1A-C window
6/8/9 (routes and storylets.md); `pacing_event_review` for the narrowing event 11; `plot.md`: 1A ceiling 15, cap 122;
journey test constants 122. Ringer runs `retime-1a-clock` (data and new `tests/test_1a_pacing_timeline.py`: FAIL on
the full suite, honestly, 46 tests pinned the old clock) then `fix-pinned-1a-tests` (PASS). Independent full-suite run
outside Ringer: **4257 passed, 32 skipped**. The shipped timeline now keeps the officer in the kitchen for the narrator
requests of turns 8, 9 and 10, answering before the departure text is appended on turn 10, so the turn-7 mixed-state
problem no longer arises in this scene. Handoff sum is 122 turns (122 x 45 s = 5,490 s of the 7,200 s budget). Open: a
live play-through at the new pacing (fast, canonical, slow scripts; earned transition in at least 80 percent of runs) has
not been run; 15 turns with a 13-turn floor is the thing to watch. The frozen probe arms were re-captured against this
clock with neutral filler turns (prereg updated). Result: the `officer` alias arm is byte-identical to the bio-only arm
when the officer is present, so the alias is not adopted on this evidence and its cell is not billed.

**New finding while re-freezing (2026-11-08): present characters are offered earned observations as speakable lines.**
After the player looked at the wall calendar and photograph, the officer's prompt contained
`Officer Reyes may say this aloud: Kristin reads the kitchen walls as a life interrupted: the calendar with Saturday
circled and the photograph of the two of them at a lake.` Source: `knowledge.py::_established_for` offers every established,
public, `voiceable` item to every present speaker (`cloudflare.py::_speaker_constraint_lines`); `k_sl_1a_g_r2` (Kristin's
own reading of the kitchen walls) is `voiceable` by default. This is a plausible route to an off-character answer from any
NPC in the kitchen, and it grows more likely now that the patrol stays longer. It did not occur in Brandon's recorded
session (he did not earn that knowledge), so it is **not** the explanation of the Jenkins reply; the probe arms were
re-captured with neutral filler turns so they match the original. Candidate repair, not applied or probed: mark Kristin-only
observation items such as `k_sl_1a_g_r1` and `k_sl_1a_g_r2` `voiceable: false`. Caution from the 3A lead-up probe: removing
speakable lines alone replaced stock speech with other unrelated chatter (2A), so it needs its own measured screen with
an ordinary-question safeguard before adoption.

**Billed source screens run (2026-11-08, Brandon approved 117 requests; all three stages done, 0 transport errors, 117 requests plus no
retries). Full results, scoring and caveats are at the end of `.plans/1a-password-officer-prereg.md`.**
- Officer greeting: control 8/12 targeted misses (wrong name "Officer Jenkins" 5/12, ally-like behavior 4/12); with the Reyes
  bio line 0/12. Reproduced, improvement met. The preregistered zero-malformed gate is not met (6/12 in the candidate, 8/12 in
  control): the real contract parser rejects those replies; separate defect, only at the greeting (0/24 at the question).
- Officer question: control 3/12 (+1 borderline), below the 4/12 reproduction bar; candidate 0/12 and 12/12 clean. Not a causal win.
- Walt: identity right everywhere; target not reproduced (0/12); the bio swaps "repeats the delivery's opening" (11/12 to 0/12)
  for "Walt voices his bio's traits early" (1/12 to 9/12). Not supported as a fix; source completeness only.
- Password: the laptop is never chosen (0/36); the remembered-device engine (proposal 4) has no reproduced miss to fix and is
  parked. Removing the laptop lines made the narrator never type (0/12 versus 4/12); the phone-context line made it type (12/12)
  but invented successful unlocks (6/12). The live issue is that `Type in the password.` is often not performed.
- The alias: not adopted (identical prompt once the officer is present).

**Voiceability probe run (2026-11-08, 52 requests, approved).** `voiceable: false` on `k_sl_1a_g_r2` is **not supported**: with the
speaker line offered, the officer voices Kristin's kitchen reading in 0/24 control rows, so there was nothing to fix; the candidate
also produced one chatter/role-confusion row (gate 0). Exploratory only: greeting rows with the line offered had no officer reply
in 6/12 versus 1/12 without it. Story data was not changed for this probe. See the end of `.plans/1a-password-officer-prereg.md`.

**Parser-rejected greeting replies: free investigation (2026-11-08; script `.plans/1a-password-and-officer/replay_provider_recovery.py`).**
- What the model does: the request uses `response_format: {"type": "json_object"}` (plain JSON mode, no schema). In 17 of 17 bad rows the
  glitch is the same: the first segment object ends `"text":"...","},{":"kind","narration":"..."}`, so the model fuses two segments into one
  object with junk keys. It appeared in 14/24 rows at the officer greeting (OFF6), 1/24 at the voice-probe question, and in 0/24 greetings of the
  voice probe, 0/24 officer questions and 0/72 Walt/password rows. It tracks the prompt, not the Reyes bio (CTRL 8/12, BIO 6/12). Cause inside the
  hosted model not established.
- What the live game does with it (`CloudflareTurnProvider._dispatch`): it does not use the bare contract parser. A fused object has no valid
  segment, so salvage (which only keeps valid segments) cannot help; the provider sends **one recovery request** (same prompt, plus "Your last answer was not
  valid..."). If that second reply parses, the turn goes on; if not, the player gets `NarrationProviderError(INVALID_PROPOSAL, 502)` and loses the turn.
  Replaying all 17 recorded bad replies through the real provider (stubbed transport): 16 of 17 used the recovery request (so about 58 percent of
  greeting turns at OFF6 cost a second model call: latency and neurons), 1 was salvaged by dropping a segment.
- Not measured: how often the recovery reply is also bad. That decides whether the player loses the turn (roughly 0 percent if recovery is reliable,
  up to the first-failure rate if it is not). Proposed bounded billed check, not run (needs approval): freeze the recovery payload for the OFF6 Reyes-bio
  request and replay it 12 times (12 requests, about 45 neurons at the old estimate) with the same scoring; also read each reply for the missing officer answer.
- Not changed: no engine or prompt change is proposed from the free evidence alone. Candidate directions to probe after the measurement: a one-line prompt
  rule about separate segment objects (narrator rules are last in the fix order), or tolerating this fused shape in salvage (a typed repair in the provider,
  not regex over prose); both need their own preregistered screens.

**Recovery request measured (2026-11-08, 12 requests approved):** the provider's recovery reply parsed in 12/12, so the live player does not lose the
turn on this path; but the officer answers the greeting in only 1/12 recovered replies (11/12: Kristin greets, the officer never speaks; 8 leave the quoted
greeting unterminated). So the visible symptom at the greeting is an unanswered greeting plus an extra model call about 58 percent of the time.
No fix applied. Candidates, each needing a preregistered screen: a narrator rule that every greeting or question to a present character gets that
character's own segment (rules are last in the fix order), or a typed repair of the fused-segment shape in the provider. Details in the prereg.

**Typed repair of fused segments built (2026-11-08, branch `fused-segment-repair`, uncommitted; Brandon chose option 1).**
`CloudflareTurnProvider._repair_fused_segments` runs on the FIRST reply only, before salvage: a segment object with valid `kind` and non-blank `text`,
a non-blank `narration` string, and otherwise only punctuation-only junk keys is split into two segments (the second is plain narration with no speaker or
grounding); anything else is left alone and takes the existing salvage/recovery path; the selected-knowledge guard mirrors salvage; one warning is logged with
key shapes only. No regex, no prose parsing, no extra model call. Tests first (`tests/test_fused_segment_repair.py`: 6 fail-closed controls green, 5
feature tests red, then green); two of my own frozen tests were flawed (an ineligible grounding id, an assumed key order) and were corrected with the other
nine verified byte-identical. Evidence, free: the 17 recorded bad replies through the real `ItemFactsProvider` with a stubbed transport: **without the repair 16
of 17 send a recovery request; with it 11 are accepted on the first reply** (the officer's line is restored, e.g. "I'm, uh, investigating a report of a
possible break-in, ma'am."), 5 still recover (3 where the officer's words are already inside the first segment, so there is nothing to split) and 1 is salvaged
by dropping a segment. Full suite 4272 passed plus the shard-manifest test fixed. Not measured: live effect on the unanswered-greeting rate, which needs the
real model; the repair only restores what the model already wrote, so the recovery path's "officer silent" behavior (1/12) is spared for those 11 of 17.
Process note: the first implementation attempt also altered `_segment_shape`'s key order to satisfy a flawed test; reverted.

Order of work if approved: (1) failing tests for A, (2) A through Ringer behind the flag, (3) free golden comparison on
recorded requests, (4) B data edit with its test updates, (5) then the billed source screens, with the officer stage first.
The billed spend in the preregistration (now 117 requests) is still **not approved**.

## Resume here

Review the source repairs and probe designs below before implementation.
The officer case has **both a missing character introduction and a timing
problem**. The officer is present before `turn()`, but has departed by the
time its narrator request is sent. The original replay's before/after prints
miss that distinction. The password case lacks a supported association
between a generated password prompt and its device. Last-mentioned-object
memory alone would fail Brandon's intervening-drawer example.

Next: approve the exact candidate source changes/experimental material and
the bounded probe batches. Claude Code then prepares frozen arms through
Ringer, tests first, and preregisters them before billed execution. This
request authorizes investigation and this plan, not applying its proposals.

## Evidence and limits

Read the PRD, contributor detail guides, scene-fixing, narrator-writing,
player-input and world-model grounding guides (all seven detail files), agent
workflow, testing runbook and its prompt-inspection/local-check entries.
Checked the requested story/package/runtime sources, the two lead-up plans,
`.plans/astra-fixes-plan.md`, `.plans/world-model.md`, and its historical
W1–W14 decisions and amendments at `5ea0119955c62b84699a8dc7878a4af770b55a7e`.
Code discovery used the existing codebase-memory index; Serena was not
available. No runtime symbols were edited.

Primary inputs are [the transcript](1a-password-and-officer/transcript.md),
[the replay](1a-password-and-officer/replay_1a.py) and its saved output, and
the scope/character diagnostic and its saved output in that directory.
These are reconstructed requests, **not captured original production HTTP
requests**. The replay stubs the model and omits world-capture integration;
it cannot measure live model behavior or prove the original hosted state.

Free verification run from the repository root:

```sh
TMPDIR=/tmp uv run python .plans/1a-password-and-officer/check_scope_and_characters.py
TMPDIR=/tmp uv run python .plans/1a-password-and-officer/replay_1a.py > /tmp/freytag-1a-replay-review.txt
cmp .plans/1a-password-and-officer/replay_1a-output.txt /tmp/freytag-1a-replay-review.txt
```

Both scripts succeeded; replay output was byte-identical to the supplied
output. No pytest suite was needed for this documentation-only diagnosis.
The existing prompt-inspection runbook covers this procedure.

The replay is not verbatim despite its description: several replies are
shortened, the opening is `Fixture.`, and command splitting changes turn 5
to `Turn off the phone. Put it in my pocket.`, so its substring stub returns
`Fixture.` there too. `last record text: None` comes from probing nonexistent
record attributes; it is not evidence that no turn was recorded. Preserve
these artifacts as historical evidence. Correct a separate probe harness
before making any recency or dialogue-quality claim from it.

### Miss 1: password selects the wrong device

Transcript: `unlock the phone` receives “a password prompt appears.” The next
input, `type in the password`, receives “the laptop screen flickers to life”
and an unrequested file search. Naming Michelle's phone on the next turn
produces phone narration. This is evidence of a contextual-reference miss,
not evidence that a password was known or successfully authenticated.

The reconstructed password request contains both:

> Michelle's phone is on the kitchen floor.
> Kristin's laptop is on the passenger seat of Kristin's truck.

It also contains the ownership examples for both devices, but **no preceding
phone/password narration**. No password property or phone-password binding
is declared in the inspected story package. The original password prompt is
generated detail. Device presence in a scene is not evidence of that binding.

`reference_resolution.py::_scene_things` builds heads from current display
names/scoped aliases; `_noun_matches` matches those heads. It does not infer
an object from its affordance or from earlier generated narration. The
diagnostic returns:

```text
type in the password -> passthrough () None
type in the laptop password -> resolved (('laptop', 'kristin_laptop'),) None
```

`RuntimeEngine.turn` only returns `ClarificationTurn` when the resolver has a
question. Here it has none. `recent_cue_referent_text` is not general
conversation memory: it considers the latest accepted reveal delivery or
eligible staged authored cue, requires a unique owner and content-word
overlap, and expires across an unrelated accepted turn or scene change.
The generated password prompt is neither kind of authored evidence.
`assemble_turn_prompt` projects current scene/knowledge material; it does
not forward the preceding conversation.

**Established mechanism:** no contextual device binding reaches either the
reference decision or narrator. The laptop is competing prompt material.
**Unproven causal claims:** that the laptop line specifically caused the
sample, that deleting it suffices, or that a generic recency instruction
would cure it. The continuation into files is a separate action-overreach
failure to score, even if device choice improves.

### Miss 2: the wrong person answers

The transcript explicitly addresses `officer, do you know where Dr. McGehee
is?`; “Michelle's neighbor, Mrs. Jenkins” answers. The authored neighbor is
Walt Pruitt, not Mrs. Jenkins. Scene 1A.4 says:

> Officer Reyes, young and polite, works from a printed list.

The world already declares `patrol_officer`, `walt_pruitt`, their aliases and
narrator biographies; scene participants include both. However,
`package.characters` contains only Kristin, Michelle, Brandon, Charles,
Rebecca and the senior official. `_parse_characters` reads headings under
Principal Characters and only then chooses `npc.narrator_bio`. Neither 1A
NPC has such a heading. `_character_lines` iterates `package.characters`,
so presence alone cannot introduce either of them. Every reconstructed
request lists only Kristin and Michelle. The requested existing bios never
reach those requests.

All requests already include:

> When the player talks to someone, that person answers.

No reconstructed user prompt names Jenkins, Reyes or Walt; the diagnostic
also finds no Jenkins in the assembled/system prompt. Charles and Rebecca's
surname elsewhere in the package does not establish that it caused this
answer. The supplied reply is a stub, not a new sample demonstrating failure.

**Timing correction.** Before turn 7, the replay says:

```text
officer parent='kitchen' ... together(kristin,officer)=True present(officer)=True
```

That is before `RuntimeEngine.turn`, not at the model request. I repeated the
network-free replay with `diag("AT REQUEST")` inserted immediately after
`captured.append(payload)` in `fake_urlopen` (guarded with
`if "world_for" in globals()` because opening runs before that import).
The source was transformed in memory; the supplied script was not changed.
At the final request the trace instead says:

```text
[AT REQUEST] officer parent='patrol_staging' ... together(kristin,officer)=False present(officer)=False
[AT REQUEST] patrol facts=[('patrol_departed', 'story', 'true'), ...]
```

`_turn_active` increments the turn and calls `_activate_pacing` before
`self.provider(command_text)`. `pacing.yaml::patrol_leaves_1a` fires at turn 7;
`world.yaml::patrol_departed.on_assert` moves Reyes to `patrol_staging`.
The verbatim sentence “The patrol pulls away from the curb.” is appended to
the generated response. Thus **the reconstruction does record departure
before narration generation, despite displaying departure afterward**.
The before-turn observation is true; the claim “asserted only after that
turn” is not. Final asserted-set listings include historical true/false
facts and should not be treated as a current-state query by themselves.

This answers Brandon's timing question affirmatively for the current
reconstructed path. It does not prove what state the original server had.
The missing biography is independently established. Bare `officer` also
lacks an exact ordinary alias: existing forms include `the officer`,
`patrol officer`, `federal patrol officer`, `Reyes`, and `Officer Reyes`.
`_entity_surface_forms` supplies authored forms verbatim, not a stripped
article. This matters when presence is false and `_character_lines` relies
on naming. A zero-resolution diagnostic alone does not prove every naming
path failed; explicit forms can be masked and passed through intentionally.

Neither absence nor a missed alias licenses someone else to answer. The
provided script puts the substituted speech in a narration segment with no
speaker ID, so its acceptance is not proof that structured dialogue checks
would allow a wrong `speaker_id`. A narration-attribution enforcement gap
remains to test with the real provider schema.

## Earlier fixes and decisions checked

| Precedent | Result and relevance |
| --- | --- |
| Scene 3A, `f7cbf7b3`, lead-up plan/prereg 1A and 1A2 | Same Principal Characters omission. Supplying the official bio changed hostile-jailer replies from 11/12 to 0/12; trimmed bio retained 0/12. A generation result, not full live qualification. This is the first repair to reuse for Reyes/Walt. |
| Scene 2C, `00052d39` | “When the player talks to someone, that person answers.” improved Brandon answering from 5/15 to 10/15. Already shipped here; not a guarantee and not a new proposed fix. |
| Scene 1A cue, `271541dc`; Stage 4 `8e1d40eb`, corrected scene check `dfcf21ae` | Authored “the gap” can refer back to its drawer owner on the next turn. This supports bounded owner evidence, but not generated password context surviving an intervening drawer turn. |
| Stage 4 `eac8db0b`, `7e899d85`; Stage 5 `351ffb1f` | Clarify real bare-noun ambiguity, retain unique typed commands, enrich evidence with unique names, exclude protected things. Reuse these contracts rather than replacing them with guess-and-rewrite. |
| W1, W4, W7, W8, W9 amendment, W10, W12, W14 | No prose-to-world regex repair; authored placement text; one-way story effects; participants are not presence; visible contents supplied without revealing hidden things; worldkeeper owns world logic; no fixed action tables; names must not disclose protected identity. |
| Scene guide's 3B missing entry, 3A talk-line/2C stance and stale-recall repairs; astra-fixes plan | Source-first method, not proof a new rule will win. Failed go-into-place, plain-corridor and copy-refers rules are not revived. |
| Lead-up prereg 1B, 2A, 3A reunion, S4 | Malformed gate failure, irrelevant replacement chatter, nonreproduction, and action suppression respectively prevented adoption. A target-only improvement is insufficient. |

The missing-character defect repeats a fixed class. General generated-context
reference with compatibility filtering is a new extension beyond the authored
cue implementation. The inspected precedents do not establish a successful
fix for the pacing/display-order mismatch; do not call it previously solved.

## Ranked proposals

### 1. Restore missing character material at its source

**Story-text proposal, ChatGPT Desktop authors; Brandon approves.** Add these
two blocks at the end of Principal Characters, before Expanded Scene Outline
in `plot.md`. Text is copied exactly from existing `world.yaml` narrator bios:

```diff
+### Officer Reyes
+
+A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.
+
+### Walt Pruitt
+
+A retired bus driver in his seventies whose wife is one of the missing. He is tired, careful with his words, and unsure what he saw.
+
```

Do not copy Walt's witness account or the patrol's covert purpose into a
permanent bio. Keep `knowledge.yaml`'s neighbor handoff/evidence and storylet
eligibility intact. Test the officer block first on the recorded turn-6
request (officer present); test Walt on an eligible outside-house talk turn.
Walt's block is source completeness, not a demonstrated cure for substituted
speech on an officer turn.

**Story-data edit, separate arm:** append `officer` to
`world.yaml::npcs[patrol_officer].aliases`. No runtime article-stripping rule.
This exact spoken address occurs in the transcript and authored prose.
Inspect disclosure/name collisions across all scenes before adoption. At
turn 7 this alias can make the officer *mentioned*; it must not assert that
he is physically present. Do not claim bio-plus-alias solves timing.

### 2. Probe competing material and the missing context before building memory

**Engine projection experiment, not a story edit:** on the frozen password
request, remove the laptop placement line and its mentions in the two
ownership-rule lines, leaving the phone versions intact. This is the exact
subtractive arm; do not delete the laptop from world state or scene data.
Compare with a second arm that adds only this experimental context line:

> Michelle's phone showed a password prompt.

This is an investigator-supplied representation of the preceding accepted
narration, **not an existing committed fact**. It is a prompt sufficiency
probe and cannot license shipping transcript recall. A combined arm can be
preregistered later only if the isolated results warrant it. A winning
subtraction would license action-relevant projection from resolved targets;
it would not solve omitted references by itself.

### 3. Align event order and preserve the addressed person

**Engine change, Claude Code through Ringer, conditional on probes.** Freeze
a second diagnostic state for turn 7 in which the action is evaluated with
the pre-departure world and the existing departure sentence/effects form
the trailing event. Compare it independently of the bio/alias changes, then
test the combined source repair plus ordering repair. Do not merely change
`at_turn: 7` to 8, make departed people permanently present, or hold off all
pacing whenever a player talks.

Proposed contract: a trailing authored event follows the player's action in
the candidate transaction. Validate the action against its phase's world,
apply the event to the candidate final state, validate the composed result,
and commit everything atomically before rendering. If an event is intended
to interrupt first, its display and action context must both reflect that
order. Trace other arrival, deadline, forced-handoff and departure events
before generalizing. Runtime orchestration belongs in `storygame`; moving
entities/checking co-location remains `World` methods.

Retain an explicitly resolved addressee separately from the question's
subject (Reyes versus Michelle). When he is already absent before the action,
report inability to address him locally or clarify an available communication
method; do not switch to Walt, Michelle, or an invented neighbor. First test
existing structured speech validation. If the real provider also permits
wrong attribution inside narration, propose a bounded typed speaker/target
check in the existing proposal-validation path, without parsing dialogue
with regex or adding an extra narration call. Freeze the schema and its
failure behavior before implementing this additional mechanism.

### 4. Compatibility-filtered recency, not a global last object

**Engine design proposal, Claude Code through Ringer.** Existing techniques
cannot cover the generated prompt plus intervening drawer example: authored
cue recall intentionally expires after one turn, and bare-head resolution
does not represent a password relation. Extend the shared proposal contract
only after the context probe establishes benefit.

1. Explicit targets win. `Type the password into my laptop.` must not be
   redirected to the phone because the phone was recent. Choosing a target
   does not grant a password, unlock a device, reveal files, or waive reach.
2. Build a bounded set of currently referenceable objects through `World`.
   Apply known kinds, properties, relations, visible state and protected-name
   rules before recency ranking. Scope and ability to act are distinct: a
   remembered device outside reach is not silently moved into the hand.
3. Interpret the player's descriptive reference with a typed, bounded model
   proposal grounded in these objects and permitted evidence, not a hardcoded
   `password -> phone` table, fuzzy alias widening, or noun-recency heuristic.
   Distinguish compatible, incompatible and unknown evidence. Unknown does
   not mean known incompatible; it cannot justify a confident selection.
4. Keep per-object reference evidence. Proposed initial bound: the last eight
   accepted turns in the current scene visit, with invalidation when the
   supporting state changes. Rank recency *within* the eligible compatible
   set. A drawer reference does not refresh or erase the phone/password
   association. Equally supported candidates, conflicting evidence or
   uncertain association use the existing clarification flow. Do not pick
   alphabetically or assume the physically nearest device is intended.
5. A presentation reference and a world property are different. Reuse
   declared axes or validated trait proposals for real characteristics;
   `embellishments.py` already adapts `TraitProposal` to
   `World.check_embellishments`/`apply_embellishments` under an authored
   policy. It does not currently supply a password-binding guarantee.
   Do not treat arbitrary accepted prose as new world truth. If generated
   context needs a new presentation association, propose it in the same
   structured response, bind it to a resolved entity and exact accepted
   evidence, validate scope/policy, then commit its bounded reference facts
   atomically. Missing or rejected association means clarification, not a
   guessed password target. No retrospective regex extraction of properties.
6. Facts remain the sole mutable authority. Persist any reference metadata
   as facts (entity, supported association, accepted-turn order, scene visit
   and evidence provenance); derive bounded views from them. Immutable
   delivery/narration records can supply provenance but are not an independent
   memory store. Rejected attempts, retries and clarification questions never
   refresh recency. Snapshot restore, save/load and scene exit preserve or
   invalidate it consistently.
7. Pure world queries, compatibility checks over structured properties and
   their tests belong in `packages/worldkeeper` as `World` methods. Language
   interpretation, story policy and prompt projection remain adapters in
   `storygame`. Do not send a transcript to the narrator. Project only the
   selected, supported object context. Keep authored reveal matching's
   existing eligibility rules; resolving a reference cannot earn a reveal.

The eight-turn bound is a proposed resource limit, not evidence of a natural
language rule. Test its boundary explicitly. A drawer with an authored
password-controlled lock would be compatible; rejecting every drawer by kind
would fail the story-agnostic requirement. In Brandon's example it is
excluded because it has no supporting password association, while the phone
has one. If neither has supported evidence, ask rather than invent it.

Before implementation, freeze the reference-proposal schema, permitted
association vocabulary/policy, validation guarantees and request-budget
integration. Prefer reusing existing interpretation/capture calls. If a new
pre-narration call proves necessary, explicitly budget and probe its latency;
do not silently exceed the current inference contract. This design is not
yet an implemented or measured semantic resolver.

## Probe matrix and preregistered win rules

Use Ringer, a corrected network-free capture harness and immutable prompt
files with hashes, model/settings/schema/package SHA recorded. Verify each
arm's byte diff. Keep all unrelated bytes identical. Interleave arms,
blind the reading order, keep the key separate, and read every composed
narration. Include appended delivery/event text exactly once. Score prose,
not `item_facts`; check state separately for integration. Preserve errors as
rows, with no rerunning until green. One unscored smoke per arm precedes each
12-sample-per-arm screen. Author approval precedes experimental prose use.

| Screen | Arms and endpoint | Narration measure |
| --- | --- | --- |
| Officer source | Control / Reyes bio only at recorded turn 6; repeat at turn 7; 12 per arm per endpoint (48 counted calls) | Reyes responds to the address; no substituted person, unsupported whereabouts, or contradiction with the appended event. Turn 7 is separately flagged for its timing problem. |
| Bare address | Bio-only / bio plus `officer` alias, actual captured turn-7 payloads (24) | Alias resolves the addressee and improves relevant handling without making an absent NPC physically present. A bio-only change may produce no prompt difference at turn 7; retain that diagnostic result. |
| Walt source | Control / Walt bio at the same eligible outside-house `Ask the neighbor what he saw.` state (24) | Correct witness identity, coherent handoff, no early disclosure. Also inspect unaddressed kitchen prompts offline. |
| Password source | Recorded control / laptop-subtraction / phone-context addition at `Type in the password.` (36) | Phone is the target or genuine ambiguity is clarified; no laptop/drawer substitution, unsolicited file search or invented successful authentication. Record correct target separately from action success. |
| Officer timing | Original / pre-departure action phase / source repair plus pre-departure phase, frozen turn 7 (36) | Intended officer handles the question before coherent departure; no invented Michelle location. Compare source-only results above to separate causes. |
| Recency integration, after design approval | Current engine / proposed compatible-referent engine, 12 per arm per case below | Exact target/clarification expectation, no unauthorized state or reveal; do not pool cases. |

Default causal win, fixed before calls: control has at least 4/12 targeted
misses; candidate has at most 1/12 and at least three fewer. Otherwise report
not reproduced or inconclusive. Candidate must perform the relevant action
or correct clarification in at least 11/12; silence is a miss. Require zero
wrong-speaker substitutions, hidden knowledge leaks, invented password
knowledge/authentication, contradictions, malformed/empty outputs and
transport failures. No safeguard may worsen relative to control. A source
completeness repair can be approved separately on authoring grounds if a
model miss does not reproduce, but cannot be called a causal win.

Recency cases (canonical commands except the explicitly labeled transcript
replay) each get 12 per arm, 24 calls:

- Phone shows password prompt → `Type in the password.`: phone.
- Same phone context → `Inspect the drawer.` → `Type in the password.`:
  phone, despite the newer incompatible object.
- Phone and another device have supported password prompts with indistinct
  salience: clarification names only eligible devices, never the drawer.
- Both have supported prompts, one is clearly the newer referent: choose that
  device; reverse the order and require the opposite choice.
- Phone recent → `Type the password into my laptop.`: explicit laptop target,
  no phone substitution and no assumed password knowledge.
- No password association recorded: clarify the device; never fabricate an
  association or silently choose a laptop.
- Authored password-controlled drawer in a synthetic second genre: allow it
  to compete. This catches a phone-only table or blanket drawer exclusion.
- Supporting association expired, contradicted, hidden or outside permitted
  reference scope: no stale selection or disclosure; clarify safely.

These are eight cells (192 counted narration requests), with the swapped
recency order balanced six/six within its cell and all deterministic cases
tested independently. Freeze fixture characteristics/placements and expected
answers before running; synthetic package prose follows the grounding guide.
For ambiguous/no-evidence cells require 12/12 correct clarification decisions
in deterministic checks, and at least 11/12 in the live interpretation screen.
Keep the original lowercase/vocative transcript as a deliberately raw-language
regression alongside canonical `Greet the officer.` and
`Ask the officer where Dr. McGehee is.`; never silently rewrite the recorded
inputs and claim reproduction. Qualify raw forms separately, 12 per arm.

The counted screens above are staged alternatives, not authorization to run
all calls. Freeze per-stage request caps including prefix/capture/recovery
calls and pricing from the configured endpoint before approval; do not
pretend counted narration rows equal total provider requests. No billed
judge is necessary for these hand-read screens.

## Implementation and qualification gates after approval

Write failing tests first through Ringer. Cover package character headings,
exact aliases, present/named/absent prompts, and protected bio content. For
timing, assert state at the provider boundary as well as before/after the
turn; test arrival, departure, rejection rollback, deadline behavior and
save/load. For references, cover every case above, explicit targets, failed
proposals, clarification without clock advancement, per-object aging, scene
re-entry, snapshot rollback and a second genre. Preserve one-turn authored
cue behavior unless explicitly changed and separately probed.

Use the existing runbook's focused suites for package loading, reference
protection, narration safety, pacing and persistence, then the Ringer quick
tier plus relevant heavy files and Ruff. Before merge run the required full
suite/coverage checks. A live prompt win licenses implementation, not a
claim about persisted state. Rerun the same accepted scene script with three
live replicates and read narration plus committed state, then staged E2E
after SHA-bound main CI deployment. Follow the production promotion guide
for any later promotion; none is part of this planning task.

Unresolved: original hosted request/state, actual password knowledge, live
causal attribution of Mrs. Jenkins, frequency of either miss, the schema
needed for generated reference evidence, and whether capture/prompt changes
fit current latency/budget. Do not close these based on stub replay success.
