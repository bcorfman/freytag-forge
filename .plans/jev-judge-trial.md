# Jev judge trial: plan

Status (2026-09-24): Phase A done (access, price, one live call). Next is
Phase B, the Jev judge with offline tests. Written
to be picked up in a new chat with no other context.

Goal: find out whether TypeSafe's Jev (`typesafe/jev` on Cloudflare Workers
AI) can replace `gpt-5.6-luna` as the model behind the two bench judges, the
continuity judge (`bench/continuity-judge.mjs`) and the fact-tracking judge
(`bench/fact-tracking-judge.mjs`). The trial must match or beat Luna's
agreement with Brandon's own labels, at lower cost. The escalation judge and
the E2E roleplay judge (`frontend/e2e/roleplay-judge.js`) are out of scope
until this trial passes.

This is a trial only. The Luna judges stay the default and keep running
unchanged throughout. Jev runs beside them as a separate, opt-in judge, and
nothing about the OpenAI judges is removed or changed. Whether Jev ever
becomes the default is Brandon's decision after Phase D (Phase E).

Where the judges run: only locally. `python -m bench run` and
`bench/calibration/rejudge.py` start the judge scripts with `node` on the
developer's machine. The Railway backend never runs a judge.

## Contents

1. Why try Jev
2. What Jev is, and why it is not a drop-in model swap
3. Settled constraints (do not re-litigate)
4. The bar to beat
5. Design: questions per cell, answers combined in code
6. Phases
7. Risks
8. Decisions
9. Reference

---

## 1. Why try Jev

The judges moved from `gpt-5.4` to `gpt-5.6-luna` on 2026-09-24 (`9eb2b1e`)
because Brandon could not afford `gpt-5.4`. A two-replicate bench run costs
roughly $0.06-0.10 in Luna judge calls. Luna agrees with Brandon's labels
less often than `gpt-5.4` did, mostly on the fact judge (section 4).

Jev is priced by TypeSafe at $0.042 per million input tokens, and output is
free. That is about a fifth of Luna's input price, with no output charge at
all. Jev is also built for exactly this job: it returns calibrated
probabilities for typed yes/no, choice and score questions, not free text.
It runs on Workers AI, which is already the project's inference budget (see
memory `cloudflare-workers-ai-is-the-inference-budget`).

The Cloudflare listing does not publish a price; it points to the dashboard.
Phase A reads the real Cloudflare price before anything else is built.

## 2. What Jev is, and why it is not a drop-in model swap

Sources: https://developers.cloudflare.com/ai/models/typesafe/jev/ and
https://docs.typesafe.ai/models.md (and its linked pages
`model-jaggedness/jev-1.13.md`, `concepts/state.md`).

- **Request:** `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run`
  with `{"model": "typesafe/jev", "input": {"state": ..., "questions": {...}}}`.
  `state` is a string, a JSON object, or an array. `questions` maps a name
  to a question of one of three types:
  - `noul`: yes/no. Optional `criteria: {"true": ..., "false": ...}`.
    Answer: `{"noul": 0.95}`, the probability of true.
  - `choice`: one of named options, `criteria: {"option": "meaning", ...}`.
    Answer: `choice`, `confidence`, and `probabilities` per option.
  - `score`: an ordered scale, `criteria: ["low", ..., "high"]`. Answer:
    `score`, `confidence`, `probabilities`.
- **Response:** `{"model": "jev-1.13.0", "answers": {...}, "usage":
  {"input_tokens": n, "output_tokens": n}}`. The `model` field names the
  exact version that answered.
- **No generated text.** Jev never writes a reason, a list, or an
  explanation. It cannot produce the judges' `reason` string or the fact
  judge's `changes` list.
- **Limits:** 64k tokens per request in total; 32k tokens for `state` plus
  the longest single question. One v27 replicate's full judge input is about
  133k characters (about 33k tokens), so a whole replicate does not fit.
  Requests must be per turn.
- **Rate limits:** TypeSafe lists 1,200 requests per minute. Cloudflare's own
  limits may differ.
