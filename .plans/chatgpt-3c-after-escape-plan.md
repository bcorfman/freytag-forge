# Scene 3C after the escape: evidence and next experiments

Written 2026-10-22 against `09bba8520c61cd2989c490eedd8a3f363e3efa93`.
Replaces the earlier version of this plan. Status: investigation complete;
candidates below are **unimplemented and unmeasured**. This task changes this
document only. No implementation, paid calls, deployment, or plot edits.

**Resume here:** preregister proposal 1's isolated entry-line subtraction, then
inspect its free payload diff. Do not implement the former plan's console,
Michelle relocation, reunion fact, or new location prerequisites. Do not rerun
the losing surface binding, C1 rewrite, A1 rewrite, or families aliases.

The rows show two failures: completed evacuation becomes another urgent
evacuation, and the reports/families continuation fails to become an earned
ending. The common mechanical finding is that **none earns D2**. The strongest
counterexample to a placement-only fix is row D: the narrator sends captives
back into the tunnel even when their surface location is in its prompt. The
ending dependency already requires both D parts; it does not need a new gate.

## Evidence read and boundaries

Read all four prefixes and every continuation turn in full, including complete
final replies, cues, reveals, places, and available capture records. Read all
seven package files: `plot.md` (including 3A–3C), `world.yaml`, `knowledge.yaml`,
`storylets.md`, `storylet-routes.yaml`, `handoffs.yaml`, and `pacing.yaml`.
Read the PRD and the contributor, workflow, grounding, player-input,
narrator-writing, scene-fixing, testing, authoring, and promotion guidance.

Historical comparison includes relevant `implementation_plan.md` entries,
the stuck-turns and option-3 plans, the carried-row diagnosis, and the
surface-binding, escape-result, recall-live, broadcast-live, broadcast-result,
earn-when, families-v2, relay-access and escape-close preregistrations/results.
Also read the current world-model checklist and historical W1–W14 decisions in
`5ea0119955c62b84699a8dc7878a4af770b55a7e`. Historical custody descriptions do
not override today's declarations.

Code discovery used indexed codebase-memory tools; Serena was unavailable.
Inspected canonical-event application, deadline backstop, knowledge projection
and visibility, scene-entry assertion, prompt rendering, cue composition,
package validation, and existing D/E tests. Source inspection is not a claim
that those tests were run in this task.

| Key | File and row |
| --- | --- |
| A | `bench/results/stage7-3c-escape-close-smoke/rows.json`, `arm=item-facts` |
| B | Same file, `arm=no-close` |
| C | `bench/results/stage7-3c-relay-access-maintenance_network/rows.json`, `arm=control` |
| D | `bench/results/stage7-3c-world-capture-row/rows.json`, `arm=item-facts` |

Turn citations mean select `turns` by `scene_turn`, then the named field. This
is more precise than a physical line inside a long JSON string. A/B/D save
requests at `world_capture.after.narration_prompt.{system,user}`. Read the full
base request and lossless differences for every subsequent saved request. C
has no saved narrator requests; current source cannot recover its exact inputs.

All rows are labelled **synthetic post-turn-7**, with A1/B1/C1/C2 already
committed. `accepted_turns=14` includes that starting index; there are seven
continuation turns, 8–14. C/D prescribe the first command; A/B let the blind
player choose. C has no product place capture. These differences prevent
pooling or treating the two smoke rows as a success-rate estimate.

Raw commands below are quoted evidence, including recorded bare `look`, not
new recommended inputs. Proposed test inputs use imperative commands.

## The four prefixes

These four authored actions occur in every prefix. They are not live narrator
performances or a complete historical account of turns 1–7.

| Action | Result and diagnostic consequence |
| --- | --- |
| `Send the evidence package.` | A1: Michelle broadcasts; Rebecca leaves with the case. Exposure is established before continuation. |
| `Take the Portable data case from Rebecca.` | B1: Kristin takes the case, Michelle sends locations, pumps need power. These rows have no subsequent case-retaking failure. |
| `Restore the drainage pumps.` | C1: Kristin restores power and holds a barrier; Michelle leads captives through the tunnel. Completed reveal, but present-tense statement persists. |
| `Open the surface gates.` | C2: Michelle releases gates; Brandon keeps the relay open. A/C/D then deliver the escape close. B omits only that close. |

