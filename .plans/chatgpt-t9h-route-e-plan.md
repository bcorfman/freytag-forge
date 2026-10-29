# Route E: diagnosis and measured repair plan

Status: investigation complete; proposed changes only. Written 2026-10-28
(America/New_York). The artifacts use UTC dates on October 29. Inspected source
HEAD `1a155fc18c690b8a99e44d53ed84d7d35efa8be4`, the smoke's recorded SHA.
No product code, package data, tests, deployment, or billed experiment changed.
The pre-existing staged changes to the parent plan were left alone.

Resume here: fix the measurement gaps first, then probe the missing placement
material. Do not run T9h F or silently repeat S. The old sample remains a stopped
sample. The proposals below are not measured wins and are not a new approval to
spend. Any plot change needs approval before application.

## What actually went wrong

There are several independent problems, not one bad observation classifier:

1. **Prompt material loses the underside placement.** All three bench objects
   start `under` the bench. THINGS and PLAYER show only `Place: park bench.`
   Both initial inspections describe them on the bench and report their parent
   without `under: true`. Applying that response changes their relation to `on`.
   The subsequent exhausted-underside sentence is therefore derived from already
   corrupted state; deleting that sentence alone treats the symptom.
2. **The bench is an unintended sight boundary.** Its inherited seat kind is
   enterable, with no outside `view`. `given_with` supplies its objects to the
   narrator, but `sees` excludes them from the observation context. All ten bench
   turns have zero verifier requests. Six successful turns are not evidence that
   the verifier checked the bench's contents.
3. **The unrelated-move guard uses the candidate's scope.** Even after repairing
   the view, a photographed object picked up from the bench leaves the bench's
   descendant set. Its new candidate context no longer exempts it. Simply adding
   the focus's *post-change* descendants does not solve this. This is a distinct
   engine contract issue; it is not permission to accept every object move.
4. **Malformed custody output costs matching requests.** Some responses use
   `"place": "held_by Kristin"`, not the supported `"held_by": "Kristin"`.
   Repeating this on recovery consumes the separate two-request matching budget.
5. **The storm-drain rejection is a different check.** Jev receives a required
   location relation but only narration as evidence. The two complete attempts
   describe the drain and nearby grounds without saying “Los Angeles park.”
   Scores 0.58 and 0.57 are uncertain, hence fail closed. These look acceptable
   in the scene; calling them proven false rejects under the current isolated
   relation question would overstate the evidence.
6. **The harness hides important state and stops short.** Its tracked parent
   list omits all three clues, the bench and drain, and every relation. The
   final drain turn reaches the 90-call cap before a verifier answer; this is
   not another model rejection. The manifest also requires route F artifacts
   even when its own conditional check correctly permits stopping at E.

## Evidence and deciding lines

Paths and line numbers below refer to the inspected SHA. Artifact references
use `E = bench/results/environment-narration/t9h/smoke/e/rows/rows.json`;
`r0t0` means zero-based replicate 0, command position 0, **not** `turn_index`.
Rejected turns reuse engine turn indices.

### Placement, visibility and capture

- `data/stories/continuity-initiative/plot.md:179–181` declares each of
  `transit_card`, `number_sequence`, `michelle_photograph` as
  `{parent: park_bench, under: true}`. The entry at line 183 ends with Kristin
  kneeling beside the bench. Scene 1B.1, line 204: “The bench could be nothing,
  or it could hold the only lead Michelle prepared for her.” There is no
  sentence here licensing their relocation onto its seat.
- `world.yaml:232–242` gives those objects names and a token state axis, but
  **no `hidden: true`**. Under and hidden are different declarations. The
  photograph's knowledge statement calls it hidden (`knowledge.yaml:746`),
  while its physical declaration does not. Treat that as an authoring ambiguity,
  not authorization to hide all three objects or give them a new recovery beat.
- `item_facts.py:182` uses `world.place_label(entity_id)`;
  `packages/worldkeeper/src/worldkeeper/model.py:655–658` returns authored text
  if present, otherwise the parent's name. `item_facts.py:486–489` prints it as
  `Place`; lines 628–634 do the same for PLAYER. None renders `under`.
  `cloudflare.py:986–989,1034–1040` likewise uses authored placement text for
  base-provider placement sentences. This is intentional W4/W5 behavior, not
  evidence that a generic English tree renderer is missing.
