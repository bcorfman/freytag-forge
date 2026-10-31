# T9h stage 2 diagnosis and proposed next checks

Status: diagnosis complete; proposals only. Written 2026-10-30 (America/New_York).
No implementation or story change, model call, resampling, deployment, or historical
artifact edit was made. The existing working tree already contains substantial
uncommitted work. This document does not approve that work or change its status.

Resume here: review the measurement corrections below first. Preserve stage 2 as
FAIL. Do the free harness and composition checks before deciding whether to
commission a separately registered integration smoke or a material probe. Every
proposed plot edit below requires Brandon's approval before application.

## Finding

The two failed gates do **not** establish that hidden-clue recovery is broken.
P1a counts three labels that conflate a lack of visible clues with an empty
underside. P1b measures narrator lead-up while omitting the delivery the narrator
was explicitly told the game would append. Neither finding justifies changing
the discovery earning statement or asking the narrator to perform the recovery.

There are real prose concerns: lifting language, unsolicited/recollected Brandon
speech, premature use of his name, and one explicit reference to “the story.”
The experiment also has a contaminated P0 control and does not exercise the
full world-aware narration path. These limits prevent treating its results as
an end-to-end success or a causal estimate of the package change.

## Evidence and reproducibility

Paths below are repository-relative. Abbreviations:

- `prose/` = `bench/results/environment-narration/t9h-hidden/prose/`.
- `probe/` = the adjacent `probe/` directory.
- `scorer` = `scripts/ringer/environment_narration/hidden_bench_prose_probe.py`.
- `prereg` = `.plans/grounded-llm-environment-narration/t9h-hidden-clues-prereg.md`.

Read the six recorded payloads, the 60 replies, labels and blind key, freeze,
reports, Worker log, scorer and tests, all six story diffs, narration composition,
and smoke reporting. The labels file's SHA-256 was recomputed read-only and
matches both freeze and report:
`76559b6f7db42eaabb09445993bfa31c0a2dd9ef5f7e2ccfdebd7c79152bc1a3`.
This establishes file consistency, not independent proof of when the labels
were frozen or that their author remained blind. The sheet hides arm labels;
the prose itself makes some arms readily recognizable.

`prose/report.md:3–9` records 60/60, P1a FAIL, P1b FAIL, P1c PASS.
`prose/worker.log:3–62` records 60 successful narration requests;
line 63 records 38,796 micro-USD ($0.038796). `rows.json` has no stop reason.
This was not a quota, truncation-of-run, or missing-samples failure.
`probe/report.md:5–9` records M1–M5 passing: both underside inputs select D
10/10, neither selects E, near-miss bench actions never select D, and guessed
photo/drain actions select nothing. This qualifies the sampled semantic earning
boundary, not recovery composition or accepted world state.

The following are **frozen label counts**, not corrected scores:

| Label | P0 opening | P0 pre-find | P0 find | P1 opening | P1 pre-find | P1 find |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| names_clue_object | 10 | 10 | 0 | 0 | 0 | 0 |
| describes_photograph_content | 9 | 9 | 0 | 0 | 0 | 0 |
| states_route_or_identity | 0 | 0 | 0 | 0 | 0 | 0 |
| claims_nothing_under_bench | 0 | 0 | 0 | 2 | 1 | 0 |
| moves_fixed_bench | 0 | 0 | 9 | 0 | 0 | 3 |
| conveys_all_three_objects_and_keeping | 0 | 0 | 0 | 0 | 0 | 0 |
| invents_fourth_object | 0 | 0 | 9 | 0 | 0 | 0 |

### P1a: a label-definition failure, not evidence of an empty underside

The three offending rows are:

| Blind ID / payload / sample | Exact relevant prose | Artifact |
| --- | --- | --- |
| sample-033 / p1-opening / 3 | “no obvious clues or markings”; immediately followed by “perhaps hidden from view” | `prose/rows.json:108`; `sheets.md/labels.json:290`; `blind_key.json:226`; `blind_sheet.md:261` |
| sample-021 / p1-opening / 10 | “no obvious clues or markings”; wonders whether something is nearby or the bench is significant | `prose/rows.json:164` |
| sample-034 / p1-prefind / 9 | “no visible signs of disturbance or clues”; then tries “to get a better look at the space beneath it” | `prose/rows.json:316`; `sheets.md/labels.json:299`; `blind_key.json:233`; `blind_sheet.md:269` |

