# Preregistration: the richer scene 1A, opening and first turns

Written 2026-11-02 before any billed probe run, on branch `richer-narration-1`. Brandon asked for this probe
("run opening probe first") after the richer 1A was applied (`f8999d3a`, renamed `519a6c60`, windows `790545a3`).
Method: scene-fixing guide (replay the shipped prompts, read every reply), preregistered caps, smoke first.

**Disclosure.** Before this document, `python -m bench run` was invoked twice (one replicate per arm, no
`--confirm`, because the CLI only asks above its neuron threshold). The bench loads `.env` itself, so both runs
reached the live narrator and matcher for the opening and the first four turns, then crashed on the fifth command
(a walk between places) before writing any artifact. An offline replay with the network blocked makes 9 requests
before the same crash, so the real spend was roughly 9 to 15 requests per run, about 20 to 30 in all, plus any
capture asks. It is unrecorded and is not counted below. Cause: bench bug fixed under tests/test_bench_traversal.py.

## Questions
- **Q1 Does the richer story give the narrator real material?** For the same six commands, how many plain things
  does the matcher resolve as new (invented) with the old story versus the new one?
- **Q2 Do the new situations deliver when earned?** Wall calendar and photograph (kitchen things), the back door
  (outward splinters), the neighbor (Walt's account) appear in the narration when the command reaches them.
- **Q3 No regression.** The core 1A path still works: the card is found when the drawer is searched, no protected
  term appears, no clarification loop, the walk outside works.
- **Q4 Opening baseline.** What does the shipped opening write for the new kitchen start?

## Design (shipped transports, runtime-wired capture, no retries, no replacement samples, partial rows kept)
Arms: `richer-1a-baseline` (frozen story from `6eebe4e8`, in `bench/frozen/continuity-pre-richer-1a/`) and
`richer-1a-candidate` (current `data/stories/continuity-initiative`). Identical settings. Script `richer-1a-kitchen`,
seven canonical imperative commands in order: `Examine the back door.` `Look at the wall calendar.`
`Look at the photograph.` `Search the drawer.` `Search beneath the drawer.` `Go outside.` `Talk to the neighbor.` Each replicate also makes one
opening request. Judges on: continuity and fact-tracking (7-criterion and invented-change are recorded, never pooled).

**Smoke first:** 1 replicate, candidate arm only (about 12 narrator and matcher requests plus judges). Read it fully;
stop if the run fails, a reply is unusable, or any quota error appears. **Full run:** 4 replicates per arm, one Ringer
task per arm, run in sequence. Request cap: 150 narrator and matcher requests in total, judge calls separate and
reported separately. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.

## Scoring (every turn read by hand; report per replicate, never pooled)
- **Q1:** per arm and command, plain things resolved new (from each turn's `item_facts_resolutions`, kind thing).
  Harmless invented scenery counts for information only (Brandon: "okay with invented things as long as they don't
  affect the main storyline"); list any that touch the storyline.
- **Q2 (candidate):** per command, whether the authored detail appears: back door (splinters point outward, from
  inside), calendar (lemon cake, Saturday), photograph (lake), neighbor (vans, clipboard, skipped the house).
- **Q3:** card recovered after `Search beneath the drawer.` in at least 3 of 4 replicates per arm; zero protected terms
  (JANUS, selection system, Brandon's history, detention network); zero clarification questions; the walk records
  cleanly; 7-criterion scores recorded as given.
- **Q4:** each opening yes/no: names the kitchen; uses only declared things for layout; reacts to Michelle's absence;
  KMS treated as new and strange; hidden card not revealed and no search done for the player; no story-breaking
  invention.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves fewer plain things as new than the baseline on commands 2, 3 and 6,
  and Q2 holds for at least 3 of 4 replicates on each of the four details.
- A Q3 failure in the candidate is a defect to fix before scene 1B, whatever Q1 and Q2 show.
- Prompt size: record each turn's narrator and matcher prompt lengths against `tests/test_prompt_budget.py`.
- With four replicates per arm, a one- or two-point gap is not reported as real (bench README).

## Not covered
Later turns after the patrol, other scenes, the hosted staging path, other models, and tuning wording.

## Amendment 1 (2026-11-02, after the smoke run, before any full run)
Smoke result: one candidate replicate, 6 turns judged, no failures (7-criterion 4 of 7; fact tracking clean; spend 77
projected neurons, 22 estimated from requests, 2 OpenAI and 10 Jev judge requests). Reading every turn found
four defects in the story and one error in this preregistration:
1. `Search the drawer.` earns the gap pointer, not the card (existing two-step design). The card criterion now
   follows `Search beneath the drawer.`, a seventh command inserted after it; `fixed_turns` is 7.
2. The photograph was narrated as a landscape: the lake photograph's text never said what it shows.
3. The kitchen storylet delivered all five details on a calendar command: split into a workstation reveal and a walls reveal.
4. Walt's account was unreachable once the patrol entered (`patrol_in_house` stays true): the patrol gate is dropped.
The full run uses the story after these fixes. The smoke row is kept and reported as pre-fix, not pooled.

## Result (2026-11-02; code `1bb68d81`; 4 replicates per arm, 7 commands, every turn read by hand)
Run by Brandon with the two bench commands. Rows: `bench/results/richer-1a-probe/{baseline,candidate}/` (gitignored). Both arms
completed 4 of 4 replicates, 28 turns judged each, no failures, no quota stop. Spend per arm: 352 neurons projected, 88
estimated from requests, 8 OpenAI judge calls, 49 (baseline) and 51 (candidate) Jev judge requests. The earlier smoke row is
pre-fix and not pooled.

**Q1 invented material (baseline versus candidate).**
- Calendar: baseline invented appointments in 4 of 4 (specific notes in 3 of 4: "Meet J at 2pm on the 10th" twice, a
  meeting with "Dr. Patel"); the matcher resolved "calendar" as a new thing in 4 of 4. Candidate: 0 of 4 new. It still
  misdescribed the object in 3 of 4 ("a simple white board with scribbled notes and photographs") and once "old, with a worn cover".
- Photograph: baseline invented its content in 4 of 4 (beach 2019; mountain landscape; "Michelle and I at the lab, 2018" twice);
  matcher new 4 of 4. Candidate: 4 of 4 correct (Kristin and Michelle at the lake); harmless extras ("holding up a fish").
- Neighbor: both arms invented one in 4 of 4. Baseline: "Mrs. Jenkins" once (collides with the villains' surname), otherwise
  an unnamed man or woman. Candidate: "a man in his mid-40s with a scruffy beard" in 4 of 4, not Walt.

**Q2 authored details delivered when earned (candidate).** Back door, outward splinters: 4 of 4. Calendar and photograph
(lemon cake, lake): 4 of 4. **Neighbor, Walt's account: 0 of 4.** Cause, read from the records and confirmed offline: the
worker had added a third `action_evidence` group to `k_sl_1a_i_r1` ([saw, before dawn, 3:40, vans, clipboard], copied from the
phrase "asks the neighbor what he saw" in `earn_when`), so "Talk to the neighbor." matched two of three groups; and the
narrator's THINGS line said only "Walt", so it did not know the neighbor was Walt. Both fixed after this run (see the plan).

**Q3 regression.** Card recovered after `Search beneath the drawer.`: 4 of 4 in both arms. Protected terms: 0 and 0. Clarification
questions: 0 and 0. The walk outside recorded cleanly in 8 of 8. Old behavior seen in both arms, not caused by this work:
the patrol-arrival cue repeats on turns 4 to 7, and the narrator copies beat sentences ("The drawer rides high in its frame").

**Q4 opening.** Candidate openings named the splintered frame or thrown deadbolt in 3 of 4 (baseline 0 of 4); none mentioned
the card; none mentioned KMS (the KMS line arrives on a later turn in both arms).

**Judges (recorded, never pooled).** 7-criterion: baseline [5, 5, 4, 4], mean 4.5, sd 0.58; candidate [4, 4, 4, 4], mean 4.0;
minimum detectable effect 3.87 for baseline: a 0.5 gap is not a real difference. Continuity "contradicts stated fact": 0 of 28
versus 4 of 28, all four on turn 7 (the invented neighbor). "Acts beyond command": 5 versus 4, all on turn 5 (old behavior).
Fact judge `invented_change`: 0 versus 2 of 28 (turn 3, replicates 2 and 3: the narrator "moved" the lake photograph), harmless
under Brandon's rule; `facts_after_correct` 28 versus 26.

**Prompt size.** Narrator prompts that had a prompt: baseline 4,053 to 5,239 characters, candidate 4,087 to 6,063. The new
maximum is under the 6,500 worst-case ceiling in `tests/test_prompt_budget.py` with about 7 percent headroom: mid-scene prompts
grow as more things are resolved, so the turn-start budget (5,000) understates them.

**Decision rule.** Richness is supported on commands 2 and 3 (fewer plain things resolved as new, correct content) and on the back
door. It is not yet supported on command 7: after the neighbor fix, rerun the candidate arm only (4 replicates) and report that
row as a second candidate run, never pooled with this one.

## Result, second candidate run (2026-11-02; code `b13ba90c`; 4 replicates, 7 commands, every turn read; not pooled with the first run)
Run by Brandon: `bench/results/richer-1a-probe/candidate-run2/`. 4 of 4 replicates completed, 28 turns judged, no failures. Same
story as the first candidate run except the neighbor and calendar fixes.

- **Q2 delivered when earned: all four details, 4 of 4 each.** Back door (outward splinters), calendar and photograph (lemon cake,
  lake), **Walt's account (vans, clipboard, skipped the house) 4 of 4** (it was 0 of 4 before the fix), and the card after `Search
  beneath the drawer.` 4 of 4. Two of four openings named the splintered frame or thrown deadbolt (three of four in run 1; one run
  of four replicates does not separate them).
- **Q1:** zero plain things resolved as new in any of 28 turns (baseline: calendar and photograph in 4 of 4 each). The calendar is
  now a "paper calendar" in 4 of 4 (run 1: a whiteboard with photographs in 3 of 4). The photograph is the two friends at the lake in
  4 of 4. Walt stands at the fence in his jacket as written; the narrator no longer invents a different neighbor.
- **Q3:** protected terms 0; clarification questions 0; the walk recorded cleanly in 4 of 4. Old behavior unchanged: the patrol cue
  repeats and beat sentences are copied. One harmless capture issue: the narrator tried to put the fixed wall calendar at
  "refrigerator" in one turn and the engine refused ("fixed things cannot move").
- **Judges (recorded, never pooled):** 7-criterion [7, 6, 5, 6], mean 6.0 (baseline [5, 5, 4, 4], mean 4.5; run 1 [4, 4, 4, 4]); with
  four replicates and a minimum detectable effect near 3.9 these gaps are not reported as real. Continuity "contradicts stated fact"
  0 of 28 (run 1: 4, all the invented neighbor); "acts beyond command" 4 (turn 5, as in the baseline). Fact judge `invented_change` 3
  of 28, all on turn 3 in three replicates: the narrator "moved" the lake photograph when asked to look at it. Harmless by Brandon's
  rule, but a recurring drift; owed: mark the kitchen photograph `fixed: true` (it hangs by a magnet).
- **Prompt size:** narrator prompts 4,371 to 6,063 characters, the same maximum as run 1, about 7 percent under the 6,500 ceiling.

**Conclusion for scene 1A.** After the neighbor fix the richer 1A meets the decision rule: fewer invented things on commands 2, 3 and 7,
every authored detail delivered in 4 of 4 replicates, and no Q3 regression. The earlier defect (Walt) is closed.