- `item_facts.py:1272`: `under = value.get("under") is True`.
  Lines 1280–1282 skip only when both parent and underside flag agree, otherwise
  call `world.move(..., under=under)`. Thus a same-parent echo can change
  `under` to `on`. Lines 1915–1916 compare the flattened item-fact views to
  populate `changed`, so that relation-only change can still report `changed: []`.
- `item_facts.py:700–704` refuses to say the underside is exhausted while any
  authored or actual child remains under it. Line 732 emits “Nothing else is
  under the park bench. Searching under the park bench finds nothing more.”
  Its appearance starting at t1 fits the t0 mutation exactly.
- `world.yaml:6–9`: seat inherits supporter and has `enterable: true`;
  `world.yaml:201–206`: the bench is a fixed seat with no view.
  `model.py:544–560` crosses every enterable ancestor and returns false when no
  view from the observer's places permits sight. `model.py:612–616`, in
  contrast, gives supporters' visible `on` **and** `under` children.
  `item_facts.py:547–550` uses that expansion for THINGS.
  `observation.py:94` requires both `is_visible` and `sees`. This explains the
  two projections disagreeing without hypothesizing a Jev error.
- `observation.py:63–65` excludes furniture/supporters from item requirements;
  `:168–169` considers only the focus's descendants for a supporter.
  `capture.py:394–400` builds the context **after** applying proposed item facts.
  `_moved_unrelated`, `:294–301`, exempts the protagonist, focus, and candidate
  context's visible objects and descendants; `:307` compares old/new parents.
  With no relations, `:432` decides `accepted = not moved_unrelated`.
  `engine.py:225–229` turns any unaccepted preview into the same
  `observation_unverified` error: “The narration did not show the observed
  things as the world has them.” That wording alone cannot identify the check.

### Reveals and scene start

- `knowledge.yaml:718–722` earns route knowledge by matching token to numbers;
  `:747–750` earns the face by examining **the photograph**;
  `:775–779` requires showing it to the man. The route's commands name the
  bench, not those actions. No selected knowledge or handoff appears on any E
  command. The matcher is not demonstrably broken: its low scores are consistent
  with its authored task. Scores reach 0.10 for the photo candidate, not merely
  the 0.07 maximum claimed in the earlier diagnosis.
- `handoffs.yaml:37` supplies the appended cue “A transit token and a handwritten
  number sequence lie beside Michelle's photograph.” This is not a successful
  reveal delivery. It appears in both openings and both t0 committed outputs;
  `handoff_id` and `delivered_text` remain null on t0. At t1 the appended cue
  is instead the man waiting near the service path (`handoffs.yaml:50`). These
  cues amplify exposure but do not move the objects or teach the photograph's
  actual content. The narrator repeatedly invents a photograph **of Michelle**;
  the authored delivery at `knowledge.yaml:772` shows the following man's face.
- `live_baseline.py:399–410` restores the first matching journey checkpoint,
  index 9 for 1B. `tests/journey_prefix.py:23–24,143–180` builds that journey
  with `PLAYED = _legacy_package(PACKAGE)` and a scripted provider, without
  live world capture. `personas.py:74–92` removes the first authored reveal's
  delivery text for that test journey. It is an earned deterministic prefix,
  **not a captured live player's state**. No evidence shows it creates the
  bench placement error: its placements agree with the source.
- `tests/test_live_baseline_scene_start.py:65–83` compares the restored facts
  against the same checkpoint and checks the focus parent. It does not prove
  live-prefix parity, visibility, underside retention, or opening consistency.
- `live_baseline.py:594` calls `engine.opening()` again at the restored scene.
  `engine.py:232–259` validates an opening and returns prose, without capture or
  world mutation. r1's opening says “As she picks up the token” and returns a
  held token, but t0 still starts with it under the bench. This is an
  opening-prose/state mismatch, not a committed token pickup. It also means
  the two sampled openings do not create two different durable starting states.

### Budgets, verifier and instrumentation