None says the underside is empty. The first expressly allows hidden material;
the third says the inspection beneath is still pending. These are compatible
with hidden objects. They may be unhelpful guidance, but “15% false emptiness”
is not supported. The gate itself (`prereg:58–59`) specifies the space under
the bench; the labels broadened that to visible clues on the bench. The report
simply ORs those booleans (`scorer:403–415`). A stricter-sounding label is not
necessarily a more accurate one.

The opening payload (`capture.json:17`) provides an ordinary bench and a search
objective, without the later pointer. This plausibly elicits generic inspection
prose; the experiment does not isolate that cause. The pre-find payload already
contains the safe underside pointer (`capture.json:31`), which the sheet omits
as an appended segment. Do not add an “underside is not empty” rule or reveal
hidden things to cure these labels. Reassess guidance separately from truth.

### P1b: wrong scoring unit

`capture.json:45` gives the complete discovery delivery followed by:

> Write only what leads up to it. Do not have Kristin find anything else.

The supplied delivery is:

> Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence and Michelle's photograph. She keeps all three with her.

`storygame/runtime/cloudflare.py:885–893` constructs that instruction;
`:1456–1496` appends the delivery as a narration segment, grounds it to the
selected candidate, and selects that knowledge. The scorer calls `_request`
directly and stores its response (`scorer:234–264`); the sheet displays only
`response_text` (`:313–320`). It never runs the returned response through the
composition step for scoring. All ten P1 find replies (`rows.json:407–484`)
obey the division of labor by stopping before recovery. The original plan
explicitly required scoring the delivery too, as does
`docs/scene-fixing-guide.md:24–27`.

Appending the recorded delivery would supply all three objects and custody
in every one of the ten examples. That is a textual counterfactual, not ten
accepted game turns, and not a revised stage pass. Full validation, effects,
rollback, and rendering were bypassed in the billed replay. Other prose faults
remain in the lead-up after composition.

### P1c and the remaining labels

P1c's zero fourth objects is supported for these P1 replies. P0 find invents
paper/note/receipt material in nine replies (`rows.json:332–404`), including
“Meet me at the old oak” and an invented midnight meeting. P0 find receives
neither a discovery handoff nor the synthetic clue list (`capture.json:38`).
Its object inventions are real model output, but “fourth” is an awkward label
when no first three are presented in that frozen find state. Do not add them
to canon or treat notes as recovered number sequences by keyword matching.

The zero P1 clue-name labels accurately describe narrator text before the
delivery. Zero photograph-content labels are also supported. P0's 18 content
labels mostly concern “a photograph of Michelle”; sample-023's “Shelly's
picture” is ambiguous ownership rather than a clear description of its image
(`rows.json:44`). Do not report all 18 as elaborate invented photo content.
There are unmistakable inventions too, e.g. a serious expression (`:52`),
a recent photo/background (`:212`, `:244`), and invented digits (`:228`).

Zero `states_route_or_identity` does **not** mean no name exposure. P1 find
sample 1 directly narrates “Brandon Corfman” watching and speaking
(`rows.json:412`), as do other rows. The prompt supplies his full biography
and the named talk permission (`capture.json:45`). These rows do not establish
the plot relation between the follower and the photo, but they do name him to
the reader. A future rubric must distinguish a route/face/identity revelation
from premature narrator naming; the current combined boolean obscures this.

The three fixed-bench labels are also overcompressed:

- sample-010 / p1-find 2 (`rows.json:420`, labels `:83`): “reaching out to lift
  the edge of the bench **or** peer into the space beneath it.” This is an
  unresolved alternative, not an accomplished lift.
- sample-018 / p1-find 6 (`rows.json:452`, labels `:155`): hands “reaching out
  to lift the edge of the seat.” An attempted/preparatory action, not a stated
  changed final bench location.
