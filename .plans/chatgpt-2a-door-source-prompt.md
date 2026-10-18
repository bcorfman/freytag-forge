# ChatGPT follow-up: both source fixes lost; what is left?

Paste everything below the line into the SAME ChatGPT Desktop thread that
produced `.plans/chatgpt-2a-door-source-approach.md`. It already holds the defect,
the first screen, the evidence layout and the rules, so this prompt does not
repeat them. Bring the answer back to Claude Code, which applies it through a
Ringer task and probes it.

---

Follow-up to your last answer (`.plans/chatgpt-2a-door-source-approach.md`).
Same defect, same repository, same rules from my first prompt: proven
techniques only, subtractive first, no keyword or regex gates, no engine
changes, no restriction on player wording, plain 12th-grade text. Do not
restate the diagnosis you already gave.

## What happened to your two candidates

Claude Code built your probe as written and ran it: smoke, then N=12 with a
freshly sampled control (`door_probe.py --experiment source`; arms control,
location, limits; all generated; same raw player and exact-matcher 2B
continuation). Both lost.

| Arm | Reveal earned by command 2 |
| --- | ---: |
| control (fresh) | 7/12 |
| location (A: perimeter sentence removed) | 5/12 |
| limits (B: console limits restored) | 6/12 |

Neither reaches 10/12 and neither beats control, so both are dropped. Spend was
109 of 180 Cloudflare calls and 72 of 72 player calls.

One deviation from your text: the `limits` replacement needed its YAML value
quoted, because the appended sentence contains a colon.

## What the smoke added (one row per arm, reviewed)

All three arms invented an access route in 2A, and the player pursued it:

- control: "a small, almost imperceptible seam ... hidden access panel". The
  player typed "open the hidden access panel" and still reached the archive on
  command 2.
- location: "a small access panel hidden behind a ventilation grille". Earned on
  command 2.
- limits: "a small, almost imperceptible seam ... partially hidden by a
  maintenance panel". The player kept examining the seam and never reached the
  archive.

So restoring the console limits did not remove the invented panel or seam, even
though it was the missing material you identified. The invented object appears
whatever the knowledge lines say about place or console limits. Your table said
the evidence could not isolate one causal line, and this run agrees.

The invention review (by object, per row) was not run for the 36 N=12 rows,
because the reveal count already decides the screen. Only the 3 smoke verdicts
exist.

## Where to look

- `bench/results/stage7-door-source-n12/results.json`: all 36 composed screens,
  commands, responses and matcher evidence; `prompts/` has the three prompts.
- `bench/results/stage7-door-source-smoke/`: the 3 reviewed rows
  (`verdicts/`, `review-summary.json`).
- `.plans/implementation_plan.md`, "Stage 7 door SOURCE screen RESULT".

Read the N=12 narrations yourself before answering. The reviewer was not run on
them, so the object counts are yours to establish.

## Added to the already-tried list

- Remove "at the facility perimeter" from `k_sl_2a_e_r1`: 5/12 against 7/12.
- Restore the console-limits sentence in `k_sl_2a_c_r2`: 6/12 against 7/12.

Do not propose another knowledge-line edit for this symptom unless the N=12
narrations point at a different line.

## What I need

1. **What the 36 narrations show.** Per arm, what object does 2A invent and how
   often, and is there any row that did not invent one? Say what that implies
   for your earlier reading that the pull sits in the "Finish each action"
   system rule plus the search-completion shape of the command. State what you
   could not establish.
2. **One to three ranked next screens or fixes.** Subtractive and scoping
   first. For each: exact file, exact old and new text or deletion, the proven
   technique and the earlier scene that used it, what it could break, and the
   evidence supporting it. If your answer is the story-neutral search-completion
   ablation you called untested, say exactly what wording changes, in which
   file, and why it is story-neutral. If you think no further 2A-side fix is
   justified, say so and say what the 2B side could do instead without
   weakening a guard.
3. **Probe arms** reusing the new `--experiment` config in
   `scripts/ringer/stage7/door_prompt.py` and `door_probe.py`. Say only what
   must be added: arms, replacements, caps, and what N=12 must show to win.
   Keep the same bar: at least 10/12 earned by command 2, at most 2/12
   unsupported access, no premature disclosure, and a clear improvement over a
   contemporaneous control. Count invention per row from verdict files, and say
   when the review should run.
4. **Limits** that are new since your last answer, if any.

Do not write code. Give story and package text, plus the reasoning above.
