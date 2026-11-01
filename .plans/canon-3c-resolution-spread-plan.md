# Scene 3C: spread the earned resolution across turns

Status: investigation complete; proposals below are unapplied. Written against
`4fc9dd77e5c582b3ecdadda5bc43aa0ca8808a4d`. No code, package, generated fixture,
or runbook was changed. No tests or billed calls were run. Only this plan was
created. Existing dirty plans were left alone.

Resume here: review the proposed canon-script replacement, then implement and
run the free checks below. Preserve the original hosted artifact as the baseline.
This plan does not authorize a hosted run or a story edit.

## Finding

**The existing earned-reveal path can spread 3C across separate turns. The
recorded canon script fails to exercise it.** It never requests the surface
gates or engages the families. Its broad assessment and unnamed fragment
commands also miss the current exact evidence vocabulary. At turn 14 the
intentional resolution backstop supplies the remaining chain, and the ordinary
ending appends a second summary. This is not evidence that resolution events
must always wait until the last turn.

Correct the script before changing the story or engine. This proves a scripted
route is reachable; it will not prove that an uninstructed player discovers
the route, that the narrator carries out movement correctly, or that every
resolution fact gets its own turn. Those are different claims.

## Evidence and cause

`P` below means
`bench/results/staged-1abb54b0/canon/e2e-llm-canon-progress.json`.
Line citations refer to the actual artifact, not its rendered Markdown.

| Scene turn | Evidence | What happened |
| --- | --- | --- |
| 1 | P:3988–4056 | A-R1 delivery broadcasts the evidence and points to Rebecca. `truth_no_longer_containable` commits. |
| 2 | P:4060–4126 | B-R2 delivery captures Rebecca and says Charles escapes. Archive/capture facts commit. |
| 3 | P:4130–4194 | C-R1 restores pumps and holds the barrier; only `evacuation_route_open` commits. This is not completed escape. |
| 4 | P:4198–4253 | Broad assessment earns no reveal. Collapse pressure commits. Player text explicitly says the surface gates remain shut and authorization is expiring. |
| 5 | P:4256–4304 | The fragment request earns nothing; prose returns to restoring pumps. |
| 6–9 | P:4307–4518 | The five-input cycle replays broadcast, archive, pumps and assessment. No new reveal or fact delta. |
| 10 | P:4521–4571 | Fragment again earns nothing; `escape_routes_collapsing` is timed pressure, not a player-earned reveal. |
| 11–13 | P:4574–4734 | Broadcast/archive/pumps repeat. The gate warning appears again on 11. Still no gates, reports or families action. |
| 14 | P:4737–4839 | No selected reveal. Four `route_fallback` spans deliver escape, network consequences, Phase Two and completion; ten fact predicates commit at P:4801–4812. The ending follows. |

The first three turns do return substantive authored consequences. The long
empty stretch starts after them; describing all pre-final turns as empty would
hide the precise break.

`frontend/e2e/canon-journey.js:72–88` contains five commands and cycles them
modulo five. Repetition cannot invent the missing gate or families action.
`knowledge.yaml:2847–2874` gives the gate reveal, `k_sl_3c_c_r2`, surface-gate
or authorization evidence; it belongs to **SL-3C-F**, despite its knowledge ID.
Pumps are **SL-3C-C**. `storylet-routes.yaml:3063–3077` requires both storylets
for ordinary `resolution_escape`, which produces `captives_reaching_surface`.

That fact gates both reports and families (`knowledge.yaml:2875–2936`). Both
**SL-3C-D** and **SL-3C-G** are required by `resolution_network_consequences`
(`storylet-routes.yaml:3082–3107`). That event supplies `charles_at_large`.
Both E variants require that fact plus network fragmentation and escape
(`knowledge.yaml:2937–3015`). Thus reports alone do not unlock E, and prose
saying Charles escaped on turn 2 does not substitute for the missing fact.

The broad assessment does not match the reports action groups; the recovered
“fragment” is not the recovered “document”/JANUS-file evidence phrase. More
fundamentally, D and E are still ineligible in this recording. Do not diagnose
those blocked reveals as only synonym misses or widen the matcher to bypass
the prerequisite chain.

`CanonicalEventMixin._apply_canonical_route_events`
(`storygame/runtime/canonical_events.py:13–35`) requires all realization
storylets before committing a resolution event. Its loop can commit multiple
ready events in one turn; it is not a one-event-per-turn scheduler.
`_apply_resolution_deadline_backstop` (:50–82) deliberately bypasses that
storylet requirement at the deadline, commits ready events in declaration
order, emits their fallback text, and marks their storylets shown. Each event
can enable the next in the same accepted turn.

