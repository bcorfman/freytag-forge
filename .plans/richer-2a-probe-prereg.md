# Preregistration: the richer scene 2A, the facility gate

Written 2026-11-02 before any billed 2A run. Same method and instruments as `.plans/richer-1c-probe-prereg.md` (including the 1B
Amendment 1 value rule: presence is necessary but not sufficient; every added detail must do a job). Read every turn by hand with
`.plans/richer-probe-report.py`; report replicates separately, never pooled.

**Smoke (free, done).** `bench describe` runs on all three variations; the baseline and candidate package hashes differ. An offline
walk of both scripts through the matcher (facts applied as each reveal establishes them) reaches the intended reveal on every
command: script A gives F, E, B, G, C-R5; script B gives B, H, C-R5. Both arms use `entry_state: thorough`.

## What changed in 2A (each addition has a job)
- **Badge readers** (E, 2A.2): Brandon says "The readers only check three things. I know which three." He says it easily and does not
  say how. Plants his hidden role for 2B.3. Declared things: `inspector_badges`.
- **Alarm log** (F, 2A.2): forty cooling alarms in three weeks, each closed from upstairs as a sensor fault, none with the supervisor's
  name. Explains his anger and why an outside inspection is believable; plants him as the worker Michelle recruited (2B.4). Declared
  thing: `alarm_log` (alias tablet).
- **Return line** (G, 2A.3, needs the manifold fault found): the line shares its feed with the pumps that keep the lower levels dry,
  and a heavy door across the corridor holds water back. Plants the 3C.3 pumps and watertight barrier and makes Kristin's expertise
  concrete. Declared thing: `return_line`. The delivery avoids the exact names of the 3C things ("drainage pump controls",
  "watertight barrier").
- **Camera** (H, 2A.4, needs the manifold fault found): the camera has turned and stays on Brandon; he does not look up. Plants 2C.1
  ("Rebecca has watched them since the camera turned toward Brandon"). It does NOT establish `rebecca_observing_infiltrators`.
  Declared thing: `security_camera`.
- All four are optional, priority -1, not voiceable, short statements with the images in the delivery text, window 0/2/4 (the
  inspection window closes at scene turn 5, so `latest_turn` 4 is the last turn they can land; lesson from 1C).

## Questions
- **Q1 Invented material.** Plain things resolved new (`item_facts_resolutions`) and specifics the narrator invents, old versus new 2A.
  The baseline narrator has nothing authored for badges, a log, a line or a camera.
- **Q2 Authored details delivered when earned (candidate).** Script A: alarm log (cmd 1), badges (cmd 2), return line (cmd 4).
  Script B: camera (cmd 2). Each lands on the command that asks for it, with the facts it needs.