- **Known weaknesses of jev-1.13** (TypeSafe's "jaggedness" page), and what
  each means here:
  1. *Literal reading.* It answers the question written, not the one meant.
     Every boundary case in the current rubrics has to be written into the
     question's instructions or criteria.
  2. *Counting and math.* Do all counting and aggregation in code.
  4. *Indirection.* Multi-hop questions ("a property of a property") lose
     accuracy. Split them into direct questions.
  5. *Large state full of irrelevant detail.* Accuracy falls as unrelated
     content grows. Send each turn only what its questions need.
  7. *Contradictory instructions and criteria.* Make `true` mean the
     failure the cell names, never the reverse.
  8. *Structural invariants are not guaranteed.* A question and its negation
     need not sum to 1. Ask each decision one way only.

External guidance, gathered by a ChatGPT web search on 2026-09-24. Jev
launched on 2026-09-15, so most of this is vendor text or self-reported:
- TypeSafe's official skill file
  (github.com/typesafe-ai/skills, `skills/typesafe-ai/SKILL.md`, checked).
  It says: "Put the judgment in instructions and define its possible answers
  in criteria." It also says: "Ask one narrow, coherent judgment per
  question." A second request is warranted only to fetch evidence, build new
  state, or choose the next options. Thresholds should be "evaluated on the
  user's data". Nothing on personas or few-shot examples.
- Community, unverified: richer criteria (definitions, "not for" cases,
  examples) measured 64.5% -> 81% -> 84.5% on one dataset (jev-mcp
  RECIPES.md). Best thresholds varied from 0.30 to 0.75 across questions
  (jevi). A roleplay author reports that whole-transcript subjective judging
  fails, while narrow adherence checks work.
- No Jev comparison with GPT-class judges on stories was found.

So the trial is a new judge implementation that asks many narrow questions
per turn and combines the answers in code. It is not a one-line model change.

## 3. Settled constraints (do not re-litigate)

- Every code change is a Ringer task on `gpt-5.6-luna`
  (`"engine": "codex"`, `"model": "gpt-5.6-luna"`). Claude writes the spec
  and the check, reviews the patch, and commits it. Worktrees are detached at
  HEAD, so commit before running. A fresh worktree has no
  `frontend/node_modules`; a check that loads the judges must link the main
  checkout's copy first and remove the link before exporting the patch (see
  `9eb2b1e`'s check).
- Unit tests stay hermetic: no live Cloudflare call and no real credentials
  (memory `unit-tests-never-need-a-live-worker`).
- Smoke-test every billed run on the smallest input first, and read its
  artifacts before the full run (memory `smoke-test-billed-runs-first`).
  Billed runs are Ringer tasks with `"max_attempts": 1`.
- The judge rubric points Brandon has ruled on carry over unchanged:
  - tracked world facts override authored canon and earlier narration;
  - a more specific place or state inside the given one is consistent;
  - an NPC refusing, resisting or staying silent still finishes a command;
  - trying to take a thing is the player character's whole part;
  - a condition the narration never showed is invented.

  The memories are `judges-trust-world-facts-and-allow-refinement` and
  `npc-refusal-is-not-an-unfinished-command`, and the current rubric text
  is in the two judge files.
- Nothing is tuned to one story in a way that would not carry to another
  (memory `audits-must-generalize-across-stories`). The labels come from
  continuity-initiative only, so any threshold tuning must be held out
  (section 5.4).
- Brandon picks the judge model for cost (memory
  `judges-run-on-luna-for-cost`). The trial does not propose going back to a
  larger OpenAI model.

## 4. The bar to beat

Luna, calibrated 2026-09-24 on HEAD `d09db55`
(`bench/results/probes/luna-calibration/r7`-`r9`, recorded in
`.plans/narrated-world-continuity.md`, "Luna judge calibration"):

| Round | Continuity | Fact |
|---|---|---|
| r7 | 111/114 = 97.4% | 91/105 = 86.7% |
| r8 | 184/192 = 95.8% | 315/336 = 93.8% |
| r9 | 132/142 = 93.0% | 236/251 = 94.0% |
| total | 427/448 = 95.3% | 642/692 = 92.8% |

Pass criteria for Jev:
- On the held-out rounds r8 and r9, it matches or beats Luna's agreement on
  each judge.
- It reaches `check_calib.py`'s 90% bar on every round and judge.
- It costs less per two-replicate bench run than Luna.

Brandon does not care about `invented_change` disagreements unless the
invention breaks the story (2026-09-24, over a receipt tracked as
"crumpled"). Report `invented_change` cells separately, as context. Do not
tune questions to win them, and do not ask for relabels.
`protagonist_acts_beyond_command` is likewise context, never a failure
(memory `narrator-initiative-is-not-a-failure`).

Luna's known weak cells are the ones to watch:
- `narration_contradicts_given_facts` on the t3 pocket turn;
- `invented_change` on r7 t10's "crumpled" receipt;
- `restarts_scene` in r9 1B.

It also missed an invented paper under the drawer in v28.

## 5. Design: questions per cell, answers combined in code

### 5.1 One request per turn per judge

State is one JSON object per turn, holding only what that judge's questions
need. It is built in code from the same records the current judges receive
(`bench/judge_input.py` `judge_turns`, plus the package canon that
`bench/judge-canon.mjs` already extracts).

- Continuity state: `scene_id`, `command` (player input), `narration`,
  `story_text`, `given_facts`, `hidden_canon` (only the scene's
  `**Hidden canon:**` lines from plot.md, not the whole plot), `opening`
  (the scene's opening narration), and `earlier_narration` (the previous
  two turns in the same scene). Phase B measures whether more history helps.
- Fact state: `command`, `narration`, `story_text`,
  `item_facts_before`, `item_facts_after`.

### 5.2 Literal sub-questions, combined in code

Each current verdict cell becomes one or more `noul` questions with
`criteria.true` naming the failure. Where a rubric rule is a conjunction or
has an exception, split it and combine in code. A first mapping, to be
revised in Phase B:

**Continuity judge:**
- `contradicts_stated_fact` = narration states a thing's place or physical
  state that conflicts with `given_facts`; or it conflicts with `opening`,
  `earlier_narration` or `hidden_canon`. That is two nouls, OR-ed in code, so
  the world-facts-win rule is its own literal question.
- `protagonist_acts_beyond_command`: one noul, with the listed exclusions
  (looking, noticing, small movements needed for the command) written into
  `criteria.false`.
- `restarts_scene`: a noul on arriving at or entering the scene's location,
  plus a noul on re-discovering something `opening` or `earlier_narration`
  already showed, OR-ed.
- `command_not_finished` is the rule most in need of splitting. Code
  combines these nouls:
  - Does the command need another character to act?
  - Does the narration show her doing her own part?
  - If another character must act, is any response shown? A refusal,
    struggle or silence counts.
  - If the command names a place, does the narration name that place as
    where she arrives or is heading?
- `reveals_hidden_canon`: a noul on whether the narration shows a
  `hidden_canon` thing before her action reaches its spot, or in another
  spot.

**Fact judge:** ask per tracked thing, and aggregate in code. Things are
the union of `item_facts_before` and `item_facts_after` keys; the
thing's name goes in the question text, e.g. "Does `narration` show
Michelle's phone moving to a new place or holder?".
- Pure structure is decided in code with no model call at all: a condition
  phrase present before and absent after, or a key added or removed.
  Comparing these dicts is not scanning prose, so it does not conflict with
  memory `narration-fix-strategy-ranking`.
- Per thing, nouls ask:
  - Did the narration change its place or holder?
  - Did it change or end a condition?
  - Does the `after` place or condition show something the narration never
    showed?
  - Does the narration conflict with `before`?
  - Is the `after` place a state instead of a place?
- `facts_after_correct`, `missed_change`, `invented_change`,
  `dropped_true_condition`, `kept_ended_condition` and `state_as_place` are
  then boolean combinations over things. Each combination is written out in
  the judge's code with a unit test.
- The `changes` list and its `cause` are rebuilt from the per-thing
  change nouls, plus one noul per change: "Does `command` itself ask for
  this change?"

### 5.3 Output stays in the current schema

The Jev judge writes `continuity-judgments.json` and
`fact-tracking-judgments.json` in exactly the schema the current judges
write, so `bench/calibration/check_calib.py` and `bench/failure_report.py`
work unchanged. Two additions:
- `reason` is generated in code, not by the model. It lists the
  sub-questions that decided the cell with their probabilities, e.g.
  `own_part_shown 0.93; response_shown 0.12`.
- A sidecar `jev-raw.json` keeps every request's `model` version, question
  set, answers and `usage`, for audit and cost.

This loses the model-written reason. Brandon ruled that the verdict alone
is enough (section 8).

### 5.4 Thresholds

The default is `yes` when a failure noul's probability is above 0.5. Tuning
a per-question threshold is allowed only on r7. Report r8 and r9 at the r7
threshold and at 0.5, so the held-out numbers are honest. Never tune on r8
or r9.

## 6. Phases

### Phase A - Access, price and a live hello (Brandon plus one probe)

1. Brandon created a user-owned Cloudflare API token with Workers AI
   permission, `CLOUDFLARE_AI_TOKEN`, and added it to `.env` with
   `CLOUDFLARE_ACCOUNT_ID` (done 2026-09-24). Verify it for free with
   `GET https://api.cloudflare.com/client/v4/user/tokens/verify`; the
   account-level verify endpoint rejects user-owned tokens. The worker's
   `CLOUDFLARE_WORKER_TOKEN` is not a Cloudflare API token: it is the
   worker's own `DEMO_SHARED_TOKEN`, and Cloudflare rejects it. The narration
   worker is not changed. A worker branch was built and passed its check,
   but it is not needed and was not applied.
2. Price, read by Brandon in the Cloudflare dashboard on 2026-09-24:
   $0.042 per million input tokens, the same as TypeSafe's direct price.
   Cloudflare bills Jev through AI Gateway credit, not the Workers AI
   allowance that narration uses. The first probe call authenticated but was
   refused with "Insufficient balance; add money to your gateway or use
   BYOK" (code 2021). Nothing runs until the gateway has a balance. To add
   one: AI Gateway page -> Credits Available -> Manage -> Top-up credits
   (a 5% fee applies to credit purchases; the gateway's Workers AI Billing
   setting may need to be "Unified billing"). The BYOK route is not
   available: direct TypeSafe access is behind a waitlist.
3. One Ringer probe task sends the documentation's example once to
   `POST https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run`
   with `Authorization: Bearer $CLOUDFLARE_AI_TOKEN`, and saves the response. Its check asserts that `answers` has
   the three typed answers and that `model` starts with `jev-`.

Exit: access works, the price is known, and the cost estimate in 6.D is
recomputed from it.

DONE 2026-09-24. After Brandon added AI Gateway credit, one call with the
documentation's example returned `jev-1.13.0` answers matching the docs
(`is_urgent` 0.95, `department` billing 0.88, `frustration` 1.04; 426 input
tokens), billed as `"keySource": "Unified"`. Cloudflare wraps the answer one
level deeper than the docs show, and the judge must parse this shape:
`{"success": true, "result": {"state": "Completed", "result": {"model",
"answers", "usage"}, "gatewayMetadata": {...}}}`. Treat any `state` other than
`Completed` as a failure. The price is unchanged at $0.042 per million input
tokens, so the 6.D estimate stands.

### Phase B - Question design on a small slice (offline code, then a tiny billed probe)

1. Ringer task: write `bench/jev-judge.mjs` with the same CLI shape as
   `bench/continuity-judge.mjs` (`--input`, `--output`). It builds
   the per-turn states and questions of section 5, calls `/ai/run` with
   `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_TOKEN`, combines
   the answers in code, and writes the two judgment files plus
   `jev-raw.json`. The tests `bench/jev-judge.test.mjs` are hermetic: a stub
   fetch returns canned Jev answers, and the tests cover:
   - every code combination rule (including the command_not_finished
     conjunctions and each fact-judge aggregation);
   - the schema of the written judgments;
   - that state is filtered per judge;
   - that a request over the 32k state limit fails loudly before sending.
2. Billed probe on 10 hand-picked turns with known labels, run once. It must
   include the four weak spots from section 4, one hand-over turn and one
   scene transition. Read every answer by hand. Revise question wording
   where Jev read it too literally. This is the only loop, and it runs on 10
   turns, not whole rounds.

Exit: on the 10 turns, every cell's answer agrees with the label, or the
disagreement is understood and the rubric point is written into the
question.

### Results so far (2026-09-24)

Phase B, first 10-turn probe (`bench/results/probes/jev-probe`, first
questions): Jev 79/88 labeled cells against Luna 77/88 on the same cells.
Four fixes followed (`4b17bff`): the facts_after_correct combining bug, a
starting-place conflict question, trips finished in the opening, duplicate
names, and look-alikes of hidden things.

Full rounds 7-9 with the round-2 questions
(`bench/results/probes/jev-calibration`, 473k input tokens, about $0.02),
against the author's labels. "Held out" drops `invented_change`,
acts-beyond-command and the 10 probe turns the questions were tuned on:

| Judge | Continuity, all | Fact, all | Continuity, held out | Fact, held out |
|---|---|---|---|---|
| gpt-5.4 (saved, older rubric) | 96.9% | 96.4% | 96.9% | 97.3% |
| Luna (current rubric) | 95.3% | 92.8% | 96.4% | 92.6% |
| Jev (round-2 questions) | 86.4% | 92.9% | 85.7% | 93.3% |

Fact: Jev is level with Luna, at a fraction of the cost. Continuity: Jev is
about 10 points behind. Its misses are spread fairly evenly:
- `command_not_finished`, 11 false yes: a look command where she also picks
  the thing up fails `own_part_done`, and "around the bench" is read as a
  named place that is never reached;
- `command_not_finished`, 11 false no;
- `restarts_scene`, 11 false yes: `rediscovers` fires at 0.53-0.74 on
  ordinary turns;
- `contradicts_stated_fact`, 11 false yes and 8 false no.

Many of the deciding probabilities sit near 0.5.

### Continuity request-design ablation, round 7 (2026-09-24)

Five ways of sending the continuity questions (`--variant`, `2ce4c71`,
`8f71e79`), each run once over round 7
(`bench/results/probes/jev-variants-r7`, about $0.03 in total):

| Variant | Round 7 continuity | Input tokens |
|---|---|---|
| baseline (one request per turn) | 96/114 = 84.2% | 97k |
| preamble (continuity-editor task line in state) | 103/114 = 90.4% | 100k |
| split (command / turn / history requests) | 101/114 = 88.6% | 127k |
| split-examples (split plus invented worked examples in state) | 100/114 = 87.7% | 177k |
| split-criteria (split plus the same examples in criteria) | 100/114 = 87.7% | 142k |

Jev is not deterministic. The baseline sent byte-identical requests to the
earlier round 7 run, which scored 99/114. Answers moved by 0.013 on average
(max 0.20), and 6 of 688 crossed 0.5. So about 3 cells (2-3 points) is the
noise floor. The preamble's gain (+4 to +7 cells) is suggestive, not proven.
The split and example variants sit within about twice the noise. This goes
against the external guidance (section 2), which found no support for
personas. Even the best variant trails Luna (97.4%) and gpt-5.4 on round 7
continuity.

### Preamble confirmed on rounds 8-9 (2026-09-24)

`preamble` and a fresh `baseline`, each run once over rounds 8 and 9
continuity (`bench/results/probes/jev-preamble-r8r9`, about $0.02).
Held out means without the 10 probe turns, 306 cells:

| Judge | All 334 cells | Held out |
|---|---|---|
| Jev baseline, earlier run | 86.2% | 85.6% |
| Jev baseline, today | 86.2% | 85.9% |
| Jev preamble | 91.0% | 90.8% |
| Luna | - | 95.8% |
| gpt-5.4 (saved, older rubric) | - | 96.1% |

The two baseline runs agree within 1 cell, and the preamble beats both by
15-16 cells. The gain is spread across command_not_finished,
contradicts_stated_fact and restarts_scene, so it is real. It still leaves
Jev's continuity about 5 points behind Luna and gpt-5.4.

### Free analysis of the saved preamble answers (2026-09-24)

No new calls. The script is kept in the session scratchpad as
`r16/analyze.py`, and a Ringer task should move it to `bench/` if it is
kept. It uses the preamble answers for rounds 7-9 (132 labeled turns), with
leave-one-round-out validation: each round is scored by a model trained on
the other two. Held out means without the 10 probe turns, 414 cells:

| Approach | Continuity held out | contradicts | restarts | command | reveals |
|---|---|---|---|---|---|
| Flat 0.5 hand rules (committed) | 90.8% | 92.1% | 88.8% | 85.7% | 95.1% |
| A. Per-question thresholds | 91.1% | 93.0% | 86.2% | 87.8% | 95.1% |
| B. Learned combiner (logistic regression per verdict) | 94.0% | 93.0% | 93.8% | 89.8% | 98.4% |
| Luna | 96.4% | 96.5% | 91.2% | 96.9% | 99.2% |

- A is noise: tuning thresholds does not help.
- B gains about 3 points over the hand rules. It beats Luna on restarts, is
  level on hidden canon, and trails on contradictions and, mostly, on
  unfinished commands.
- C, the Jev -> Luna cascade, is simulated with Luna's saved verdicts:
  - Cells whose questions are all at least 0.2 from 0.5 cover 77% of cells
    and are 95.4% correct. Uncertain cells are only 75.7% correct.
  - Sending every turn with any uncertain answer to Luna scores 96.2% (all
    448 cells) against Luna's 95.3% alone, but routes 89 of 132 turns (67%)
    to Luna. That is little saving.
- Caveat: B learns weights from one story's labels, which cuts against
  "audits generalize across stories". It should be re-checked on a second
  labeled set, such as v29, before it is trusted.

### Unfinished-command variants (2026-09-24)

`8aca8dd` adds three variants built on the preamble:
- `preamble-rubric`: the author's command-finishing rules added to the task
  line;
- `preamble-holistic`: one direct `command_unfinished` question, recorded
  but not used by the hand rules;
- `preamble-rubric-holistic`: both.

Each ran once over rounds 7-9 (`bench/results/probes/jev-unfinished`,
about $0.04). Scored held out, with leave-one-round-out learning (analysis
script `r18/analyze_unfinished.py` in the session scratchpad):

| Variant / method | Continuity | Unfinished commands |
|---|---|---|
| preamble, hand rules | 90.8% | 85.7% |
| preamble, learned combiner | 94.0% | 89.8% |
| preamble-rubric, learned combiner | 94.0% | 90.8% |
| preamble-holistic, direct question alone | 91.8% | 88.8% |
| preamble-holistic, learned combiner + direct question | 95.2% | 94.9% |
| preamble-rubric-holistic, learned combiner + direct question | 94.4% | 93.9% |
| Luna | 96.4% | 96.9% |

- Writing the rules into the preamble does not help.
- The direct question is weak on its own, but as one more input to the
  learned combiner it adds 5 unfinished-command cells.
- The best Jev setup (`preamble-holistic` plus the learned combiner) is 1.2
  points behind Luna on continuity: 394 against 399 of 414 cells. On
  unfinished commands it is 2 points behind.
- The same caveat applies: the combiner's weights come from one story's
  labels, and it needs a second labeled set before it is trusted.

### Phase C - Calibration on rounds 7-9 (billed, cheap)

1. Ringer probe task (`max_attempts: 1`): extend `rejudge.py`, or add a
   sibling, so it can call `jev-judge.mjs`. Re-judge
   `item-facts-v8/v9/v10-two-scene-1a` into
   `bench/results/probes/jev-calibration/r7`-`r9`, then score each with
   `check_calib.py`. Keep the same package HEAD as the Luna calibration
   (`d09db55`, or record the one used), so the inputs match.
2. Report per round and judge, at 0.5 and at the r7-tuned thresholds, next
   to Luna's table. Also list per-label mismatches for the four weak spots.

Exit: the section 4 criteria are met or clearly missed. A miss ends the
trial unless the mismatches point to one fixable question.

### Phase D - One live round with both judges (billed)

Only if Phase C passes, and with Brandon's go-ahead. Run the next bench
measurement (v29 or later) with both the Luna judges and the Jev judge on
the same turns. This needs a bench option that runs the Jev judge beside the
current ones; it is a small Ringer task. Compare their verdicts turn by
turn, and send Brandon the disagreements for rulings. They become new
calibration labels.

Cost estimate, to be recomputed after Phase A:
- One two-replicate run: 38 turns x 2 judges at about 3-6k state tokens,
  plus about 1-2k question tokens, per request. That is about 0.3-0.6M
  input tokens, or $0.01-0.03 at TypeSafe's list price.
- Luna: about $0.06-0.10.
- The Phase C calibration: about 130 turns x 2 judges, about 1-2M
  tokens, or under $0.10.

### Phase E - Decision

Brandon decides whether Jev becomes the default bench judge. If it does:
- `E2E_JUDGE_MODEL` does not apply to Jev. Choose the backend with a new
  setting (for example `BENCH_JUDGE=jev`), defaulting to whatever Brandon
  picks.
- Update the runbook entry in place.
- Keep the Luna judges working as the fallback.
- If Jev does not become the default, it stays an opt-in judge or is
  removed. Either way the Luna judges are untouched.

## 7. Risks

- **Literal reading fails a nuanced rule.** The rubrics carry many boundary
  cases. The mitigation is splitting and writing each into criteria, but
  some may need Brandon's wording. Phase B exists to find them on 10 turns,
  not 130.
- **History-dependent cells.** `restarts_scene` and
  `contradicts_stated_fact` look back over earlier turns. Too little history
  misses restarts; too much is the distractor problem. Phase B tries two
  history sizes.
- **Calibration is TypeSafe's, not ours.** Jev's probabilities are
  calibrated on TypeSafe's data. A 0.5 threshold may not be right for these
  questions, hence the held-out threshold rule.
- **One story's labels.** Agreement on continuity-initiative does not prove
  it generalizes. Record this; do not claim more.
- **Version drift.** On Cloudflare the ID is `typesafe/jev`, which may move
  to a new version. Every result records the `model` field. Phase C and D
  comparisons must use one version, and the check fails if it changes
  mid-run.
- **Rate limits.** TypeSafe says its limits "are adjusting dynamically". A
  429 mid-run must fail loudly, never retry silently into a billed rerun.

## 8. Decisions (Brandon, 2026-09-24)

1. **Access:** call Cloudflare's REST `/ai/run` directly from the local
   judge, with `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_TOKEN` in `.env`.
   The narration worker (`.plans/cloudflare.js`) is not changed, so the trial
   cannot affect the live game.
2. **Reasons:** the verdict alone is enough. "Just getting the verdict is
   fine (command_not_finished, restarts_scene, etc.)." No generative model
   writes reasons. The code-built `reason` in 5.3 is an optional debugging
   aid. Do not spend effort making it readable.
3. **Scope:** the continuity and fact-tracking judges only.

## 9. Reference

- Judges: `bench/continuity-judge.mjs`, `bench/fact-tracking-judge.mjs`,
  `bench/judge-cli.mjs`, `bench/judge-canon.mjs`, `bench/judge_input.py`.
- Calibration: `bench/calibration/README.md`, `labels-round7/8/9.json`,
  `check_calib.py`, `rejudge.py`.
- Luna calibration results: `bench/results/probes/luna-calibration/`.
- Jev docs: Cloudflare model page above; TypeSafe `models.md`,
  `model-jaggedness/jev-1.13.md`, `concepts/state.md`, `patterns/fan-out.md`.
- The continuity plan this feeds: `.plans/narrated-world-continuity.md`.