- sample-050 / p1-find 8 (`rows.json:468`, labels `:443`): hand “reaching out
  to lift the edge of the bench,” then peering underneath. Suggestive lifting
  language, but no explicit final displacement.

These are genuine undesirable action proposals for an ordinary underside
look. Report **three lifting-language cases**, not three proven world moves.
The gate overlooks them because P1a covers only opening/pre-find and P1b
does not check bench movement. `world.yaml:201–206` already declares the bench
fixed. `capture.json:45` says only “ordinary park bench”; it gives no fixed
property. Missing material is a plausible contributor, not a measured cause.

P1 find 9 (`rows.json:476`) says “the story doesn't reveal what it is yet.”
The handoff instruction is plausibly being echoed as meta-narration. Brandon
also warns or refuses on unaddressed turns and in invented recollection
(`:412`, `:428`, `:460`, `:476`, `:484`). The source
`knowledge.yaml:3115–3121`, `k_1b_stranger_evasion`, supplies unconditioned
sayable dialogue, whereas `plot.md:216` conditions it on Kristin speaking to
him. This is a material/scope mismatch worth probing; no causal isolation was
performed. It is not a reason to erase his legitimate response to a question.

## Experimental validity limits

1. **P0 is altered after capture.** `scorer:113–121` adds
   `LEGACY VISIBLE BENCH OBJECTS:` and the three names to P0 opening/pre-find.
   The injected text is visible at `capture.json:10,24`. Thus the 20/20 P0
   exposures cannot be attributed solely to the HEAD package. The test
   `test_head_control_retains_the_old_clue_names` entrenches that contamination
   by asserting names rather than request fidelity. P1's zero exposure is a
   useful observation, but this is not a clean old/new treatment comparison.
2. **Synthetic start and independent states.** `scorer:68–80` bootstraps,
   assigns scene 1B, moves Kristin onto `park_bench`, and activates every 1B
   storylet. Each payload starts fresh (`:102–111`); find is not the second
   turn after the recorded pre-find. There is no faithful 1A journey prefix.
   Caption these as synthetic request snapshots, not Route E checkpoints.
3. **Incomplete provider path.** Construction uses bare
   `CloudflareTurnProvider` (`:104`), not the world-context capture stack.
   None of the six payloads contains THINGS. The world-aware provider renders
   that block in `storygame/runtime/item_facts.py:463–500`. Its optional fixed
   marker is also outside this capture. The preflight cannot prove hidden-item
   filtering of a block that was never generated. Do not compensate by
   injecting a hand-built visible list into either arm.
4. **No composed or validated result.** Neither pointer nor find delivery,
   opening entry/cues, state delta, item-facts capture, nor guard acceptance is
   represented by the raw reply alone. The request path is real transport;
   that does not make it the complete game-turn path.
5. **Rubric omissions.** No separate face label, attempted-lift distinction,
   premature-name label, irrelevant dialogue label, or meta-prose label exists.
   P1b excludes route/identity but not photograph content or fixed movement.
   The tests manufacture booleans over “A quiet bench scene.” They verify
   arithmetic and hash checking, not the meaning of the scoring unit.

## Proposed changes, in priority order

These are reviewable specifications, not applied edits. No regex or semantic
parsing of narration is proposed. Use the existing typed response boundary,
runtime composition, facts and human prose labels. Never extract delivery
text from a prompt string or infer committed facts from narrator sentences.

### A. Correct measurement before touching the story

Remove the P0-only augmentation at `scorer:113–121` in its entirety. Exact old
rendered block (P0 opening/pre-find only):

```text
LEGACY VISIBLE BENCH OBJECTS:
- Transit token
- Michelle's photograph
- handwritten number sequence
```

New: absent. Capture the real provider stack for both packages from equivalent
journey checkpoints, including preparation, THINGS, and opening/turn composition.
Record typed delivery/cue segments separately alongside the untouched raw reply
and complete proposed/accepted player text. This restores existing mechanisms;
the new harness plumbing has not been implemented or qualified.

In a **new** registration only, replace the scoring instruction:

Old: “Labels are written by Claude from the narration text, blind to arm, with a frozen hash before the join.”

New: “Label the complete player text, including runtime delivery and cue segments. Keep the narrator text and engine text separately visible. Label proposed text separately from accepted text. Hide arm identifiers. Freeze the labels before joining them to the arms.”

Old label: `claims_nothing_under_bench` with no explanatory rubric.

New rubric: “True only when the text says the space beneath the bench is empty or contains nothing. A lack of obvious or visible clues does not establish this. Record uncertainty separately.”

Old label: `moves_fixed_bench`.

New rubric: “Record an attempted lift separately from a completed lift. Record a final changed place separately from both. Score prose independently of captured world changes.”

Old P1b wording is `prereg:60–61`. New proposed wording:

> At least 9 of 10 complete find-turn texts convey the three declared objects and Kristin keeping them. No complete find-turn text reveals the route, the photograph's contents, or the man's identity before its separate earning action. Report premature naming separately. No opening, inspection, or find text invents an extra clue or has Kristin attempt to lift the fixed bench. Record meta-narration and unsolicited dialogue separately.

These are new measurement criteria, not a reinterpretation of the frozen gate.
Retain the original report and labels unchanged. A free annotated reread can
be saved separately and explicitly marked post hoc; it cannot reopen the chain.

Cheapest free check: two scoring views (raw/composed), all 60 existing rows,
120 human review views, $0; use the actual composition helper for the 20 P1
pointer/find cases, and distinguish inferred composition from accepted turns.
Then two packages × three checkpoints = six faithful stubbed captures, $0,
with raw request byte comparison. Cheapest billed check for the **measurement
repair itself**: zero calls. It is deterministic plumbing. If a fresh comparison
is later wanted, two authentic arms × three states × ten = 60 calls, estimated
$0.039–$0.042, ceiling $0.06, newly registered; it is not a stage-2 rerun.

### B. First material candidate: expose the bench's existing fixed property

Only after faithful capture confirms the information is still missing, propose
this **PLOT CHANGE — Brandon approval required** to `plot.md:204`:

Old:

```text
**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols
```

New:

```text
**Details:** The park bench is fixed in place.; damaged grounds; service path; checkpoints; emergency patrols
```

This replaces one detail with a concrete existing world fact; it adds no place,
object, bolt, compartment or new axis. `park_bench` is already uniquely declared,
scoped as “bench,” placed in the park and fixed. This uses the proven approach
of supplying missing material through existing Details, not a new narrator rule.
**This particular wording is new and unmeasured.** Do not change D's delivery,
knowledge, or handoff to demand that the narrator recover the items itself.

Free: baseline/candidate × opening, inspection, find = six stubbed captures,
$0; real loader and authoring lint; check that only the approved detail changes,
hidden names remain absent before discovery and the delivery stays exact.
Billed: one fresh baseline arm and one replacement-detail arm, ten find samples
each = 20 narration calls, estimated $0.013, ceiling $0.02. Score completed
player prose, attempted/completed lifts separately, identity exposure, extra
objects and meta-prose. Use a new Ringer preregistration. A winning result is
still followed by integration; this ten-sample screen proves no general rate.

### C. Remove distracting material in a diagnostic arm before adding rules

For the unsolicited dialogue hypothesis, an isolated recorded-prompt probe may
remove exactly this existing line (`capture.json:31,38,45`):

Old:

```text
- Brandon Corfman may say this aloud: I won't tell you that. Keep your voice down; patrols are nearby.
```

New: absent **on the non-dialogue diagnostic arm only**. Do not remove the
CHARACTERS biography simultaneously: that would mix two causes. This is the
existing scene-fixing technique of removing a conflicting talk line, used in
earlier scene diagnosis. The proposed arm is new and has not won a probe.

No production knowledge/handoff edit is specified yet. Global `voiceable: false`
would also remove the legitimate response when Kristin speaks to him. If the
removal arm wins, first verify an existing supported scope for the conditional
line; otherwise return a separate proposal for that gap, explicitly marked new.
Any subsequent plot, knowledge or handoff change is a **PLOT CHANGE** requiring
approval. Do not quietly implement a story-specific runtime condition.