`pacing.yaml:288–291` sets 3C's deadline to 14. The accepted-turn path calls the
backstop (`engine.py:367–379`). `_finish_ending` (:742–756) appends `ending.text`
when `phase_two_conflict_plan_known` is true (`pacing.yaml:363–380`). That is why
P:4738 has four fallback paragraphs plus the authored ending. The completion
marker is not another player action, and fallback-produced facts are not
selected-knowledge reveals.

The recorded narrator request at P:4204 and P:4262 says “This turn has no
candidates.” It also repeats the pump/tunnel statement, immediate escape
pressure, and voiceable broadcast/archive material. This explains the material
available for repetition; it does not isolate a causal prompt fix. Several
`prompt` fields (P:4068, 4138, 4425) are name-matching requests, not narrator
requests. Do not pretend those fields preserve every original narrator call.

The relevant 3C package sections and canon script have not changed between
`1abb54b0` and this HEAD. The scoped git comparison found two earlier-scene
text deletions, in 3B delivery and 3A pacing. It does not establish identity of
the entire runtime or deployed configuration.

## Authored intent and timing

The plot explicitly allows fast earned play (`plot.md:51`):

> The player may move more quickly by pursuing the central objective, but fast play still has to earn the scene's major change.

Its 3C row (:63) allocates 14 turns:

> Win the broadcast contest; secure the archive; guide the evacuation; absorb the national consequences and Phase Two.

The authored sequence is:

1. **Transmission and contest** (:845–859): “Charles interrupts the transmission
   and claims Michelle is part of a terrorist organization.” Michelle answers
   with live facility images; the truth escapes single-channel control.
2. **Archive and capture** (:865–875): “Rather than destroy it, Michelle
   transmits copies to several independent networks.” Rebecca is captured;
   Charles escapes. Archive preservation matters to rescuing prisoners.
3. **Two evacuation tasks** (:881–891): Kristin restores drainage and holds a
   barrier; “Michelle uses the senior official's expiring authorization to
   release the emergency surface gates once.” Captives then emerge into LA.
4. **Consequences** (:897–910): some sites surrender, others remain contested;
   communities organize rescues and families learn the missing may be alive.
   Michelle publishes; Kristin joins rescue teams.
5. **Final reversal** (:914–918): “The final revelation comes from a partially
   recovered JANUS file.” Phase Two provokes conflict among survivors; Charles
   watches unrest and hopes fear will restore his power.

Storylet target/latest pairs are A 3/4, B 7/8, C and F 11/12, D and G 13/13,
E 14/14 (`storylet-routes.yaml:2480–2749`). All have earliest turn 0. These
targets express pressure preferences, not a mandatory schedule. Ordinary
gating allows C/F in either order and D/G in either order. E waits for both D
parts through the network event. Existing tests explicitly cover these orders.
The authored targets also put both D parts at 13; they cannot be treated as a
literal one-reveal-per-turn itinerary followed by E at 14.

**Pacing budget retained:** `pacing.yaml:1` is `budget_seconds: 7200` (two hours).
Keep that, the plot's 120 accepted-turn maximum, and 3C's `min_turns: 10`,
`nudge_after_turns: 11`, `handoff_after_turns: 14` unchanged. Seven distinct
earned actions fit inside 14; they do not require seven additional turns.
The ending predicate does not enforce the scene's minimum-turn window, so a
focused route may finish before turn 10. Do not insert idle inputs to hit a
target or claim a real-time two-hour measurement from a package-clock run.

## Proven mechanisms and earlier fixes checked

Read the PRD, contributor boundaries, workflow, player-input and narrator
guides, scene-fixing and grounding guides, pacing/incidents, knowledge/disclosure
and route-resolution authoring guides, plus the local-checks, prompt-inspection
and hosted-probes runbooks. Code discovery used the existing codebase-memory
index; Serena was not available. No symbol edits were needed.

Checked the current world-model checklist and historical W1–W14 record at
`5ea0119955c62b84699a8dc7878a4af770b55a7e`, including its amendments. No new
entity, placement, spatial phrase parser, or story-specific runtime branch is
needed. Scene-fixing precedent includes the 3B missing office-entry material,
3A captives talk line, and 2C silent/stale-recall fixes documented in that guide:
inspect the actual request, remove the conflicting source, and hand off missing
story material before inventing a narrator rule.

