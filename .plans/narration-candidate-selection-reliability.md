# Narration candidate-selection reliability

## Status

Scoped, not started. Follow-up to `.plans/narration-grounding-citation-reliability.md`,
discovered while re-running `@llm-canon` after that plan's three fixes
(grounding-citation auto-attribution, opening-narration-safety, and the
message-alias collision) all landed and were confirmed live.

## Problem statement

`@llm-canon` was attempted twice against staging (commits `cbc427b`/`fcfc6ae`)
and aborted identically both times at `turn 5: scene 1A at turn 4`, with
`HTTP 409: narration mentions unavailable knowledge 'the card'`. Both
attempts were correctly discarded per the hosted canon judge's own procedure
(the progress artifact showed only 1 scene and 4 turns, far short of the
required nine scenes/30+ turns) — the failure signature is identical both
times, not the documented scene-handoff-timing infrastructure noise.

A direct, local, no-staging, no-Playwright reproduction of the same four
authored Scene 1A prompts plus a fifth repeated prompt — run straight through
`CloudflareTurnProvider`/`RuntimeEngine`, no test harness — reproduced the
identical failure at the identical point, and exposed the real mechanism:

- Turn 1's player input ("Search the kitchen and the back door for concrete
  signs...") already matches the offered `k_sl_1a_a_r1`/`k_sl_1a_a_r2`
  candidates. The model selects nothing.