Free: baseline/removal × inspection/find = four payload comparisons, $0.
Billed: baseline/removal × ten find samples = 20 calls, estimated $0.013,
ceiling $0.02; read dialogue, name exposure and action completion. This is
optional and lower priority than faithful capture and integration. If combined
with B in one experiment, share a fresh baseline: three arms × ten = 30 calls,
estimated $0.020, ceiling $0.03; do not combine the two interventions in one arm.

No rule is proposed for false emptiness, no generic single-word leak guard is
proposed, and no prompt change is yet justified for the single meta-prose case.
Observe it under faithful material first. A global rule would require a winning
story-neutral probe and coverage of all narrator paths named in the writing guide.

### D. Align the runbook and smoke reporter with their contracts

The existing runbook's section 3 says:

Old: “For an authored-handoff turn it contains no candidate ID, candidate statement, `delivery_text`, `must_convey`, or grounding instruction.”

Proposed replacement: “For an authored-handoff turn, private candidate metadata stays out of the narrator request. The selected delivery sentence may be shown as the text the game will append. Check the complete player text after runtime composition, including delivery and cues.”

This is a documentation correction to the observed runtime, not permission to
leak other candidates. Apply it in place during later harness work, not as a new
dated runbook entry. Free: compare the single handoff contract against normal,
opening and recovery capture paths, three cases, $0. Billed: none required.

The smoke report needs contract tests before any new billed use:

- S6 is currently printed but omitted from the returned pass Boolean
  (`hidden_clues_smoke_report.py:319–346,414–445`). Exact old criterion:
  “complete and S1–S5 PASS”; new criterion: “complete and S1–S6 PASS, with
  missing budget evidence treated as insufficient evidence.” Check the real
  narration/shared recovery and item-facts budgets, not only narration attempts
  and verifier counts. Do not increase a runtime budget to pass the report.
- `_clues_recovered` accepts a selection as evidence of a fact (`:103–104`),
  and S3 counts a persistent `facts_after` fact as a fresh assertion (`:219`).
  Old criterion: “selected D or recovery present in facts_after.” New S1
  criterion: “committed recovery fact and carried/visible world state”; new S3
  criterion: “one committed false-to-true recovery transition, with no repeated
  delivery and no later custody change.” A digest change alone cannot identify
  which fact changed. Use typed recorded state/deltas, not prose parsing.
- S2 scans all serialized prompts/responses (`:111–126`), potentially including
  private matcher input. Preserve the intended narrator/player boundary rather
  than counting permitted private candidate text as leakage. Old scope:
  “all prompts and provider responses”; new scope: “narrator requests and
  complete player text, with private selector traffic reported separately.”
  Human semantic reading supplies the prose verdict; do not extend substring
  scanning into a new reply parser.

These repairs reuse existing recorded snapshots/digests, typed segments, request
counts and human labels. Free: one synthetic clean three-replicate report plus
single-fault fixtures for missing budgets, over-budget requests, selected-but-
uncommitted recovery, persistent recovery, duplicate delivery and private/public
payload separation; baseline/repaired report arms, seven fixtures each, $0.
Billed: none to test report arithmetic; the separately authorized smoke below
is the cheapest actual integration measurement.

## Stage 3 decision

**Technically useful on its own gates; not authorized to proceed under the frozen
chain.** `prereg:6–7` requires a clean preceding pass. No post-hoc relabeling can
turn that into permission. Brandon would need to authorize a separate diagnostic
registration, retaining stage 2 FAIL and the once-only/no-replacement rule.

S1/S3 test recovery and custody, S4 committed interpretation, S5 rollback, and
S6 budgets independently of whether the narrator repeats the delivery. S2 is
explicitly a prose/payload gate; the running record's claim that all S gates
read only state is incorrect. A named Brandon in prose can coexist with S4's
absence of `brandon_identified`; even S1–S6 passing would not certify narrative
secrecy or overall prose quality. Resolve reporter gaps above before spending.

