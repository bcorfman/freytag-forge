# Narration grounding-citation reliability

## Status

Scoped, not started. Follow-up to the Phase 5 staged rollout finding recorded
in `docs/testing-runbook.md`'s "Phase 5 knowledge leakage matrix and staging
rollout" section (2026-09-11) and in
`.plans/fact-backed-knowledge-projection.md`'s Phase 5 exit gate, which
remains unmet because of this.

## Problem statement

Staging `@smoke` and `@safety|@npc` fail deterministically against the live
Cloudflare-hosted narrator. The player's first Scene 1A turn ("Look carefully
at Michelle's phone.") gets narration that mentions Michelle's phone, but the
live model does not put the phone's knowledge ID in that segment's
`grounding_ids`. `NarrationSafetyValidator` correctly rejects the turn with
HTTP 409 (`uncited_knowledge`) — this is the deterministic multi-word
known-term check in `storygame/runtime/narration_safety.py` doing exactly
what it was built to do. A local check confirms the ID was available to cite
(`k_scene_1a_entry`, whose own statement already mentions the phone) — the
model had a valid citation and did not make it.

This is not a knowledge leak, and it is not a Phase 5 code defect: nothing in
Phase 5 touched `narration_safety.py`, `cloudflare.py`, or the package's
`knowledge.yaml`. It looks like the first time this specific deterministic
check — added in the Phase 4 merge — has run against real live model traffic;
Phase 3 and 4's own staged evidence used a test-only deterministic provider.

**Player impact if left unfixed:** `RuntimeEngine.turn()` does not retry a
`ProposalValidationError` the way the provider retries a malformed JSON
response — it restores the pre-turn snapshot and re-raises immediately
(`storygame/runtime/engine.py`, the `except (ProposalValidationError,
RuntimeContractError)` block). A narration-safety rejection is therefore
terminal for that turn: the player sees an error and loses the turn outright,
not a graceful retry. If the live model is unreliable about citing grounding
for material as basic as an item the player just asked to look at, this is a
frequent, not edge-case, failure mode in real play.

## What is already known (do not re-derive)

- `storygame/runtime/cloudflare.py`'s `_turn_rules()` (`default_rules`) already
  tells the model **which** IDs it may put in `grounding_ids` — "In
  grounding_ids, use only an ID you were given as known, or the one candidate
  you picked" — and how to cite a **newly selected candidate**. It has no rule
  telling the model it **must** cite the ID of something already-known that it
  chooses to mention. That is the missing duty.
- A prior attempt to teach grounding via a worked example in the system
  prompt made things worse, not better — the file's own comment records it:
  "a live sample went from no failures in sixteen turns to six in eighteen -
  five of them HTTP 409 for grounding on knowledge that was neither committed
  nor selected." Any new rule must be validated empirically against a live
  probe before it ships, not merely reasoned about.
- `bench` (`bench/core.py`, `bench/cli.py`) is a local, dev-only harness that
  runs turns through the *same* Python runtime and Cloudflare narrator as the
  app, and can reproduce this failure cheaply without a staging deploy. But it
  currently only catches `NarrationProviderError` around `engine.turn(...)`
  (`bench/core.py` ~line 580) — a `ProposalValidationError` from
  `NarrationSafetyValidator` is **not caught** and will crash a `bench run`/
  `chat` replicate instead of recording a `failed` ledger row. This must be
  fixed first, or the fix cannot be measured locally.
- `bench compare` already does the statistically-careful thing (Welch t-test,
  minimum detectable effect, several-replicates requirement) for the
  canon-judge score. The hosted canon judge's own procedure notes that
  within-arm variance can be as large as between-arm gaps for this project's
  live model — the same caution applies to any new rejection-rate metric this
  work adds, not just the existing 63-point score.

## Governing constraints (standing project rules, inherited, not re-litigated)

1. **Rule first, then an LLM semantic check, never regex/keyword scanning as
   the runtime mechanism.** The deterministic term-scan in
   `narration_safety.py` is the accepted structural boundary already. This
   task is about getting the model to comply with it via a better
   instruction, not adding more scanning.
2. **Every rule sent to the narrator must read at an 8th-grade level:** short
   common words, one idea per sentence, name the concrete thing rather than
   describe a category. A compound rule joined by "and" reliably loses its
   second half.
3. **A prompt change belongs everywhere a path narrates**, not just the path
   that happened to fail first: turn rules, the opening's own rule list, the
   system prompt, and the malformed-response recovery hint all build
   instructions independently and can drift apart.
