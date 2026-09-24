# Jev judge trial: plan

Status (2026-09-24): not started; section 8's questions are decided. Next
is Phase A's test call; the credentials are in `.env`. Written
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
2. Brandon reads Jev's price in the Cloudflare dashboard
   (`dash.cloudflare.com/?to=/:account/ai/models/typesafe/jev`), and it is
   recorded here.
3. One Ringer probe task sends the documentation's example once to
   `POST https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run`
   with `Authorization: Bearer $CLOUDFLARE_AI_TOKEN`, and saves the response. Its check asserts that `answers` has
   the three typed answers and that `model` starts with `jev-`.

Exit: access works, the price is known, and the cost estimate in 6.D is
recomputed from it.

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
