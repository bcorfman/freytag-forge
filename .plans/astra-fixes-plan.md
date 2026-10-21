# Scene 2A–2B follow-up plan

Prepared 2026-10-18. Planning only: no story prose, implementation, billed
calls, judge changes, pipeline migration, or production promotion.

## 1. Diagnosis check

Scene-fixing step 1 has evidence, but the causal diagnosis is unfinished;
step 2 has not established a winning fix for the invented access route.
The complete saved control prompt in
`bench/results/stage7-door-n12/prompts/control.json` contains:

- PLAYER: “Look for a concealed route or access panel leading from the service
  corridors to the detention area.”
- System: “Finish each action the player gives.”
- CONSTRAINTS: “This happens now. Show it in the scene: A second credential
  check threatens their inspector cover.”
- SCENE: “Kristin must plan a way into the facility. False identities are a
  possible cover.”

The concealed-route framing is **player input**, not a plot sentence. Plot
2A.3 grants infrastructure-corridor access and describes a limited diagnostic
console; it does not declare the unmarked door, reader, or grille. Hypothesis:
finishing the search is being rendered as discovering its requested object,
with credential pressure supplying an access obstacle. No line literally
requests a keycard reader, and the prior screens do not isolate its cause.
Do not repeat the failed command rewrite, credential-review rewrite, stale
scene removal, bridge deletion, perimeter deletion, or console-limits addition.

The 2B entry now names selection files; `k_sl_2b_a_r1` still requires a search
verb plus Michelle/selection-file evidence. The Details and handoff cue still
name government/financial data. This is not permission to broaden the matcher.
The review summary's pooled “threshold met” is erroneous: no prior arm met
10/12. The source screen's summary does not establish N=12 invention counts.

**Newer evidence supersedes the request's baseline:** the active plan records
the entry-repair run at `62cae8ae`: 2B reveal on command 1, earned exit, two
stuck turns; the whole-run bar failed (29 stuck turns and two rejections).
The `995b9f07` run also exited 2B by play but stopped in 2C. Therefore do not
reimplement the entry repair or claim that 2B is still universally blocked.
Reconcile the exact package/SHA before any new comparison; these later results
are plan-reported evidence, not transcripts independently reviewed here.

The earlier old-warehouse (1A), biohazard-zone (1C), and hidden-panel/corridor
(3C) cases remain genuine invention findings in the Stage 2 record. That record
does not document a successful fix for those three inventions. The later 1A
quiet-house and 3C verb repairs address different failures. None is a proven
door-invention solution. Repeated seating and the silent 1A exit also remain
separate diagnoses, not grounds for an extra narrator rule here.

## 2. Ranked candidates

1. **Subtract the action-completion instruction.** First experimental choice
   if the residual 2A invention is still the target. Reuse the existing
   `completion` experiment in `scripts/ringer/stage7/door_prompt.py`: delete
   exactly `Finish each action the player gives.` from the system prompt;
   preserve the user command and all story material. This copies the proven
   conflicting-line removal method (3A talk line; 2C stance/stale recall), not
   a proven result for this particular rule. It differs from every failed
   story-line/command arm. If it wins, edit
   `storygame/runtime/cloudflare.py::_turn_rules_before_grounding` and check
   every narration/recovery path named in the narrator guide. Risk: incomplete
   ordinary actions across scenes. No replacement rule is proposed.
2. **Ground the route and give it a bounded archive outcome.** Conditional
   fallback if invention persists and still derails play. Edit
   `data/stories/continuity-initiative/world.yaml` for a fixed, uniquely named
   door, its parent and any actionable hardware; `plot.md` for scene scope,
   placements and the transition; `knowledge.yaml`/`handoffs.yaml` only for
   the approved outcome/evidence delivery. The design outcome is access to
   the existing archive investigation, not another credential hunt or access
   to detention. Preserve earned JANUS disclosure. All physical nouns used
   must resolve to declared entities; no prose-created fact or regex repair.
   This copies the 1B bench grounding repair and authored reveal handoffs.
   It differs from cue rewording by defining the object's world identity and
   consequence. Its efficacy is a hypothesis, and it changes story canon;
   author the material through the existing Desktop/matcher workflow before
   probing it. Merely declaring the invented door does not count as success.

Given the newer 2B success, first reconcile existing evidence offline. Do not
displace the active plan's newer 2C blocker with an automatic billed screen.

## 3. Probe designs and fixed gates

For each candidate, freeze two arms: contemporaneous control and that candidate
alone. Use the same recorded 2A prompt, model, temperature and two-command 2B
continuation; interleave arms. Freeze the bridge/entry version in the manifest.
Do not compare a repaired entry against the historical 7/12 as if paired.

| Candidate | Smoke | Counted screen | Hard request caps per smoke / screen |
| --- | --- | --- | --- |
| Completion deletion | 1 per arm | 12 per arm | Cloudflare 10 / 120; player 4 / 48 |
| Grounded route | 1 per arm | 12 per arm | Cloudflare 10 / 120; player 4 / 48 |

These caps reserve five Cloudflare and two player attempts per row, including
upstream narration and continuation. If the grounded design cannot fit, stop
at preflight and revise the preregistration; never silently raise the cap.
No extra judge calls. Combined maximum for both fresh smokes and screens:
260 Cloudflare plus 104 player attempts. These are request-spend ceilings,
not a quoted dollar price; a monetary ceiling must be computed from the
selected endpoints and token limits before live execution.