`storylet-routes.yaml:2862` says:

> The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving.

It then says reports and families' calls reach the chamber and the barrier
keeps the return route open. It **does not** reveal sites surrendering (D1) or
families organizing rescues (D2). Naming the next information sources does not
steal those reveals. It also does not explicitly put Kristin and Michelle on
the surface.

A/B's harness starts Kristin on the surface; C/D start her in maintenance.
The original captives group starts in maintenance despite the escape fact.
D's capture moves that group to the surface on turn 8; turn 9 still reverses it.

## Per-turn diagnosis

“No reveal” means no committed knowledge reveal, not no information in prose.
A staged cue is distinguished from actually delivered text. The complete reply,
including appended authored delivery and deadline text, determines the reading.

### A — close, blind first command, product capture

| Turn | Recorded action and decisive response | Diagnosis |
| --- | --- | --- |
| 8 | `Go to the broadcast chamber` → “She walks into the broadcast chamber.” Michelle: “We need to get out of here, now.” D1 cue appended. | Return succeeds in prose/capture. Close directs player toward reports, but narrator reinstates escape urgency. Kristin at chamber, original captives in maintenance. No reveal. |
| 9 | `Listen to the reports.` → Michelle says, “Michelle broadcasts captives, JANUS records, planning sessions, and detention locations to independent networks.” Appended delivery says sites surrender/release prisoners. | **D1 earns.** Lead-up copies permitted speech, but composed reply delivers D1. D2 recorded as staged, absent from response; do not claim player saw it here. |
| 10 | `Go to the surface` → rush through maintenance tunnel, Michelle leads captives, water closes in. D2 cue appended. | Moves to maintenance, not destination. Capture resolves `captives` as `new`, creates `n_captives_1` beside original group. Saved system has a recovery instruction after unavailable-thing narration; initial failed prose is not saved here. |
| 11 | `Continue through the maintenance tunnel to the surface` → “She moves forward,” Michelle whispers. D2 cue appended. | No arrival/reveal; Kristin remains maintenance. Player repeats destination rather than answering families. |
| 12 | Same command → “She leads Michelle through the maintenance tunnel,” damp earth and rust. No staged cue. | Another incomplete movement; completed escape remains underway. |
| 13 | Same command with period → “She moves forward,” Michelle follows whispering. No staged cue. | Repeats turn 11; no reveal/arrival. |
| 14 | `Keep moving through the maintenance tunnel toward the surface.` → tunnel travel and Michelle broadcasting, then full deadline resolution. | No D2/E. Backstop supplies network consequences, Phase Two, completion. Not earned progression. |

The first derailment, A8's renewed urgency, precedes the duplicate group. A10–14
are five consecutive destination-directed travel attempts without arrival.

### B — no close, blind first command, product capture

| Turn | Recorded action and decisive response | Diagnosis |
| --- | --- | --- |
| 8 | `Leave the facility through the surface gates` → “They step out into the night air,” gates slam shut. D1 cue appended. | Narrates exit although harness already puts Kristin on surface. Closure competes with cue inside facility. No reveal. |
| 9 | `look` → searches for Michelle; “none of them seem to be Michelle.” D2 cue appended. | Prompt THINGS says “With Kristin: Michelle.” Narrator invents separation, inviting search. Still surface. |
| 10 | `Look for Michelle.` → Michelle “a few blocks away.” | Continues invented search/reunion. No D reveal; not evidence for a mandatory new reunion. |
| 11 | `Approach Michelle` → “we have to move, now,” pulls Kristin toward maintenance tunnel. D1 cue appended. | Narrator initiates reversal from surface to tunnel without the escape close. |
| 12 | `Follow Michelle through the maintenance tunnel.` → follows through damp earth and mold. D2 cue appended. | Capture moves Kristin to maintenance. No D action/reveal. |
| 13 | `Continue through the maintenance tunnel.` → footsteps, damp earth and mold. No staged cue. | Incomplete movement with no new destination/source. |
| 14 | `Keep following Michelle through the maintenance tunnel.` → captives led through winding tunnel, then deadline ending. | No D1/D2/E earned; ending interrupts ongoing passage. |