- **Q3 No regression and the cost of curiosity.** The required path is two commands (feel the lines, explain). Script A spends five
  on purpose; the inspection window closes at scene turn 5 (`inspection_window_2a`), so the explanation is the 5th command. Record
  per replicate: turn each reveal landed, whether `k_sl_2a_c_r5` (clean entry) landed on command 5 or the window message turned it
  into the watched entry (`k_sl_2a_c_r6`/`SL-2A-D`), and which facts ended true (`cover_suspected`, `supervisor_escorting`). A
  watched entry is a valid path, not a failure, but report it: if detouring costs the clean entry in most replicates, ask Brandon
  whether `inspection_window_2a` should move from turn 5 to 6 (it matches the other scenes' pattern at 5, so the default is no).
- **Q4 Value.** For each detail: does it plant, pay off, deepen or set mood, or is it an inert prop? Is the narration better, flat or
  busier than baseline? Watch the known faults: Brandon reciting statements as dialogue (the old 2A entries `k_sl_2a_b_r1`,
  `k_sl_2a_c_r5` are still voiceable), the engine's delivery text repeating what the narrator just wrote (open from 1B and 1C), the
  same image repeated across turns, and the narrator inventing what a thing shows (the badge photos, the log's contents beyond
  the delivery).

## Design
Arms `richer-2a-baseline` (frozen story from `18ddb2d1`, `bench/frozen/continuity-pre-richer-2a/`) and `richer-2a-candidate` (current
story), script `richer-2a-gate` (five imperative commands): `Read the alarm log.` `Ask Brandon about the badges.` `Feel the cooling
lines at the manifold.` `Trace the return line.` `Explain the pressure fault and the ventilation problem to the supervisor.`
4 replicates per arm. Then, candidate only, never pooled: `richer-2a-candidate-b`, script `richer-2a-gate-b` (three commands):
`Feel the cooling lines at the manifold.` `Look at the camera.` `Explain the pressure fault and the ventilation problem to the
supervisor.` (The camera needs the fault found, and with script A's four detours the window closes before it can land.)
Both judges on, shipped transports, no retries, partial rows kept, one opening request each. Projected cost (the bench charges 11 neurons per
turn, opening included; measured on the 1B candidate run, where 4 replicates of 8 turns projected 352): script A is 6 turns x 4
replicates = 264 per arm, so 528 for both arms; script B is 4 x 4 = 176; about 704 in all. (An earlier draft said about 340; it was
scaled from a wrong 1C figure.) Request cap 150 narrator and matcher requests per
run; judge calls separate. Stop on HTTP 429 `AI_QUOTA_EXCEEDED` or `AI_DAILY_BUDGET_EXCEEDED` until 00:00 UTC.
Baseline note: commands 1, 2 and 4 reach no authored reveal in the baseline; that is the Q1 comparison.

## Decision rule (triage only; nothing is adopted from this probe)
- Richness is supported if the candidate resolves no more plain things as new than the baseline, Q2 holds in at least 3 of 4
  replicates for each detail, and Q4 finds the details mostly do a job.
- A candidate failure of the existing path (feel the lines, explain, entry into the corridors) is a defect to fix before 2B.
- Record every narrator prompt's length against `tests/test_prompt_budget.py` (narrator <= 5000, item-matching <= 3500), and name
  any turn over 5,000.
- With four replicates a one- or two-point judge gap is not reported as real.

## Not covered
Later scenes (the plants are paid off in 2B, 2C, 3B and 3C when those scenes are enriched), the missed-window path, hosted staging,
other models, wording tuning, the whole-game remedy for delivery text repeating the narrator.

## Owed to other scenes (so the plants pay off)
2B: let the supervisor's alarm log and Michelle's maintenance line rhyme (maintenance reports are the channel); Brandon's easy
knowledge of the badge readers surfaces in 2B.3. 2C.1: the camera turning toward Brandon. 3B.1/3C.3: the console alarms and the pumps
and heavy door from the return line.

## Result (run 2026-11-03, branch `richer-narration-2a` after merging `main` with the term-ownership fix)
Outputs `bench/results/richer-2a-probe/{baseline,candidate,candidate-b}`, 4 replicates each, none failed, 0 rejected turns in any arm, 704 projected
neurons. Every turn read. Replicates are reported separately; the judge scores below are not real signal (MDE 3.87).

**Headline: richness is supported on the 2A path, with one defect to fix.** Every authored detail landed on the command that asks for it, 4 of 4
replicates each, and the existing path did not regress.

- **Q1 Invented material.** Plain things resolved new: 0 in 20 turns baseline, 0 in 20 candidate, 0 in 12 candidate-b. Specifics invented:
  baseline command 2 makes up badge lore in all four replicates ("biometric", "a different chip", "the usual clearance levels") and command 1 hands
  the player nothing; candidate invents only "Supervisor Jenkins" (candidate-b rep 2) and, on command 5 of candidate rep 4, a walk to the heavy door and
  a "clogged" return line.
- **Q2 Authored details delivered when earned.** Alarm log on command 1: 4/4. Badge readers on command 2: 4/4. Return line on command 4: 4/4.
  Camera on command 2 of script B: 4/4. The reveals landed with the facts they need; none was voiced as dialogue by the narrator beyond the authored line.
- **Q3 No regression, cost of curiosity.** Script A (five commands): `k_sl_2a_c_r5` (clean entry) landed on command 5 in 4/4, so the five-command detour
  does not cost the clean entry; the window default stays at turn 5. All eight runs of scripts A left the scene on command 5. Script B left on command 3, 4/4.
  Baseline commands 3 and 5 reach the same reveals as before.
- **Q4 Value.**
  - Alarm log: plants the supervisor as the worker with a reason to be angry (2B.4). Does a job. Narrator adds the supervisor speaking first and
    twice leaves a stray open quote ("...systems, she says firmly."), an old narrator fault, not new.
  - Badges: the strongest addition. Brandon's easy line plants 2B.3. The narrator frames it without repeating it.
  - Return line: delivers the pumps and heavy door that pay off in 3C.3. **Defect:** in candidate reps 1 and 4 the narrator first has Brandon say the
    line carries cooling water *back to* the manifold, which contradicts the delivered "away from the manifold" (the judge flagged it). Rep 2 and 3 are fine.
    The cause is the narrator explaining a thing it was told only by name; read the recorded prompt before fixing (source, not a new rule).
  - Camera: delivered 4/4 ("The camera holds Brandon in its view. Brandon does not look up."), but three replicates have the narrator call it a
    "standard issue camera" pointed at "the facility's infrastructure" first, and rep 2 says it "stares back at her", which softens the plant.
    The plant works; the lead-in sentence is weak.
  - Narration is busier than baseline but each addition has a job; it is not extra props.
- **Judges.** Candidate 4, 4, 4, 4 vs baseline 4, 4, 4, 4 (candidate-b 4, 4, 6, 5, not poolable). Both script-A arms fail `canon_consistent`, `progressive`
  and `rich` 0/4, partly because the judge expects 7 turns of pacing in a five-command probe. No gap is reported.
- **Prompt budget.** Narrator prompt median 4,618 (baseline 4,435), max 5,380 (baseline 5,353). The only turns over 5,000 are command 5 (the explanation) in
  both arms, 4 of 20 each, so this is not new; candidate-b max 4,880.
- **Fact tracking.** invented_change 0 in all arms; missed_change 4/20 candidate vs 3/20 baseline (noise).

**Follow-ups (none done):** (1) fix the return-line direction at the source after reading the recorded command-4 prompt; (2) tighten the camera lead-in
the same way; (3) the owed payoffs below stay owed to 2B, 2C and 3C.
