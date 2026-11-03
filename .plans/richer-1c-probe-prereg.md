# Preregistration: the richer scene 1C, the freight terminal

Written 2026-11-02 before any billed 1C run. Same method and instruments as `.plans/richer-1b-probe-prereg.md` (including its
Amendment 1: richer means every detail does a job, so presence is necessary but not sufficient). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free, done).** `bench describe` runs on both arms. Offline thorough seeding reaches 1C for both arms with
`emergency_water_label_read`, `park_left_behind_read` and `brandon_identified` true and `transfer_window_missed`,
`facility_proof` false, so the pallets reveal is reachable. Both arms use `entry_state: thorough` (not the default `bare`, which
made 1B's "dead drop" guard fire on an unearned term).

## What changed in 1C (each addition has a job)
- **Water pallets** (E): the lot number matches the park thermos. Payoff of the 1B thermos plant; links the park to the terminal.
- **The park's emergency statement played below** (G): plant for the 3B/3C broadcast fight. Explains nothing.
- **Brandon watching the door, not the line** (F): plant for his hidden involvement (2B). He says only "Somebody has to watch the door."
- All three are optional, priority -1, not voiceable, short statements with the images only in the delivery text.
- Plot only (no data yet): 3A.1 now says the transfer dose wears off in the detention block.
- Pulse tell for the woman in the line: proposed and cut (no payoff, read as strange).

## Questions
- **Q1 Invented material.** Plain things resolved new (`item_facts_resolutions`) and specifics the narrator invents, old versus new
  1C. Recorded slips in 1C: identification numbers, tire tracks, prisoners, lantern, radios, equipment, guards, notebook, ladder.
- **Q2 Authored details delivered when earned (candidate).** Pallets with a matching lot number, the speaker below with the park's
  statement word for word, Brandon at the top of the stairs saying the door line.
- **Q3 No regression and the cost of curiosity.** The window closes at scene turn 5 (`transfer_window_1c`). The required path
  (inspect docks, study prisoners, choose) takes 3 turns. The script spends 6 turns on purpose, so the candidate arm is expected
  to MISS the transfer window if the three optional details are all taken first. Record, per replicate: turn at which each reveal
  landed, whether `captives_confirmed_alive` and the choice (copy numbers / secure route) were still reachable, and whether the
  window message fired. If exploring costs the player the choice in most replicates, that is a finding about pacing, not a
  defect to hide: report it and ask Brandon whether to move `transfer_window_1c` from turn 5 to 7.
- **Q4 Value (Amendment 1).** For each added detail: does it plant, pay off, deepen or set mood the scene uses, or is it an inert
  extra prop? Is the candidate narration better, flat or busier than the baseline? Watch for the 1B failures: Brandon reciting
  statements as dialogue, the same image repeated across turns, the narrator and the engine's delivery text saying the same thing
  twice, and the narrator inventing what a thing shows.

## Design
Arms `richer-1c-baseline` (frozen story from `c89e929b`, `bench/frozen/continuity-pre-richer-1c/`) and `richer-1c-candidate`
(current story). Script `richer-1c-terminal`, six imperative commands: `Inspect the loading docks.` `Inspect the water pallets.`
`Listen to the air vents.` `Study the prisoners.` `Watch Brandon.` `Ask Brandon about the transfer route.` 4 replicates per arm,
one opening request each, both judges on, shipped transports, no retries, partial rows kept. Request cap 150 narrator and
matcher requests; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.
Baseline note: commands 2, 3 and 5 reach no authored reveal in the baseline (nothing is authored for them); that is the point of
the comparison for Q1, and means the baseline's narration for those turns is the narrator's own invention.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each of the three details WHEN the window is still open, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (study the prisoners, choose, window message) is a defect to fix before 2A.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500).
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
Later scenes, the 3A.1 explanation (plot only), hosted staging, other models, wording tuning, the older quirk that
`Watch the processing line for Michelle.` has no unique handoff (both captive reveals match it).