Removing the close does not remove this row's loop. One row per arm cannot
establish its effect overall. A earns D1 at 9; B never earns it. Preserve that
difference instead of reporting two equivalent failures.

### C — relay-access control, scripted first command, no product capture

| Turn | Recorded action and decisive response | Diagnosis |
| --- | --- | --- |
| 8 | `Follow Michelle and the captives through the surface gates.` → gates “creak open,” group into night. D1 cue appended. | Script re-requests passage after prefix completion. Prose completes it. Maintenance telemetry is not product movement evidence in this arm. |
| 9 | `Return to the broadcast chamber.` → bursts through door; Michelle typing, mouths “it's working.” D2 cue appended. | Prose return succeeds. Does not demonstrate need for new location gate or console. |
| 10 | `Listen to the incoming calls.` → checks “her phone,” unknown number, “Hello?” | Invents phone and anonymous caller instead of connecting to families. Listening differs from current D2 engagement. No reveal. |
| 11 | `Continue listening to the caller.` → distorted voice, urgency/desperation without information. D1 cue appended. | Generic suspense replaces answer; no reveal. |
| 12 | `Ask the caller where they are calling from.` → repeats question aloud, no answer. D2 cue appended. | Conversation fails to advance. Anonymous caller is neither identified family nor site report. Semantic fallback ON does not explain its refusal reason. |
| 13 | `Listen to the caller.` → another “Hello?” and urgent voice. | Repeats call setup, no reveal. |
| 14 | `Ask the caller who they are looking for.` → repeats question, then deadline ending. | No substantive answer or D/E reveal before backstop. |

This supports cue/action disconnect and generic dialogue failure. It does not
show a current product movement-engine regression or identify a specific saved
prompt line causing the phone invention: neither capture nor prompts are here.

### D — earlier product-capture row, scripted first command

| Turn | Recorded action and decisive response | Diagnosis |
| --- | --- | --- |
| 8 | `Follow Michelle and the captives through the surface gates.` → emerge on Los Angeles streets; Michelle: “We have to get them to safety.” D1 cue appended. | Kristin and original captives move to `facility_escape` in capture. New safety demand reopens finished rescue. |
| 9 | `Help Michelle get the captives to safety` → Michelle “is leading the captives through the maintenance tunnel.” D2 cue appended. | Prompt gives both captives/Kristin “Place: Los Angeles surface.” Narrator contradicts it; capture moves them back. Surface placement alone is insufficient. |
| 10 | `Escort the captives through the tunnel to safety.` → rushing water, “We need to move, now.” | No arrival/reveal; urgency sustains repeated task. |
| 11 | `Lead the captives through the tunnel to the surface.` → they “begin to move through the tunnel.” D1 cue appended. | Starts rather than finishes requested passage. |
| 12 | `Lead the captives through the tunnel to the surface gates.` → more tunnel travel. D2 cue appended. | Captives proposed `held_by: Michelle`; guard refuses a group inside a person. Item-fact refusal does not reject whole turn; loop predates it. |
| 13 | `Return to the broadcast chamber.` → “She emerges into the broadcast chamber.” | Prose and capture complete return. Raw capture leaves Michelle in maintenance. No reveal. |
| 14 | `Listen to the reports from the other detention sites.` → reports heard, authored D1, then deadline resolution. | D1 earns, too late for D2/E. Still `deadline_complete`, not earned because a reveal occurred on final turn. |

All rows have zero rejected player turns and zero clarifications. A nonetheless
has a recovered narrator guard attempt; D has refused item facts. Zero rejected
turns does not mean no provider/capture problems. Every row lists these deadline
events: `resolution_network_consequences`, `resolution_phase_two`,
`resolution_complete`.

## Causes, ownership, and deciding lines

### 1. Completed work is still presented as immediate work

**Package-data problem in the prompt; causal contribution not isolated.**
`knowledge.yaml:2915` says:

> Exposure and escape are both immediate under the collapsing operation.

`knowledge.yaml:274` supplies `pressure: Expose the network and escape`.
Both persist in saved post-escape SCENE. C1 says:

> Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads captives through the maintenance tunnel.

