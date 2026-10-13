# 2C spine 409: diagnosis and proposed fix

Inspected `f8247eb6c2ba4f3befa9e0d9e336f321c9124c51`, 2026-10-13.
Status: diagnosis only; no story/runtime fix applied, no live calls made.

## Cause

The package treats an ordinary contemplated action as secret knowledge.
`transmit the evidence` has **three** leak owners, not just the two plan
reveals: `k_sl_2c_c_r2`, `k_sl_2c_d_r1`, and `k_sl_2c_d_r2`.
The first inherits its guard from `must_convey`; the others explicitly list
it in `leak_terms` (`knowledge.yaml:1702`, `:1744`, `:1791`). The compiler
explains that distinction at `storygame/story_package/loader.py:343`.
These are knowledge phrases, not entity aliases suitable for `scoped_aliases`.

The command really says “transmitting our evidence”
(`frontend/e2e/canon-journey.js:52`). The guard's normalization only folds case
and whitespace (`storygame/runtime/narration_safety.py:285`, `:304`);
an offline check confirms that command does not match `transmit the evidence`.
The reported error establishes a phrase in a validated narration segment,
not verbatim copying of the command. It does not establish the complete reply.

Prompt source: the command is passed into PLAYER (`cloudflare.py:1344`);
the scene supplies transfer orders, captives, a maintenance network and crisis
pressure (`knowledge.yaml:264`). The rules ask the narrator to finish the
player's action (`cloudflare.py:673`). Runtime-owned
reveals are excluded from model candidates (`cloudflare.py:400`), and their
later beat details are withheld unless selected (`cloudflare.py:1047`).
A selected handoff supplies its delivery as lead-up context (`:718`).
Thus the model can paraphrase the player's contemplated transmission without
ever seeing Michelle's plan. The phrase alone does not prove a plan leak.

I assembled and read a synthetic ItemFactsProvider prompt with the 2C entry,
JANUS evidence, archive crisis and Rebecca-offer facts, with no semantic
matcher and no network. It contained the offer, crisis frame and PLAYER
command; no evidence-or-rescue or combined-plan reveal was selected. This
demonstrates a plausible prompt path, **not the exact staging prompt**.
The missing prompt, reply, matcher result and saved facts prevent a claim
about why this particular model sample chose these exact words.

## What was earned

The reported rejection implies `evidence_ready_to_transmit` was not true in
the candidate state. If true, C-R2 is established and exempts the shared term,
even if neither D reveal is earned (`knowledge.yaml:1690`;
`runtime/knowledge.py:314`; `narration_safety.py:100`, `:220`). This passed an
offline guard check. Likewise, an established D owner would exempt it.
This is not an earned reveal being forgotten by bounded recall.

Eligibility is different from earning. Normal 2B exit requires JANUS
evidence (`storylet-routes.yaml:2732`), which satisfies C's prerequisite
(`knowledge.yaml:1687`). D additionally needs the purge and readiness facts
(`:1715`; `storylet-routes.yaml:1704`). Given readiness was absent, D was
not eligible before this turn. The error also shows C was not successfully
committed by this turn's candidate proposal.

The exact matcher misses the supplied “Assess…” action: neither C variant's
verb group includes `assess` (`knowledge.yaml:1633`, `:1677`). A semantic
fallback exists (`cloudflare.py:325`, `:431`), but its live outcome is unknown.
The harness advances the prompt counter after a successful response, not a
specific reveal (`frontend/e2e/scene-runtime.spec.js:88`). Success on prompt 1
therefore does not prove any particular reveal was earned.

The second prompt is entitled to ask about evidence already carried at entry
(`plot.md:531`) and the dilemma in 2C.3 (`:576`). It does not name the secret
office, route or simultaneous broadcast/rescue mechanism. It seeks the cost;
it does not assert that cost is already known. Its weak exact-match wording
is a separate progression concern, not a reason to guard ordinary discussion.

## Smallest source fix

Change only `data/stories/continuity-initiative/knowledge.yaml`:

1. Remove `transmit the evidence` from both D `leak_terms` lists.
2. Give C-R2 an explicit `leak_terms` list containing its existing alias and
   all its existing multi-word `must_convey` terms except that phrase.
   Preserve its `must_convey`, action evidence, statement and delivery text.

Removing it from D alone cannot work: C-R2 still owns the guard. Preserve
`handoffs.yaml` and all reveal prerequisites/effects. This uses the existing
reviewed-leak-vocabulary mechanism (`docs/world-model-grounding.md`, “Review
knowledge leak terms separately”), not a new technique or runtime exception.
It frees the phrase in every scene, including outside 2C. Scoping would not
solve this within-2C collision anyway. No player-text exemption, regex,
narrator rule, retry or fallback is needed.

This is deliberately the minimum fix for the reported phrase. Sibling generic
phrases such as `send the evidence` retain the same authoring risk; review
them on their own merits, rather than claiming this one removal solves all
possible knowledge-guard false positives. Unguarding the phrase does not
validate arbitrary claims that a broadcast actually happened.

Precedents checked: `.plans/world-model.md` section 12 (especially W1/W7),
its 2C handoff/stance fixes at lines 848 and 935, the Astra Phase 4 item 2
scene-vocabulary decision, and the grounding/narrator/player/scene-fixing
guides. They favor corrected material and established leak-term review.

## Hermetic proof and proposed regression tests

Performed without source mutation:

- Current package: synthetic 2C narration “Kristin considers whether to
  transmit the evidence.” rejects before readiness and passes after asserting
  readiness, with no combined-plan fact.
- In-memory application of the exact proposed three-owner edit: the phrase
  passes unearned in 1A and 2C; `Rebecca's secured office` and `maintenance
  access route` still reject in both. This exercises the real compiler and
  segment validator, not the full turn/API path.
- `TMPDIR=/tmp uv run pytest -q --no-cov tests/test_leak_terms.py tests/test_narration_safety.py`:
  **35 passed**. These are existing regressions, not tests of a persisted fix.

Implement regressions in `tests/test_leak_terms.py`: preserve recall/conveyance
indexes while removing all three leak owners; use a stub narrator through
RuntimeEngine to accept contemplated transmission before readiness in 2C
and another scene, with no readiness/plan facts granted; retain rejection and
snapshot rollback for unearned route/office disclosures. Include the current
earned-C/unearned-D acceptance control. Existing synthetic shared-owner tests
cover the story-independent mechanism. Run the package-loader and narration
safety suites too, followed by the deterministic suite per the runbook.

## Live check

Capture a fresh failing pre-turn state and full prompt first. Replay the exact
second 2C prompt above from that same state, **12 samples per arm**, baseline
versus source edit, as the scene-fixing guide's 10–15-sample comparison.
Record matcher selection, earned facts, full prompt, narration and appended
delivery. Read all replies: ordinary consideration must not become a claim
that transmission happened, or disclose the office/route/combined plan early.
Success: zero term rejections in the edited arm, no premature reveals, and
legitimate C handoffs still work. If no baseline reply elicits the phrase,
the live comparison is inconclusive; hermetic evidence still isolates the
guard defect. Identical samples are not independent reliability evidence.

Then run the same journey in three fresh live sessions through 2C to check
progression. Hosted E2E requires the merged SHA's successful main staging
deployment first (`docs/agent-workflow-guide.md`). No live check was run here.
