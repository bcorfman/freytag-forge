# Preregistration: the richer scene 1B, opening and first turns

Written 2026-11-02 before any billed 1B run. Brandon said "apply the fixes (especially the ones already shown to work in other
scenes) and run the full probe". The 1B story carries the 1A lessons (plain names, scoped aliases, exact evidence groups, aligned
windows). Same method and instruments as `.plans/richer-1a-probe-prereg.md`.

**Smoke.** The free offline replay (network blocked at the socket, stubbed replies) ran the baseline script for 7 turns with no
crash before any billed call. A live smoke row is skipped because Brandon asked for the full probe and the harness and runtime are
unchanged since the 1A run.

## Questions
- **Q1 Invented material.** For the same seven commands, how many plain things does the matcher resolve as new, and what does the
  narrator invent, with the old 1B versus the new one?
- **Q2 Authored details delivered when earned (candidate).** Picnic (kickstand, empty leash, one cup tipped), the stranger mouthing
  the broadcast a half-beat ahead, the emergency-water label with a lot number after Brandon's explanation, the keypad he does not
  look at and the freshly oiled drain latch.
- **Q3 No regression.** The bench cache is recovered, Brandon is identified, the gate and drain departure delivers, zero protected
  terms, zero clarification questions. What the narrator says the recovered photograph shows is recorded for both arms.
- **Q4 Opening.** Does the shipped 1B opening use declared park things (bicycle, loudspeaker, picnic) instead of inventing others?

## Design (shipped transports, runtime-wired capture, no retries, no replacement samples, partial rows kept)
Arms `richer-1b-baseline` (frozen story from `b13ba90c`, `bench/frozen/continuity-pre-richer-1b/`) and `richer-1b-candidate`
(current story). Script `richer-1b-park`, seven canonical imperative commands in order: `Look at the picnic blanket.`
`Search beneath the park bench.` `Look at the photograph.` `Watch the stranger.` `Ask the man about Michelle.`
`Examine the thermos.` `Follow Brandon through the service gate.` 4 replicates per arm, each with one opening request, both judges on.
Request cap 150 narrator and matcher requests in all; judge calls reported separately. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or
`AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.

## Scoring (every turn read by hand; per replicate, never pooled)
- **Q1:** per arm and command, plain things resolved new (`item_facts_resolutions`), and every specific the narrator invented
  (numbers, names, labels, writing). Harmless scenery is information only (Brandon: invented things are fine unless they affect the
  main storyline); list any that touch the storyline.
- **Q2:** per command, whether the authored detail appears.
- **Q3:** `bench_clues_recovered` after command 2; `brandon_identified` after command 5; `park_pursuit_resolved` after command 7;
  protected terms; clarification questions; what command 3 says the photograph shows.
- **Q4:** declared park things named in the opening; invented ones listed.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves fewer plain things as new than the baseline on commands 1 and 6, and Q2 holds in at
  least 3 of 4 replicates for each of picnic, stranger, thermos and gate.
- A Q3 failure in the candidate is a defect to fix before scene 1C.
- Record every narrator prompt's length against the budgets in `tests/test_prompt_budget.py`.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
Later turns after the escape, other scenes, hosted staging, other models, wording tuning.