A1's broadcast sentence occurs once in SCENE and again as permitted speech
for Michelle and Rebecca. A9 literally speaks it. This demonstrates projection
material leaking into narration, but **not** that rewriting A1 fixes progression;
that experiment lost.

`knowledge.py:316`, `_committed_for`, includes established visible knowledge
from the current scene. `cloudflare.py:1496` onward puts pressure/current-scene
statements in SCENE; line 1554 emits NPC “may say this aloud” statements.
`knowledge.py:291` excludes public entry framing from NPC speech, not SCENE.
No completed-beat suppression contract is being violated by the engine. Test
an offending source before proposing global suppression rules.

The escape close is delivered once; `k_resolution_escape` is world-only
(`knowledge.yaml:2808`). It is not persistent completion narration in these
requests. This explains the difference between player transcript and narrator
context. It does not justify publishing every canonical summary, adding full
history, or repeating the close every turn.

### 2. Families cue invites incoming-call listening; D2 requires engagement

**Package-data alignment problem, with observed narrator failure.**
`plot.md:918` says reports arrive as families call for news.
`handoffs.yaml:360` says:

> Families of the missing call the broadcast chamber for word.

`knowledge.yaml:2650` instead says `earn_when: calls the families of the missing`.
Its evidence group at 2652 includes `answer the families`, `tell`, `inform`,
`contact`, and rescue participation, not generic `listen`. The recipient group
requires families/missing/rescue meaning, not any caller. C naturally listens
to incoming calls but becomes trapped with an unidentified caller. The other
rows mostly never attempt family engagement.

This does not establish that listening must earn D2. D2 is families organizing
rescues after receiving news. Preserve that meaning and offer the existing
supported action clearly before broadening matching. Prior alias losses do
not authorize another vocabulary patch.

### 3. D2 is already required for E, indirectly

**Expected engine behavior; package dependency, not missing engine gate.**
E1 requires `national_network_fragmenting` and `charles_at_large` at
`knowledge.yaml:2695`; E2 has the corresponding dependency.
`storylet-routes.yaml:2866` supplies `charles_at_large` via network consequences;
its realization list at 2888 contains both `SL-3C-D` (D1) and `SL-3C-G` (D2).

The deciding code, `_apply_canonical_route_events` in `canonical_events.py:13`:

> `if event.id in resolution_ids and not all(storylet_id in self.state.fired_event_ids for storylet_id in event.realization_storylets): continue`

Ordinary path: both C parts → D1 and D2 → network event/`charles_at_large` → E
→ completion. A9's D1 alone cannot unlock E. Existing
`tests/test_3c_cue_chain.py:264` tests both D orders and E waiting for both.
The former plan's claim that D2 was not a prerequisite was wrong.

`canonical_events.py:50`, `_apply_resolution_deadline_backstop`, intentionally
commits ready resolution events at deadline without waiting for realization
storylets. `pacing.yaml` sets 3C's handoff deadline to 14 and ending trigger to
`phase_two_conflict_plan_known`. This explains the automatic endings. Nothing
here warrants changing the algorithm, bypassing D2, or extending the deadline.

### 4. Physical grounding is inconsistent; the simple correction already lost

**Package-data omission plus narrator/capture failures, not one proven cause.**
`plot.md:832` places captives in maintenance; `world.yaml:385` declares bare
`captives_reaching_surface`, without `on_assert` movement. Thus completion does
not relocate the original group. This conflicts with the completed result in
`plot.md:903`, “Thousands of captives emerge into Los Angeles,” and the close.

But the surface-binding screen tested precisely that move: consistency 9/12
against a 10/12 bar, earned endings 3/12 against control 7/12. Not adopted.
D9 shows failure even with surface placement present in the product prompt.
Do not prescribe the same binding again, alone or inside a bundle, as a cure.

A10's added facts include `wk_kind|n_captives_1|None|group` and its maintenance
parent; the original group remains. Capture says `same_as: {captives: new}`.
This is a reference/capture identity failure requiring an isolated reproduction.
D12's `held_by` refusal is a different malformed proposal; the guard correctly
refuses a group inside Michelle. Neither licenses a teleport, automatic alias
shortcut, or story-specific engine exception.

### 5. Michelle's itinerary needs authorial resolution before spatial redesign

