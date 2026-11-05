# ChatGPT prompt: write a plan that closes Scene 3A's open narration issues

Paste everything below the line into ChatGPT Desktop. It has the project files open, so it reads them itself. Bring the plan back to
Claude Code, which applies it through Ringer tasks (tests first) and probes it.

---

## Task

Scene 3A of the Continuity Initiative story (branch `richer-narration-3a`, head `39761567`) was enriched with four quiet reveals
(wrist tags, the radio loop, Michelle's private proof, Brandon at the checkpoint reader). The 3A probe found defects. Some are fixed,
some were tried and not adopted, some are open. Read the record, establish the causes and evidence yourself, and write a plan that
closes the open issues **as a whole**: check that no step undoes an earlier fix, that the prompt-size work and the quality work do not
fight each other, and that any step has a measurement that can fail.

Write the plan to `.plans/richer-3a-open-issues-plan.md`. Edit it in place on later rounds; do not regenerate it.

## What to read first

- `AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md`
- `.plans/richer-3a-probe-prereg.md`, every section: the original probe and defects, Amendments 1 to 5 (each records what was measured,
  what was built, what was rejected, and commit ids)
- `.plans/richer-narration.md` (richness rules, the "Resume here" list, the scenes still owed: 3B, 3C)
- `.plans/game-reimagination-plan.md`, section 6 (cue lifecycle, scene handoff) and its Rounds 6 and 7 (the 2A rewording)
- The story package: `data/stories/continuity-initiative/` (`plot.md` Scene 3A, `knowledge.yaml`, `handoffs.yaml`, `world.yaml`)
- Narrator prompt assembly: `storygame/runtime/cloudflare.py` (`_section_user_prompt`, `_speaker_constraint_lines`,
  `_character_lines`), `storygame/runtime/knowledge.py` (`project`, `scene_hidden_ids`)

## The recorded evidence (all local, gitignored, under `bench/results/richer-3a-probe/`)

Print any run turn by turn with `python .plans/richer-probe-report.py <results dir>`. Read the narrations, not only the counts.

| Directory | What it is |
| --- | --- |
| `baseline`, `candidate` | First probe: the frozen pre-3A story against the enriched 3A, 4 replicates each, 9 commands |
| `candidate-run2`, `candidate-run3` | Re-probes after Amendment 1 and Amendment 3 |
| `candidate-run4` (+ `report.md`) | Latest full 3A run, at `7c7f1f6d`: speaker-line rebuild plus the scene-frame sentence |
| `diag-pretrim`, `diag-trim-oldcode`, `fmt-nested`, `fmt-per_statement`, `fmt-per_name`, `fmt-targeted`, `fmt-presentonly`, `fmt-scenededup`, `invalid-fmt2cmd` | Amendment 4: arms for the proof-turn re-spotting and the speaker-line format. `invalid-fmt2cmd` is an invalid run, kept as a record |
| `opening-only/` | Amendment 5: 12 openings per arm (A control, B plot sentence added to the scene frame, C one statement hidden) with the script |
| `c4-C`, `c4-R`, `c4-X` | Amendment 5 part 3: two-command script, 12 replicates per arm (C control, R reworded pressure, entry statement and plot objective, X entry statement hidden) |

Bench commands: `python -m bench run --variation bench/variations/<name>.json --scene 3A --script <name> --replicates N --out <dir> --confirm`;
`python -m bench prompt --scene 3A --variation <file> --text` prints the recorded prompt for free. The bench projects 440 Workers AI neurons for a
4-replicate, 9-command run with judges; a request-based estimate is about 3.7 neurons per narration request.

## Problems already addressed in this thread (verify each; do not assume it is closed)

| Problem observed | Change made (commit) | Outcome measured |
| --- | --- | --- |
| Proof turn (command 5, "Ask Michelle about the lemon cake.") re-spotted Michelle ("She spots Michelle...") 4/4 in run3 | The nested speaker header (`d823a662`) was replaced by one "may say this aloud" line per speaker per statement, listed only for speakers present or named by the command (`c339081a`) | Command 5 re-spotting 0/4 in run4. Amendment 4 records the arms that isolated it |
| Opening invented an unnamed woman in the rows (baseline "scar above her left eyebrow" 4/4); candidate arms added "it's not Michelle" (3/4, 2/4, 2/4 in runs 1 to 3, 0/4 baseline) | The plot's own sentence "Michelle is beside the captives." added to the 3A scene frame (`7c7f1f6d`) | Opening probe, 12 per arm: invented woman 11/12 to 0/12, "not Michelle" 8/12 to 0/12. Run4: Michelle found 4/4 |
| Keypad contradiction in the reader reveal (lead-up wrote Brandon watching the keypad; delivery said he never looks at it), 3/4 | "keypad" removed from the statement, `must_convey` and delivery | 0/4 in runs 2 to 4 for that contradiction (the narrator still invents a keypad on the reader in some turns, see open list) |
| Echo: narrator writes the revealed content, then the delivery repeats it (tags 2/4, radios 1/4, proof 1/4) | Placement text carries the shared content; deliveries trimmed (`69f229ff`, `089b1bc7`) | Tags, radios, reader clean; proof echo 2/4 then trimmed again; see Amendment 1 and 2 |
| Rejected proof turn 1/4; required-path flake (framed official and uprising reveals handed off in 1 of 4 replicates) | `must_convey` regrouped; authored handoff preferred when it fits the typed words (`87566a82`; see Amendment 1 for the commits that cleared the flake) | 0 rejected turns; both reveals 4/4 and earned exit 4/4 in run2 |
| Prompt too long (Brandon: manage per-turn context aggressively) | Pick rules dropped on no-candidate turns, repeated-name placements skipped, participants introduced only when present, named or brought up (`99a48189`, `3729577a`) | The nested header saved about 1,100 characters on command 5 (2,539 against 3,102 to 3,673 old format) but caused the re-spotting; that saving was given up. Other cuts kept |

Tried and not adopted (Amendment 4): speaker trimming by who the command names (failed: missed "senior official" 3/6, invented a
"Sector Commander" 1/6); present-only speakers (kept per Brandon, saved nothing in 3A); SCENE-statement dedup (moved the re-spotting to
Brandon on command 4, 5/6). Amendment 5 part 3: rewording pressure/entry statement/objective (arm R) and hiding the entry statement
(arm X) did not change the command-2 re-spotting (11/12 and 12/12 against 12/12).

## Open problems (observed, causes not established)

| Problem | Where to read it | Observed |
| --- | --- | --- |
| **O1. Two reunions.** The 3A opening is authored entry text, the narrator's lead-up, then the authored cue `michelle_reached` ("Michelle speaks into a stolen radio beside the captives."). With the scene-frame sentence the narrator's opening now has Kristin reach Michelle (eye contact, sometimes speech). Command 1 then delivers `k_sl_3a_a_r1`: "Kristin finds Michelle alive, speaking into a stolen radio beside the captives..." | `candidate-run4` openings and command 1; `opening-only/arm-B-plot-sentence.json`; `handoffs.yaml` (`michelle_reached`); `knowledge.yaml` (`k_sl_3a_a_r1` statement and delivery) | Delivered on command 1 in 12/12 of every c4 arm; opening shows eye contact or a spoken Michelle line in most openings (arm C control: invented Michelle speech 9/12; arm R 0/12). The continuity judge did not flag it |
| **O2. Re-spotting on later commands.** "Enter the medical level" (command 4): "She spots Michelle beside the captives, directing them through stolen radios and coded announcements...", often followed by "rushes over to Michelle" or "the two share a moment". Also command 8 (2/4) and command 9 (1/4) in run4 | `candidate-run4/report.md`; `c4-*` (two-command script); the recorded command-4 prompt in `candidate-run4/all-turn-records.json` (`prompt_user`) | c4 control 12/12, R 11/12, X 12/12 spot Michelle; second meeting 7/12, 8/12, 4/12. Earlier runs: baseline 2/4, first candidate 4/4, run2 4/4 on command 4. Judge `restarts_scene` flags 3/36 in run4 (commands 4, 4 and 9). Brandon ruled earlier that "Kristin approaches X" when she is already near X is acceptable phrasing and not a restart; decide whether "spots Michelle" falls under that ruling |
| **O3. Invented Michelle dialogue** on the proof turn (command 5) and in the opening ("Kristin, what took you so long?") | `candidate-run4` replicates 2 and 4 (command 5); `opening-only` | Command 5: judge flags acts-beyond-command 2/4 (replicates 2 and 4). Opening speech: 9/12 control, 0/12 arm R |
| **O4. Command 9 acts beyond the command.** "Kristin takes the stolen radio from Michelle and gives the signal" | `candidate-run4/report.md` command 9; `knowledge.yaml` `k_sl_3a_c_r1` delivery | 3/4 replicates flagged (the signal text comes from the authored delivery on command 8, then is written again on command 9) |
| **O5. Invented keypad** on the checkpoint reader | `candidate-run4/report.md` command 7 | Turns containing "keypad": baseline 1, run1 4, run2 0, run3 1, run4 2 |
| **O6. Invented official line**, run3 replicate 3 command 8: "We need to wait for the signal from Dr. McGehee" before the authored line | `candidate-run3`, Amendment 3 result item 4 | 1 of 4 replicates in run3; not seen in run4 |
| **O7. 1A smoke** after the prompt cuts: continuity judge 1 contradiction and 1 acts-beyond-command of 7 turns, not traced | Amendment 3 result | Untraced |
| **O8. Prompt size.** Brandon: "I prefer safety but that's really expensive, and loses almost all the gains we made on prompt size reduction." | Amendment 3 and Amendment 4 parts 3, 10 | Longest narrator prompt per command in run3 and run4: read from `all-turn-records.json` (`prompt_user`, `prompt_system`) |
| **O9. Judge counts in run4:** acts_beyond_command 6/36 (run3 1, run2 3, baseline 4); restarts_scene 3/36 (run3 3); contradicts_stated_fact 0/36; fact tracking missed_change 3, invented_change 3 | `candidate-run4/summary.json` | Compare with `baseline`, `candidate`, `candidate-run2`, `candidate-run3` |
| **O10. Unreviewed lead:** arm R reworded the 3A pressure line, `k_scene_3a_entry` statement and the plot objective ("Join the uprising"). Not adopted; awaits Brandon | `.plans/richer-3a-probe-prereg.md` Amendment 5 part 3; the edit is three lines: `knowledge.yaml` (`pressure` of the 3A scene frame and the `k_scene_3a_entry` statement) and `plot.md` (`objective` of Scene 3A) | Opening: invented Michelle speech 9/12 to 0/12, no pistol; command 2 re-spotting unchanged |

Also owed to later scenes from this scene's plants (see `.plans/richer-narration.md`): 3B (radio loop "when it stops, everyone will know";
monitor light "every outbound channel is watched"; Brandon reader ease on the climb) and 3C; the supervisor on the purge list.

