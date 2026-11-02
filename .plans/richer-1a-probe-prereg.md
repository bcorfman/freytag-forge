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
six canonical imperative commands in order: `Examine the back door.` `Look at the wall calendar.`
`Look at the photograph.` `Search the drawer.` `Go outside.` `Talk to the neighbor.` Each replicate also makes one
opening request. Judges on: continuity and fact-tracking (7-criterion and invented-change are recorded, never pooled).

**Smoke first:** 1 replicate, candidate arm only (about 11 narrator and matcher requests plus judges). Read it fully;
stop if the run fails, a reply is unusable, or any quota error appears. **Full run:** 4 replicates per arm, one Ringer
task per arm, run in sequence. Request cap: 150 narrator and matcher requests in total, judge calls separate and
reported separately. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.

## Scoring (every turn read by hand; report per replicate, never pooled)
- **Q1:** per arm and command, plain things resolved new (from each turn's `item_facts_resolutions`, kind thing).
  Harmless invented scenery counts for information only (Brandon: "okay with invented things as long as they don't
  affect the main storyline"); list any that touch the storyline.
- **Q2 (candidate):** per command, whether the authored detail appears: back door (splinters point outward, from
  inside), calendar (lemon cake, Saturday), photograph (lake), neighbor (vans, clipboard, skipped the house).
- **Q3:** card recovered after `Search the drawer.` in at least 3 of 4 replicates per arm; zero protected terms
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