- `cloudflare.py:2121–2127` raises `ITEM_FACTS_REQUEST_BUDGET_EXHAUSTED` at the
  matching budget; it is separate from narration recovery. E r1t3 already used
  one command match and one malformed-place match, then asks for a third on
  recovery. Jev's `same_or_part` scores 0.16/0.17 reject the malformed phrase's
  proposed identity; do not claim all malformed entries successfully became
  Kristin's custody. Their precise candidate fallback parent is not recorded.
- `observation_verifier.py:91`: `state = {"narration": narration}`;
  `:141` asks whether the named thing is present “at its permitted relation”;
  `:164` names `at place Los Angeles park`. `:186–191` accepts only scores
  **above** 0.65. The drain's uncertainty is therefore a normal fail-closed
  result, with a possible missing-context/over-demanded-location cause.
- `live_baseline.py:143–150` tracks only Kristin, laptop, memory card, drawer,
  truck and officer. Equality of `places_before` and `places_after` does not
  prove full fact rollback or even bench-clue custody rollback.
  `:560–589` logs verifier reports, not every `CandidatePreview`. That is why
  an unrelated-move rejection has no `enforce_attempts` entry.
- The last cap row records `verifier_requests: 1` and `failure: ask_raised`,
  but its five `call_timings` contain no `relation_0` request. This counts a
  logical verifier attempt, not a sixth completed HTTP call. Its `turn_index`
  advances to 13 and `pursuit_1b` appears despite null narration; the artifact
  cannot establish full rollback for this unexpected harness exception.
- `make_t9h_run_manifests.py:40–49` conditionally checks later routes, while
  `:106–115` requires every route's files unconditionally. This is a harness
  failure-reporting bug, not evidence of a failed route F.

## Every route E turn

Every E command has `engine_opened: false`, no selected knowledge, no delivered
handoff, and empty recorded `item_facts_unplaced`. All recorded tracked-parent
maps compare equal. Bench intent is `look` on inspect/search/check and `under`
on both underside commands; drain intent is `look`. All completed transport
responses were HTTP 200. “A/V” below is narration attempts/verifier attempts.

| Row; E line | Command | A/V; seconds | Diagnosis from full replies and committed output |
| --- | --- | --- | --- |
| r0t0; 30 | inspect the park bench | 1/0; 7.859 | Commits “number sequence on the bench” plus photograph and token. All three raw place entries name bench, omit `under`. Relation changes are invisible to the flat `changed` list. Appended transit/sequence/photo cue. |
| r0t1; 362 | look under the park bench | 1/0; 5.008 | Commits “nothing but the dirty ground and some scattered debris.” Prompt already says underside exhausted. Echoes all three at bench without under. Appends man/photo cue. Successful commit, incorrect intended discovery experience. |
| r0t2; 691 | search the park bench | 2/0; 14.155 | Attempt 1 explicitly picks up photograph but reports all three as `place: held_by Kristin`; matching plus Jev follow. Attempt 2 explicitly picks up all three and correctly uses `held_by`. Both fail before verifier, consistent with unrelated moves. No narration committed. Do not equate the first reply's three claimed moves with three narrated pickups. |
| r0t3; 1050 | check the park bench | 2/0; 15.518 | Both replies pick up photograph. First uses proper `held_by`; recovery uses malformed place phrase and spends another match. Invents Michelle in the photograph, once in front of a building. Both previews rejected, no committed narration. |
| r0t4; 1409 | look under the park bench | 1/0; 6.234 | Commits no find, and “carefully lifts the edge of the bench” despite fixed bench. Item facts echo unchanged parent; no movement is captured. This prose defect is missed by both parent comparison and the empty verifier requirement. |
| r0t5; 1730 | inspect the storm drain | 2/2; 11.526 | Both replies show the drain amid grounds/vegetation and peer inside; neither moves/opens it or supplies contents. Relation scores 0.58/0.57 uncertain. Both rejected. Location evidence mismatch is a hypothesis, not a labelled false-reject verdict. |
| r1t0; 2148 | inspect the park bench | 1/0; 8.771 | Commits all three on bench; same missing-under item-facts echo as r0t0. Calls photo “a personal touch.” The opening's narrated token pickup was never applied. |
| r1t1; 2475 | look under the park bench | 1/0; 5.907 | Commits “nothing but dirt and debris … no hidden compartments or secret messages.” Same exhausted prompt and same-parent echoes. |
| r1t2; 2802 | search the park bench | 2/0; 20.210 | First picks up photo and sequence, leaves token. Recovery explicitly picks up sequence and looks at photo, but item facts claim both held. Rejected unrelated moves; no verifier. Slowest turn: narration 12.998 s total, matching 5.071 s, Jev 1.370 s. |
| r1t3; 3141 | check the park bench | 2/0; 14.291 | Both attempts pick up photo, merely look at numbers; both report photo and numbers as `place: held_by Kristin`. First rejected; second needs a third matching call and ends with item-facts budget error. No verifier. |
| r1t4; 3500 | look under the park bench | 1/0; 5.912 | Commits “nothing but the dirt and debris … no hidden compartments or objects of note.” Echoes three objects at bench, no under. |
| r1t5; 3821 | inspect the storm drain | 1/1 logical; 7.257 | Narration response received, then call cap prevents verifier HTTP request. `unavailable/ask_raised`, not a model score. No committed narration. Harness stops; F never runs. |