## Brandon's standing positions (his words and rulings; follow them)

- Richness comes from the plot, not runtime embellishment; optional quiet reveals each have a job; invented details matter only if they are
  story-breaking.
- Manage the narrator prompt aggressively: only characters and things in the scene or referred to; world state is kept by the worldkeeper.
  "If you can keep the prior behavior and reduce the prompt size in a better way, then do that instead." He prefers safety over size.
- "I also still want you to keep the feature limiting the speaker lines, even if it doesn't help in this case."
- The narrator is a small non-reasoning model: remove the mechanism that causes a defect before adding an instruction; a narrator rule
  comes last, and only if its probe arm wins. Never gate narration with keyword or regex scanning.
- Recommend only techniques proven in earlier scene fixes (cite the file and section) and say what you checked. Anything new must be
  labeled "new, unproven" with the probe that would test it. A reworded line that failed in one scene (3B situation line) is a precedent,
  not an option.
- Probes: one arm per candidate cause, 10 to 15 samples per arm, every narration read by hand, same script and replicate count when
  re-running. Fix known judge faults before comparing.
- Story text is written by you in this chat when a fix needs new wording: give the exact words for each story file edit, unchanged plot
  sentences where the plot already says it. Code and tests go through Ringer, tests first; whole quick suite as the check.

## What the plan must contain

1. For each open problem O1 to O10: the cause you established from the recorded prompts and results (cite the file and turn), whether it
   is a real defect under Brandon's rulings, and the proven technique from the record that fits it. If none fits, say so.
2. A holistic check: which fixes interact (for example the SCENE statements, speaker lines, the authored cue and delivery, the
   scene-frame sentence, arm R) and the order that avoids undoing earlier fixes. Explicitly check each earlier fix in the first table.
3. Each step: the exact files and lines to change, the tests, the probe (arms, samples, neuron cost at 3.7 per request, what result
   counts as a win or a miss, preregistered before the run), and what we may not claim from the sample size.
4. The shortest path to opening the 3A pull request: which open items are acceptable as known items, which block it, and why.
5. A short list of what you would not do.