Proposed unchanged minimum: candidate only, three replicates × six Route E
turns plus three openings; 240 HTTP call ceiling, $0.07 hard spend cap,
expected $0.03–$0.04 from the prior planning estimate. Verify actual call
accounting free first. Keep enforcement on and the scene-state flag off; do not
mix the independent drain experiment into this one. Fresh output directory and
registration, no replacement samples. Report drain rejection and latency
separately as specified, and retain full rollback evidence even for drain rows.
Stop on the registered infrastructure/cap conditions. This task launches nothing.

## Tests and earlier-plan corrections

After approval, update `tests/test_hidden_bench_prose_probe.py` to pin real request
identity, not injected clue names; exercise real pointer/find composition exactly
once; preserve raw and composed text; assert the actual world-aware provider and
checkpoint/prefix provenance. Include hidden names absent from THINGS before
recovery and present with correct custody afterward. Keep budget, missing-label,
hash-tamper and no-replacement tests. Add a blind-key bijection test so equal
counts cannot conceal duplicated/missing row mappings. Label calibration examples
belong in a human rubric; unit tests must not pretend to prove semantic truth.

Extend smoke-report tests with the fixtures in D. Add package/capture tests for
B only if approved. Use `tests/test_hidden_bench_discovery.py`, handoff transport,
pacing, live-baseline evidence and scene-start tests for first/late recovery,
repeat search, post-drop state, rejected-turn atomicity, and deadline fallback.
Restore the originally requested unrelated synthetic-story case; a missing small
helper does not establish story-agnostic behavior. Player examples remain active
imperatives, e.g. `Look under the park bench.` and `Put the transit token under
the park bench.` No implementation tests were run in this planning task.

The earlier plan got or left these things wrong:

- Its D self-prerequisite was loader-invalid. The accepted source-spending and
  activation-condition replacement is recorded in the preregistration; do not
  reintroduce the rejected condition.
- Its claim that the old revised cue sufficed before discovery was unverified
  and false once route knowledge required recovery. The accepted E pointer
  repairs that authoring gap. Do not remove it because of P1a's bad labels.
- It correctly demanded full composed prose, but that requirement was lost
  in preregistration/harness implementation. Restore it prospectively.
- It left faithful payload capture, atomic three-item observation preview,
  save/load/drop behavior, late pacing and synthetic-story coverage unproved.
  Neither a passing matcher nor this prose sample closes those gaps.
- It did not anticipate the P0 injection, bare provider or synthetic bench
  placement. The old/new prose comparison must not be advertised as clean.
- Its broad “no identity” requirement lacked a distinction between a committed
  identity fact, the photo-face revelation and simply naming Brandon. Define
  those before the next labels are written.

Techniques checked: current grounding/narrator/player-input/contributor/workflow
guides; scene-fixing material-first procedure and its 3B missing-material, 3A
talk-line and 2C stale-recall precedents; the world-model checklist and historical
W1–W14 record at `5ea0119955c62b84699a8dc7878a4af770b55a7e`, including W7's
one-way recovery and W9's contents amendment. None licenses reply-text parsing,
new hidden compartments or making prose authoritative. Current guide amendments
take precedence over historical placement wording.

## Risks and unverified work

Changing a Details line can alter style or emphasis across opening and normal
turns; capturing a string is not proof the model follows it. Removing NPC talk
globally would damage legitimate conversation. Reconstructing only composition
cannot establish validation or commit. Correcting the capture stack may produce
different contexts and require a new baseline; old samples cannot be pooled as
equivalent. The workspace's unrelated runtime changes and mutable HEAD require
an immutable source/package fingerprint before any future comparison.

Not verified here: live-prefix parity, accepted full-turn output from these raw
replies, actual capture of fixed-bench attempts, fresh matcher behavior after
any edit, prompt-rule efficacy, stage-3 results, latency at game-turn level,
coverage/Ruff/CI, or staging. Future implementation follows the focused runbook,
then appropriate quick checks and full coverage before merge; deployment still
requires the tested main SHA's staging evidence and promotion workflow.

Only this plan is written. Historical evidence, frozen labels and gates remain
unchanged. No code or package fix is applied and no paid stage is rerun.
