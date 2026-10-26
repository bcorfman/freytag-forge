# Preregistration: T5 model x context screen for environment narration

Written 2026-10-25 before any billed run, at source `14f11314` plus the uncommitted T1-T4b work. **Brandon has not approved this document. Nothing billed runs until he does.**
Plan: `.plans/grounded-llm-environment-narration.md` (T5, "Experiment and adoption gates" items 1-3, 7).

## Question

With the minimal safe projection (the opt-in observation prompt), does any of three Cloudflare models narrate the environment correctly and consistently, across six different situations, without engine-written item prose? The earlier boarding probe tested the old prompt on the 8B model only (best arm 5/30). This screen separates two causes: **context** (is the needed fact in the prompt) and **model** (can it use it).

## Candidate list is under revision (2026-10-25, Brandon's question)

The three models below were inherited from the plan's "engineering hypothesis", not chosen from a survey of the catalog, and two of them (a 70B dense model and a 552B-backbone MoE reasoning model) are the least likely to meet the speed gate. Faster-looking, cheaper candidates on the Workers AI catalog (checked 2026-10-25): `@cf/google/gemma-4-26b-a4b-it` ($0.10/$0.30), `@cf/qwen/qwen3-30b-a3b-fp8` ($0.051/$0.335), `@cf/openai/gpt-oss-20b` ($0.20/$0.30, documented "for lower latency"), `@cf/zai-org/glm-4.7-flash` ($0.0605/$0.40, "fast and efficient"). A cheap direct smoke over a wider set comes first; the 36-cell design below is rewritten from its result. Nothing below is approved.

## Arms (36 cells)

6 starts x 2 contexts x 3 models. Prompts are built offline by `scripts/ringer/environment_narration/screen.py --dry` from the real package. Contexts: **E** existing (what the current code would send; consumed boarding uses the bypass capture) and **P** proposed (observation request set). The system text is identical across E and P in every start.

| Start | Player input | Kind | What differs, E to P (read from the dry run) |
| --- | --- | --- | --- |
| S1 boarding | `Enter the truck.` from outside_house | enter | P: laptop in THINGS at the passenger seat, original action kept, one `Already done:` line with the seat step only, `Show these in your reply: Kristin's laptop.`. E: laptop only in `Just before this:` with the engine notice. |
| S2 outside view | `Look through the truck window.` | look | P (on a tmp package copy declaring a `view` of the truck from outside): laptop in THINGS and required. E (shipped package): no laptop. |
| S3 moved item | `Examine my laptop.` laptop already held | look | P adds only the `Show these` line. E already says `Held by: Kristin`. A control for the held-item label. |
| S4 drawer opening | `Open the drawer.` in the kitchen | open | **P and E are identical.** A model-only control; hidden card must stay hidden. |
| S5 search after recovery | `Search beneath the drawer.` card already held | look | P (tmp copy declaring the drawer `contents_complete`): `The drawer holds nothing else the player can find.`. E: nothing. Both keep the authored `Dr. McGehee may say this aloud: Kristin finds ... pockets it` cue line, as in the open-defect scenario. This start measures the scope line, not removal of the cue. |
| S6 nearby area | `Look around.` in the kitchen | look | P adds the back door and Michelle's phone to THINGS. E lists only Kristin. |