4. **Prefer removing a mechanism over adding an instruction, when a removable
   mechanism is the actual cause.** Before adding a new rule, this task must
   check whether the existing restrictive framing ("use only an ID you were
   given as known...") is itself pushing the model to hedge away from citing
   an ID it is unsure about, and whether simplifying it helps more than
   layering a new rule on top. Do not do both blindly — bench evidence decides.
5. **Live E2E/staging calls are billed and external.** Iterate locally via
   `bench` first; spend staging/Playwright/OpenAI-judge calls only to confirm
   a bench-validated change, not to explore.

## Phased implementation

### Phase 1: Make the failure measurable locally

- [x] In `bench/core.py`, catch `ProposalValidationError` (and
  `RuntimeContractError`, the sibling exception `RuntimeEngine.turn()` raises
  the same way) around both `engine.opening()` and the turn loop's call, the
  same way `NarrationProviderError` is caught, and record a `failed` ledger
  row with `failure_reason` carrying the validator's `.code` (e.g.
  `uncited_knowledge`) via a fallback in `_failed_scene_record`. Added a
  deterministic unit test proving this with no live call. Landed in commit
  `729fb0502fe9ef4e5f2e388f433b0fdfb2a3f332`.
- [x] Reproduced the staging finding locally and cheaply via
  `bench run --variation bench/variations/grounding-citation-baseline.json
  --scene 1A --replicates 1 --confirm`: the resulting ledger row is
  `status: "failed"` with `failure_reason: "uncited_knowledge: narration
  does not ground the knowledge term 'michelle's phone'"` — the exact
  staging failure text, for 22 Workers AI neurons. Model confirmed as
  `@cf/meta/llama-3.1-8b-instruct-fast`.
- [x] Added the reproduction as `bench/variations/grounding-citation-baseline.json`
  (Scene 1A, script `phone-grounding-repro`, shipped default rules
  unmodified) so it reruns identically for every candidate rule in Phase 2.

Exit gate: met. A `bench run` replicate against the shipped, unmodified rules
produces a `failed` row whose `failure_reason` reproduces the staging
`uncited_knowledge` rejection verbatim, using only local/dev-cost calls (no
staging deploy, no Playwright).

### Phase 2: Design and bench-validate a fix

**Root cause refined, 2026-09-11, before any candidate was built.** Reading
`CloudflareTurnProvider._section_user_prompt` in `storygame/runtime/cloudflare.py`
shows the actual bug is not primarily a missing instruction: a candidate
reveal already gets its `id` embedded directly in its own sentence ("...put
{candidate['id']} in selected_knowledge_ids."), but committed knowledge is
rendered into the SCENE section as bare prose with no id at all —
`scene.append(item["statement"])`. The model is never shown which ID
corresponds to "Michelle's phone is on the kitchen floor"; no rule wording,
however well phrased, can make it cite an identifier it was never given. This
also means a pure prompt-rule fix cannot be bench-validated through a
variation's `system_prompt.rules` override alone, because `_section_user_prompt`'s
committed-knowledge rendering is not currently variation-configurable — the
fix requires a small, reversible code change to make it so, done once as
infrastructure, so every subsequent wording iteration stays a pure JSON
variation with no further Ringer round-trips.

**Also discovered, deferred, noted so it is not silently trusted going
forward:** `bench/core.py`'s `DEFAULT_PROMPT_RULES` constant (used by
`bench describe`/`bench prompt` when a variation does not override rules) is
stale — it holds an older experimental wording (matching
`bench/variations/arm-a.json`), not the rules `cloudflare.py` actually ships
today. Actual `bench run`/`chat` behavior is unaffected (it reads the live
`CloudflareTurnProvider._turn_rules()` default when a variation's `rules` is
unset), but `describe`/`prompt` previews are misleading for that case. Worked
around in this task by always fully specifying `rules` in every experimental
variation rather than relying on the unset-default preview. Fixing
`DEFAULT_PROMPT_RULES` itself is a small, separate, low-priority follow-up,
not required to complete this task.

- [ ] Add one new `system_prompt` variation key, e.g.
  `cite_committed_knowledge_ids: bool` (default `false`, so today's shipped
  behavior and the Phase 1 baseline variation are both unchanged unless a
  variation opts in). When true: (a) `_section_user_prompt` renders each
  committed-knowledge SCENE line with its id visible, mirroring the existing
  candidate pattern rather than inventing a new format — for example
  `f"{item['statement']} ({item['id']})"`; (b) exactly two new rule sentences
  are appended (regardless of whether `default_rules` or a variation's own
  `rules` override is in effect, the same way `_owner_rules()`/`_placement_rules()`
  are always appended today), each one short idea at an 8th-grade level, for
  example in spirit: "Some SCENE lines end with an ID in parentheses." /
  "If you write about that line, put its ID in grounding_ids." Wire this
  variation key through `bench/core.py`'s `resolve_variation`/`_prompt_variant`
  so it is bench-testable without further code changes.
