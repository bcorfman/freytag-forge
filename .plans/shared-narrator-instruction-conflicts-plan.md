# Shared narrator instructions: source authority, handoffs, length, and speaker voice

Status: planning only, 2026-11-07. Source inspected at `5fc12e79`, with existing
local changes retained. No runtime/story edits, tests, model calls, or deployment
performed. This is the active plan for the three notices in
[Separate-study notices only](astra-3a-things-and-speaker-lines-plan.md#separate-study-notices-only-requested-by-brandon).
Amended at Brandon's request to include first-person speaker voice, especially
Michelle's 3A lines. The original plan continues to own people projection and
the S/U speaker-line experiments; the speaker-voice contract below also applies
to those experiments and supersedes any permission to retain third-person
self-reference as acceptable direct speech.

## Resume here

Step 1 done 2026-11-07 (free, zero model calls); see
[Step 1 results](#step-1-results-free-baseline-capture-2026-11-07). Step 2 drafted
2026-11-07 in [the preregistration](shared-narrator-instruction-conflicts-prereg.md)
(endpoints, one-edit arms, 168 requests, ~622 neurons, ceiling 756, order B, C, A);
**nothing billed; waiting for Brandon to approve the rubric and spend.** D correction:
experiment S already ran and missed (Amendment 20 of the open-issues prereg), so D's
remaining routes are a first-person-instruction arm (new prereg) or U (needs Brandon's go-ahead).

1. ~~Prepare free captures of current opening, ordinary, selected-handoff, and
   recovery payloads; record the exact baseline and source of each rule.~~
2. Preregister separate source-authority, completion, and length comparisons
   below. Reconcile existing completion evidence before buying another run.
3. Probe one change at a time. Implement only supported changes, tests first,
   through the project's Ringer workflow; then qualify their combination.
4. Apply the speaker-voice contract in D to the existing S/U study. Audit
   speaker-facing source text and composed dialogue before declaring it fixed.

This request authorizes the study and this document. Proposed implementation
and billed experiments remain future work. No story, knowledge, world, schema,
matcher, judge, or request-budget changes are needed for A–C. D first uses the
existing speaker-template experiment; its conditional authored-text option
retains the original plan's separate schema and content proposal boundaries.

## Findings and limits

References below are to `storygame/runtime/cloudflare.py` at the inspected SHA.
They identify current source, not a guarantee about every historical wire prompt.

| Notice | Current mechanism | Conclusion |
| --- | --- | --- |
| Competing source authority | `_turn_rules_before_grounding` (884–898) says “Use only what the SCENE section tells you.” `_system_prompt` (1158–1181) directs use of CHARACTERS, SCENE and CONSTRAINTS. `_section_user_prompt` (1642–1750) also emits EARLIER IN THE STORY and PLAYER. | Confirmed ambiguity: SCENE is not the sole legitimate input. Removing exclusivity must preserve knowledge earning and speaker permissions. This does not establish that the wording caused a particular 3A miss. |
| Completion versus lead-up | `_turn_rules` (946–1020) includes the general completion rule even when `_is_authored_handoff_turn()` is true. `_authored_handoff_rules` (936–944) then supplies the delivery sentence and says to write only its lead-up. | The composed turn should finish the action; the generated portion must leave the selected delivery to the runtime. A scoped omission is a smaller candidate than removing completion everywhere. |
| Minimum output length | `_system_prompt:1174` always says “Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately.” | The requirement is current, not merely historical. It can pressure a short lead-up to expand, but causation is unproven. No global shortening is justified yet. |
| Third-person self-reference offered as speech | The original 3A study identifies `_speaker_constraint_lines` offering third-person knowledge statements as `<Name> may say this aloud: <statement>`, including Michelle's own reunion/organizing material. | A factual summary is not necessarily an utterance. Direct speech must use the speaker's own perspective; fixing presence or section authority alone does not fix this defect. |

Two path details matter. `_constant_opening_rules:921` says “Show only the
opening beat and what the SCENE section tells you,” so changing only the normal
turn line would leave a related ambiguity. `_recover_malformed_response`
(1437–1463) keeps the original system payload and adds recovery instructions;
handoff recovery repeats the handoff rules. A fix must survive recovery without
reintroducing the conflicting instruction.

**Corrected by the step 1 capture:** the base `_system_rules` returns an empty
list, but `ItemFactsProvider._system_rules` (`item_facts.py:854`) returns the
constant turn/opening rules whenever the prompt variant sets
`constant_rules_in_system`, and the production `capture_prompt_variant`
(`capture.py:916`) sets it. So in the production wire payload all three disputed
lines (A, B, C) are in the SYSTEM message; only the selected-handoff delivery and
lead-up lines (and recovery's repeat of them) are in CONSTRAINTS in the user
message. The door experiments' system-message patch location is therefore right;
a variation without `constant_rules_in_system` would put A and B in the user
message instead. Any test of A–C must use the production capture provider.

### Prior work to retain

The [scene-fixing guide](../docs/scene-fixing-guide.md) supports removing or
scoping a conflicting source line before adding rules. The
[grounding prompt guides](../docs/world-model-grounding/prompt-inputs.md) and
[historical checklist](world-model.md#decisions-and-evidence) preserve concrete
world material, start-place guidance, and command-scoped state instructions.
These are method precedents, not proof that these three candidates win.

[The 2A–2B follow-up](astra-fixes-plan.md) already proposes global completion
deletion for route invention. Its existing
`bench/results/stage7-door-completion-smoke/summary.json` records one row per
arm, six Cloudflare requests and four player attempts. The summary has no
quality verdict. Only smoke/dry completion summaries were found in this pass;
no counted completion win was established. Read those rows and their exact
payloads before reuse. The handoff-only comparison here differs in scope and
outcome; it does not reopen or duplicate the global door experiment.

The original 3A plan separately owns conditional omission of “When the player
talks to someone, that person answers” on selected handoffs. Keep that winning
ordinary-dialogue rule unchanged here. If it masks the completion comparison,
record the residual failure and coordinate a separately preregistered experiment
with that plan; do not silently remove both rules.

## Isolated candidates and the speaker-voice requirement

All candidate prompt wording here is proposed and unproven; D's first-person
requirement is Brandon's requested behavior, not an optional hypothesis.
For A–C preserve story material,
delivery sentences, JSON shape, model/settings, and all other rules within each
comparison. Keep facts as the only mutable truth; no new runtime state is needed.

### A — Remove SCENE-only exclusivity

First arm: delete only “Use only what the SCENE section tells you” on ordinary
and handoff turns. Existing positive section instructions, no-invention rules,
THINGS/start-place guidance, and knowledge/speaker restrictions remain.

For openings, replace only “Show only the opening beat and what the SCENE
section tells you” with “Show only the opening beat.” Keep the adjacent bans on
acting for the player, inventing events, repeating the entry, and solving the
goal. This is a separate opening endpoint of A, not evidence that the normal
turn deletion fixes openings automatically.

Do not replace the rule with “Everything in this message is true.” PLAYER is an
attempt, EARLIER IN THE STORY is history, and offered candidates are conditional
knowledge. Their presence is not permission to commit, disclose, or re-enact
them. If subtraction fails, first identify a specific missing source instruction;
any explicit section map is a new arm requiring its own words and evidence.

### B — Scope completion to turns without a selected handoff

Omit exactly “Finish each action the player gives” when
`_is_authored_handoff_turn()` is true. Retain it on ordinary turns, including
turns with eligible but unselected handoffs, no match, ambiguous match, and
legacy model-selected candidates. Reuse the existing predicate; do not infer
handoff status from dialogue, candidate availability, or a scene ID.

Keep the existing delivery/lead-up instruction unchanged. Do not add another
explanation of composition to the prompt. Test the final player-visible text:
the runtime must append the exact selected delivery once, and the lead-up must
fit it without prematurely supplying a different answer or discovery. A short
lead-up that omits the appended answer is expected behavior.

### C — Relax length only on selected handoffs

Test C independently of B, with the current completion rule retained. On a
selected handoff replace the fixed length sentence with:

> Write only as much as the lead-up needs. Then stop.

Retain the existing paragraph-to-segment JSON instruction and require nonempty
valid text. Ordinary turns and openings keep their current length rule. This
isolates the minimum-length pressure without prescribing another arbitrary
sentence count or reducing the output token ceiling.

This intentionally makes one system instruction depend on turn type. If adopted,
update `_system_prompt`'s claim that its content never varies with the turn.
Use one helper for the length choice; explicitly preserve opening behavior even
if a provider is reused. Do not duplicate alternate strings across callers.

### D — Speakers use first person when referring to themselves

**Required behavior:** sentences spoken by a character use that character's
own perspective. Self-reference uses first person (`I`, `me`, `my`, or `we`
when a supported group is meant), unless the character is quoting someone.
Michelle must not say “Michelle is coordinating the prisoners” as her own
account of what she is doing. Her corresponding line is “I'm coordinating the
prisoners.” These are illustrations of person, not new story declarations.

This does not require every sentence to contain “I.” A speaker can address
someone as “you,” talk about another person in third person, ask a question, or
give an instruction. Brandon can say “Michelle is coordinating the prisoners”;
Michelle cannot use that same sentence as unquoted self-description. A real
quotation retains the quoted speaker's perspective and clear attribution.
Ordinary dialogue quotation marks do not make third-person self-reference an
exception: the character must actually be quoting someone else's words.
Do not invent a quotation to excuse copying a factual summary.

Keep third-person knowledge statements as factual summaries where appropriate.
Do not change canonical statements, facts, eligibility, grounding, or SCENE
summaries merely to make them sound like speech. Separate permitted information
from words offered for literal delivery. The fix must preserve who did what,
who knows it, tense, and audience; it must not turn another person's experience
into the speaker's memory or imply unsupported membership with “we.”

**Source-first implementation order:**

1. Audit the speaker lines for both 3A A realizations, including Michelle,
   Brandon, and the official, then inventory the same shared formatter across
   loaded packages. Include authored dialogue deliveries and recovery outputs;
   an appended line is still player-visible speech. Distinguish a summary about
   someone from an actual utterance and from an attributed quotation.
2. Extend the original plan's S experiment: replace the invitation to say a
   third-person summary literally with permitted-information framing. If a
   perspective instruction is needed, propose this short shared wording:
   “When a person speaks about themselves, use first person. Keep another
   person's words unchanged when quoting them.” Freeze its exact placement and
   diff. Test S alone before S plus this instruction so their effects remain
   distinguishable. Do not pile the instruction beside the unchanged literal
   invitation and call the source defect repaired.
3. If S cannot meet the contract, use the existing U frozen substitutions before
   building its optional `speaker_text` schema. Michelle's first-person text
   belongs only to Michelle; Brandon and the official may refer to Michelle in
   third person. Review each utterance for semantic equivalence and legitimate
   speaker knowledge. Never perform a global name/pronoun replacement.
4. If U is adopted, absent overrides must use the approved information framing,
   not silently fall back to presenting third-person self-description as words
   to say. This tightens the older U proposal's “absent map preserves old
   rendering” rule; explicitly review and test the wider prompt compatibility
   impact. Schema/fingerprint compatibility and speech-rendering compatibility
   are separate requirements. Do not auto-migrate all knowledge statements.

Audit all narration paths listed above, using a shared instruction helper if
one wins. Do not add story-specific runtime branches or a production regex
that rewrites dialogue. This is a presentation contract, not permission for
the narrator to change world truth.

## Free preparation and deterministic checks

Before implementation, freeze the baseline SHA, dirty diff, package fingerprint,
entry facts, command, selected handoff, complete system/user text and settings.
Use network stubs and the existing capture procedures in
[prompt inspection](../docs/testing-runbook/prompt-inspection.md). The existing
1A-only capture does not establish other-scene coverage.

Inventory `_turn_rules`, `opening()`, `_constant_opening_rules`, `_system_prompt`,
`_section_user_prompt`, `_scene_setting`, and `_recover_malformed_response`.
Also inspect configured prompt variants and the final dispatch assembly. Apply
shared wording in one helper where appropriate; a path needing no edit must
still have a captured explanation. Do not alter `_scene_setting`'s earned-beat
filter to compensate for an instruction conflict.

For each candidate, require an exact allowed-line diff. Report system/user/total
characters; retain prompt-size ceilings. After a probe win, add meaningful tests
before the runtime edit, primarily in `tests/test_cloudflare_transport.py`:

- A: opening and normal payloads no longer exclude legitimate sections; hidden
  candidates and speaker-private knowledge remain filtered. Include a second
  genre/package rather than relying solely on Kristin/Michelle fixtures.
- B: selected-handoff versus ordinary, eligible-unselected, ambiguous and
  unmatched turns; exact-once delivery composition; subsequent ordinary turn
  restores the completion rule; recovery retains the same ownership.
- C: selected-handoff length choice; unchanged opening/ordinary lengths;
  recovery preserves the choice; a reused provider does not retain it after
  the handoff. Verify actual wire payloads, not only helper return strings.
- D: speaker-specific projection keeps Michelle's self-description distinct
  from Brandon's description of her; third-person factual summaries remain
  intact; another speaker's first-person override cannot leak across audiences.
  Include legitimate attributed quotations, ordinary dialogue quotation marks,
  third-person references to other people, plural self-reference, and authored
  handoff/recovery paths. Deterministic fixtures prove rendering and isolation;
  live prose review is still needed to establish model behavior.
- All: valid response content, fail-closed recovery exhaustion, unchanged
  earning/guard behavior, atomic rollback, and save/load behavior in the
  existing relevant suites. Never loosen a guard to make a prompt arm pass.

Use the focused transport, knowledge leakage, narration safety and handoff/
pacing suites listed in [local checks](../docs/testing-runbook/local-checks.md),
then the quick tier with relevant journeys and Ruff. Use `TMPDIR=/tmp` and
`uv run python`; verify current command help and installed Ringer timeout support
before execution. Full suite/coverage is an end-of-change gate. Update an
existing runbook entry only if its procedure changes; keep results here.

## Bounded behavioral study

Freeze exact endpoint states and commands in a preregistration before billing.
New commands follow the [player-input guide](../docs/player-input-guide.md).
Prefer saved failures whose full prompt and composed output can be inspected.
Do not edit commands or story text between arms.

| Comparison | Initial endpoints | Requests at 12 per arm per endpoint |
| --- | --- | --- |
| C0/A | One opening with necessary non-SCENE context; one ordinary action using THINGS; one ordinary dialogue using permitted speaker context | 72 |
| C0/B | 3A proof handoff; a physical discovery handoff in another scene | 48 |
| C0/C | The same two handoff states, with B absent | 48 |

These are 168 diagnostic narration requests if all three comparisons proceed.
This count covers A–C only. D reuses the original plan's S/U endpoint study
instead of scheduling duplicate Michelle probes. Any S-plus-instruction arm or
new cross-package/quotation endpoint needs its own preregistered request count
and spend ceiling; it is not included in either plan's existing totals.
Use same-day interleaved controls per comparison; never treat the old smoke as
a contemporaneous control. Fix model, sampling settings and output limits.
Calculate a monetary/neurons cap from the actual endpoint configuration before
requesting billed execution. No matcher/player/judge calls are included in this
frozen-payload count. Stateful qualification needs a separate budget, including
recovery and auxiliary calls. Stop an unsuccessful route before downstream spend.

Preregister an endpoint-specific targeted failure: ignored valid context for A;
duplicated/contradictory delivery for B; extra unrequested actions or disclosures
for C. Shorter prose alone is not a C win. At each endpoint require the control
to reproduce its targeted miss in at least 4/12 rows; otherwise mark the cause
not reproduced. Candidate target: at most 1/12 misses and at least three fewer
than control. These are engineering screen gates, not significance claims.

For D, add a separate **zero unquoted third-person self-reference** gate to
every candidate endpoint and composed journey. Check every speaker, including
runtime-appended dialogue, rather than only Michelle or generated segments.
Record each violation with the speaker, exact sentence, intended referent and
whether a genuine attributed quotation is present. Preserve legitimate
quotations and references to other people. Count source bookkeeping recital
separately: converting a repeated reunion summary to “I” fixes grammatical
person but does not fix the unwanted reunion speech. D must also pass the
original S/U relevance, identity, proof-answer, disclosure, and replay gates.
Silence or omission of a required answer cannot pass as correct first-person
speech. If a control has no perspective defect, report it as not reproduced;
do not claim a causal win from that endpoint. A failed method leaves the
requested contract unmet, rather than making third-person self-reference
acceptable again.

At every endpoint require zero premature/private disclosures, invented physical
capabilities, impossible committed state, malformed JSON or missing/invalid
segment text. Require correct requested action or correct composed handoff in
at least 11/12 and no worse than its matched control. Score generated lead-up
and appended text separately, then score the whole turn. Preserve every raw
failure, refusal and transport error; no replacement samples or rerun-until-green.
Read all prose, including malformed readable prefixes. Do not accept item_facts
or a cake keyword as proof that the action happened.

A partial endpoint win supports only that scope. A failed candidate is dropped
or redesigned with a new preregistration. If B and C individually fail, do not
assume their combination works; a hypothesized interaction is a separate study.

## Adoption and closure

After independent wins, compare the implemented combination with the unchanged
control on all five endpoint states above: 120 additional narration requests
at 12 per arm. Prove implementation payloads match the winning frozen forms.
That 120-request figure covers A–C's five states. If D is combined, include its
distinct endpoints and recalculate the preregistered total before billing.
Retain every endpoint's gates; averaging cannot hide a regression. Coordinate
with the people/speaker plan before combining its changes: freeze a new shared
baseline rather than mixing its unqualified candidate into these controls.

Then preregister matched stateful journeys through the changed scenes and a
cross-scene regression set, with at least three replicates per arm. Include
openings, ordinary action/dialogue, selected and unselected handoffs, follow-up
turns, recovery, cues and scene transitions. Require earned reveals/exits,
correct exact-once deliveries, intact custody/identity, no extra acts or leaked
knowledge, and no ordinary-action regression in every replicate. A global A
change needs all-scene coverage; B/C need every distinct handoff behavior plus
unchanged ordinary-turn coverage. A frozen replay cannot qualify live history.
Any adopted speaker change must also pass D's perspective and quotation gates
across affected speakers/packages, while preserving third-person narration and
factual summaries. Document any remaining violation as an open defect.

Before merge, record deterministic/coverage/Ruff outcomes, payload diffs, raw
row reviews, remaining failures and unmeasured paths here. Follow the existing
SHA-bound staging workflow after merge to `main`; production promotion remains
separate under the [promotion guide](../docs/railway-production-promotion.md).
Do not claim these changes solve 3A presence, reunion recitation, or radio replay
unless their owning plan's gates also pass.

Twelve repeats of a frozen prompt can be highly correlated. Even zero failures
does not establish a near-zero production error rate. The study can identify
useful changes within tested states; it cannot prove that all prompt conflicts
or all narration defects have been removed.

## Step 1 results: free baseline capture (2026-11-07)

Zero model calls; network stubbed. Script `scripts/ringer/shared-narrator/baseline_capture.py`
(builds the production `build_capture_provider`, the first narration reply is
deliberately malformed so the real recovery path produces the recovery payload).
Output: `bench/results/shared-narrator/baseline/baseline.json` (git-ignored, with
the two generated variations beside it). Baseline: SHA `5fc12e79`, dirty-diff
sha256 `c34efd9fd3ed…` (`git diff HEAD`, the retained local changes), package
hash recorded per row, 3A state from `bench/variations/richer-3a-loc-P.json` with
its scripted-handoff prefix.

| State | Kind (observed) | Selected handoff | system / user chars |
| --- | --- | --- | --- |
| 3A opening | opening | — | 2154 / 2181 |
| 3A c1 `Free the captives.` | handoff | `k_sl_3a_a_r1` | 2527 / 1873 |
| 3A c2 `Read the wrist tags.` | handoff | `k_sl_3a_f_r1` | 2527 / 2836 |
| 3A c3 `Listen to the stolen radio.` | handoff | `k_sl_3a_g_r1` | 2527 / 2873 |
| 3A c4 `Enter the medical level.` | handoff | `k_sl_3a_b_r2` | 2527 / 2874 |
| 3A c5 `Ask Michelle about the lemon cake.` | handoff | `k_sl_3a_h_r1` | 2527 / 3269 |
| 3A c6 `Ask the senior official about the gate codes.` | handoff | `k_sl_3a_d_r1` | 2527 / 3470 |
| 3A c7 `Check the checkpoint reader.` | handoff | `k_sl_3a_i_r1` | 2527 / 4516 |
| 3A c8 `Tell the prisoners to start the uprising at the checkpoints.` | handoff | `k_sl_3a_c_r1` | 2527 / 4676 |
| 3A c9 `Lead the prisoners upward toward the command levels.` | ordinary | — | 2527 / 6570 |
| 1C opening | opening | — | 2154 / 1679 |
| 1C c1 `Look around the loading docks.` | handoff | `k_sl_1c_a_r1` | 2527 / 1611 |
| 1C c2, c3 | ordinary | — | 2527 / ~1550 |

Source of each rule (confirmed in the wire payload):

- **A, ordinary and handoff:** “Use only what the SCENE section tells you.” — SYSTEM,
  once, present on every turn (all 3A and 1C turns). Opening: “Show only the opening
  beat and what the SCENE section tells you.” — SYSTEM, once.
- **B:** “Finish each action the player gives.” — SYSTEM, once, present on every
  selected-handoff turn as well as ordinary ones. The delivery/lead-up pair is in
  the user CONSTRAINTS. So the completion rule and the lead-up rule sit in different
  messages.
- **C:** “Describe each scene in 2-3 paragraphs …” — SYSTEM, once, on openings, ordinary
  and handoff turns alike.
- **Recovery:** the recovery payload is the original payload with the instruction
  appended to the SYSTEM message. A, B and C are therefore still present in recovery.
  Handoff recovery repeats the lead-up pair (count 2 in the payload: one in CONSTRAINTS,
  one in the appended system text). Opening and ordinary recovery add only the generic
  JSON-repair text. Any scoped change for B/C has to cover the original system text
  that recovery reuses, not only the helper strings.
- **D (current source):** `<Name> may say this aloud: …` appears 6–24 times per 3A
  turn, growing with committed knowledge; 1C has none.
- “When the player talks to someone, that person answers.” is present on every
  handoff turn (left unchanged here, as planned).

Observations that change step 2:

- The 3A script is almost all handoffs (8 of 9 commands select one). The only ordinary
  3A endpoint is c9, and it is an action, not dialogue. The plan's “ordinary dialogue
  using permitted speaker context” endpoint does not exist in this script. Step 2
  must author or find a dialogue command that really stays ordinary (for example,
  after the relevant handoff is spent) and freeze it.
- 1C c1 `Look around the loading docks.` already selects the physical-discovery handoff
  `k_sl_1c_a_r1` (a loose match). For the B/C “physical discovery” endpoint use the
  stricter wording `Check the loading docks for signs of activity.` unless the loose
  match is itself under study; confirm which one the matcher selects before freezing.
- The 3A-vs-1C pair gives the “second scene” coverage for B/C. A needs a second
  genre/package for the deterministic tests (still open; only one story package exists
  in `data/stories`, so use a test fixture).

Completion evidence reconciled (free): `bench/results/stage7-door-completion-smoke/`
has `summary.json` (1 row per arm, `control` vs `no-finish`, 6 Cloudflare requests,
4 player attempts, no quality verdict), a `verdicts/` directory without a counted
result and `notes.md` saying “interpretation requires blinded review and does not
establish hosted adoption.” No counted completion win exists; B stays an open
hypothesis, and its handoff-only scope does not duplicate the global door experiment.

Not done: no preregistration, no billed run, no runtime/test edit. The wire-payload
flag counts above are from stubbed captures and describe prompt content, not model
behavior.

## Step 4a: speaker-line audit, free (2026-11-07)

Source: the 3A baseline payloads above (`baseline.json`, c1–c9), which carry every
`<Name> may say this aloud: …` line the narrator received. Result: **8 distinct
third-person statements, each offered verbatim to all three speakers** (Michelle,
Brandon, the imprisoned senior official), 24 lines in the fullest prompt.

- **Michelle (own account in third person), 5 of 8:** “Michelle coordinates the prisoners
  through stolen radios…”, “Michelle has explained that freeing this block means little…”,
  “Michelle shows Kristin the medical level…”, and the two “Michelle hands Kristin the stolen
  radio…” statements. Offered as words she may say aloud, each invites “Michelle …” as self-reference.
- **Official, 2 of 8:** “The senior official Charles framed gives Kristin one-use
  authorization…” and “The framed official proves the emergency gate authorization is real…”
  describe the official in third person and are offered to him as speech.
- **Brandon:** none of the 3A statements is about him, so no self-reference defect arises from the
  current 3A set; he still receives Michelle's and the official's statements as speech material
  (third person about others is allowed).
- **Second person:** statements also name the player (“gives Kristin”, “shows Kristin”). A speaker
  addressing her should say “you”; first-person `I` is the required fix, “you” is the same family
  and should be in the same review.
- **Outside the audit:** no speaker lines exist in the 1C baseline; packages and scenes beyond 3A
  and 1C are not inventoried yet (the shared formatter is `cloudflare.py:1639`, so any scene with
  `sayable_knowledge` is affected). Authored dialogue deliveries and recovery outputs not yet reviewed
  for person.

So the defect is in the source line shape, as the plan predicted: the facts are correct summaries,
the template presents them as utterances. S (re-headed template) already missed; U (authored
`speaker_text`) was approved to proceed by Brandon on 2026-11-07 (“yes to both”) and is the next D work,
after B/C/A are reported.

## Results and status (2026-11-07, end of session)

Preregistration, scripts, sheets and per-comparison results:
[the prereg](shared-narrator-instruction-conflicts-prereg.md). 168 narration requests, ~622 neurons, no
runtime/story/test change.

| Candidate | Outcome |
| --- | --- |
| B — omit completion rule on selected handoffs | **Dropped.** H1 control did not reproduce; arm worse (2/12 vs 0/12); H2 unchanged (12/12 both). |
| C — relax length sentence on selected handoffs | **Dropped.** Targeted miss did not reproduce (H1 0/12, H2 1/12); arm no shorter at H2. |
| A — delete SCENE-only exclusivity, ordinary turns | **Dropped.** A2 no effect (12/12 both); A3 cause not reproduced and the arm raised verbatim third-person recital of speaker lines to 12/12 from 8/12 (adverse for D). |
| A — opening edit only (`Show only the opening beat.`) | **Candidate, not adopted.** A1 4/12 → 1/12, malformed 1 → 0, at the screen's margin on one frozen state; needs a confirmatory preregistration on other openings. |

Corrections to this plan found while running: the production wire payload carries A, B, C in the system message (not
CONSTRAINTS); the planned ordinary-dialogue endpoint had to be authored (A3); experiment S had already missed.

Open findings, untested: (1) at the 1C discovery handoff every lead-up opens “She sees nothing out of the ordinary”
before the appended discovery, and restates the SCENE keywords; (2) removing the SCENE-only line increases verbatim
recital of speaker lines. Both need their own preregistrations.

**D (speaker voice) is not met and nothing was changed.** The audit above shows 5 of Michelle's 8 offered statements
and 2 of the official's are third-person self-description. The 3A plan's proposal U overrides only two entries
(`k_sl_3a_a_r1`, `k_sl_3a_a_r2`); it leaves Michelle's `k_sl_3a_b_r2` (“Michelle shows Kristin the medical level…”) and the
two radio-handover statements (`k_sl_3a_c_r1` and its 2-line variant) as third-person speech, so U as written cannot meet the
zero-unquoted-third-person-self-reference gate. Candidate wording for review is needed for `k_sl_3a_b_r2` (and the official's two
statements) before any probe; the radio statements overlap the unresolved c9 replay (O4). The free substitution payloads can be built from
`bench/results/richer-3a-probe/speech/frozen-C.json` (c4, c5, c9). Billing that probe is a new preregistration with its own request
count (72 requests, ~266 neurons at 12 per arm per endpoint for C/U) and needs a fresh spend approval, since the 756-neuron ceiling was approved
for A–C only (about 134 neurons remain under it, less than the probe needs).

### D update (2026-11-07): U probe missed

Brandon approved new wording and a 324-neuron ceiling; the 72-request frozen-substitution probe of U ran (prereg, “Experiment U”).
Result: the D gate was met (0/36 unquoted third-person self-reference against 2/36 in the control) but U failed on relevance at every
endpoint: at c4 the authored lines were voiced in 12/12 replies and the commanded medical-level action vanished (10/12 to 0/12); at c5 plan
exchanges 4/12 and an invented earlier conversation 1/12; at c9 item 3 and radio-conflict item 4 failed in 3/12 each. U is not built and no
repository file other than the scripts and plans changed. Remaining D routes, each needing its own preregistration and spend approval: (a) the
shared first-person instruction (“When a person speaks about themselves, use first person. Keep another person's words unchanged when
quoting them.”) on the current template, without handing over utterances; (b) making Michelle's and the official's self-describing statements
non-speakable for themselves (the 3A plan's `voiceable` work for c9), so nothing third-person is offered to them as speech; (c) a
combination. Until one passes, the current production behaviour (third-person speaker lines offered as speech) remains an open defect.

## D, new route from Brandon (2026-11-07): a speaker may reference an event only after the narrative has mentioned it

Brandon's rule, checked against the code before planning. Today a statement is offered to speakers when `KnowledgeProjector._established`
(`storygame/runtime/knowledge.py:413`) finds every fact in the entry's `establishes` list true. Alternate realizations of one storylet share the
same `establishes` facts, so once one realization is delivered its siblings count as established too, although their event was never
narrated. In the 3A script that is exactly what happens: after c1 delivers `k_sl_3a_a_r1`, the sibling `k_sl_3a_a_r2` (“Michelle has
explained that freeing this block means little…”) is offered as speech at c4, c5 and c9; the same holds for `k_sl_3a_d_r2` and `k_sl_3a_c_r2`
(3 of the 7 statements traced at c9 were never narrated; the delivered ones are `a_r1`, `b_r2`, `d_r1`, `c_r1`). Those never-narrated lines are the
bookkeeping recital the c4 and c5 rows keep voicing, and they are why U got them spoken 12/12.
There is no cumulative record of delivered entries to gate on: `revealed_knowledge_ids` (`state.py:52`, set at `engine.py:689`) holds only the latest
turn's selection, and facts record effects, not which entry was shown. Facts are the sole mutable truth, so the record must be a fact (or an
equivalent saved/rolled-back state), not a side list.
Not yet done: no code, test, billed run. This route addresses unnarrated references; it does not by itself convert a delivered statement such as
`a_r1` (“Michelle coordinates the prisoners…”) into first person, so D's grammatical-person gate is still open for delivered lines.

### Narrated-prerequisite gate: built and counted offline (2026-11-07)

Built through Ringer (`scripts/ringer/shared-narrator/gate-manifest.json`, tests first, one task). The worker's check failed only because of a shell
bug in the check itself (`${PIPESTATUS}` under `/bin/sh`); its tests passed, I ran ruff and the patch export by hand and applied
`ringer-work/shared-narrator-gate/gate.patch` to the main checkout, uncommitted. Changes: `RuntimeState.apply_proposal` asserts the fact
`knowledge_narrated(<id>)=true` for each id in `selected_knowledge_ids` on the candidate fact store (atomic with the turn, so a game break drops it,
snapshot restore rolls it back, saves carry it); `KnowledgeProjector._established_for` offers a `storylet_realization` entry to speakers only when that
fact is true. Grounding, scene-entry and canonical-route entries are unchanged. New `tests/test_knowledge_narrated_gate.py` (7 tests) plus six existing
test files now narrate the entry before expecting it sayable. 359 focused tests pass; full suite and ruff gate not yet run.
Known limits: the forced-handoff fallback selects no id so it marks nothing; saves made before this change have no narrated facts.
Free line count (`gate_lines.py`, `bench/results/shared-narrator/gate-lines.json`): speaker lines offered per turn go 6 to 3 at c4, 9 to 6 at c5,
24 to 15 at c9. Exactly the unnarrated siblings are removed (`a_r2`, `d_r2`, `c_r2`); `a_r1`, `b_r2`, `d_r1`, `c_r1` and the c9 uprising line stay.
What remains offered is still third-person self-description (“Michelle coordinates the prisoners…”), so D's grammatical-person gate is still open.
Next, needing a preregistration and spend approval: billed replay of control vs gate at c4, c5, c9 (72 requests, about 266 neurons).

## Overlap with the 3A plan and agreed path (2026-11-07, later)

Both plans were reviewed together. The 3A plan's "Resume here" now carries a superseding update. D is the 3A plan's S/U work with a
stricter pass condition; A–C are the 3A plan's three separate-study notices; B and the 3A plan's H are one idea (H retired unless a c5
failure reproduces). The two plans share one baseline and should share one qualification.

Free work done this session:

- **Delivery audit (step 1 of D, free).** All 13 `k_sl_3a_*` `delivery_text` values and the three 3A handoff fallbacks are indirect
  narration; none contains a quoted utterance, so none carries the third-person self-reference defect. Recovery payloads add only
  generic JSON-repair text (baseline capture). The defect is confined to the speaker-line template. Packages other than 3A and 1C are
  still not inventoried.
- **Ruff.** The repo-level ruff check failed with 40 findings, all in my uncommitted Ringer scripts (not runtime or tests). Fixed:
  formatting, a file-level `# ruff: noqa: E501` on `things_people.py` (precedent: `reunion_effect.py`), `strict=True` on one `zip`, and
  a renamed `l`. `ruff check .` and `ruff format --check .` now pass. The full suite was not re-run; it is the end-of-change gate.

Agreed order from here:

1. Preregister and, with approval, run one billed replay at c4, c5, c9: **control / gate / gate + first-person sentence**
   (“When a person speaks about themselves, use first person. Keep another person's words unchanged when quoting them.”), 12 per arm
   per endpoint, 108 requests, about 400 neurons (the two-arm version is 72 requests, about 266). Each arm adds exactly one change to the
   one before. Keep the SCENE-only line (A-ordinary raised recital). Score the zero-unquoted-third-person-self-reference gate and the
   original S/U relevance, identity, proof-answer, disclosure and replay gates.
2. Branch on the result. Pass: D is done with no story edits. c9 still replays: `voiceable: false` on completed signal and handover
   statements (the 3A plan's c9 step 1; needs Brandon's approval). Self-description persists: make self-describing statements
   non-speakable to their own subject; their required answers come from authored deliveries, not speaker lines, but test it.
3. Run the A-opening confirmation as an extra arm on the 3A plan's other-scene opening checks (1B, 2A, 2B, 2C), which need billing
   for the presence work anyway.
4. Qualify once: frozen combined check, nine-command 3A journeys, other-scene checks, full suite, then staging.

The 1C “She sees nothing out of the ordinary” lead-up finding stays a separate preregistration.

### Step 1 result (2026-11-07): experiment G ran; the first-person sentence is out, the gate is undecided

108 requests, ~400 neurons ([prereg, Experiment G](shared-narrator-instruction-conflicts-prereg.md)). **GF (gate + first-person sentence) failed** and
is dropped: it left 1 unquoted third-person self-reference at c4, raised recital (8/12 against 3/12), made Michelle hold up Kristin's radio at c9
(5/12) and lowered the c9 command answer (9/12). **G (gate alone) missed its win rule at every endpoint but did not trip the preregistered revert
rule.** It removed all three verbatim third-person self-references at c4 (3 to 0) and cut the c9 handover replay 12/12 to 7/12 and authorization speech
8/12 to 1/12; but at c4 the commanded medical-level action fell from 9/12 to 1/12 (Michelle talks plans 10/12), at c5 Michelle answers inside the lead-up
3/12 and 2 c9 replies were malformed. The c4 flip matches experiments S and U, so c4 may be a fragile frozen endpoint. Open for Brandon: keep the gate on
principle (uncommitted, nothing adopted) and qualify it on live stateful play, or hold it. D remains unmet. The remaining D routes are the 3A plan's
`voiceable` step for completed handover statements and making self-describing statements non-speakable to their own subject, each its own prereg.

### Brandon's direction (2026-11-07): author the first person in advance, no prompt sentence

“I don't want a prompt for the first-person sentence; I want it written that way in advance.” This confirms the authored route (experiment U's `speaker_text`)
and closes the prompt-sentence route for good. U alone missed on relevance because it also handed over the never-narrated sibling lines (the other-sites line was
voiced 12/12 at c4). The gate removes exactly those, so the combination **GU = gate + authored lines** is the next test. Free payloads built by
`scripts/ringer/shared-narrator/gu_capture.py` into `bench/results/shared-narrator/g/frozen-GU.json` (prefix `9d5581f900c1`, system byte-identical to G).

**Revised 2026-11-07 after Brandon's note** (the first draft read as stilted; he also wants an emotional reunion with an embrace). Wording below is
**for Brandon's review before any schema or story edit**. Free payloads: `gu_capture.py`, `frozen-GU.json` prefix `ca887c1b1147` (system identical to G).
Canonical `statement` text stays third person and unchanged. “You” means Kristin. Michelle's bio says everyone except Kristin addresses her as “Dr. McGehee”,
so Brandon and the official use that name (the first draft used “Michelle”). The reunion is no longer in speech: it is delivered once, in authored text (below).

| Entry | Michelle says | Brandon says | Senior official says |
| --- | --- | --- | --- |
| `k_sl_3a_a_r1` organizing | I've been organizing everyone with secret announcements over our stolen radios. | Dr. McGehee's been organizing everyone with secret announcements over the stolen radios. | same as Brandon |
| `k_sl_3a_b_r2` medical level | I showed you the medical level. That's where they ran memory, compliance, and resistance experiments on the prisoners. | Dr. McGehee showed you the medical level. That's where they ran memory, compliance, and resistance experiments on the prisoners. | same as Brandon |
| `k_sl_3a_c_r1` radio handover | I gave you the radio, you gave the signal, and now the prisoners have the checkpoints and are fighting their way up toward the command and broadcast levels. | Dr. McGehee gave you the radio, you gave the signal, and now the prisoners have the checkpoints and are fighting their way up toward the command and broadcast levels. | same as Brandon |
| `k_sl_3a_d_r1` authorization (smoothed to match; you did not ask for it) | The official Charles framed gave you one-use authorization for the emergency surface gates. It expires when Charles activates his new authority. | same as Michelle | I gave you one-use authorization for the emergency surface gates. It expires when Charles activates his new authority. |
| uprising-active entry (`knowledge.yaml:3515`) | unchanged (no self-reference) | unchanged | unchanged |

Changes from canonical, stated so none is hidden: the reunion sentence is not offered as speech; `shows` and `hands` become past tense (the lines are voiced
only after the gate sees them narrated); the player is “you”; the official's `a_r1` and `b_r2` lines refer to Michelle as “Dr. McGehee”. The `c_r1` line still
describes the handover, so it may keep inviting its replay (O4); the GU probe measures that and `voiceable: false` stays the fallback.

**Emotional reunion and embrace (authored text, not speech; for Brandon's review, nothing applied).** The reunion is delivered by the entry's `delivery_text`,
which the game appends once, when the reunion is earned. Two realizations establish `michelle_reached`, so both get it. Proposed:

- `k_sl_3a_a_r1` delivery: *Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block.
  Michelle looks up, goes completely still, and then pulls Kristin into a tight embrace. “You're here,” she says, her voice breaking. “You're really here.” Kristin
  holds on just as hard, and for one unhurried moment nobody asks anything of either of them. Then Michelle wipes her eyes, turns back to her coded announcements, and
  points toward the medical level, where the experiment records wait.*
- `k_sl_3a_a_r2` delivery: *Michelle looks up, goes completely still, and pulls Kristin into a tight embrace. “You're really here,” she says, her voice breaking. For one
  unhurried moment nobody asks anything of either of them. Then she wipes her eyes and explains that freeing this block means little without exposing the other sites.
  Michelle points toward the medical level, where the experiment records wait.*
- `handoffs.yaml` `michelle_reached` fallback: *…They embrace and share one unhurried moment before Michelle turns back to the radio and the rescue.* The opening
  `cue_text` (Michelle speaking into a stolen radio beside the captives) stays unchanged, so the opening still shows no greeting.
- Kept consistent with the bio (thoughtful, determined, private; Kristin alone says “Shelly”): the emotion is restrained and shown by action, and Michelle uses no
  nickname for Kristin. Open: do you want Kristin to say “Shelly” in the embrace?
- Known risks to measure, not assume: the embrace text enters EARLIER IN THE STORY for every later turn, so c4, c5 and c9 might re-perform it (rubric item A, greeting as
  if just found); the c1 lead-up must not pre-empt it; tests that pin these delivery strings change. Measuring this needs payloads recaptured from a private story copy
  carrying the new text (the Amendment 19 method), so it is a second stage after GU.

Proposed probe, stage 1: **GU only, 3 endpoints × 12 = 36 requests, about 133 neurons, ceiling 162 (4.5 per request)**, compared with the same-day C0 and G rows already
collected (same frozen prompts, same day; not interleaved with them, which weakens the comparison and is stated as a limitation). Required: the D gate 0/12 at every
endpoint (all speakers, runtime-appended text excluded because the probe sends the model request only), F1 0/12, and GU no worse than G by more than 2/12 on H, item 1,
J, K, E, item 3 and item 4. The c4 command loss seen in G (medical level 1/12 against 9/12) is reported against C0; if it persists, it goes to Brandon as an
open decision rather than a pass. If GU passes: schema (`speaker_text`), tests first through Ringer, payload match to the frozen GU, then the qualification pass.

Stage 2 (after stage 1 passes): **GUE**, GU plus the embrace delivery text in the scripted prefix, from a private story copy; 36 requests, about 133 neurons, ceiling 162, compared
with GU, plus the free check that the c1 payload and the appended text compose correctly. Rubric adds item A (greeting or reunion re-performed) at c4, c5 and c9.

### Step 1 result for GU (2026-11-07): the written rule is met, the contract is half met

36 requests, ~133 neurons ([prereg, Experiment GU](shared-narrator-instruction-conflicts-prereg.md)). With the gate on and the speaker lines written per speaker in advance (no prompt sentence),
**unquoted third-person self-reference is 0/36**, first-person misuse 0/36, premature c5 answers 0/12, and the c9 handover replay is the lowest recorded (5/12, from 12/12). The written win rule is met.
It is **not** a pass because the prereg's own clause fires: Michelle voices the authored organizing line almost word for word in 10 of 12 c4 replies, in place of the commanded step (command 0/12;
control 9/12, gate alone 1/12), and five c9 replies shout the authored handover result again. So the *person* defect is fixed and the *unwanted speech* defect is not, as this plan warned.
Open decision for Brandon: (a) go on to qualification with GU and test it in live stateful play, where the engine appends the medical-level delivery; (b) first make the organizing and handover
lines non-speakable (`voiceable: false`) or offer each only when the player's command is about it, which fixes the repeat but leaves no speakable line for the organizing role; (c) hold.
Stage 2 (the embrace delivery text) has not run.

### Built (2026-11-07): optional `speaker_text` per speaker, with the four approved 3A entries authored (uncommitted, applied in the working tree)

Brandon chose option 1 (qualify GU) and asked whether this follows the plans: it does, with one tracked gap (below). Ringer run `shared-narrator-speaker-text`
(`scripts/ringer/shared-narrator/speaker-text-manifest.json`, one task, tests first, main checkout because the gate and presence work are uncommitted). The task's own
check reported FAIL only because of a bug in my check (`${PIPESTATUS[0]}` is a bashism and Ringer runs checks under `/bin/sh`: "Bad substitution"), the same mistake as the gate
task; every real step passed and I ran the rest by hand. Verified by hand: 371 tests pass in the related suites (new `tests/test_speaker_text.py`, 11 tests); the engine's real payloads
match the frozen GU arm byte for byte, system and user, at c4, c5 and c9 (`scripts/ringer/shared-narrator/gu_match.py`); `ruff check` and `ruff format --check` clean on `storygame` and `tests`;
only the owned files changed (snapshot comparison). I reviewed the diff.

- `KnowledgeDefinition.speaker_text`: immutable, hashable mapping speaker id to text; omitted from serialization when empty (existing packages serialize unchanged); rejects blank or non-string text,
  malformed ids, and a populated map on `voiceable: false`. The loader rejects a speaker id that is not a declared NPC.
- Rendering (`cloudflare.py`): a speaker's own text replaces the canonical statement in that speaker's line only; an entry with no map renders as before; a speaker missing from a non-empty map
  gets no line for it (never a fallback to a third-person statement that may describe them). Canonical `statement`, facts, SCENE, `brought_up` and the safety projection are untouched.
- Story: `speaker_text` added to exactly `k_sl_3a_a_r1`, `b_r2`, `d_r1`, `c_r1` with the approved wording.
- Existing tests changed: `tests/test_speaker_lines.py` (the formatter's expected line now uses the authored text) and `tests/test_knowledge_projection.py` (the narrated gate: it narrates the entries first and
  expects the authored `a_r1` lines to no longer carry the canonical statement). Shard metadata refreshed (`tests/shard_durations.json`, two new files). `tests/test_shard_balance.py` fails when run in the
  same process as `tests/test_regen_shard_durations.py`, also against the committed metadata, so it is not caused by this change; it passes alone.

**Tracked gap, not yet fixed (decision for Brandon): the alternate 3A realizations are still third person.** Five voiceable entries are not authored, so if a player triggers them instead of their
siblings they are offered as before: `k_sl_3a_a_r2`, `b_r1`, `e_r1`, `d_r2`, `c_r2` (the rest of 3A is `voiceable: false`, or has no self-reference: the uprising-active entry and the public scene entry).
This matters for the A-r2-first journey. Proposed wording, for review (nothing applied; Brandon and the official say “Dr. McGehee”, “you” is Kristin):

| Entry | Michelle says | Brandon says | Senior official says |
| --- | --- | --- | --- |
| `a_r2` | Freeing this block doesn't mean much unless we expose the other sites too. | Dr. McGehee says freeing this block means little unless we expose the other sites. | same as Brandon |
| `b_r1` and `e_r1` (same statement) | I showed you the experiment records. They prove the planned “survivors” were conditioned to support Charles's story. | Dr. McGehee showed you the experiment records. They prove the planned “survivors” were conditioned to support Charles's story. | same as Brandon |
| `d_r2` | The official Charles framed proved the authorization is real, but the panel's brief response shows the one-use code is about to expire. | same as Michelle | I proved the authorization is real, but the panel's brief response shows the one-use code is about to expire. |
| `c_r2` | With the authorization about to expire, I gave you the radio and you gave the signal instead of waiting. | With the authorization about to expire, Dr. McGehee gave you the radio and you gave the signal instead of waiting. | same as Brandon |

Also still open from the shared plan: an entry with no `speaker_text` keeps the old rendering (no tested alternative framing exists; the `may talk about this fact:` header missed), other packages and scenes
are not yet inventoried, and the embrace delivery text (stage 2) and live-play qualification have not run.

### Rewrite rule and full wording for all nine entries (2026-11-07; Brandon: "Yes, rewrite all of them"; wording below awaits his review, nothing applied)

Rule from Brandon's objection to the `c_r2` and `c_r1` lines: a speaker must not retell Kristin's own action (or what the speaker just did with her) to Kristin, who already knows it. A line says what the event
means now or what comes next. First person is kept where a speaker really speaks about themselves (`a_r1`); elsewhere the line is neutral, so the same words can be given to every speaker. The canonical statements
stay third person and unchanged; the dropped detail (who handed what) stays true in the facts and the scene text. This replaces the earlier wording for `b_r2`, `c_r1`, `d_r1` (built and probed in GU) and for
the five proposed entries.

| Entry | Michelle says | Brandon says | Senior official says |
| --- | --- | --- | --- |
| `a_r1` organizing (unchanged) | I've been organizing everyone with secret announcements over our stolen radios. | Dr. McGehee's been organizing everyone with secret announcements over the stolen radios. | same as Brandon |
| `a_r2` other sites | Freeing this block doesn't mean much unless we expose the other sites too. | Dr. McGehee says freeing this block means little unless we expose the other sites. | same as Brandon |
| `b_r1`, `e_r1` records | Those records prove the “survivors” were planned. They were conditioned to support Charles's story. | same | same |
| `b_r2` medical level | The medical level is where they ran memory, compliance, and resistance experiments on the prisoners. | same | same |
| `d_r1` authorization | That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority. | same | same |
| `d_r2` authorization proven | The authorization is real, but the panel's brief response shows the one-use code is about to expire. | same | same |
| `c_r1` handover and uprising | Your signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels. | The signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels. | same as Brandon |
| `c_r2` handover under the deadline | Good thing we didn't wait. That authorization was about to run out. | Dr. McGehee didn't wait. The authorization was about to expire. | same as Brandon |

Consequences, so none is hidden: the four built entries change text (`b_r2`, `d_r1`, `c_r1`; `a_r1` stays), so `frozen-GU.json` and the payload match must be rebuilt, and the GU probe result (written for the old
wording of those three) no longer covers them: a second 36-request probe (GU2, about 133 neurons, ceiling 162) is needed before calling the lines good. The five new entries are added in the same Ringer task, tests
first. Open check for that probe: neutral lines such as “The medical level is where they ran…” could be volunteered as bookkeeping speech just as the first-person organizing line was (10 of 12 at c4); that is
exactly what GU2 measures.

### GU2 result (2026-11-07): rewritten lines fix the person and the handover replay; the organizing line is still voiced

36 requests, ~133 neurons ([prereg, Experiment GU2](shared-narrator-instruction-conflicts-prereg.md)). Nine entries are now authored in the working tree (Ringer `shared-narrator-speaker-text-2`, PASS; payload matches the frozen GU2 arm; uncommitted).
Result: written win rule met. Third-person self-reference 0/36, no speaker retells Kristin's action, premature c5 answers 0/12, and the **c9 handover replay is 0/12** (control 12/12), the first value inside the 2/12 bar. Not fixed: Michelle voices the one offered line,
her first-person organizing sentence, in 12/12 c4 replies and the command is 0/12 (both open-decision clauses fire); at c9 the unchanged “The uprising is active…” line is voiced 12/12; 4/36 replies are malformed (runaway `item_facts`). Options for Brandon:
(a) continue to the embrace text (stage 2) and live stateful play, where the engine appends the medical-level delivery after the lead-up; (b) first stop the single offered line from being volunteered (make `a_r1` non-speakable once the reunion has been delivered, or offer a line only
when the command concerns it), each its own prereg; (c) hold.

### Stage 2 status (2026-11-07): embrace text applied; corrected probe prepared, not billed

Brandon: "go with 1". The embrace is in the working tree (Ringer `shared-narrator-embrace`; `a_r1` and `a_r2` `delivery_text` and the `michelle_reached` fallback; no "Shelly"; opening cue unchanged; uncommitted). Finding: the scripted history never contains a delivery's text, so the planned c4/c5/c9 stage-2 payloads are byte-identical
with and without the embrace and would measure nothing. The embrace reaches the model only on the reunion turn ("the game will add this: <embrace> … Write only what leads up to it"). Corrected probe GUE1 is built and preregistered: 48 requests (R1 `Free the captives.`, R2
`Ask Michelle about the other sites.`, old versus embrace delivery), about 178 neurons, ceiling 216. Awaiting Brandon's approval of that cost (it is 12 requests and about 45 neurons above the 36-request figure he approved). Live stateful play follows and needs its own preregistered cost.

### GUE1 result (2026-11-07): the embrace text helps the second path a lot and adds four Brandon lines on the first

48 requests, ~178 neurons ([prereg, Experiment GUE1](shared-narrator-instruction-conflicts-prereg.md)). Second path (ask Michelle about the other sites): with the old delivery text all 12 lead-ups had Michelle give the answer and the game then repeated it; with the embrace text 0/12 do (composed turn coherent 12/12, from 0/12).
First path (free the captives): the embrace adds no hug in the lead-up (1/12 pre-empt) and the composed turn is coherent 12/12, but Brandon speaks a line before the reunion in 4/12 replies against 0/12, so the written rule (EXTRA at most 1/12) is missed on that one item. The lead-up goes to Brandon rather
than Michelle in most R1 replies in both arms (pre-existing). Next: the live stateful study, which needs its own preregistered cost; Brandon's call on whether four Brandon lines in the lead-up matter.