Totals: 6 committed, 3 terminal observation-preview errors on bench pickups,
1 terminal drain observation error, 1 item-facts budget error, 1 call-cap error.
Five unsuccessful of eleven non-cap-completed turns; six null narrations in
twelve recorded rows. E uses 88 timed turn HTTP calls plus two openings = 90.

Worker side: `smoke/worker.log` has 75 narration/matching `/` responses and
116 `/jev` responses, all 200, across C/D/E; three successful spend requests.
`spent.json` reports 39,073 micro-USD = **$0.039073**, whole smoke, not E alone.
The call cap, not the $0.07 spend cap or an upstream 503, stops the run.
E's narration calls span 2.864–9.091 s; Jev is fast in this sample. Retried turns
are slow mainly from narration, with one 5.071 s matching call. No latency
claim here is a general service benchmark.

## Why 1A behaves differently

The drawer's card also has `under: true` (`plot.md:86`), but is explicitly
hidden (`world.yaml:159`). It never enters ordinary THINGS before its reveal.
The drawer is a container, with four declared supplies (`world.yaml:169–174`).
The 1A card-find entry explicitly matches underside/workstation actions
(`knowledge.yaml:336–340`), and `memory_card_recovered` moves it to Kristin and
reveals it (`world.yaml:344–347`). The narrator receives the handoff lead-up
instruction; the engine appends the actual discovery. No under relation needs
to survive a pre-discovery narrator echo.

Route C's t0/t1/t3/t4 get the repeatable gap nudge; t2 search engine-opens the
drawer and also gets the nudge; t5 gets the witnessed card recovery. The three
open-interior turns require and show all four supplies and each has one verifier
request. All six commit. The hidden card remains separate from drawer contents.

Route D also has **zero verifier requests on all twelve turns**. Both searches
right the chair; both workstation-under commands earn the card handoff. Chair
turns have no child items to require. r0's underside prose invents lost paper
clips under the workstation and a lost paperclip under the chair. “No errors”
does not mean clean narration, nor does it validate the bench's visibility or
its unrelated-move behavior. The D handoff supplies the discovery text missing
from E, but that does not justify broadening E's matcher to award route knowledge
for a bench inspection.

## Ranked proposals: exact changes, precedent and risk

These are separate experiments/changes in order, not a bundle. “New” below
means the existing record has not demonstrated the proposed behavior. For
engine changes, old/new describe the precise contract to implement after tests;
this plan does not supply an untested implementation patch.

### 1. Make the next measurement trustworthy — harness

**Files:** `scripts/ringer/transcript_1a/live_baseline.py`,
`scripts/ringer/environment_narration/make_t9h_run_manifests.py`, their tests.

**Old:** `TRACKED` is the six IDs at lines 143–150; before/after store parents
only; `enforce_attempts` contains only calls to `verify`.
**New:** retain those legacy fields, add full immutable runtime-snapshot
before/after evidence and structural parent/relation/hidden/axis evidence for
the observation focus and its pre-turn scope. Record every preview's
`outcome`, `failure`, `moved_unrelated`, and required relations separately from
verifier requests. Record the opening's proposed item facts beside its unchanged
state. Avoid a bench-only ID list.