**Plot ambiguity and package representation concern.** Deciding lines:

> `plot.md:897`: Michelle leads the prisoners through the maintenance tunnel while Kristin keeps the pumps and barrier working.

> `plot.md:901`: From Rebecca's office, Michelle uses the senior official's expiring authorization to release the emergency surface gates once.

The plot does not explain her intervening return or say she leads remotely.
It may intend a return, rather than an impossible story. Package
`companions: [michelle]` at line 819 also does not express the separation while
Kristin maintains the barrier. A co-located companion following Kristin is
consistent with the declaration, not proof companion following is broken.

3A already includes rescue/reunion; 3B continues their cooperation. B9's new
missing-Michelle search contradicts THINGS, not a missing reunion gate.
3C spans office, facility and surface (`plot.md:837`); the scene's
`location_id: facility_escape` does not mean everybody belongs there at entry.

**No plot change is proposed for application here.** Replacing physical escort
with remote guidance, adding a return journey, or making reunion another earned
ending beat is a **plot change requiring approval first**, then coordinated
package work. These rows do not select one of those stories. Do not silently
encode the former plan's preferred itinerary in placements.

### 6. No new device or spatial earning prerequisite is demonstrated necessary

**No demonstrated missing engine gate or world object.** The chamber is already
declared beneath the executive office (`world.yaml:60`). Return succeeds in
A8, C9 (prose), and D13; reports earn in A9 and D14. Current D/E entity lists do
not require a console, and predicates do not test Kristin's room. The plot
already supplies the communication source. A console adds an interaction to
introduce/ground/match without addressing D2 or tunnel repetition. A chamber
location prerequisite makes earning stricter without evidence it solves this.

## Historical results that constrain the next work

| Earlier work | Result | Consequence |
| --- | --- | --- |
| 1A framing subtraction, #668, `implementation_plan.md:957` onward | Control re-entered house 9/10; shortened entry statement 0/10, reading 10/10. | Proven technique: isolate/remove stale framing. Does not prove a 3C candidate wins. |
| 2C earlier-scene recall, historical world-model decisions | Person-only recall suppression removed observed Brandon/corridor drift in the small follow-up; heading-only treatment did not reliably fix it. | Scope offending context; do not pile on narrator rules. Different category from current-scene C1/A1. |
| 2B/3C entry and custody/pump handoffs | 3C first-action A 12 vs 1; custody retakes 15 commands in 10 rows → 4 in 1; pump both-C-by-10 10/10 vs 5/10 in incomplete n=12 run. | Make existing action/source/result concrete. Local gains, not proof of earned endings. |
| Surface binding, `astra-3c-surface-binding-prereg.md`, RESULT | Consistency 9/12 below bar; earned 3/12 vs 7/12. | Stopped; no repeat/bundle. |
| C1 rewrite, `astra-3c-recall-live-prereg.md` | Synthetic D-by-10 3/12 vs 7/12; earned 2/12 vs 5/12. Changed-context prompt finish 3/12 vs 6/12. | Stopped twice. Do not propose “The drainage pumps have power. The evacuation route is open.” again. |
| A1 rewrite, `astra-3c-broadcast-live-prereg.md`, RESULT | Finish 5/12 vs 7/12; broadcast drift zero in both. | Stopped; no A1 rewrite or C1+A1 bundle. |
| Families aliases v1/v2 | v1 earned 9 vs 8, indistinguishable; v2 9 vs baseline 10, misses bar. | Prefer baseline; no aliases mined from those sentences, no bare broadcast wildcard. |
| D2 earn-when expansion | Dropped preregistered idea, not demonstrated win. | Not revived by generic listening/absent family actions here. |
| Deadline 16 | Earlier conditional counterfactual for rows with both D parts already earned. | None here earns D2. More tunnel/phone turns are not a supported cure. |
| Close smoke | A earns D1 at 9; B never does; both deadline. | n=1 neither proves benefit nor harm. Hold close constant in next experiment. |

Static architectural neatness does not cancel the surface-binding loss. Seeing
stale C1/A1 sentences today does not justify retrying their losing replacements.

## Ranked fixes to test: exact edits, precedent, risks, cheapest probes

