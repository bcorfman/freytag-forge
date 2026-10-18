# ChatGPT: choose the next step toward a quality free-text playthrough

Paste everything below the line into the SAME ChatGPT Desktop thread that produced
`.plans/chatgpt-2a-door-source-approach.md`. It already holds the repository rules and
the 2A/2B defect. Bring the answer back to Claude Code, which applies it through a
Ringer task and probes it.

---

Same repository and rules as before: proven techniques only, subtractive first, no
keyword or regex gates, no engine changes, no limits on player wording, plain
12th-grade text. Write Kristin as Kr and Brandon (the character) as Br.

## The goal has changed

My goal is a quality free-text playthrough, confirmed by a real end-to-end run, as soon
as possible. The 2A door defect is not the goal. It is one thing that broke one run.
I do not want more diagnostic screens unless they are the fastest route to a better
playthrough. Decide the next step against that goal.

## What we know

Stage 7 step 1 is done: one raw-profile blind-player run on staging, all nine scenes.
It passed: 84 turns, the story ended, 0 rejections, 0 game breaks, 30 stuck turns.
Exits: 1A, 1B, 1C, 2A, 2C, 3A, 3B earned. 2B was FORCED (15 turns, turns 2-15 stuck).
3C ended the story. Stuck turns by scene: 1A 2, 1C 1, 2A 3, 2B 14, 2C 4, 3B 3, 3C 3.
Only 2A and 2B have been read closely. This is one sample, not a success rate.

The 2B failure comes from 2A. The 2A exit turn (t7) invented "a small, unmarked door
with a keycard reader and a ventilation grille". No authored text declares it. The
player chased "inspector credentials" in 2B and never named Michelle's selection file,
so `k_sl_2b_a_r1` was never earned.

Everything tried against it has lost:

| Test (all N=12, same recorded 2A turn-7 prompt) | Reveal earned by command 2 | Invented access in 2A |
| --- | ---: | ---: |
| 2B cue wording: current / B / C | 0 / 0 / 2 of 12 | n/a |
| 2A prompt wording: control / review / stale-scene / wording | 7 / 3 / 3 / 4 | 12 of 12 each |
| Fixed 2A text: fixed-control / bridge deletion | 5 / 4 | 0 (inherited door only) |
| Source knowledge lines: control / perimeter sentence removed / console limits restored | 7 / 5 / 6 | 12 of 12 each |

Every generated 2A arm invents a panel, seam or grille in every row, whatever the edit.
The fresh control earns the reveal 7 of 12 times. We have never reached 10 of 12.

One more test was built but not run at N=12: delete the system instruction "Finish each
action the player gives." from the recorded system prompt (arms control / no-finish).
The N=1 smoke gave the same invented panel in both arms and no reveal earned in either.
That is one sample and says nothing either way.

I dropped the by-hand invention verdicts for these screens. LLM judging is also dropped
(2026-10-15 decision: judge verdicts flip on identical input). Use only deterministic
checks: the matcher's earned-reveal count, attempt-bundle reports, stuck-turn counts,
the attribution audit.

## What I need

1. **Pick one next step and defend it against the goal.** Candidates I can see; add any
   you think is better, and rule out the others with the evidence above:
   - Accept the invented-route pull and guard it on the 2B side: make 2B's first turn
     or entry bring the selection files into view regardless of what 2A invented.
   - Repair a different broken scene first (2C 4 stuck, 3B 3, 3C 3, 1A silent exit) and
     rerun the whole playthrough, leaving 2B as is.
   - Rerun Stage 7 step 1 unchanged to see whether 2B's failure repeats. It is one
     sample.
   - Run the 2A "Finish each action" ablation at N=12.
   - Something whole-game (a pattern across the nine scenes) rather than scene-local.
2. **For the step you pick:** the exact change (old text and new text, file and key),
   why it is a proven technique from the scene-fixing guide or an earlier fix, what
   could go wrong, and what a rerun of the E2E must show for me to call it confirmed.
   Use deterministic evidence only. State the bar before the run, not after.
3. **The cheapest confirmation.** One billed E2E replicate costs about 8 minutes and one
   blind-player plus Cloudflare run. Say whether the step needs any probe first or can
   go straight to a full replicate, and why.
4. **What not to do.** Name anything above that I should stop spending on.

Do not propose another knowledge-line edit for the 2A invention. Both tried lost.
Do not restate the diagnosis. Flag plainly where the evidence is one sample.