Also checked `.plans/chatgpt-3c-after-escape-plan.md`, the option-3 route plan,
and the 3C results in `.plans/implementation_plan.md:998–1010`. Surface binding
and the C1 completed-state rewrite lost their screens; neither belongs in this
fix. Entry wording improved first-action delivery, custody wording reduced
retaking, and pump wording improved earning both C parts, but those improvements
did not establish reliable earned endings. The later D/E diagnosis and
`tests/test_3c_cue_chain.py` establish the need for distinct family engagement.
The after-escape plan's synthetic rows demonstrate that removing the escape
close does not cure the loop; retain it.

`tests/test_resolution_cascade.py:45–130` already exercises no premature
cascade, deadline completion, and both D orders followed by earned E.
`tests/test_3c_cue_chain.py:40–110` already lists matching commands for pumps,
gates, reports, families and recovered document. These are inspected existing
tests, not fresh passing results. This proposal uses those existing techniques.
The new seven-command canon composition is **unmeasured**, not a new mechanism.

## Proposed changes: exact text, checks, risks

### 1. Replace the incomplete canon script

Classification: **test/harness input change; no plot, pacing or story-data
change.** This changes what the scripted player attempts, not what the engine
accepts. Remove the vague/redundant inputs before adding any runtime behavior.
Keep `promptFor` cycling and all existing journey budget/completion checks.

File: `frontend/e2e/canon-journey.js`, entire 3C array.

Old:

```js
  "3C": [
    "Open the broadcast with Michelle and push the evidence out - the captives, the selection records, the locations.",
    "Stop her leaving with the portable archive and copy it out to independent networks.",
    "Hold the emergency supports while the prisoners are led up through the maintenance tunnels.",
    "Assess what this has changed across the country, and what it has not.",
    "Read the recovered fragment describing what was meant to follow all of this.",
  ],
```

New:

```js
  "3C": [
    "Send the evidence package.",
    "Copy Rebecca's archive.",
    "Restore the drainage pumps.",
    "Open the surface gates.",
    "Check reports from other detention sites.",
    "Call the families of the missing.",
    "Open the recovered document.",
  ],
```

All seven are active imperative commands with concrete objects. The first three
use existing matcher-test wording and target the same A1/B2/C1 realizations as
the recorded run. The new gate command earns F, then the two consequence
commands earn D/G, then the file earns E1. Do not combine reports and families
into one compound command: exact-handoff uniqueness can refuse a tie.

Cheapest free check: inspect the existing command expectations, then run the
focused matcher/chain tests and the real offline journey after applying this
change in the implementation task:

```sh
TMPDIR=/tmp uv run pytest -q tests/test_3c_cue_chain.py tests/test_resolution_cascade.py
```

Use the existing `simulate_expected_reveals` path for the whole-story replay.
Its provider assembles prompts, filters eligibility and uniquely matches a
handoff without dispatching a request (`scripts/generate_spine_expected_reveals.py:43–70`).
For the progression check, inspect per-turn runtime records as well as the
returned set: expect A1, B2, C1, C2, D1, D2, E1 on distinct accepted actions,
escape only after both C parts, E only after both D parts, and no deadline event
IDs on the earned completion. A sorted reveal set alone cannot prove spacing.

What could break: carried state or earlier pacing can make a candidate
ineligible; an unforeseen match tie can return no handoff; player movement may
still be wrong in live narration. Explicit test language reduces linguistic
coverage and makes this a directed canon demonstration, not a blind-player
quality measurement. Preserve the old sample for comparison.

### 2. Regenerate the expected reveals from the approved script

Classification: **generated test fixture change; no story-data change.**
File: `frontend/e2e/spine-expected-reveals.json`. Never hand-edit it.

Old 3C member:

```json
  "3C": [
    "k_sl_3c_a_r1",
    "k_sl_3c_b_r2",
    "k_sl_3c_c_r1"
  ]
```

Expected new member, subject to actual replay:

```json
  "3C": [
    "k_sl_3c_a_r1",
    "k_sl_3c_b_r2",
    "k_sl_3c_c_r1",
    "k_sl_3c_c_r2",
    "k_sl_3c_d_r1",
    "k_sl_3c_d_r2",
    "k_sl_3c_e_r1"
  ]
```

Cheapest free check and generation, after change 1:

```sh
uv run python -m scripts.generate_spine_expected_reveals
TMPDIR=/tmp uv run pytest -q tests/test_spine_expected_reveals.py
```