The completion smoke **already exists** (two rows, six Cloudflare and four
player attempts). Its summary is not a review gate. Inspect its saved prose,
hashes, budget events and matcher evidence before deciding whether it is
reusable; no N=12 completion directory was present. Reuse matching valid
smoke evidence rather than paying again. Existing manifests are
`scripts/ringer/stage7/door-completion-{smoke,n12}.json`.

Preflight and stopping rules for both candidates:

- Run a network-stubbed dry screen; prove only permitted payload lines differ.
  Package changes also require loader, real `_matches_all` positive/near-miss
  checks and the shipped payload capture diff. Keep unrelated payloads identical.
- One Ringer task per smoke, full screen, or review unit; one attempt per run.
  Record all attempts, including aborted ones. Guard every actual endpoint
  request and retry before dispatch, including player and auxiliary calls.
- Read every smoke narration plus appended delivery. Stop for malformed output,
  quota/outage/cap errors, missing evidence, premature disclosure or contradictory
  delivery. Preserve partial results. No replacement samples or smoke pooling.
- Otherwise run the fixed N=12 once. Do not extend N after seeing results.
  Read every row, including failures. Count upstream invention, inherited
  invention and downstream new obstacles separately. Count a row with any
  unsupported access invention once in the combined invention measure.
- **Keep only if** the candidate earns exactly one eligible reveal by command
  2 in at least 10/12 rows, has unsupported invention in at most 2/12, has zero
  premature disclosures/contradictory deliveries, and beats the fresh control
  by at least three reveal rows without increasing invention. This three-row
  margin is a proposed engineering screen, not statistical significance.
  Require `k_sl_2b_a_r1` counts separately; inspect committed delivery rather
  than accepting `item_facts` as success. Unchanged transition eligibility and
  guard behavior are mandatory. Otherwise drop the candidate for adoption.

For the grounded route, explicitly score reaching the declared archive outcome
without a new credential prerequisite; require at least 10/12. Also report
how often the door appears in both arms. Reclassifying the door as supported
must not conceal a continuing dead-end chase.

New scripted probe commands follow the player-input guide: imperative verbs,
with first-person ownership only where needed. Raw blind-player continuations
are a deliberate language experiment and retain exactly what the player typed.
Do not edit the recorded search command to make either arm pass.

## 4. Done and regression evidence

A screen win is not completion. Apply only a winning change, run the focused
runbook checks and payload diff, then use the SHA-bound staging workflow.
After smoke, run three linked free-text 2A–2B replicates with earned entry and
actual carried facts. Each must commit `k_sl_2b_a_r1` by 2B command 2, leave 2B
by play, and have no unsupported access chase, premature disclosure or ordinary
input rejection. Read composed exit/entry/reveal text and state evidence.

Check 1A–1C on matched starts for earned exits, action completion, custody,
disclosure and rejection regressions. Shared-rule removal additionally needs
cross-genre offline coverage and all-scene live action-completion inspection.
Follow Stage 7's broader three-runs-per-profile gate for readiness: at least
two of three canonical and raw journeys finish through earned exits, with no
ordinary-vocabulary rejection or premature secrets. Report forced progress
separately. Pre-register the live manifests' request/token ceilings and stop
rules before these additional billed runs; they are outside the screen caps.

Record SHA, every attempt, passed/failed/unmeasured checks and unresolved
failures in the active plan. A 2B win may be recorded separately; the current
2C blocker prevents a whole-playthrough completion claim.

## 5. Limits and files checked

One story, one recorded 2A state and temperature-zero repeats do not establish
human benefit, varied-state robustness or independent samples. The existing
bare-state exact-matcher continuation omits hosted world capture, pacing and
semantic fallback. Neither screen proves that action-completion caused the
original invention. The grounded route risks making an accidental invention
canon. No broad rule, judge tuning or production readiness follows from it.

Files checked (sections relevant to this plan; source-screen results limited
to summaries):

- `.plans/astra-fixes.md`, `.plans/implementation_plan.md`,
  `.plans/world-model.md`, `.plans/stage7-door-probe-implementation-plan.md`,
  `.plans/chatgpt-2a-door-source-prompt.md`,
  `.plans/chatgpt-2b-door-probe-implementation-prompt.md`;
  historical world-model decisions at `5ea0119955c62b84699a8dc7878a4af770b55a7e`.
- `docs/PRD.md`, `docs/contributor-guide.md`, `docs/agent-workflow-guide.md`,
  `docs/railway-production-promotion.md`, `docs/scene-fixing-guide.md`,
  `docs/world-model-grounding.md`, `docs/narrator-writing-guide.md`,
  `docs/player-input-guide.md`, `docs/testing-runbook.md`.
- `data/stories/continuity-initiative/{plot.md,knowledge.yaml,handoffs.yaml,world.yaml}`.
- `bench/results/stage7-door-n12/{review-summary.json,prompts/control.json}`,
  `bench/results/stage7-door-source-n12/summary.json`,
  `bench/results/stage7-door-completion-smoke/summary.json`.
- `scripts/ringer/stage7/door_prompt.py`,
  `scripts/ringer/stage7/door-completion-{smoke,n12}.json`,
  `storygame/runtime/cloudflare.py` (targeted codebase-memory snippets).
