# Narration defects the verifier cannot see: preregistration (UNAPPROVED, nothing built, nothing billed)

Status: written 2026-10-25 for Brandon's approval. No billed call has been made. The probe script, its frozen prompts and its tests do not exist yet; they are the first build step below. This is post-gate step 4 of the plan.

**Two defects, one question each.** The T8 shadow sample (code SHA `7faf10cc`, 5 replicates) found two narration defects that the observation verifier neither detects nor repairs:

- **A. Re-find of the held card.** All 10 `feel under the drawer` turns (turns 3 and 4 of each replicate) describe Kristin finding Michelle's memory card taped under the drawer, although she already holds it. Some quote the scene sentence as speech ("Kristin finds Michelle's memory card taped beneath the drawer and pockets it," she says to herself) or add "Dr. McGehee might have said".
- **B. Invented object on a seat.** 3 of 5 `inspect the passenger seat` turns invent an object (a piece of paper on the floor; scraps of paper and a water bottle; strands of hair in the seatbelt). In 4 of 5 replicates the laptop is held by Kristin by then, so the seat truly holds nothing in the facts; in replicate 4 the laptop is still on the seat and the narration describes it correctly.

Question: for each defect, which minimal change to the narrator prompt stops it on the real recorded prompt, so that the matching product fix can be specified?

## What the recorded prompts show (read, not measured)

Source: `bench/results/environment-narration/shadow-sample/full/rows/rows.json` (gitignored, sha256 `aaca5776240d1a347bc21c7c61c609ffa7be3f3ffc8f757b591ff3702e4a447b`), replicate 0, user and system prompts exactly as sent.

- **A.** Every prompt from `pull out the drawer` onward carries the CONSTRAINTS line `Dr. Michelle McGehee may say this aloud: Kristin finds Michelle's memory card taped beneath the drawer and pockets it.` It is generated in `storygame/runtime/cloudflare.py` (the `sayable_knowledge` loop) from the committed knowledge statement `k_sl_1a_b_r0` in `data/stories/continuity-initiative/knowledge.yaml`. Michelle is the story's missing person. The statement is the protagonist's own earned event, so the line hands the narrator a ready-made "find" to say aloud on a turn when the card is already held. The earlier S5 and S5b smokes were confounded by exactly this line, and S5b's 0/15 was measured with the line deleted from the prompt (the "B" and "C" arms). The same prompt also carries `Show these in your reply: binder clips, pens, spare batteries, stapler.`, the observation requirement for a `look` at the drawer, which pushes the narrator to list the drawer's contents on a command that asked about the space under it. In replicate 0's turn 4 the card additionally carries a stale `Condition: taped under drawer.` while `Held by: Kristin.` (the narrator's turn 3 reply set it); turn 3's prompt does not, and turn 3 re-finds the card in 5 of 5 replicates, so that condition is not the sole cause. It is reported as a finding, not tested here.
- **B.** The prompt lists `passenger seat. Place: Kristin's truck.` and no other thing there, so the seat is empty in the facts, but nothing tells the narrator that. The scope line `Nothing is left in or under the X. Searching the X finds nothing.` (T3f, 0/15 inventions on S5b) is rendered only when the focus is declared `contents_complete` and empty. **No `contents_complete` appears anywhere under `data/`**, and the markdown package format cannot express it (open item in the plan), so that line never fires in the shipped story. The earlier S5b result came from a harness-built prompt, not from the product path. The prompt also carries `What presses on Kristin now: Find evidence of Michelle's disappearance`, which the S5b probe found worth deleting (0/8 with it gone, at n=8).

## Frozen prompts

Two prompts, extracted by script from the file above (replicate 0): **PA** = turn 3 `feel under the drawer`; **PB** = turn 8 `inspect the passenger seat`. The script writes `scripts/ringer/environment_narration/defect_probe/prompts.json` (system and user text per prompt) and a SHA-256 lock; `--run` refuses if the file differs from the lock. Arm edits are applied by the script, by exact line match, and each arm's diff against the control is printed and saved so the edit can be read. An edit that does not match exactly one line aborts the build.

## Arms