Inspect the diff: all other scene members must be unchanged, including 2C C-R2.
The generator executes the real runtime for at most 120 turns and writes only
in `main` (:73–103). Do not run its writing entry point during this plan-only
task. If output differs from the expected block, diagnose it instead of editing
the output to match the plan.

What could break: generated expectations can faithfully encode a stalled route,
as the old three-ID member demonstrates. Require the temporal check in change
1 rather than declaring success merely because fixture generation completes.

### 3. Correct the existing replay runbook description

Classification: **documentation change; no story-data change.** Proposed for
the implementation task, not applied here. In
`docs/testing-runbook/local-checks.md`, the spine-expectation row currently ends:

Old:

> Expectations keep player-visible matches in prompt order, spend each source storylet once, and retain 2C C-R2. They do not simulate pacing or provider behavior.

New:

> The generator replays the real runtime with a network-free scripted provider that assembles prompts and selects eligible exact handoffs. It retains 2C C-R2 and writes sorted per-scene reveal sets. Inspect turn records separately to verify reveal order, spacing and deadline use; this replay does not measure live narration or semantic fallback behavior.

Cheapest free check: compare this wording with generator lines 43–103 and the
actual generated output. No new test required. Risk: overstating offline/live
parity; the explicit boundary prevents that. This is a correction to an existing
entry, not a new dated diagnosis entry.

## Story changes deliberately not proposed

**No plot, pacing, handoff, knowledge, world or route-data edits are proposed
for the first fix. Any later such edit requires Brandon's approval before
application.** No exact old/new story patch is hidden behind a general request
to “improve pacing.”

Keep the deadline fallback: it guarantees an ending for players who miss
actions. Removing realization gates would commit consequences before earning
them; increasing the deadline would conceal the missing actions. Lowering
targets would not add those actions to this script. A new rule that trickles
one fallback event per turn would be a **new, unproved runtime mechanism**;
neither the route guide nor current code supports that proposal.

Keep the ending text for this first fix. On the ordinary path, network
consequences commit Michelle's publishing, Kristin's rescue work and Charles's
at-large fact without a `delivery_text`; the ending still supplies that closure.
Deleting the summary wholesale would lose player-facing material. Spreading
the earned gate, reports, families and file turns removes the four-event final
fallback pileup but does not make the final response free of recap.

The file E1 delivery does not include the full Charles-watching coda that E2
delivers. A1 likewise does not deliver every line of the broadcast contest.
These are existing realization coverage limits, not permission to invent a
second same-storylet reveal or silently rewrite the plot. If full beat fidelity
remains a requirement after the progression fix, review the composed replies
and propose separate exact story-text edits for approval.

## Limits, acceptance and implementation order

1. Review changes 1–3 and preserve P. Coordinate with the separate canon-stall
   plan: its unchanged-prompt harness-validation sample serves a different
   comparison and must not silently use this revised script.
2. Apply only the script replacement; inspect exact eligible matches and the
   carried whole-story offline progression. Stop on a tie, missing fact or
   unexpected deadline; do not broaden aliases automatically.
3. Regenerate the fixture and run focused checks. Record actual reveal turns,
   completion turn and deadline IDs here. Correct the runbook entry. Complete
   the normal implementation checks from the workflow before merge.
4. If a live quality test is later authorized, follow SHA-bound staging and the
   existing hosted runbook, with explicit attempt/cost limits. Read complete
   replies, including authored spans, and distinguish earned from deadline
   completion. No paid experiment is authorized by this document.
5. Only then consider independently evidenced discoverability or narration
   fixes. Reuse the scene-fixing workflow; do not revive losing surface-binding,
   C1-rewrite or broad-alias experiments without new evidence.

Free acceptance is separate earned steps before the unchanged deadline, correct
prerequisites, no premature E, and completion within the unchanged 120-turn /
7,200-second authored envelope. Live acceptance must additionally establish
coherent prose and visible transitions; facts alone are insufficient.

Unverified: the proposed script has not been executed; current test results,
live semantic selection, movement/custody consistency, blind-player discovery,
and actual wall-clock duration are unknown. The archived sample is one run,
not a reliability estimate. Recorded matcher requests cannot reconstruct missing
narrator requests. Earlier synthetic screens are precedent with their stated
limitations, not proof of this new whole-story composition.

Investigation used read-only source/artifact inspection (`jq` on P, indexed
code search, numbered source reads and a scoped git comparison). No environment
credentials, external service, staging mutation, test execution or generated
artifact write was needed. Cleanup: none. The testing-runbook-creator skill was
consulted; the explicit plan-only scope takes precedence over applying its
runbook edits now.