Models (through the Worker's gated `X-Bench-Model` header): `@cf/meta/llama-3.1-8b-instruct-fast` (current configured default; baseline), `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `@cf/deepseek-ai/deepseek-v4.1-flash-1017` (`reasoning_effort` low). `max_tokens` 1024, 1024, 3072. The deployed production model is **unverified**; the first arm is the code default, not a measured production fact.

## Design and cost

- **Smoke first:** 6 calls (S1 x both contexts x 3 models, 1 sample), ceiling $0.016. Purpose: transport only (auth, header honored, echoed model equals requested, the response shape of each model, DeepSeek reasoning/usage fields, paid access). Smoke rows are not scored and are not part of the screen.
- **Screen:** 10 samples per cell, **360 calls**, interleaved round robin across cells, one call each, **no retries, no replacement samples**, partial rows kept after every call. Estimated ceiling **$0.964** (dry run; input estimated as ceil(bytes/3) tokens, every call priced at its full `max_tokens`). Total approved ceiling requested: **$1.00** (`--max-usd 1.00`), hard call cap 366.
- Stop at once on `AI_QUOTA_EXCEEDED`, `AI_DAILY_BUDGET_EXCEEDED`, `BENCH_MODEL_REJECTED`, or any echoed-model mismatch (run invalid). Quota or budget errors are reported, never rerun around.
- No Jev, matcher, capture, or verifier calls. The screen is generation only.

## Scoring (hand, every reply read; narration text only)

A reply is **fully correct** when all hold. Unusable replies (unparseable) count as failures.

- **S1:** the laptop is shown on the passenger seat (any wording that places it there); Kristin stays seated (no exit, no driving, no second sitting-down); nothing story-breaking invented.
- **S2:** the laptop is seen through the window from outside; Kristin stays outside (does not enter); nothing story-breaking invented.
- **S3:** the laptop is described as with or in Kristin's hands; it is not put on a seat or in the truck; no second laptop.
- **S4:** the drawer opens; only contents the prompt supplied may be described; the memory card is not found or described; no replacement clue.
- **S5:** the card is not found again; no replacement clue or new hidden object; an empty or nothing-more result in any wording.
- **S6:** only things in the prompt are described (door, phone, anything already in the kitchen scene); nothing from the truck or another area; nothing story-breaking invented.

Per project scoring rules: an invented detail is a failure only if it is story-breaking or actionable (a new clue, object the player could use, or a place); narrator initiative beyond the command is not a failure; an NPC refusal is not an unfinished command. Failures are also classed: **protected disclosure** (the hidden card shown before earned), **unrequested movement** (exit, drive, or entering when only looking), **unsupported actionable discovery**. A judge model may assist annotation; the generating model never certifies its own output; the reference is my reading, with the full report at `bench/results/environment-narration/t5-report.md`.

## Speed is a requirement, not a footnote (added 2026-10-25 at Brandon's direction)

Narration must respond fast. A correct but slow model does not advance. Every call's wall-clock latency is already recorded by the harness (`latency_ms`); at scoring time I compute p50 and p95 **per model, over its 120 screen calls**, from the rows file (no harness change). Because the three models run interleaved in the same window, the comparison is fair, and the current default is measured as the baseline in the same run. Cold-start effects are visible in the smoke and the first rounds; I will report them and not drop them.

Proposed gate (**Brandon to confirm or change the numbers before approval**): the plan's end-to-end target is p95 < 10 s for a normal turn, and that turn also pays for item matching, any verifier and a possible recovery call. So the narration call alone must come in at **p95 <= 5 s**, and its **p50 no more than 2x the baseline model's p50**. A model that breaks either bar is reported as too slow, however correct.

DeepSeek is a reasoning model and is fixed at `reasoning_effort: low` in the Worker profile, which spends hidden tokens before it answers and is the likeliest speed risk. Open choice: (a) test `low` only and accept it may fail on speed; (b) also test `none` (no reasoning, expected faster, possibly less accurate), which needs a small Worker profile change and adds 120 calls (about +$0.12 ceiling). Recommend (b), since speed is a hard requirement.

## Decision rule (triage, not reliability proof)

A (model, P) cell **advances** when it is fully correct in at least **9 of 10 in each of the six starts**, with **zero** protected disclosures, unrequested movements and unsupported actionable discoveries in its 60 replies, **and** its model passes the speed gate above. S4 is a control (P equals E). If more than one advances, prefer the cheaper and faster, then the one with the smaller E-to-P gap on S1, S2, S5 to confirm the projection (not the model) did the work. If none advances, report which layer failed per start: P beats E for a model but fails the bar = model limit; P equals E = projection does not help; every model fails the same start = the material or task is wrong. **A losing screen stops the line.** No story prose, no fallback sentence, no retuning against these same samples. GLM escalation needs its own preregistration.

## Not covered / limits

- Samples per cell are small and prompts are repeated (10 identical prompts per cell). Nine of ten is a screen, not a 99% claim; I will report Wilson intervals.
- S2 and S5 P arms use tmp package copies with new declarations; the shipped story data is unchanged and the declaration is part of the proposal.
- S5 keeps the authored reveal cue in both arms, so it can fail for a reason the scope line cannot fix. If S5 fails in both arms, I will say so and will not conclude the scope line is useless.
- Reveal handoffs, bridges, refusals and dialogue are untouched and out of scope.
- No verifier and no recovery path here. Latency is gated as above; cost is recorded. Latency measured through the bench Worker includes its own hop, so it is an upper bound on what the product's Worker adds.

## Needed from Brandon before the smoke

1. Approve this document and the **$1.00** ceiling (smoke + screen).
2. **A bench Worker.** The production Worker does not have this branch's model profiles or `CF_BENCH_MODELS`. The `X-Bench-Model` header exists only in the uncommitted `worker/` changes. A separately named Worker deployed from this branch with `CF_BENCH_MODELS` set to the three ids above (and its own `DEMO_SHARED_TOKEN`), plus its URL and token in `CLOUDFLARE_WORKER_URL` / `CLOUDFLARE_WORKER_TOKEN`. I will not deploy or change production configuration without that instruction.
3. DeepSeek V4.1 Flash needs paid Workers AI access; the smoke will show whether the account has it.