**Old manifest:** unconditional c/d/e/f row and summary entries plus spent file.
**New manifest:** unconditional c rows, c summary and spent file only; retain
the existing conditional route checks at lines 40–49 to require all later
artifacts when those routes actually run. Regenerate rather than hand-edit JSON.

**Earlier fix followed:** T8 stale-record correction (parent plan line 727)
and T9g split timings (1097); stop-reason checks already in this generator.
Recording full previews is new instrumentation, not a changed acceptance rule.
**Risk:** snapshot volume, serialization of mutable references, stale failed-turn
data, breaking readers that assume exact row keys. Keep old fields compatible.

**Cheapest probe:** free, two arms `current recorder` / `extended recorder`,
six synthetic terminal cases per arm: commit, unrelated reject, verifier
uncertainty, matching exhaustion, call-cap exception, early route stop. Zero
model calls, $0. Include a relation-only mutation and a newly created entity.
Full-state equality must be asserted, not inferred from the old six parents.

### 2. Supply the authored underside location — package prompt material

**File:** `data/stories/continuity-initiative/plot.md:179–181`.
For each of `transit_card`, `number_sequence`, `michelle_photograph`:

**Old:** `{parent: park_bench, under: true}`.
**New candidate:** `{parent: park_bench, under: true, text: under the park bench}`.

This changes plot.md front matter: **plot-file/package placement change requiring
approval before application**. It describes an already declared location; it
does not approve a new reveal or hiding the objects. No SCENE rule, no tree-built
English, no engine string naming this bench. The generated THINGS/PLAYER place
lines would say `Place: under the park bench.` while the placement text remains
valid. Capture every narration path, including opening and recovery, not only
the inspected prompt.

**Earlier fix followed:** W4 authored placement text; scene-fixing's “material
before rules”; existing phone and laptop placement text in plot.md. **This
particular wording is unproven.** Historical W5 and the failed “with Kristin”
data-removal trial warn that copying a place phrase can break capture. This is
why it gets a prompt-and-capture probe, not immediate adoption. It can also
vanish after a real move, so it is not a general relation-rendering solution.

**Cheapest probe:** `P0 recorded r0t0` versus `P1 same prompt, only those three
place lines changed in THINGS and PLAYER`; 10 narration samples per arm,
20 calls, about $0.014, cap $0.03. Use the actual generated payload diff as the
arm specification. Replay replies through free local capture where names resolve;
report any reply needing a live matcher separately, never call it a pass. Score
prose location, unwanted pickup, item-facts relation, invented photo content,
and whether a following under prompt falsely says exhausted. Require control
reproduction and at most one bad candidate of ten before a separate 15-per-arm
confirmation (30 calls, about $0.021, cap $0.04). This is the T8 defect-probe
procedure, not reuse of its results. If phrase copying or loss after movement
persists, stop and specify a new typed presentation proposal; do not add regex
place parsing or silently preserve `under` against explicit narrated movement.

### 3. Remove the accidental sight barrier — package data

**File:** `data/stories/continuity-initiative/world.yaml:201–206`.
**Old:** bench block ends `kind: seat` / `fixed: true`, no view.
**New candidate:** append `view: [{from: los_angeles_park}]` to that block.
Keep kind, fixed status and enterability. Making the bench non-enterable would
remove seating, and changing every seat would have much wider effects.

**Earlier fix followed:** T2 visibility audit and T3 validated view declarations;
`tests/test_package_view_scope.py` already checks package-to-world view wiring.
This is an existing mechanism, **new use on an open bench**, not yet a live win.
Treat its story-visible exposure as an authoring decision: if the intended
objects are secret until earned, this is the wrong fix by itself; settle that
plot decision first. Never add view as a substitute for `hidden` semantics.