All arms change the user prompt only (system prompt unchanged), 70B `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, JSON mode off, product default sampling, direct Workers AI, as in smokes 5 to 7.

| Arm | Defect | Edit to the recorded prompt |
| --- | --- | --- |
| A0 | A | none (control) |
| A1 | A | delete the `may say this aloud` line |
| A2 | A | A1, and delete the `Show these in your reply:` line |
| A3 | A | A1, and add the CONSTRAINTS line `- Nothing else is under the drawer. Searching under the drawer finds nothing more.` |
| B0 | B | none (control) |
| B1 | B | delete the `What presses on Kristin now:` line |
| B2 | B | add the CONSTRAINTS line `- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing.` (exactly what the product renders for a complete empty scope) |
| B3 | B | B1 and B2 |

A3's wording is an analogy to the proven outcome wording, not itself proven; A1, B1 and B2 reuse edits already tried on S5b. Deletion is preferred over addition when two arms tie (plan rule: prefer subtractive fixes).

## Stage 1: screen

8 arms x 10 samples = **80 narration calls**, one stream, fixed-seed interleaved order, no retries, no replacement samples. Cost: the 30-call smoke 7 was $0.0182, so about $0.0006 per call; expected **$0.05**, ceiling **$0.10**. Pass `--max-calls 80 --max-usd 0.10`. Stops after 3 consecutive unusable replies or on HTTP 429/5xx. An unusable or truncated reply counts as one sample and is read; it is not replaced.

**Scoring (hand, narration text only, blind to arm).** The script prints replies under random ids with the arm key held in a separate file whose SHA-256 is recorded before reading; I read all 80 and write one verdict per reply into a labels file, frozen by hash before the join.
- **A fails** when Kristin finds, detaches, peels off or discovers anything under or in the drawer that the prompt does not already give her, including re-finding the memory card as if new, or when the reply quotes the scene or cue sentence as speech or attributes it to Dr. McGehee. **A passes** when the card appears only as already held (or not at all) and nothing new is found.
- **B fails** when the reply puts any object on, under, in or around the seat that the prompt does not list (paper, bottle, hair, a key, a cup, etc.). The seat, its belt and upholstery, the truck and the sirens or patrol already in the prompt are not objects. Mentioning the held memory card is fine. **B passes** otherwise.
- Also recorded per reply, outside the pass rule: strict and repaired JSON validity, latency, any unrequested move of Kristin, and any new contradiction of the facts.

**Advance rule (per defect).** Control must reproduce the defect: at least 3 of 10 control samples fail (the shadow sample saw 10 of 10 on A and 3 of 5 on B). If it does not, the defect is reported as not reproduced in this setting and nothing advances. An arm advances when it has **at most 1 failure in 10**. Among advancing arms the simplest (A1 before A2 before A3; B1 before B2 before B3, deletion before addition) is the candidate.

## Stage 2: confirmation (only for an advancing candidate; same approval, no new tuning)

The candidate and its control each get **15 more samples** of the same prompt: up to 4 arms x 15 = **60 calls**, about **$0.04**, ceiling **$0.08**, `--max-calls 60 --max-usd 0.08`, run only after I have recorded stage 1. Gate: **at most 1 failure in the candidate's 25 samples** (10 + 15; Wilson upper bound about 20% at 1 of 25, 13% at 0 of 25) and the control still reproduces the defect (at least 25% failing across its 25). If the candidate fails, the next-simplest advancing arm gets its own 15 with its own cap; no arm is rescued by re-sampling. Total worst case 140 calls, ceiling **$0.18**.

## What a pass permits, and what it does not

- A pass picks a prompt change. It does not change the product. The product change is a separate Ringer task, tests first, written afterwards, and its form depends on the arm:
  - A1 or A2: stop offering an earned event of the protagonist as a line an absent person may say aloud, or stop re-offering a cue after it has landed. First step is a free offline diagnosis of which engine path adds the line for a speaker the scene calls missing (`_speaker_contexts` / `_is_present`), because the plot statement is co-equal ground truth and the fix may belong in how the engine treats it, not in the authored text.
  - B2 or B3: a story-package declaration of `contents_complete` for the passenger seat, which needs the markdown package format to express it first (loader tests, open-world default unchanged).
  - B1: removing the pressure line from the observation prompt only, or everywhere; that is a wider change and gets its own check on the frozen T7 corpus and T1 baseline.
- The integrating test is the second shadow sample (plan step 5), under a new preregistration and your go. T9 stays blocked until it passes.
- A fail means the cause is not in these prompt lines; the next hypothesis (the stale `Condition` on a held card for A, narrator initiative on empty places for B) gets its own preregistration.

## Limits

One recorded prompt per defect, from one story and one replicate (replicates 0 to 3 reached the same facts at turn 8; replicate 4 differs and is not tested). Ten samples per arm cannot show a 9/10 bar on its own (0 of 10 has a Wilson upper bound near 28%); stage 2 exists for that and is still a screen. The hand reader knows the aim and the arm key is hidden, not the prompt context. Prompt-edit arms measure the narrator given a different prompt; they do not prove the engine can produce that prompt on every turn. The 70B revision, Workers AI behavior and the date are recorded per row. The stale `Condition: taped under drawer` finding and the over-demanding `Show these` requirement on a `look` at a container's underside (shadow-sample addendum A) are reported next to this probe, not decided by it.

## Build steps (all unbilled, each a Ringer task, tests first; none started)

1. `scripts/ringer/environment_narration/defect_probe.py` plus tests: `--build-prompts` (extract PA and PB, apply arm edits, write prompts, diffs and lock), `--dry-run` (call count and cost estimate), `--run --confirm --max-calls --max-usd --stage 1|2`, `--sheet` (blind reply sheet, arm key kept apart), `--report` (join with frozen labels, advance rule and gate). Reuse the request, retry-free call and row code of `smoke_direct.py`; no regular expressions; no story vocabulary in the script's logic (the arm edits are data in a table).
2. Offline check that the lock verifies and that each arm's diff is the single intended line.
3. Your go on this preregistration, then one Ringer probe task for stage 1, then I read every reply and record the result in the plan, then stage 2 if a candidate advances.

**Commands after approval (one Ringer probe task per stage).**
`(set -a; . ./.env; set +a; .venv/bin/python scripts/ringer/environment_narration/defect_probe.py --run --confirm --stage 1 --max-calls 80 --max-usd 0.10 --out bench/results/environment-narration/defect-probe-s1-rows.json)`, then `--sheet`, label, `--report`.