- Turn 3's player input ("Recover the interrupted message she was recording,
  and listen to whatever survives of it") is a near-verbatim match for the
  then-offered `k_sl_1a_b_r1`/`k_sl_1a_b_r2` candidates. The model still
  selects nothing — instead narrating vague, atmospheric action ("presses
  the volume button, hoping to hear something, anything").
- By turn 4, `selected_knowledge_ids` has been empty and `events` has been
  empty on every turn. The scene has not progressed at all; no reveal has
  committed.
- On the repeated fifth prompt, the model's own narration — which by now has
  spent four turns describing searching, listening, and "checking under the
  drawers" without ever actually earning any of it — drifts into referencing
  "the card" as though a memory card had already been found. It hasn't
  been, according to the canonical fact store. `NarrationSafetyValidator`
  correctly rejects this: the term is genuinely uncommitted, not a
  citation-omission and not a false-positive alias collision, which is why
  neither of this plan's siblings apply here.

**This is not a leak-detection or aliasing problem.** The root cause is that
the model is not reliably using `selected_knowledge_ids` to commit an offered
reveal even when the player's own words are an close match for what a
candidate describes. The story stalls; several turns later, the model's own
free-running narrative sense — which has quietly diverged from the engine's
canonical state precisely because nothing was ever committed — produces a
claim the engine correctly refuses to accept. Fixing the downstream symptom
(another alias rename, another leak-detection tweak) would not address this;
the failure would simply resurface at a different term, a different turn, or
a different scene, because the model's underlying tendency to describe
without selecting is what let the divergence accumulate in the first place.

## Governing constraints (standing project rules, inherited from the sibling plan)

1. **Rule first, then an LLM semantic check, never regex/keyword scanning as
   the fix mechanism.** Already-established for this project; applies here
   too, though see constraint 4 below for why a rule-only fix is a weaker
   candidate for this specific failure than it might first appear.
2. **Every instruction sent to the narrator must read at an 8th-grade
   level.** Any rule change (existing selection rules or a new one) must stay
   short, concrete, one idea per sentence.
3. **A prompt change belongs everywhere a path narrates**, not just the path
   that happened to fail first — turn rules, the opening's own rule list, and
   the recovery hint all build instructions independently.
4. **Prefer a deterministic, code-level mechanism over a prompt appeal when
   one exists or can be built**, per this project's own recent, direct
   evidence: the sibling plan's prompt-only attempt at a related compliance
   problem (citation) was bench-tested live and measurably failed, while the
   deterministic auto-attribution mechanism that replaced it worked
   immediately and needed no model cooperation. Any fix proposed here should
   be judged against that same bar, not assumed reliable because it "should"
   work.
5. **Live E2E/staging calls are billed and external.** Iterate locally via
   `bench` and/or direct `CloudflareTurnProvider`/`RuntimeEngine` calls (as
   demonstrated in this plan's own reproduction) before spending
   staging/Playwright/OpenAI-judge calls.
6. **Do not fix the downstream symptom.** A new alias rename or a broadened
   leak-detection exception for "the card" would make this specific
   reproduction pass without addressing why the model stalled for four turns
   first. Any accepted fix must demonstrably make the model select an
   offered, clearly-matching candidate more reliably — not just make the
   eventual drift-narration pass validation.

## What is already known (do not re-derive)

- `storygame/runtime/cloudflare.py`'s `_turn_rules()` already carries several
  selection-duty rules: "Pick at most one candidate. Put its ID in
  selected_knowledge_ids.", "If you pick a candidate, tell it in one
  paragraph, and put its ID in that paragraph's grounding_ids.", "Do not
  pick a candidate that has no text to tell.", "If no candidate fits what
  just happened, leave selected_knowledge_ids empty.", "If you tell a
  candidate but do not pick it, the story gets stuck." That last rule
  literally names the failure mode this plan is investigating and the model
  still exhibits it — so the existing rule wording is demonstrably
  insufficient on its own, at least in this reproduction.
- The candidates ARE present in the prompt with a player-safe statement and
  their own id (confirmed via direct inspection of
  `KnowledgeProjector.project(...).candidates` at each turn in this plan's
  reproduction) — this is not a missing-information problem the way the
  citation issue was. The model has everything it needs to select correctly
  and does not.
- This is not 100% reproducible on every attempt — earlier staging evidence
  in `docs/testing-runbook.md`'s Phase 3 section records a successful
  `k_sl_1a_b_r2` selection on a different run. The failure is a reliability
  problem (how often the model selects correctly on a clear match), not an
  absolute one (the model is never capable of selecting).

## Phased implementation

### Phase 1: Measure the actual selection rate

- [ ] Using `bench` (fix `bench/core.py`'s `DEFAULT_PROMPT_RULES` staleness
  first if it gets in the way of an accurate preview — see the deferred note
  in the sibling plan — or work around it as that plan did, by always fully
  specifying `rules` in any experimental variation).
- [ ] Add a bench variation and script reproducing this plan's exact
  four-prompt Scene 1A sequence (reuse `bench/variations/grounding-citation-baseline.json`
  as a shape reference; a new file, since the script here is different).
- [ ] Run it for several replicates (four per the tool's own default
  guidance, more if the first four are inconclusive) and record, per turn,
  whether the model selected the candidate a reasonable reading of the
  player's input would expect. This may require a manual/LLM-judged
  per-turn label rather than a purely mechanical one, since "did this input
  clearly match this candidate" is a judgment call — but keep the
  measurement itself (selected vs. not, per turn, per replicate) mechanical
  and logged, not just narrated in prose.
- [ ] Establish a baseline selection rate on this exact script before
  proposing any fix. Do not skip straight to a fix based on a single
  four-turn anecdote (this plan's own reproduction), however suggestive.

Exit gate: a baseline selection-rate measurement exists for the reproducing
script, from more than one replicate, so a later fix's effect can be
compared against a real number rather than one lucky or unlucky run.

### Phase 2: Diagnose why the rule is not landing

- [ ] With the baseline established, inspect what varies between a replicate
  where the model selects correctly and one where it does not (same script,
  same candidates, same rules) — is it something about how the candidate's
  `statement`/`must_convey` reads, ordering in the prompt, the length of the
  CONSTRAINTS section, or genuinely just sampling variance in a small model
  with no legible cause?
- [ ] Consider, per constraint 4, whether a deterministic mechanism can
  reduce reliance on the model's own selection judgment at all for a clearly
  unambiguous case, analogous to how `derive_grounding`/`derive_statement_grounding`
  already exist for a related bookkeeping gap — for example, detecting when
  a segment's text unambiguously conveys a currently-eligible candidate's
  `must_convey` groups but the model left `selected_knowledge_ids` empty, and
  deciding whether auto-selecting is safe here the way auto-grounding was
  safe for the citation case. Weigh this carefully: auto-*selecting* a
  reveal is a bigger, more consequential inference than auto-*grounding* an
  already-committed mention, since it would newly commit canon rather than
  just labeling prose that was already going to render. Do not build this
  without being explicit, in the writeup, about what makes it safe or why it
  is not.
- [ ] If a rule-wording change looks promising instead (or in addition),
  design it and hold it to the same bench-measured bar as Phase 1's
  baseline — a wording change is not accepted on "it should be clearer,"
  only on a measured improvement over the baseline selection rate.

Exit gate: a specific, evidence-backed hypothesis for why the model
sometimes fails to select a clearly-matching candidate, and one candidate
fix (rule wording, a deterministic mechanism, or both) ready for Phase 3
validation.

### Phase 3: Validate and land

- [ ] Bench-validate the candidate fix against the Phase 1 baseline, same
  discipline as the sibling plan: enough replicates to be distinguishable
  from noise, and a check for regressions on at least one other scene/script.
- [ ] If validated, land the fix, audit every prompt-constructing path it
  touches (per constraint 3), and re-run `@llm-canon` against staging,
  deleting stale artifacts first and confirming a complete nine-scene,
  30+-turn run before recording it as evidence, discarding and retrying an
  aborted attempt exactly as the hosted canon judge's procedure requires.
- [ ] Record the real result in `docs/testing-runbook.md`'s Phase 5 section
  and update `.plans/fact-backed-knowledge-projection.md`'s Phase 5 exit gate.

Exit gate: `@llm-canon` completes a full nine-scene run against staging
without this specific stall-then-drift pattern recurring, with a measured
selection-rate improvement over the Phase 1 baseline as the evidence, not
just the absence of one failing run.

## Explicitly out of scope

- **Renaming or excepting "the card" or any other term this specific
  reproduction happened to surface.** That is the downstream symptom, not
  the cause, per constraint 6.
- **An automatic retry when the model fails to select.** Same reasoning as
  the sibling plan's equivalent exclusion: fix the underlying reliability
  before adding machinery that papers over it.
- **Production promotion.** Out of scope by the same standing decision as
  the sibling plan.

## Verification commands

```bash
# Local, free, no model calls:
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench prompt --scene 1A --text

# Local, billed (small model, low per-call cost):
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench run --variation <this-plan's-variation> --replicates <n>
/home/bcorfman/dev/freytag-forge/.venv/bin/python -m bench compare <baseline-name> <candidate-name>

# Full repo suites before any PR:
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
cd frontend && npm test && npm run build

# Staged, billed, external (Phase 3 only, after merge + exact-SHA redeploy):
rm -f artifacts/e2e-llm-canon.json artifacts/e2e-llm-canon-progress.json artifacts/e2e-llm-canon.md artifacts/e2e-llm-canon-progress.md
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon
```