**Cheapest probe:** free arms `no view` / `park view`, three checkpoints per arm
(entry, after initial inspect, after one pickup), real scene and a second
synthetic story, 12 context evaluations, $0. The view must supply required
objects and preserve hidden-item exclusion and seating. Then compare 10 live
replies per arm on the corrected placement prompt: 20 narration calls, expected
$0.014, cap $0.03; free capture first. **Do not claim this fixes pickups:**
candidate-scope loss below remains even when initial sight works.

### 4. Keep related items related after a pickup — engine, NEW technique

**Files:** `storygame/runtime/capture.py:365–400,291–309` and
`storygame/runtime/observation.py:154–172`.
**Old:** exemption membership and required identities come only from the
post-item-facts focus context.
**New proposed contract:** retain the pre-application public, seen scope IDs
for this observation; evaluate those identities at their candidate positions.
A public in-scope object moved from the focus to the protagonist stays related
and stays required (mention-only when held, using the existing held relation
policy). Unrelated objects remain guarded; hidden things are never admitted;
scene/area changes keep the existing requirement-drop rule. Do not exempt all
focus descendants regardless of visibility or exempt arbitrary new objects.

**Precedent and limit:** T8 candidate preview/atomic commit, post-change shadow
ordering and held mention-only relations are proven pieces. **Preserving scope
membership across capture is new; none of those records proves this fix.**
The earlier candidate “exclude focus contents” is underspecified and fails if
computed after the pickup. Keep candidate positions, not stale original places.
**Risk:** broadening initiative permissions; hiding a move behind mention-only
verification; resurrecting stale requirements; accepting capture's false pickup
when prose merely looks at an object. Prose/capture disagreement needs separate
labels and is not solved by this exemption.

**Cheapest probe:** free `candidate-only scope` / `stable identities, candidate
positions`, eight fixtures per arm, real and synthetic coverage: one/all contents
picked up, untouched object, unrelated move, hidden object, object moved back,
scene transition, area transition. $0, zero model calls. Only if these identify
the intended boundary should implementation proceed. Reuse frozen narration
replies through deterministic capture; no new narration calls are needed to
show which guard changes its decision. A later live 3-replicate E confirmation
measures integration, not this free proof.

### 5. Diagnose the drain question before changing it — verifier/prompt material

**Files:** `storygame/runtime/observation_verifier.py:90–92,136–155`;
frozen probe data under `scripts/ringer/environment_narration/` if built.
**Old evidence:** `{"narration": narration}` only.
**New candidate evidence:** keep narration separate, add the already validated
current scene name and the observed thing's public pre-turn location. Candidate
instruction replacing the second sentence at line 141:
“Check whether the narration shows the named thing in the scene. Use its
starting place when the narration leaves it there. Reject a different final
place stated by the narration.”

This is **new judge context/wording**, not an approved product fix. No changed
threshold, no drain exception, and no switch to mention-only for every location.
The historical holder wording arms failed; their later mention-only policy was
explicitly limited to held objects. The established technique to reuse is frozen
positive/negative calibration with isolated arms, not those losing sentences.

**Cheapest probe:** first hand-label both recorded drain attempts under two
questions: scene continuity versus isolated explicit-place evidence ($0).
Then `J0 current` / `J1 add context only` / `J2 add context plus replacement
sentence`; six frozen cases (two actual replies, one explicit correct-location
positive, missing drain, remembered drain, explicitly elsewhere drain), 10
samples per case per arm = 180 Jev calls, expected under $0.005, cap $0.01.
Zero false accepts; positive strict failures at most 10%; choose the simpler
winning arm. This small screen cannot qualify a changed verifier: rerun the
frozen T7 corpus and fresh held-out locations under a new preregistration before
enforcement. No new product wording if neither candidate wins.

### 6. Repair photo discovery only if the author chooses that plot — plot, deferred

The current plot does not unambiguously decide whether a bare bench look should
reveal hidden clues, merely show visible objects, or only cue a later search.
Do not “fix” it by changing `hidden` flags alone: that can make the current
photo-targeted handoff inaccessible. Do not make a search grant route knowledge.