Ranking is experiment order, not measured efficacy. Each uses an established
technique; **both specific applications are new and untested**. Only an isolated
winner proceeds to source variation and continuation.

### 1. Remove redundant immediate-escape entry framing from projection

**Package-data subtraction; no plot/runtime change.** This specific entry-line
ablation was not tested in the reviewed record. Not the failed C1/A1 rewrite.

Recorded-prompt old line:

```text
- Exposure and escape are both immediate under the collapsing operation.
```

New: omit that one line with no replacement. Keep pressure, C1/C2/A1, THINGS,
command, system rules, selection, and composed delivery fixed. Test one demand
that is no longer immediate after escape, rather than every possible pull.

**Exact candidate source mapping, only if ablation wins:**
`data/stories/continuity-initiative/knowledge.yaml:2919`, `k_scene_3c_entry`:

```yaml
# Old
  audience: {kind: public, player_visible: true}
# New
  audience: {kind: world_only, player_visible: false}
```

Retain every other field. This retains the entry fact/source but omits redundant
framing from the narrator. `knowledge.py:391` already excludes world-only items
for all audiences; `state.py:263` asserts the entry fact independently. Existing
projection mechanism, new application to this entry item. It does not remove
the actual exposure/escape reveals or make the player forget them. Require the
source-to-payload check before claiming it implements the tested subtraction.

Do not simply delete `scene_frames[3C].pressure`: `SceneFrame` in
`story_package/models.py:162` requires nonempty pressure, and the loader requires
one frame per scene. No schema change to permit this experiment.

**Precedent:** #668 shortened stale entry framing. This proposal follows its
subtraction technique but uses existing audience visibility to omit the whole
redundant statement. That source mapping is new; its availability is not
evidence of narrative effectiveness.