- [ ] Add `bench/variations/grounding-citation-candidate-1.json`: same Scene
  1A `phone-grounding-repro` script as the Phase 1 baseline, shipped default
  rules (no `rules` override, so the new sentences land on the real
  `default_rules`), with `cite_committed_knowledge_ids: true`.
- [ ] Using `bench describe`/`bench prompt --variation ... --text`, confirm
  the resolved SCENE section actually shows the parenthetical id and the two
  new rule sentences appear, before spending a model call.
- [ ] Run the baseline and candidate-1 variations for several replicates each
  (`bench run --replicates N`, default four per the tool's own guidance) on
  the reproduction script, and on at least one other scene/script the shipped
  rules already cover, to check for regressions elsewhere.
- [ ] `bench compare` the two arms on both the existing 63-point canon-judge
  score and the rejection-rate signal Phase 1 made measurable. Require enough
  replicates per arm to be distinguishable from noise per the tool's own
  Welch-test/minimum-detectable-effect output; do not report a one- or
  two-run difference as conclusive.
- [ ] If candidate-1 does not measurably help, iterate on the two rule
  sentences' wording only (a pure JSON change, no further code edit needed
  now that the structural id-exposure is variation-configurable) before
  concluding the structural fix itself was insufficient.

Exit gate: one specific combination (id-exposure plus rule wording) is
selected with bench evidence that it measurably reduces the
`uncited_knowledge`/`narration_known_term_leak` rejection rate on the
reproducing script, does not regress the canon-judge score, and introduces no
new failure code, across enough replicates to be distinguishable from noise.

### Phase 3: Land the fix and re-verify live

- [ ] Make the validated combination unconditional in the shipped code path:
  either flip `cite_committed_knowledge_ids`'s default to `true` and keep the
  variation key only for a future A/B (documented as no-op for the shipped
  provider), or remove the flag and make id-exposure plus the two rule
  sentences the only behavior, per this project's stated preference against
  leaving unused feature-flag branches around once a decision is made. Do not
  leave the fix reachable only through a bench variation.
- [ ] Audit every other prompt-constructing path — `_system_prompt()`, the
  opening's own rule list, and `_recover_malformed_response`'s retry hint —
  for whether the same missing-id gap applies there too (an opening segment
  can also name already-established knowledge without ever having been shown
  its id). Apply the same fix wherever it is needed; do not leave the turn
  path fixed while the opening path still drifts, per constraint 3.
- [ ] Deploy to staging (merge to `main`, wait for the exact-SHA redeploy, per
  this project's standing procedure) and re-run the exact gates that first
  caught this: `@smoke`, then `@safety|@npc`. Only after those pass, run
  `@llm-canon` for the full spine.
- [ ] Record the real observed result in `docs/testing-runbook.md`'s Phase 5
  section (or a new dated entry there), following the same no-fabrication
  discipline as the original finding: discard and retry an
  infrastructure-aborted `@llm-canon` run rather than record it, per the
  hosted canon judge's own procedure.
- [ ] Update `.plans/fact-backed-knowledge-projection.md`'s Phase 5 exit gate
  and phase evidence to reflect the real, now-passing (or still-blocked)
  outcome.

Exit gate: `@smoke` and `@safety|@npc` pass against staging with the new
rule; `@llm-canon` completes with no new or worse uncited-grounding rejection
pattern than the 2026-08-31 baseline; the Phase 5 exit gate in the knowledge
projection plan can be marked met, or the remaining gap is stated precisely
if it cannot.

## Explicitly out of scope

- **Adding an automatic retry when narration safety rejects a turn.** The
  project's own fix-ranking prefers curing the model's non-compliance over
  adding machinery that papers over it. If Phase 2's bench evidence shows no
  rule wording gets the rejection rate low enough, a retry-on-rejection
  design is a legitimate fallback to propose then — but only after the
  cheaper, root-cause fix has actually been tried and measured, not before.
- **Production promotion.** Out of scope for this task by the same standing
  decision that scoped it out of Phase 5.
- **Touching `world.protected_knowledge`, the knowledge catalog schema, or
  any Phase 1-5 runtime contract.** This task is a prompt-instruction fix
  plus a bench measurement gap fix; it does not change what the engine
  validates, only what the model is told.

## Verification commands

```bash
# Local, free, no model calls:
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --scene 1A --text

# Local, billed (Cloudflare Workers AI is the inference budget — small model, low per-call cost):
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench chat --variation bench/variations/grounding-citation-baseline.json
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation <baseline-or-candidate> --replicates <n>
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare <baseline-name> <candidate-name>

# Full repo suites before any PR:
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
cd frontend && npm test && npm run build

# Staged, billed, external (Phase 3 only, after merge + exact-SHA redeploy):
source .env && cd frontend && npm run test:e2e -- --grep @smoke
source .env && cd frontend && npm run test:e2e -- --grep "@safety|@npc"
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon
```