A minimal **plot-change proposal for review**, separate from proposals 2–5:
`handoffs.yaml:37`, old “A transit token and a handwritten number sequence lie
beside Michelle's photograph.” → “The bench could be nothing, or it could hold
the only lead Michelle prepared for her.” This copies `plot.md:204` unchanged
and removes the premature object-list cue. It does not hide objects already in
THINGS and cannot fix capture or visibility. Probe it only if the author wants
the opening to preserve uncertainty: free arms `Q0 current opening` /
`Q1 cue replaced`, using both recorded openings in each arm (four composed
outputs, zero calls, $0). Score the full opening including the appended cue.
The engine appends the cue after generation, so changing only that cue cannot
explain a change in the narrator's raw reply. The retained raw replies still
expose the token; this deletion/replacement alone is insufficient. Do not spend
on a narrator replay to measure a sentence appended after the narrator runs.

If the author instead wants a hidden discovery like 1A, write a separate
approved discovery statement and handoff with `hidden: true` plus one-way
`on_assert` move/reveal effects (W7). Its exact text, event fact and earning
action are **not verified by these artifacts** and are not invented here.
That larger option is not ready to apply. Avoid changing the existing
`brandon_face_known` meaning merely to make a bench search pass.

### What does not get a fix yet

- Do not increase the product's two narration or two matching requests. Fewer
  malformed place echoes may follow better material; if they persist, use a
  separate recorded-response format probe. Parsing `held_by Kristin` as a new
  special case would be a new runtime technique, not a proven correction.
- Do not delete the exhausted-underside mechanism globally: T8 A3 won 0/25
  against 25/25 failures; cue deletion alone failed 2/25. Its triggering state
  is wrong here because of capture, not because the proven wording lost.
- Do not delete pressure lines (T8 B1 lost), restore copy-refers/plain-corridor/
  go-into-place rules, add a blanket no-pickup rule, open supporters, or replace
  Jev intent with verb tables. T9d search-open belongs to containers only.
- Do not lower the verifier threshold to rescue the drain or broaden
  `action_evidence` to award an unrelated revelation. T9f's `voiceable: false`
  fixes witnessed statement-as-dialogue; it does not explain these E errors.
- Do not add an engine-written successful search sentence. Do not hand-edit
  the historical rows, generated story projections, or frozen gate values.

## Order, tests and completion evidence

1. Preserve this sample and its SHA. Build the free instrumentation fixtures
   from proposal 1. Confirm complete rollback on ordinary rejections and
   explicitly classify the cap exception. Add a test that the first scene-start
   checkpoint has the expected clue relations, hidden state and observation
   context; checkpoint equality alone is insufficient.
2. Obtain the authoring decision about public-under versus hidden-until-earned
   objects before applying plot-file changes. Prepare only the placement probe
   first. Read every output and reject phrase-resolution failures. Choose one
   measured change, capture all affected payload paths, and preserve unrelated
   payloads byte-for-byte.
3. Test the view proposal independently. A nonempty expected observation list
   is an explicit success condition. Then test stable membership independently;
   do not bundle it with relaxed verification or new plot reveals.
4. Calibrate the drain question independently. Keep failure to establish a
   location distinct from missing the object. Judge prose and appended authored
   text separately; score `item_facts` separately from both.
5. Only after free checks and measured prompt wins, write a **new** integrated
   confirmation preregistration. Proposed smallest scene confirmation: same six
   E commands, **3 replicates = 18 turns**, expected roughly $0.03–$0.04,
   `max-calls 240`, Worker cap $0.07, one run, no replacement samples. This cap
   includes openings and recovery headroom; it changes no per-turn budget.
   Zero null turns, no false empty underside, correct clue locations and photo
   content, no fixed-bench lift, no inappropriate reveal, exact rejected-state
   rollback, and non-vacuous requirements are required. Report latency without
   silently waiving 10 s. Freeze labels before joining verdicts. A pass is a
   small smoke, not T9h F qualification.
6. Then regression C and D, **3 replicates each = 36 turns**, expected about
   $0.04, cap $0.08, up to 240 calls per route. Preserve card-find, gap nudge,
   interior supplies, no supporter opens, and voiceable protections. F remains
   unmeasured and requires its own previously specified start/verification;
   passing E does not stand in for F. Follow SHA-bound staging and production
   promotion guidance for any later release; this document changes no switch.