**Cheapest probe:** offline extract A11's saved request for `Continue through
the maintenance tunnel to the surface` and diff a one-line omission. It is a
non-reveal turn and avoids A10's recovery-system confound. After preregistration
and paid-run authorization, sample 12 fresh control/12 subtraction replies,
interleaved, using the existing recorded-prompt replay approach. Read every
reply; surface `item_facts` without surface prose does not pass.

**Proposed triage bar:** candidate coherently finishes Kristin's requested
movement to the surface in at least 10/12 and three more than control, with no
new pump/gate reset, captive rescue restart, device invention or grounding
failure. Unusable replies count as failures; no replacement samples. Tie/miss
stops this candidate, not a license to remove C1/A1 too. This is a screening
rule, not a population success-rate claim.

**Risks:** loss of useful entry urgency; changes to bounded projection/reference
availability; remaining pressure/C1/C2 still dominates. Before source adoption,
compare actual fresh-entry, post-C and post-D payloads, entry truth, and reveal
eligibility. If the source mapping changes more than intended, stop and account
for the differences instead of calling it the same experiment.

### 2. Make the families cue offer its existing answer action

**Package-data handoff clarification, new wording.** No new object, place,
fact, earning predicate, or plot outcome. Uses concrete-action handoff technique,
not the failed alias approach.

Exact file: `data/stories/continuity-initiative/handoffs.yaml:360`,
`community_rescue_efforts_begun`:

```yaml
# Old
cue_text: Families of the missing call the broadcast chamber for word.
# New
cue_text: Families of the missing call the broadcast chamber for word. Kristin can answer the families with news of the captives.
```

Keep must-convey, fallback, D2 delivery, earn-when, evidence groups, facts and
prerequisites. The invitation does not pre-deliver rescue organization. The
chamber and families' calls already exist in the plot; this sentence does not
put Kristin there or invent a device.

**Precedent:** concrete existing-source/action handoffs in 2B/3C, especially
pump need. Those local gains do not prove an ending gain here.

**Cheapest probe:** offline first, run the real projected selector for
`Answer the families with news of the captives.` after both C parts, with D1
unspent/spent. Verify no early/spent D2 selection. Diff complete response with
cue appended; authored composition needs no narrator call. This checks current
matching; a surprise is not permission to add aliases.

Then a frozen-transcript player-choice screen can test the invitation: A's
transcript through turn 10, only final cue changed, 12 independent choices per
arm. Retain its competing tunnel task; do not invent an easier history. Feed
raw actions to the real projected selector and separately read whether each
actually engages families. The word “families” alone is not success. This
screen spends player calls only and does not test hosted semantic fallback.

**Proposed triage bar:** at least 10/12 choices genuinely answer/contact families,
at least three more than control, without a newly induced hardware/search
thread. Tie/miss stops wording; pass proceeds to continuation, not adoption.

**Risks:** prescriptive tone, answering from an implausible location, compound
reports-and-families commands tying the unique selector, or tunnel urgency
still winning. Do not patch those outcomes with gates/aliases/instructions in
the same arm. Read the resulting prose and complete action sequence.

### Held issues: no justified implementation patch yet

Michelle itinerary, missing canonical captive move, duplicate capture group,
and generic caller dialogue remain open. There is no supported implementation
edit for them today: the known surface patch lost, itinerary changes need a plot
decision, and an engine change needs an isolated story-neutral contract.
Inventing old/new engine lines before diagnosis would not make a sound fix.

Cheapest duplicate-group diagnostic: free replay of A10's captured match/capture
proposal against its pre-turn state. Check whether declared captives were in
the resolver's visible inventory and why `new` was accepted. Do not force names
to match or add production aliases. For D12 preserve a negative fixture proving
people cannot be contained in people; do not relax the guard.

## Sequential order of work

1. Freeze SHA/package, rows, selected requests. Preregister exact arm deltas,
   prompt hashes, models/transport, caps, scoring, failure handling and stop
   rules. Preserve losing-arm records. This request is plan-writing, not new
   paid-run authorization; follow the existing Ringer/runbook process later.
2. Proposal 1 free diff and source-mapping check in an isolated variation,
   without changing shipped data. If it cannot reproduce the one-line omission,
   stop before spending. No global renderer edit.
3. Authorized proposal 1 replay screen; read all complete replies, report
   denominators/recoveries/failures, stop on miss/tie. Record decision here
   before starting another experiment.
4. If it wins, validate source mapping and run a separate post-C continuation
   screen: 12 rows per arm, product capture, semantic ON, deadline 14, no
   scripted first command, fresh interleaved control. Keep current escape close
   in both arms. Do not reuse diagnostic rows as controls. Movement gain alone
   is not an ending fix.
5. Only after proposal 1's keep/stop decision, run proposal 2's free checks then
   player-choice screen. Both arms share the chosen baseline; disclose whether
   proposal 1 survived. Do not bundle two unmeasured edits or pool stages.
6. A local proposal 2 win gets its own continuation screen. For an ending-gain
   claim require at least 10/12 earned endings and three more than control,
   without new story-breaking failures. If both pass with fewer than three
   difference, prefer simpler baseline: addition is not shown necessary.
7. Validate survivors from carried entry through real 3B→3C crossing, then the
   scene-fixing guide's three live replicates with the scene check. Three is
   qualitative regression evidence, not an 80% rate claim. Preserve first-action
   A, case custody, both C orders, D/E progress and movement continuity.
8. Before adoption, run focused and required runbook checks; update this plan
   with commit, measured results and open defects. Later hosted checks follow
   main CI's SHA-bound staging deployment and promotion guide. No production
   promotion belongs to this plan-writing task.

Continuation measures: actual D1/D2/E turns/order, deadline IDs,
earned/deadline/no-completion, attempted/accepted turns, repeated evacuation
commands, requested movement finished in prose, original versus new groups,
Kristin/Michelle places, misleading urgency, caller/device inventions, guard
retries, refused/unplaced facts, raw selected actions. A final paragraph or
`story_complete=true` alone is insufficient; E must earn without deadline
backstop supplying the result.

Preserve partial artifacts on failure: no replacement malformed samples,
top-ups, undocumented retries, pooled controls, or desired-answer hints to the
blind player. Keep synthetic starts explicitly labelled. If both proposals
stop, return to an untested source mismatch or authorial ambiguity; do not
assemble a bundle from losing arms.

## Tests to reuse or extend

No tests added in this documentation task. Future implementation should extend
behavior coverage, not pin a sentence and call that proof of narrative quality.

| Boundary | Existing files and needed coverage |
| --- | --- |
| D/E dependency | Reuse `tests/test_3c_cue_chain.py` (`test_both_d_parts_are_earnable_and_e_waits_for_both`) and `tests/test_resolution_cascade.py`: both C orders, both D orders, E absent after D1 alone then available after both. Do not duplicate existing coverage. |
| Proposal 1 projection | If adopted, extend `tests/test_knowledge_projection.py`: entry fact retained across save/load; redundant framing omitted; actual A/B/C/D knowledge and reveal universe preserved at entry/post-C/post-D. No truth or unrelated-scene regression. |
| Proposal 1 payload/package | Reuse `tests/test_markdown_story_package.py` and `tests/test_cloudflare_transport.py`: exact variation loads, full payload reproduces the tested omission; no schema relaxation. |
| Proposal 2 selection | Extend stateful cue-chain coverage for `Answer the families with news of the captives.`: both-D eligible, D1 spent, D2 spent, pre-C. Keep generic listening/music/unrelated-recipient negatives and compound-command tie behavior. No alias added just to pass. |
| Proposal 2 composition | Reuse `tests/test_3c_cue_wording.py` conveyance and transport tests: complete cue preserves families asking for word, does not reveal rescue result or change eligibility; reveal still appends authored delivery and keeps hidden candidate content out of narrator instructions. |
| Deadline classification | Reuse cascade/bench coverage: D1 on turn 14 plus backstop remains deadline-complete; earned chain without deadline event is earned. Do not change classification to improve counts. |
| Capture anomalies | After reproducing A10, add regression at actual resolver/capture boundary for isolated contract. Preserve D12 person-containment refusal. No hardcoded captives fix or approval of prose contradicting THINGS. |

Focused command for a subsequent implementation, from repo root:

```bash
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_3c_cue_chain.py tests/test_3c_cue_wording.py tests/test_resolution_cascade.py tests/test_knowledge_projection.py tests/test_markdown_story_package.py tests/test_cloudflare_transport.py
```

Finish required checks with `docs/testing-runbook.md` sections 1–4, including
coverage/Ruff as applicable. Existing free prompt-capture example captures 1A,
not post-C 3C. Use actual recorded 3C request and preserve composed-delivery
boundary. New manifests need checked dry runs; no hypothetical CLI flag is
claimed here to exist.

The testing-runbook-creator skill was consulted. Existing runbook procedures
cover these boundaries; no procedure changed, so no dated diagnosis was added
to the runbook. Repository guidance places observations in this plan.

Document verification: `git diff --no-index --check /dev/null
.plans/chatgpt-3c-after-escape-plan.md` reported no whitespace errors. Git status
still lists only the already-untracked prompt and plan; no tracked file changed.
No pytest run was needed for this plan-only replacement.

## Risks and unverified points

- No candidate run, package edit, or measured improvement occurred here.
  Completed verification is read-only JSON/source inspection.
- Four selected failures cannot establish prevalence or whole-game success
  rates. Historical n=12 screens are triage evidence.
- C lacks saved narrator requests/capture; A10 lacks the original failed
  narration before recovery. Neither can be reconstructed with certainty.
- A9 records next cue staged but not delivered. Staged telemetry is not a
  delivery guarantee. Exact timing across handoff acceptance was not replayed;
  do not patch cue timing from this alone. A10/A11 visibly deliver the cue.
- Source inspection explains persistent context, not causal weights among
  pressure, C2, B1 speech, character biography (“She wants to find her best
  friend, Michelle”), and entry line. Failed C1/A1 screens remain negative.
- A10 fact delta proves duplicate-group creation; exact resolver visibility
  failure is unisolated. Original-group parent telemetry alone misses it.
- No row reaches ordinary E selection here. Compound-E ambiguity comes from
  earlier work, not these four rows.
- Michelle itinerary remains an authorial decision. No console, remote-leading
  retcon, extra reunion or spatial gate is validated/approved by this task.
- Prompt replay, synthetic continuation, carried scripted prefix and hosted
  play are different evidence levels; success is not silently transferred.

The investigation is complete when the next experiments are reviewable. The
scene fix will require measured earned continuation without renewed evacuation,
coherent physical grounding, and implementation/staging verification—not merely
a deadline ending or passing wording assertion.