Costs are planning estimates, not quotes or spending authorization. Narration
estimates use roughly $0.0007 per prompt from the earlier measured defect probes;
whole-route estimates include matching and Jev and can vary with tokens/retries.
Build exact call counts and a hard Worker cap into each new manifest before
requesting approval. Run paid probes through Ringer. Do not pool them with S.

Tests to add/change when each proposal is implemented:

- `tests/test_live_baseline_scene_start.py`: no live calls for deterministic
  prefix; actual clue parent/relation/hidden state; synthetic package handling;
  opening output does not masquerade as applied capture.
- `tests/test_live_baseline.py` and T9h harness tests: full before/after evidence,
  every preview outcome, stale failure telemetry, logical versus HTTP requests,
  a stop at each route, and missing files when no stop occurred.
- `tests/test_package_view_scope.py`, `tests/test_observation_context.py`:
  public objects under an enterable supporter with/without view; hidden sibling
  excluded; view does not imply entering; update the old “only passenger seat
  uses view/completeness fields” assertion for the approved declaration without
  replacing the original backwards-compatibility hash.
- `tests/test_bench_item_facts.py`, `tests/test_underside_exhausted.py`:
  replay the real inspect response; assert relations, not only flat place
  strings; populated underside, emptied underside, and object returned under it.
  Test authored text invalidation and whether it resolves without extra calls.
- `tests/test_observation_preview.py`: related pickups retain requirements at
  candidate positions; remote/hidden objects remain guarded; two rejections
  restore all facts; mention-only held policy; save/load round trip; a synthetic
  story with different names and kinds. Add a case where prose and capture
  disagree rather than treating capture as the prose score.
- Verifier tests plus frozen calibration fixtures: missing, imagined, remembered,
  wrong-place and omitted-place cases. No threshold changes or prompt-string
  assertions offered as evidence of model obedience.
- Package/narration safety tests for any approved plot change: reach, exactly
  one handoff, protected knowledge withheld, correct photograph content,
  subsequent token/number comparison and man-identification paths still work.

Use the testing runbook's focused commands between steps, Ruff autofix/format
for implementation changes, quick suite with relevant journey files included,
then the required full suite/coverage once before merge. No test files or
implementation were written during this planning task.

## What was verified here, and what remains uncertain

Read every E opening and turn prompt, provider body, narration, item-facts
entry, error, intent, engine-open field and timing. Repeated identical prompt
strings were compared/deduplicated for reading, not treated as missing. Read
C/D comparisons, Worker log/status totals, summaries/spend, specified source
paths, the focused guides, the earlier visibility, holder, defect, scope,
engine-opening and post-change-verifier records, and historical W1–W14 with
their relevant amendments at `5ea0119955c62b84699a8dc7878a4af770b55a7e`.

Free in-memory diagnostics reconstructed `_start_state` and
`ItemFactsProvider` with no Worker URL. Entry checkpoint 9 has all three clues
`under`, not hidden, `is_visible=True`, `sees=False`, with an empty observation
context. Both a direct move-path check and a full `apply_item_facts` replay of
the recorded r0t0 response make all three `on`; full application reports no
issues and `changed=set()`. The underside-exhausted predicate becomes true.
An in-memory schema using the proposed park view makes all three required
before pickup. Moving the photograph to Kristin then removes it from the
candidate requirement, and `_moved_unrelated` returns `("Michelle's photograph",)`.
This confirms that view alone does not solve the pickup guard. The first
full-application diagnostic failed on a mistyped import before executing; the
corrected diagnostic completed. No source files or live facts were mutated.
These are local deterministic checks, not new model experiments. Artifact JSON
inspection and `git diff --check` also completed; no pytest suite was run for
this documentation-only task.

Limits: no blind gate labelling or `join`; no billed probe; no hosted state
check; no full-turn replay of every rejected attempt; no full runtime snapshots
in the old artifacts; no live-prefix parity proof; only one story and two E
replicates. The exact internal fallback parent of malformed `held_by Kristin`
is not recoverable from the failure telemetry alone. The drain cause requires
calibration. Proposed prompt wording, view exposure and scope preservation
need the separate checks above. Existing accepted prose also violates fixedness
and invents photograph content, so successful commit counts alone cannot close
this work.
