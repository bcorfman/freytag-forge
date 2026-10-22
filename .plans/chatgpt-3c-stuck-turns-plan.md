# Scene 3C: stuck-turn diagnosis and measured repair plan

Status — corrected (Round 7, 2026-10-20): Steps 9/10 COMPLETE. Pump is
merged in PR #674 at `f918c663d67d368645f9a24a47a28ffb29fb77d8` and staged;
identity and smoke passed. Step 11 ran one raw whole-game journey: 79 turns,
all earlier exits earned, but 3C earned A/B/C1/C2 only and ended by fallback.
Replicates 2/3 are dropped, not pending. No rate conclusion follows from n=1.
**Step 11a RESULT (2026-10-20): the C1 prompt screen ran and MISSED.** Frozen turn-6
prompt, 12 replies per arm, 30/48 Cloudflare requests: shipped pump finishes the
passage 6/12, C1-scoped 3/12 (bar 10/12 and +3). C1 is stopped for good; Step 5's loss
stands. Details in `.plans/astra-3c-recall-live-prereg.md`. The free live-versus-
scripted state comparison was then DONE (2026-10-20, zero model calls): see
"Step 11a free comparison result" below. Next decision is Brandon's (see Resume). No implementation, billed run or promotion is
performed by this planning-only update. Existing worktree edits are preserved.
**confirmed**, **corrected**, and **new** label retained findings, revised decisions,
and additions. Results below supersede the first plan's untested predictions.

## Decision

**corrected (Round 7):** Keep the staged pump package as the control. The
latest carried 10/12 and earlier 8/12 are separate scripted-prefix results;
neither predicts the live-history outcome. The new run demonstrates an unresolved
escape loop, not a population failure rate. Hold the recommendation to promote
as a quality repair until an earned staged journey and prose review support it.

**new (Round 7):** Do not buy another whole-game run merely to rediscover this
loop, or immediately buy a carried n12 that repeats the easier history. First
compare the recorded prompt/state with the scripted-prefix state for free.
Then permit one C1-only prompt screen on the recorded turn-6 prompt, with the
prior losing result retained. Do not bundle C2, surface binding, aliases or a
longer deadline. A semantic-judge screen answers the wrong question here: the
recorded player did not attempt either D action.

**corrected:** #667 fixes individual commands, not the fresh scene. Live A proves
turns 12/14 commit D-R1 in 12/12 control probes and 0/12 pre667 probes. Live B
finds no D-R1 commits; Live C earns only 1/12 per arm. Keep #667 and stop testing
that comparison. The matcher is not to be changed.

**corrected (Round 3):** Steps ran in order 1, 5, 2, then the Step 3 smoke.
Neither escape edit passed its live bar; neither is adopted. Entry text earns A
on attempt 1 in 12/12 versus 1/12, but earned endings remain 1/12 per arm and
both-C completion falls from 6 rows to 2. Keep entry as a baseline candidate,
not an adopted repair. **corrected (Round 4):** The harness stop is superseded;
custody and pump results are recorded in Steps 3/4. **corrected (Round 5):** that screen is complete. Resume with revised Step 7
D-R2 checks, then a fresh carried comparison. Deadline 16 stays deferred.

**new (Round 3):** The custody delivery is shown only after B. It cannot repair
the four entry rows that never reach B; that earlier handoff remains unresolved.
The two clear entry-screen effects are the turn-1 gain and the drop in pump
commits. The missing route-pressure sentence is a hypothesis for the latter,
not an isolated causal finding. Differences under three rows are not
distinguishable here; post-C control earned counts moved from 7/12 to 5/12.

**corrected:** Do not describe all post-gates failures as a missing surface move.
Eight of the 18 gate-earning rows never earn the pumps; another earns them only
on accepted turn 12. The surface binding cannot fire early enough in those rows.
It also does not move Kristin, Michelle, or Brandon. Physical consistency is
necessary but does not itself teach the player to check reports and answer families.

**corrected:** Retain the refusal to add bare `evidence` to A-R1's object group,
but for a newly checked reason, not because this is one recorded command. That
addition makes `Run away with the evidence.` earn A-R1: its verb group includes
`run`. `Show Rebecca the evidence.` also matches without public transmission.
Fix the opening's underspecified material first; do not change selection rules.

**new (Round 4 decision):** A reviewed D-R2 communication alias is legitimate:
three independent pump rows attempt to give families news, the action the story
requires. This is different from redefining D-R1 report inspection to reward
turn 7 or changing the matcher. However, reject **bare `broadcast`**: the real
matcher then earns D-R2 for `Broadcast music to the families.`. The three recipient-qualified phrases were the Round 4 candidate.
**corrected (Round 5):** use the revised Step 7 phrase family for the next
screen; retain the exclusion of `listen` and bare communication verbs. Earlier-scene precedent is the missing-material handoff in 3B for
story-side repairs; the evidence-alias precedent is #667 in this scene, now
measured by Live A. Do not mislabel #667 as an earlier-scene win. The PRD and
player-input guide explicitly permit reviewed aliases for missed phrasings.
No new narrator rule or technique is needed.

**corrected (Round 4 timing):** Re-reading `stage7-3c-pump-n12/rows.json`
shows all ten pump rows earn C1 on turn 3 and C2 on turn 5. Rows 03/05/09 earn
D1/D2/E on turns 7/9/11. Thus the prompt's “about 12 to 14” is not the timing
of these pump earners; earlier Live C earners did use 12/13. Pump rows 01/02
never earn D; 04/06 earn D1 but abandon the families; 07/08/10 attempt family
broadcasts at 9 and 12 and miss D2. There are **four**, not three, rows outside
the verb repair. Three repaired rows plus three existing earners would only be
6/10, even if each repair worked; this is an exposure ceiling on those recorded
rows, not a causal prediction for a new run. Do not promise 80% from aliases.

## Sources and verification boundary

**new (Round 7 verification):** Read the saved identity, operator note, report,
turn-6 prompt and decision bundles under
`bench/results/stage7-3c-blind-raw-f918c663/attempt-1/`, the Step 5 preregistration
and exact variation, current C/D source and plot, and the prefix implementation
through codebase-memory. Recounted scene exits, stuck turns and commands.
The prompt's claim of eight near-identical “Lead” commands is corrected below:
turns 11–13 say “Watch”. The turn-6 semantic shortlist has two candidates even
though the final narrator prompt offers none. No new tests, model calls or
payload reconstruction ran in this review. Merge is confirmed by local HEAD;
CI/full-suite/Pages results below are supplied Round 7 evidence, not remotely
rerun here. Dashboard dollar spend is unavailable in the local artifacts.
Older verification paragraphs describe their historical worktrees and rounds.

**new (Round 6 verification):** Read the latest summary, spend ledger, failed
row commands and commits, semantic replay results, both preregistrations, actual
adoption/variation git diffs, adoption test and Ringer manifest, promotion guide,
testing runbook, workflow YAML and hosted blind-player source. Recounted 300
player and 300 Cloudflare calls. The recorded rows confirm 10/12 versus 9/12.
Families-v2 row 06 commits D1 at turn 9: it was not spent at the turn-8 miss;
it was spent at the turn-12 miss. This closes the prompt's eligibility question.
The semantic replay separately tests both D1-open and D1-spent cases.
Codebase-memory confirms the narrow sentence reaches the semantic question;
`jev_questions.py:123–167` asks whether the command performs the same whole act.
The trace establishes refusals, not a model explanation or proof that changing
the sentence will cure them.

No new pytest, live probe, matrix regeneration or deployment ran for this
documentation review. The 102 build tests and 853 focused-gate tests are supplied
worker results, not independently rerun here. Historical verification statements
below describe their rounds, including their then-clean `data/` worktree.
Current `data/` has the two intended adoption edits. No procedure changed.

**new (Round 5 verification):** Read carried rows/summary/spend, diagnosis,
preregistration, source evidence and selector. Recomputed 8/12 vs 9/12, D2
9 vs 11, first-attempt A 12 per arm, and 302 requests of each kind. Independently
ran `TMPDIR=/tmp uv run python scripts/ringer/stage7/check_three_c_probe.py
bench/results/stage7-3c-carried-n12 12 --mode artifacts` and the same command for
`bench/results/stage7-3c-carried-smoke2 1`: both OK. Initial revised-alias checks
used in-memory candidate copies only; no product/test/harness source changed.
Focused existing regression check: `TMPDIR=/tmp uv run pytest -q
tests/test_3c_cue_chain.py tests/test_resolution_cascade.py` — **33 passed**.
This verifies existing behavior, not the new alias implementation. Plan integrity
checks preserved the historical matcher/per-turn/Live C tables and Steps 1–5
byte-for-byte; the proposed old YAML block occurs exactly once, and the new
block parses as two evidence groups. `git diff --check` is clean; `data/` and
`storygame/` have no worktree changes.
The existing testing runbook sections 2–3 cover free matcher/prompt verification;
no operating procedure changed, so no dated runbook entry was added.

**corrected — precedent retrieval:** `bb8f7271:.plans/world-model.md` is the
short checklist, not the W1–W14 text. Follow its link to
`5ea0119955c62b84699a8dc7878a4af770b55a7e:.plans/world-model.md`, section 12.
W12 does discuss verbs and rejects fixed action tables for seating; W7 names
`handoffs.yaml`. The blanket “nothing about handoffs or verbs” claim is false.
These decisions supply no alternative D2 recognition fix and do not prohibit
author-reviewed evidence aliases under the explicit PRD contract. #667 is the
measured alias precedent used here; no claim of an exhaustive history search.

**new (Round 4):** This update additionally reads the Step 3/4 RESULT and D/E
DIAGNOSIS paragraphs in `.plans/implementation_plan.md`, both preregistrations,
the pump variation, all ten pump command/commit sequences, current D evidence
and cues, and the real matcher through codebase-memory. The free checks below
run against in-memory evidence only; no package was edited.
Round 4 focused verification: `TMPDIR=/tmp uv run pytest -q
tests/test_3c_cue_chain.py tests/test_resolution_cascade.py` — 25 passed.
These existing tests do not validate the proposed aliases; Step 7 explicitly
requires those new controls. Existing testing-runbook sections 1–3 cover these
checks; no operating procedure changed and no runbook edit was needed.

**new (Round 3, historical):** That update used the Round 3 prompt, the full Step 1 surface,
Step 5 escape and Step 2 entry result paragraphs in `.plans/implementation_plan.md`,
and `.plans/astra-3c-custody-result-prereg.md`. Results and limits are recorded
inside their steps below. Earlier verification paragraphs in this section
record Round 2 work; they are not claims of new test or probe runs today.
No billed probe or implementation ran for this update. Nothing is adopted into
`data/`; `git status --porcelain data storygame` is empty. Harness and tests
remain uncommitted. Those Round 3/4 screens used labelled synthetic starts, semantic
fallback ON, one raw-player prompt and one story. **corrected (Round 5):**
the completed Step 8 screen replays the canon prefix separately on each arm.

**confirmed:** Read the prompt's guides, PRD, contributor/workflow guidance,
world-model checklist, 3C plot and all A–G storylets, all `k_sl_3c_*` entries,
handoffs, pacing, world bindings, and the existing plan. Consulted current matcher
and deadline source through codebase-memory and the new cue-chain tests.
The earlier-scene precedents below are documented in the scene-fixing guide and
implementation-plan history, including #668's measured 1A subtraction.

**confirmed:** Evidence paths are under `bench/results/`:
`stage7-3c-matcher-table/`, `stage7-3c-surface-binding/report.json`, and
`stage7-3c-live{a,b,c}-n12/`. Live C's `rows.json` contains the per-row commands,
responses, committed reveals, fact deltas and deadline IDs. Row references below
abbreviate `stage7-3c-07-control` as **C07**, and pre667 as **P07**.
All 24 command sequences and their progression/escape responses were reviewed.
The Round 1 historical recording remains `stage7-2b-entry/attempt-1/`.

**corrected:** Starts were synthetic, not restored historical games. The entry
start asserts 3C entry facts; post8 scripts A/B/both C/D-R2 and sets turn 8.
Semantic fallback is ON. The player sees entry text plus accepted transcript.
Earlier no-history smokes are superseded. These runs do not establish whole-game
quality or realistic carried inventory/knowledge from earlier scenes.

**new:** Recomputed the row table below. Ran the real `_matches_all` with and
without hypothetical bare `evidence`, without changing the package. Current /
widened results: `Transmit the evidence.` false/true; `Send the evidence.`
false/true; `Run away with the evidence.` false/true; `Show Rebecca the evidence.`
false/true; `Send the evidence package.` true/true. These are lexical checks,
not claims that semantic fallback always refuses the controls.

**confirmed:** Re-ran `TMPDIR=/tmp uv run pytest -q tests/test_3c_cue_chain.py
 tests/test_resolution_cascade.py`: **25 passed**. Existing runbook sections 1–3
cover the procedure; no new operating procedure or runbook entry is needed.
No billed probe ran for this rewrite. Existing worktree edits were preserved.

**new:** Parsed the five standalone JSON variants below, required each replacement
to match exactly once, and loaded each disposable package with the real loader.
All passed. The conditional pump replacement was checked separately against
both the original and revised custody delivery. Temporary packages were removed.

**corrected — evidence discrepancies:** The measured rows take precedence over
both the old plan and the supplied prose summary. All 24 first commands omit
`package`, but C10/P07 say `look`; only 22 actually attempt transmission.
Twenty of those 22 fail to earn A on attempt 1. The remaining two transmission
attempts succeed through the live path. Thus 22/24 first-attempt misses is right;
22 transmission misses is not. Stored Live C rows have **nine rejections in nine
rows**: card 4, house/the house 3, evidence transmission 1, remaining detention
sites 1. No `janus selection` or `kitchen` rejection is present there. Do not
pool smoke failures into Live C. Rejected raw narrator replies are not stored in
these rows, so their exact wording cannot be reconstructed from the error alone.

## What the matcher actually does

**confirmed:** The reproduced 15-command table is unchanged. Live A additionally
separates exact selection from a successful guarded commit: turn 13 is rejected
in all 12 samples of both arms, despite current exact selection.


IDs in this table omit `k_sl_3c_`. An empty set means no exact match. “Eligible now” means current package evidence applied to the **recorded pre-turn eligibility**, not a claim about the changed continuation after an earlier turn succeeds.

| Turn | All ten, deployed evidence | All ten, current evidence | Eligible, deployed | Eligible, current |
| ---: | --- | --- | --- | --- |
| 1 | — | — | — | — |
| 2 | b_r1 | b_r1 | b_r1 | b_r1 |
| 3 | c_r1 | c_r1 | c_r1 | c_r1 |
| 4 | — | — | — | — |
| 5 | c_r2 | c_r2 | c_r2 | c_r2 |
| 6 | c_r2 | c_r2 | — | — |
| 7 | a_r1, b_r2 | a_r1, b_r2 | — | — |
| 8 | d_r2 | d_r2 | d_r2 | d_r2 |
| 9 | d_r2 | d_r2 | — | — |
| 10 | — | — | — | — |
| 11 | — | — | — | — |
| 12 | d_r2 | d_r1, d_r2 | — | d_r1 |
| 13 | — | d_r1 | — | d_r1 |
| 14 | d_r2 | d_r1, d_r2 | — | d_r1 |
| 15 | d_r2 | d_r2 | — | — |

`candidate_matcher.py:196–222` requires an alternative from every group as whole words/phrases. It does not stem “coordinating” to “coordinate”, or “broadcasting the truth” to “broadcast the reports”. `:158–193` returns a result only for exactly one match in the supplied candidate set. The live provider supplies the projected universe (`cloudflare.py:414–424`), not every package reveal.

State-appropriate subsets, confirmed against the bundles' universe sizes and the package chain:

- Turn 1: A-R1/A-R2; turn 2: B-R1/B-R2.
- Turn 3: C-R1/C-R2; turns 4–5: C-R2.
- Turns 6–8: D-R1/D-R2; turns 9–15: D-R1.

Do not reinterpret the raw all-ten ties at turn 7 as a live tie either: both A-R1 and B-R2 are already established. Their shared “independent networks” noun and “broadcast” verb explain that static result.

## Per-turn diagnosis

**confirmed:** Historical turn numbers below refer to the Round 1 recording,
not Live C. Source lines refer to the reviewed files. The historical refused
selections were `semantic_refusal`; static all-ten ties do not describe the
eligible universe after D-R2.

| Turn | Deciding source and result | Classification / Round 2 disposition |
| ---: | --- | --- |
| 4 | `knowledge.yaml:2555–2616`, `reveal_eligibility.py:48–62`: only gates remain; following Michelle does not open them. | **confirmed:** fair non-reveal movement; do not add a reward. |
| 6 | `knowledge.yaml:2586–2678`: gates spent, D eligible; escape command earns neither D. `world.yaml:377` lacks a surface binding. | **corrected:** one walk is fair; repeated re-evacuation despite the completed fact is a real grounding/presentation defect. |
| 7 | `knowledge.yaml:2621–2622`, `cloudflare.py:536–601`: noun matches, verb misses; fallback refuses. | **confirmed:** affordance/recovery miss, not dead eligibility. Reporting known locations does not necessarily inspect new reports. |
| 9 | `knowledge.yaml:2621–2653`, `reveal_eligibility.py:51–52`: spent D-R2 matches; D-R1 does not. | **corrected:** late-loop symptom, but low prevalence as a fresh-start primary cause. |
| 10 | `candidate_matcher.py:196–222`: neither D evidence group pair matches. `pacing.yaml:162` supplies pressure only. | **confirmed:** repeated work earns nothing; a timer fact is not earned progress. |
| 11 | Same miss; `cloudflare.py:1414–1433` appends the staged reports cue. | **confirmed:** cue repetition does not grant D-R1 or prove narrator leakage. |
| 12 | `candidate_matcher.py:172–193`, `knowledge.yaml:2621`: current evidence uniquely selects eligible D-R1. | **corrected:** #667 coverage repair now proven live, 12/12 versus 0/12. |
| 13 | `knowledge.yaml:2832–2841`, `narration_safety.py:214–235`: unavailable `remaining detention sites`; atomic rejection. | **confirmed:** not counted as stuck by design; current selection still cannot override the guard, 12/12 rejected in both arms. |
| 14 | Same state-specific correction as 12. | **corrected:** live commit 12/12 versus 0/12; not proof that a free player will type it. |

**confirmed:** Historical turn 15 ended through fallback. Current
`canonical_events.py:47–79` uses the scene's `handoff_after_turns`, then commits
ready resolution events and their fallback text. `pacing.yaml` ends the story
on `phase_two_conflict_plan_known`. `transition_cause: none` is compatible with
story completion. No reveal on a turn is not automatically a defect:
`frontend/e2e/blind-player.js:326–335` also considers affordance mentions,
new storylets and grounding IDs, and excludes rejected/game-break turns.

### New: all 24 fresh rows, and ranked causes

Numbers are **accepted scene turns** of committed reveals, not attempt numbers.
A dash means that link was never player-earned. The deadline later supplies
missing links. E identifies the only earned completions.

| Row | A | B | Pumps C1 | Gates C2 | Reports D1 | Families D2 | E | Rejections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 | 2 | 4 | 6 | 8 | — | — | — | 0 |
| P01 | 2 | 3 | — | 14 | — | — | — | 0 |
| C02 | 8 | 12 | — | — | — | — | — | 1 |
| P02 | 1 | 3 | 13 | — | — | — | — | 0 |
| C03 | — | — | — | — | — | — | — | 0 |
| P03 | 2 | 3 | 4 | 6 | 8 | 10 | 12 | 0 |
| C04 | 2 | — | — | — | — | — | — | 0 |
| P04 | 2 | 3 | — | 8 | — | — | — | 1 |
| C05 | 2 | 3 | 5 | 7 | 12 | 14 | — | 0 |
| P05 | 2 | 3 | 5 | 7 | — | 10 | — | 1 |
| C06 | 3 | 4 | — | 7 | — | — | — | 0 |
| P06 | 2 | 3 | — | 6 | — | — | — | 1 |
| C07 | 2 | 3 | 5 | 7 | 9 | 11 | 13 | 0 |
| P07 | 2 | — | — | — | — | — | — | 1 |
| C08 | 2 | 4 | 6 | 8 | — | 11 | — | 0 |
| P08 | — | — | — | — | — | — | — | 0 |
| C09 | 2 | 4 | — | 7 | — | — | — | 0 |
| P09 | 1 | 3 | — | 7 | — | — | — | 0 |
| C10 | 2 | 4 | — | 7 | — | — | — | 0 |
| P10 | 2 | 3 | 5 | 7 | 9 | 13 | — | 0 |
| C11 | 2 | 3 | 4 | 6 | — | 9 | — | 1 |
| P11 | 2 | 3 | 4 | 6 | — | — | — | 1 |
| C12 | 2 | 3 | — | 7 | — | — | — | 1 |
| P12 | 2 | 4 | 12 | 7 | — | — | — | 1 |

**new:** Rank by observed exposure first, not by an invented causal percentage.
The categories overlap. Observational counts say where a repair could help;
they do not show how many failures that repair would prevent.

1. **Opening delay: 22/24 first-attempt misses, including 20/22 transmission
   attempts.** Eighteen rows eventually earn A on accepted turn 2; C06 on 3,
   C02 on 8; C03/P08 never earn it. Two earn it on turn 1. Early invented tasks
   become long detours in C03 (bush/tunnel) and P08 (satellite/JANUS shutdown).
   First-command wording is the widest measurable opportunity, but two misses
   are `look`, and a guard rejection consumes no accepted turn.
2. **Archive possession is not clear enough: 18/24 rows attempt to take,
   retrieve, grab or wrest the case again after B.** Rows: C01/P01, C02/P02,
   P04, C05/P05, C06/P06, C07, C08, C09/P09, C10/P10, P11, C12/P12.
   Both earned rows demonstrate that some extra actions are recoverable; C07
   is in this set. Repeated custody attempts cost several turns in P04, P09
   and C12. The world binding already gives Kristin the case, but B-R1's
   delivery only says she stops Rebecca. Narration then often puts it back
   in Rebecca's hand. This is missing result material plus possible state
   regression, not evidence that B must fire again.
3. **Missing pump/gate work: 14/24 never complete both C parts.** Thirteen
   never earn C1; P02 earns C1 at 13 but not C2. Eight gate earners never
   earn C1: **P01, P04, C06, P06, C09, P09, C10, C12**.
   Of 18 gate earners, **10** complete both parts;
   P12 is one of the 10, but only at turn 12. The binding cannot help those
   eight before fallback. C10 goes to the pump controls but never operates
   them. A command to move there should not automatically operate them.
4. **Long post-gates escape behavior: 9/24 under the summary's broad
   no-D-action grouping; only 2/24 are clean early binding targets.**
   C01/P11 complete both C parts at 8/6, then spend 6/8 turns fleeing with
   no D action. P04/P06/C09/P09/C10/C12 flee with C1 missing; C09 also
   re-takes a newly invented second case, so “only flee” is too literal.
   P12 flees, finally earns C1 at 12, then holds the barrier through 14.
   C06 also travels and tries journalists, but C1 is missing; those commands
   are not an eligible D opportunity. Seven rows with both C parts actually
   engage reports/families: P03, C05/P05, C07/C08, P10/C11. Of these, only
   P03/C07 earn E. P01 earns gates on the deadline with no continuation.
5. **Rejections: 9/24 rows, one each.** They consume attempts, not turns.
   No row exhausts the 20-attempt cap; none of these nine errors by itself
   proves a deadline-budget failure. Keep guards correct.
6. **Late report/family recovery and E timing: 5/24 failures after genuine
   D engagement.** P05/C08/C11 earn families but never reports; C05/P10
   earn both D parts only at 14/13 and never E. C11 has the clearest repeated
   community-work loop (five accepted turns after D2 plus a rejection).
   This supports retaining a narrow community-result hypothesis, not making
   it the universal next experiment. The 20/24 missing D1 count is a downstream
   result; it must not be assigned wholesale to D1 wording.

**new:** A useful disjoint accounting of the 22 failures is: 14 incomplete C
chains; 3 complete-C rows with no D commit (C01/P11/P12); 3 families-only
rows (P05/C08/C11); 2 both-D rows without E (C05/P10). This reconciles the
counts without attributing every timeout to the same loop.

## Verdicts on the seven leads

1. **confirmed — compound-tie theory corrected:** “The candidate list is
   already projected” (`candidate_matcher.py:178–180`). D-R2 is spent after
   turn 8. Live A settles #667's per-command value; retain all-ten tie tests.
2. **confirmed — turn 7 was not guaranteed D1:** `earn_when: checks reports
   from detention sites` (`knowledge.yaml:2619`); “report” is not that verb
   group. Both D candidates were eligible. Do not add variants to rescue it.
3. **corrected — surface fact exists, physical consequence missing:**
   `resolution_escape` waits for both C/F storylets (`canonical_events.py:13–33`,
   `storylet-routes.yaml:2844–2861`). The offline binding works. Gates alone
   are not escape; the fresh rows make this distinction essential.
4. **confirmed — D1 survives D2:** their effects are respectively
   `national_network_fragmenting` and `community_rescue_efforts_begun`.
   Both require truth plus surface; both storylets together supply
   `charles_at_large` through the canonical event. E requires truth, surface,
   fragmentation and Charles-at-large, and either E alternative sets both
   Phase One/Two facts. The established-effect filter at `cloudflare.py:681–684`
   does not discard D1 because D2 fired. The new stateful tests pin this.
5. **confirmed — remaining detention sites has an owner:**
   `k_resolution_kristin_rescue` explicitly declares `leak_terms:
   [remaining detention sites]` (`knowledge.yaml:2832–2841`). No new physical
   thing fixes this; Live A confirms that selecting D1 does not license it.
6. **confirmed — original cue attribution:** the reports sentence belongs to
   `handoffs.yaml:316–324` and cue composition, not an unearned D1 surrender
   statement. It appeared on historical turns 6/11, not 12. **new:** Fresh
   rows do contain serious unrelated drift: P02's Phoenix note, P07's new
   search for Michelle, P08's JANUS shutdown, C09's second case. Address
   evidenced source/material gaps; do not declare each invented prop.
7. **corrected — legal fallback, failed player outcome:** the ending follows
   its contract, but 22/24 relying on it misses the earned bar. A seven-reveal
   path can finish within 14; the two earned rows prove possibility, not an
   80% rate. “No slack” means little measured margin, not mathematical
   impossibility. Deadline adjustment remains a conditional authored option.

## Already tried or settled (do not recommend these again)


Search `.plans/implementation_plan.md` for each term before you recommend
anything.

- The PR #667 verb additions to `d_r1`. You may judge whether they are enough;
  do not just add more verbs of the same shape.
- More cue wording as a general lever. The 2B probes found cue wording weak
  against an invented object.
- Judge calibration and any LLM-judge changes. Dropped by Brandon.
- Making the scripted canon journey match the chain. That is a test-script
  matter, not a player-facing fix.
- Widening `action_evidence` just to make a recorded command match.

- **confirmed (Round 2):** The #667 phrases are proven correct per command
  by Live A. The matcher is not to be changed. No additional pre667 screen.
- **corrected (Round 3):** The surface binding passes offline state, order,
  deadline, save/load and populated-member checks. It was measured live and
  missed the consistency bar (9/12 versus 10 required); it is not adopted.
- **new (Round 3):** The escape-statement arm also missed its live bar. Neither
  escape edit should be rerun on the same starts without new evidence. Entry
  passed its first-stage bar only; custody has no valid n=12 result yet.
- **corrected (Round 2):** Earlier no-transcript smokes are superseded. Live C
  misses the 10/12 bar in both arms. The two old wording arms were not run.

## Rules you must follow


- Use only techniques the project already proved. `docs/scene-fixing-guide.md`
  and `docs/world-model-grounding.md` list them. In order: missing story
  material goes in as a reveal handoff or a statement; a line that pulls the
  narration the wrong way is scoped or removed; a narrator rule comes last, and
  only if it is story-neutral. For each fix, name the technique and where an
  earlier scene used it.
- Remove before adding. Prefer a subtractive fix.
- Never use keyword or regex scanning of narration as a gate.
- Facts are the only mutable truth; the shared runtime stays story-agnostic.
  If the cause is in the engine (for example the tie rule or the eligibility
  filter), report it as a finding with file and line, and separately give the
  best story-side fix. Do not make an engine change part of the story fix, and
  do not fix one story's problem with a story-specific engine branch.
- A fix must generalize: say what the same defect would look like in another
  story and whether your fix covers it.
- Do not weaken a correct guard. Any evidence change must respect the matcher's
  rules: whole words, possessives, negation words, exactly one match per
  command.
- A declared state axis is exactly two opposite values. Things need a place
  that is their most local container. Follow the Things and Names sections of
  the grounding guide for anything you declare or place.
- Player-input examples in your probes follow `docs/player-input-guide.md`:
  imperative commands, first-person possessives.
- New text is plain: 12th-grade reading level, one idea per sentence, no
  figurative filler.

## Ranked follow-up fixes

**corrected (Round 7 priority):** A–C retain earlier exact replacement strings
and rationale. Their measured dispositions are in Steps 1–5. Entry/custody/pump
are adopted; aliases lost. Only the bounded C1 changed-context retest in Step
11a is next. E ties, surface binding and deadline edits are not queued.

### A. New: opening and archive/pump material (largest observed reach)

**new — entry replacement, preferred to bare evidence.** In `plot.md:831`,
replace the entire 3C `entry_text` value:

Old:
> The broadcast chamber lights steadied as Brandon's relay held open. Outside, Charles's emergency deluge was filling the outer access level and forcing water toward the maintenance routes; inside, the evidence was ready to leave for good.

New (retain the existing trailing two newlines):
> The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence package is ready to send. Water is entering the outer access level.

This scopes the opening to the first task and removes the figurative “leave
for good” plus long escape emphasis. The package is already named in 3C.1 and
A's cue; no invented device, outcome, entity, or future revelation is added.
Technique: place missing story material on the initial screen, as with 3B's
missing office-entry material in the scene-fixing guide; subtract a misleading
pull as in 1A #668. These precedents prove the technique, not this wording.
Do not claim the newer 2B entry text has an isolated measured win: the plan
history explicitly says the merged entry was not in that earlier screen.

**corrected — alias alternative rejected for now.** New evidence warrants
reopening the question, but broadening the noun group fails the free negative
controls above. The guide allows author-reviewed aliases; it does not require
accepting an alias that pairs with unrelated verbs. Do not remove `run`, `show`,
and other legitimate alternatives as an unmeasured collateral change. If the
entry screen loses, report that and review action semantics separately; neither
a parser rewrite nor an instruction telling players exact commands is in scope.

**new — explicit custody delivery.** In `knowledge.yaml`, B-R1 `delivery_text`:

Old:
> Kristin stops Rebecca from fleeing with the data case. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls.

New:
> Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls.

This states the same custody change already committed by
`world.yaml:portable_archive_secured`; it creates no new fact. Technique: missing
result in an earned handoff, as in the guide's 3B office-entry repair. Retain the
pump sentence. Check the following turn's actual parent and reply: a better
handoff cannot repair a later model-proposed move back to Rebecca by itself.
This is a presentation hypothesis, not proof that all 18 repeat actions vanish.

**new — pump need, measured separately after custody.** Replace only the last
sentence of that B-R1 delivery:

Old:
> Water rises around the drainage pump controls.

New:
> The drainage pumps need power. Water rises around the drainage pump controls.

This supplies the task from plot 3C.3 (restoring power), before either C part can
have fired, and names the existing pump controls. It does not assert an axis,
move captives, open gates, or instruct the player to use a particular command.
Technique: the same missing-material handoff. Do not change all copies of the
water sentence in handoffs or plot: this is one earned handoff experiment, not
a generic cue rewrite. Verify C1-first and C2-first remain legal. If the source
payload already expresses the need equally clearly, do not run this arm merely
to repeat it; first locate the competing sentence that the narration follows.

### B. Corrected: surface binding, completed implementation screen

**confirmed:** Exact `world.yaml:377` replacement:

```yaml
# Old
- captives_reaching_surface
# New
- id: captives_reaching_surface
  on_assert:
  - {move: captives, parent: facility_escape}
```

The existing rule is “Story facts that restate a physical relation declare the
effect once.” Precedents: the override-code binding in 3A and office-entry
binding in 3B (`world.yaml:355–367`), with the 1B bench fix illustrating why
place names must resolve. The report proves that this moves the existing group
only after both C parts (either order) and at fallback, survives save/load, and
leaves the three named people where they were. Its listed member parents do not
constitute a populated-member test. **corrected (Round 3):** the later
`tests/test_3c_surface_binding.py` covers populated members and passes, as
recorded in the Step 1 result; the original report's limit still stands.

**corrected (Round 3):** Do not adopt: the live consistency screen below missed
its bar and continuation worsened. The original conditional adoption criterion
was not met. Do not promise a 9/24 rescue: only C01/P11
are clear early complete-C/no-D targets. P05/C08/P10 also regress into travel
and may benefit, but that effect is unmeasured. No new surface reveal, no
unconditional player teleport, and no gate-only surface announcement.

**corrected (Round 7) — this fallback already lost Step 5.** The exact C1
replacement below was tested, not merely proposed: D by turn 10 was 3/12 versus
7/12; earned endings 2/12 versus 5/12. Do not call it unbuilt or unrun.
The new hosted prompt justifies only the bounded changed-context retest in
Step 11a, not adoption or automatic repetition of that n12. Its source text is:

Old:
> Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads captives through the maintenance tunnel.

New:
> The drainage pumps have power. The evacuation route is open.

The reveal-time delivery stays unchanged. This removes the perpetual travel
assignment from repeated recall. It follows 2C's stale recall scoping and 1A
#668; it does not assert who is now on the surface. If C2's ongoing flood/relay
statement is the actual pull, scope it in a later independent arm, not bundled
with C1. No new narrator rule is justified by these rows.

### C. Corrected: old wording arms, guards, and budget

**corrected:** Drop broadcast-result and community-result from their old
positions as immediate Steps 2/3. Neither can affect an unearned A or D2
statement. Live B has no report/family/broadcast-target commands, and most
fresh failures occur before completing C. Retain them only as targeted
hypotheses for newly reproduced loops: C02's post-A waiting, C05's repeat
upload, or C11's repeated post-D2 community work. Do not claim they were tested
and lost. Their exact candidate replacements remain:

| Knowledge statement | Old | New |
| --- | --- | --- |
| A-R1 | Michelle broadcasts captives, JANUS records, planning sessions, and detention locations to independent networks. | Independent networks have the captives' video, JANUS records, planning sessions, and detention locations. |
| D-R2 | Families and communities organize independent rescue efforts after learning that many of the missing are still alive. | Families and communities have begun independent rescue efforts. They know that many of the missing are still alive. |

Technique: remove/scoped completed-action recall, as in #668 and 2C. Retain
reveal effects, guards and delivery. Reopen only one whose newly recorded
prompt supports that cause; if none does, drop both from implementation.

**new — grounding decisions for rejections:**

| Term | Decision under the grounding guide |
| --- | --- |
| `card` (4 rows) | No new generic card. Rejected raw replies are absent, so do not infer whether these meant a credential, a memory card, or an echo. Replay/capture the exact rejected payload first. If authored text requires an actionable credential, give that particular thing a unique name, scoped aliases and its local holder/container. No source establishes such a new 3C prop here. |
| `house` / `the house` (3 rows) | Do not add a house at the facility. The earlier house is already declared; premature return to it is a wrong-scene problem. P07 has already wandered into a fabricated search. Repair the source/context that caused the detour if reproducible. |
| `kitchen` | Not in these rows. Existing earlier-scene place; no new 3C declaration warranted without the actual artifact. |
| `evidence transmission` (C02) | Abstract process, not a physical thing. It is a `must_convey` alternative of `k_sl_2c_c_r1` (`knowledge.yaml:1685`), whose effect is `evidence_ready_to_transmit`. Synthetic entry may omit previously earned knowledge; compare a genuine carried state before calling this a story vocabulary defect. Do not grant every earlier reveal to silence it. |
| `remaining detention sites` | Existing resolution-knowledge owner; keep the guard and earn both D links. No new place/alias. |
| `janus selection` | Not a Live C rejection in the supplied rows. Keep its actual owner/protection; inspect separately if reproduced. |

“Invented details matter only if story-breaking” does not mean rejected turns
are harmless. It means prioritize the detours that change the player's task,
such as P02's invented note and P08's shutdown quest. Declaring the bush,
dumpster, satellite or Phoenix note would canonize the detour, not repair it.
No new physical declaration is justified by these rejection tokens alone.
The existing case, pump controls, gates and captive group are the immediate
grounding targets. Any later declaration must follow local containment,
unique names, scoped aliases, and exactly two opposite state poles.

**new — budget decision:** Seven commits are needed: A, B, C1, C2, D1, D2,
and either E. The two earned rows use 12/13 accepted turns, so 14 is possible.
Fourteen turns cannot explain every long loop, and rejections do not
subtract accepted-turn budget. Yet the authored targets are inconsistent with
comfortable sequential play: C/F target 11, latest 12; D/G both target/latest
13; E target/latest 14. One reveal per command means both D steps cannot happen
on 13. If the second C part lands at 12, D1/D2/E require turns 13/14/15 even
with no extra movement or clarification.

If the repaired scene still misses the bar and failures now reach both C parts
but run out of room for D/E, screen **handoff_after_turns 14 → 16**, leaving the
deadline enabled, min 10/nudge 11 unchanged. Fifteen is the sequential minimum
for a turn-12 C finish; sixteen allows one extra accepted discovery action.
This uses the existing authored pacing mechanism and the PRD's one-match
contract, not a new technique. Earlier scenes already use different authored
windows, including 2C at 16; that is mechanism precedent, not proof of a 3C win.

The isolated probe changes only the 3C window in `pacing.yaml`. If adopted,
synchronize the 3C table in `plot.md` (14 → 16); change D/G latest 13 → 14,
E target 14 → 15/latest 14 → 16 in `storylets.md` and their executable
`storylet-routes.yaml` counterparts if those timing fields are present.
Inspect actual fields before editing; do not alter realization prerequisites.
Risks: longer aimless play, pressure at 4/10 becoming repetitive, extra cost,
and changes to fallback fixtures/whole-story duration. Do not combine D steps,
remove a required C part, or weaken the earned definition to fit the clock.

## Probe specifications and order of work

**corrected (Round 7 active order):** Steps 1–8 are measured history, except
Step 6, which remains unrun and is not queued. Steps 9/10 and one Step 11
journey are complete. Preserve historical strings and protocols for reproducibility.
Next is Step 11a, then the conditional Step 12 decision. Do not interpret
historical “next screen” or “nothing adopted” wording as current instructions.

### Common protocol — confirmed

One source change, one measurement, then re-baseline. Preserve all samples and
report both arm counts, not a small difference as proof of superiority. Freeze
package hashes, state construction, transcript, raw player/model/settings and
caps in the preregistration. Semantic fallback ON for acceptance. Use the established Ringer workflow. **corrected (Round 5):** carried smoke2
already validates this harness; after free alias validation, the next billed
run is 12 interleaved rows per arm, not another synthetic or billed smoke.
No judge changes. Read narration plus delivery/cues; score commits and facts,
not `item_facts` or lexical narration scans. World-parent checks are deterministic.

Control is the last adopted package with `{"overrides": {}}`, except the
**Round 3 Step 3 baseline**: `entry` carries the entry-text override in both
arms, with custody delivery as the sole contrast. This is not adoption. Each candidate
uses `{"name": "...", "story_package": "data/stories/continuity-initiative",
"overrides": {"FILE": {"replacements": [{"old": "...", "new": "..."}]}}}`.
Exact old/new YAML strings are below. Require each replacement exactly once;
load the package and diff shipped payloads before paying for a run. State resets
must use complete snapshots; never continue a different arm's mutated state.
A controlled post-C screen is diagnostic; fresh entry with real carried state
is the adoption test. **new (Round 4):** Step 4 baseline was `custody`; the next
baseline is `pump`. The original Step 7/8 smoke and comparison are now measured. The revised
Step 7 free checks and Step 8 fresh comparison supersede their old queue.

### Step 1 — corrected: surface binding, not another #667 comparison

**corrected — measured outcome (2026-10-18):**
`.plans/astra-3c-surface-binding-prereg.md`; `bench/results/stage7-3c-surface-n12/`;
12 rows per arm, checker OK. Synthetic `postc` scripts A/B/C1/C2 at turn index 7,
then the first command specified below; cap 10 attempts. Captives are at
`facility_escape` after that command in 12/12 surface rows versus 0/12 control;
no person moved. Offline both-C orders, C2-only, deadline, save/load and populated
members pass in `tests/test_3c_surface_binding.py`. First smoke failed on missing
`scripted_prefix.turn_index`; the corrected second smoke passed. Its reversed
outcomes underline that n=1 is not a rate.

Consistency is 9/12, below the 10/12 bar. Surface rows 02, 10, 12 narrate Kristin
following the group through the tunnel; rows 10, 11, 12 spend another 5–6 turns
there. No control row loops there. Earned/deadline/none: control 7/5/0, surface
3/9/0; D-R1 commits 10/12 versus 6/12; rejections 0 versus 1; clarifications 0.
Kristin remains in `broadcast_chamber` in every row, as the binding does not
move her. The four-row earned loss exceeds the three-row comparison threshold.
**Not adopted.** This synthetic start is kinder than fresh Live C (control 1/12);
it does not establish real carried-state behavior. Requests: 172/480 Cloudflare,
139/240 player, no run-failure file. Keep the original specification below as
the tested proposal, not a pending instruction to run or adopt it again.

Use the already present `bench/variations/stage7-3c-surface-binding.json`:

```json
{"name":"3c-surface-group-binding","story_package":"data/stories/continuity-initiative","overrides":{"world.yaml":{"replacements":[{"old":"- captives_reaching_surface\n","new":"- id: captives_reaching_surface\n  on_assert:\n  - {move: captives, parent: facility_escape}\n"}]}}}
```

Cheapest check is the existing offline report plus a populated-member fixture,
not another paid state test. Reconfirm both C orders, C2-only, deadline and
save/load. Then construct equal synthetic states after A/B/C1/C2 at accepted
turn 7, retaining full scripted transcript and leaving Kristin in the maintenance
network. Commands: `Send the evidence package.`, `Take the Portable data case
from Rebecca.`, `Restore the drainage pumps.`, `Open the surface gates.`
Explain any synthetic turn padding in metadata, not fictitious player history.

Replay `Follow Michelle and the captives through the surface gates.` once per
sample, then allow raw continuation. Mechanical win: captives at facility_escape,
no extra person move, no earlier move with C2 alone. Live consistency target:
at least 10/12 replies respect the completed captive escape and answer Kristin's
own movement, with no new guard failures. Also score return-to-tunnel narration,
accepted travel commands before the next D commit, and both D plus E completion.
An initial fair walk is not a failure. Adopt for grounding if consistency passes;
claim stuck-turn improvement only if continuation improves. A full scene claim
still requires fresh-entry >=10/12 earned. Expected source: `world.yaml`; tests
and variation/preregistration/reporting only around it.

### Step 2 — new: entry setup

**new — measured outcome (2026-10-18):**
`.plans/astra-3c-entry-package-prereg.md`; `bench/results/stage7-3c-entry-n12/`;
clean smoke and n=12 checker. Fresh synthetic entry, cap 20 attempts, deadline 14.
A on attempt 1: entry 12/12 versus control 1/12, passing the first-stage bar.
Control earns A on attempt 2 in eight rows, attempt 14 in one, never in two.
No reveal outside the chain commits. Earned/deadline/none is 1/11/0 in both arms:
the full earned bar fails. Control/entry: B 9/8, both C parts 6/2, both D parts
1/1; rejections 0/6 and clarifications 0. Requests: 356/960 Cloudflare,
337/480 player, no run-failure file.

Entry rows 05, 06, 09, 12 never reach B; rows 01, 02, 03, 04, 07, 11 earn gates
but not pumps; row 08 earns pumps late at turn 10; only row 10 earns the ending.
The smoke's evacuation drift does not broadly recur: row 06 alone spends turns
on the inner access level/parking garage. **Keep as a baseline candidate;
not adopted.** Step 3 uses this text in both arms by override. The four pre-B
failures cannot be fixed by changing B's delivery. Step 4's pump hypothesis is
more urgent after the four-row drop. **corrected (Round 4):** Steps 3/4 have
now run; their measured results below supersede that wait.

**corrected — rejection attribution:** Six rejections occur in two rows, not
six rows. Row 06 has `house` once and `card` twice; row 11 has `relay open`
three times on the repeated player command `Keep the relay open` (attempts
14–16). That is player-word echo, not evidence against the entry sentence.
The standalone guard accepts `Brandon's relay is open.`; the relay-wording
probe's positive control failed, so it supports no wider conclusion. Do not
reword the relay sentence on this evidence. Custody's different relay failures
are recorded separately below.

```json
{"name":"3c-entry-package","story_package":"data/stories/continuity-initiative","overrides":{"plot.md":{"replacements":[{"old":"entry_text: \"The broadcast chamber lights steadied as Brandon's relay held open. Outside, Charles's emergency deluge was filling the outer access level and forcing water toward the maintenance routes; inside, the evidence was ready to leave for good.\\n\\n\"","new":"entry_text: \"The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence package is ready to send. Water is entering the outer access level.\\n\\n\""}]}}}
```

Cheapest probe: loader plus exact first-player-screen capture; unchanged
matcher results for all 15 historical commands and the negative controls above.
Then fresh-entry raw rows, cap 20 attempts, deadline 14. First-stage win:
>=10/12 A commits on attempt 1 (A2 also counts as a valid alternative), no false
public-disclosure commits, reduced invented pre-A work. Report first-command
wording separately. Continue every row to measure the full earned bar; do not
mistake first-turn improvement for completion. If it fails, stop and diagnose
its recorded opening before adding more cue synonyms. Expected source: `plot.md`.

### Step 3 — corrected: custody handoff, measured

**corrected — Round 4 measured outcome:**
`bench/results/stage7-3c-custody-n12/`, n=12 per arm, checker OK; preregistration
`.plans/astra-3c-custody-result-prereg.md`. Synthetic `posta`, A at turn 1,
`Follow Rebecca.` at turn 2, entry text in both arms. B commits 12/12 each.
Entry/custody earned: 1/12 each. Re-takes: 15 commands in 10 entry rows versus
4 in one custody row; 11/12 custody rows never retry. This is a measured
behavioral gain, **not a passed next-reply prose/parent criterion**: that hand
read was not done. Gates: 10/11 rows; pumps: 6/5; rejections: 1/4. D1: 3/1,
D2: 2/3; differences under three rows are not distinguishable. Nothing adopted.
Keep custody as a provisional baseline component; do the missing hand read
from existing artifacts for free, not another custody screen. Complete live
parent evolution remains unverified where snapshots are absent.


**new — smoke outcome (2026-10-19):**
`.plans/astra-3c-custody-result-prereg.md`; `bench/results/stage7-3c-custody-smoke/`;
n=1 per arm only. Baseline `entry` and candidate `custody` both include the
Step 2 entry override; the actual custody variation combines that override
with the delivery-only JSON retained below. Synthetic `posta` scripts A-R1
at turn index 1, then `Follow Rebecca.` earns B on scene turn 2 in both rows.
**corrected:** “after A at turn 2” below means B is attempted on turn 2;
the recorded scripted-prefix index must be **1**, not 2.

The artifacts checker FAILED: `row does not record the scripted posta turn index`.
The new `posta` path omits `scripted_prefix.turn_index`, a gap already repaired
for `post8` and `postc`. This was a harness stop, not a custody loss or a clean
smoke. **corrected (Round 4):** The subsequent n=12 artifacts pass and record
turn index 1. The old stop/permission wait is superseded. Preserve the failed
smoke as history; do not rerun it. The original >=10/12 prose criterion below
is not retroactively replaced with a count of player commands.

Hand read, **two observations, not rates**: the case's parent after B is
`kristin` in both arms. The binding already performs the handoff; this edit
changes wording only. Baseline says “Kristin stops Rebecca from fleeing with
the data case”; custody says “Kristin takes the Portable data case from Rebecca.”
Re-take commands: baseline 1, custody 0. Both end at the deadline. Custody has
two `unavailable knowledge 'relay open'` rejections on `Help Brandon at the
console` and `Help Brandon leave the facility`; neither command says relay.
Unlike Step 2 row 11, these cannot be attributed to player-word echo.

**new — open synthetic-state question:** Starts assert entry facts without
committing the 3B reveals. Does missing carried knowledge affect every
synthetic-start screen, and what does a genuine carried real state show?
Compare the relevant committed knowledge and rejected payloads against such
a state before assigning these failures to authoring. This is unverified;
do not grant all prior reveals, weaken the guard, or infer a custody effect
from this failed n=1 smoke.

```json
{"name":"3c-custody-result","story_package":"data/stories/continuity-initiative","overrides":{"knowledge.yaml":{"replacements":[{"old":"delivery_text: \"Kristin stops Rebecca from fleeing with the data case. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls.\"","new":"delivery_text: \"Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls.\""}]}}}
```

Cheapest check: after B, the existing on_assert puts the actual case under
Kristin. Compare prompts for `Take the Portable data case from Rebecca.` when
already held, and `Restore the drainage pumps.`; record whether the held-by
line is present and correct. Then screen B handoff plus raw continuation in
12 rows per arm, starting after A at turn 2 and earning B with `Follow Rebecca.`
Win: >=10/12 treat custody as completed, no regression in correct case parent,
and fewer repeated acquisition attempts than baseline. Test actual prose on
the next accepted turn, not just the changed delivery. Follow with fresh-entry
completion measurement. If the world parent regresses despite correct material,
report that shared proposal/commit finding separately with a reproducer; do not
add a story-specific engine branch. Source: `knowledge.yaml` B-R1 delivery only.

### Step 4 — new: pump task before gates

**corrected — Round 4 measured outcome:** Built and smoke passed;
`.plans/astra-3c-pump-need-prereg.md`, `bench/results/stage7-3c-pump-n12/`.
Baseline `custody`, candidate `pump`; same `posta` start and raw continuation.
INCOMPLETE: 20/24 rows (10 per arm) before Cloudflare HTTPError on request 499
and the harness exception path crashed. Preserve partial rows, spend and failure;
no replacement rows or pooled rerun. The preregistered 10/12 bar is undecided.
Pump/custody both C by turn 10: 10/10 versus 5/10; pumps: 10/10 versus 7/10;
gates: 10/10 each; gate-only escape behavior: 0 versus 3; rejections: 0/1.
Earned: 3/10 each. Strong component evidence, no earned-completion improvement.
Keep pump as the next comparison baseline, not adopted package data. Completing
four old rows will not resolve the D/E miss; drop that expenditure from the path.

**new — harness outcome (reported, not rerun here):** `door_transport.py`
`counted_provider` is now a plain context-manager class; the generator wrapper
tried to assign `__traceback__` on re-raised `NarrationProviderError`. Its new
regression fails before/passes after, per the implementation plan; 124 tests and
touched-file Ruff passed there. The Ringer task failed on pre-existing Ruff
errors in other stage7 files. Fix remains uncommitted. Before new spend, include
`test_door_transport.py` and `test_three_c_probe.py` with the relevant 3C tests:
two modules importing `three_c_probe` have a pre-existing standalone import-path
failure. Do not describe that combined run as standalone collection passing.

**corrected:** The replacement below used the provisional custody baseline;
“winning” means reduced re-takes, not a prose bar or adoption.
Exact replacement in the Step 3 winning B delivery: suffix
`Water rises around the drainage pump controls.` becomes
`The drainage pumps need power. Water rises around the drainage pump controls.`
Apply to the **whole B-R1 delivery line** shown above, not every suffix occurrence.
If Step 3 lost, use its original line as baseline. Format is the same JSON
`knowledge.yaml.replacements` record; the full old/new values are defined here
by that single-sentence substitution. Validate exactly one occurrence.

For the provisional custody baseline, the exact `replacements` entry is:

```json
{"old":"delivery_text: \"Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations to independent networks. Water rises around the drainage pump controls.\"","new":"delivery_text: \"Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations to independent networks. The drainage pumps need power. Water rises around the drainage pump controls.\""}
```

Free check: B commit cannot itself assert either C fact; inspect the screen.
Replay C2-first with `Open the surface gates.`, then `Restore the drainage pumps.`;
prove surface remains false until both. Live screen after B plus fresh rows:
>=10/12 earn both C parts by accepted turn 10, no gate-only escape fact. This
leaves four turns for three required D/E commits and one discovery action.
A different deadline is not part of this experiment. Expected source:
`knowledge.yaml` B-R1 delivery only; cue text and matcher unchanged.

### Step 5 — new, conditional: remove the observed persistent escape pull

**corrected — order and measured outcome (2026-10-18):** Brandon moved this
screen immediately after Step 1 because that arm's tunnel loops gave a specific
reason to test the repeated statement. It has already run; it is no longer a
pending conditional step. `.plans/astra-3c-escape-result-prereg.md`;
`bench/results/stage7-3c-escape-n12/`, checker OK. Neither arm includes the
surface binding. Same synthetic `postc` start and first command as Step 1.
Free checks in `tests/test_3c_escape_result.py` pass: only the statement differs,
C1-only neither supplies surface nor moves people, matcher unchanged. Smoke
passed, with one unrelated invented `senior official` guard rejection.

**corrected — measured bar:** The preregistration measures a D commit by scene
turn 10 (>=10/12), superseding the earlier two-accepted-command target below.
The escape arm scores 3/12 versus control 7/12: bar missed. Earned/deadline/none:
control 5/7/0, escape 2/10/0; any D commit 8/12 versus 5/12; rejections 1 versus
2; clarifications 0. Escape first replies 01, 02, 05, 06, 07, 12 place Kristin
at or approaching shut gates instead of through them. The rewrite appears to
remove the sense that the group is already moving; this is a hand-read
interpretation, not proof of a general mechanism. **Not adopted.** Control
earned 7/12 in Step 1 and 5/12 here on the same setup; differences under three
rows are not distinguishable. Requests: 180/480 Cloudflare, 144/240 player,
no run-failure file. The exact rejected candidate and original probe design
remain below for reference, not as an instruction to rerun them.

Only if Step 1's group is correct but the prompt keeps directing completed
escape. Use this exact replacement in `knowledge.yaml`:

```json
{"name":"3c-escape-result","story_package":"data/stories/continuity-initiative","overrides":{"knowledge.yaml":{"replacements":[{"old":"statement: 'Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads captives through the maintenance tunnel.'","new":"statement: 'The drainage pumps have power. The evacuation route is open.'"}]}}}
```

Offline: identical eligibility/effects and no new location claims. Screen equal
post-both-C states (turn 7) and C1-only states. Win: >=10/12 complete-C continuations
reach a D commit within two accepted commands, with no premature escape in
C1-only controls, then improve earned completion in fresh rows. If another source
line is shown to cause the loop, replace this candidate with that one scoped
line and preregister it; do not combine speculative edits. Earlier broadcast/
community alternatives are reopened only for their specific surviving loops,
in separate screens using the same replacement format and exact texts in C.

### Step 6 — new, conditional: deadline 16

**corrected (Round 6):** Not supported as the next experiment. In the latest
screen, families-v2 12 and pump 07 earn D2 at 12 but spend 13/14 on more rescue
coordination rather than E. Both also had recognition misses. Extra time might
help, but the recordings do not show an attempted E blocked only by time.
Do not revive this screen on eligibility alone; require evidence of an otherwise
correct chain losing an E attempt specifically to the deadline.

**corrected (Round 5):** Not built or screened; defer until after the revised
alias. Now there is evidence of budget exposure: families 2/5 and pump 12 earn
D2 at 14 and lose E to fallback. Five other rows earn E at 14 with empty
`deadline_event_ids`, so 14 itself is not automatically a timeout. Extending
to 16 might save three rows, but two are also alias targets and no turn 15/16
was recorded. First isolate recognition at 14. Use Step 8's residual-loss
criterion before paying for a 14-vs-16 comparison; do not bundle both edits.
Conditional cost: a fresh 24-row comparison, separately capped at 960/480,
plus free harness/deadline checks. Prior run duration is only an estimate.

```json
{"name":"3c-deadline-16","story_package":"data/stories/continuity-initiative","overrides":{"pacing.yaml":{"replacements":[{"old":"- scene_id: 3C\n  min_turns: 10\n  nudge_after_turns: 11\n  handoff_after_turns: 14","new":"- scene_id: 3C\n  min_turns: 10\n  nudge_after_turns: 11\n  handoff_after_turns: 16"}]}}}
```

Free probe: a valid synthetic chain with second C at 12, `Read the detention
site reports.` at 13, `Call the families of the missing.` at 14 and
`Open the recovered document.` at 15. Control must expose fallback provenance;
16 must earn without fallback. Also prove a stalled state still falls back at
16. Validate the harness first: its current `accepted >= 14` / extra-turn stop
logic is hard-coded (`three_c_probe.py:345–347`). It must derive the varied
deadline before this comparison; otherwise it cannot measure the candidate.
Keep attempts separately bounded (20 initially) and count capped rows as failures,
not replacements. Expected files: pacing plus harness/test changes; synchronize
plot/storylet source timings only on adoption as described above.

Live win: fresh-entry >=10/12 earned at 16, improved over the unchanged 14 arm,
with no extra false reveals or weakened guard. If the same escape/case loops
continue, reject the longer window as a stuck-turn remedy. This step depends on
new near-complete rows after material/grounding repairs, not the old two earners
alone. Do not change the global time budget to conceal a local pacing problem.

### Step 7 — new: review family communication aliases, then one mechanics smoke

**RESULT — corrected (Round 6):** Revised aliases were built in
`bench/variations/stage7-3c-families-v2.json`, arm `families-v2`, with the exact
34 alternatives and `their families` below. Reported build validation: 102
tests pass, Ruff clean, no `data/` change at build time. Step 8's fresh screen
then failed the alias arm at 9/12. Close this step; retain its exact specification
as history, and do not append aliases to rescue the latest missed sentences.

**corrected — Round 4 outcome:** The original three-phrase arm passed its
free checks, then earned 9/12 versus pump 8/12 in Step 8. It misses the scene
bar. Preserve its variation and results; do not overwrite it with a new arm.

**new — revised alias decision:** Permit a reviewed alias for the in-world
act of sending family news, not an expansion of selection semantics. PRD and
player-input guide explicitly allow author-reviewed aliases; #667 is the
measured alias precedent (same scene, not an earlier-scene win). A cue telling
the player to use `tell` would not repair recognition of a correct message.
The settled prohibition still excludes changes justified only by making stored
sentences green. Freeze the action grammar and controls before a fresh screen.

Prefer one recipient-qualified phrase family over full transcript additions.
Its literal expansion below covers two recipient forms, message/response/update
or prisoner-name/record information, and recipient-first `send` or recipient-last
`send`/`broadcast`. It includes unseen cross-combinations; it never copies the
recorded claims about survival, detention-network collapse, or rescue status.
The current matcher needs literal contiguous phrases, so this is 34 explicit
alternatives, not new wildcard syntax or a runtime grammar. Existing `tell`
already handles `the families`; add `their families` to the object group for
that ordinary recipient form. Preserve the older legitimate rescue/call verbs.

Exact proposed replacement in `data/stories/continuity-initiative/knowledge.yaml`,
D-R2 only, lines 2651–2653. This is a proposal, not an applied package change.
The `families-v2` variation copies pump's existing overrides and adds one
`knowledge.yaml.replacements` entry whose `old`/`new` are these complete blocks.
Do not stack it on the old families variation, which changes the old string.

Old:
```yaml
  action_evidence:
  - [ask, talk to, call, contact, tell, inform, reach, join, help, organize, support, meet, work with, coordinate, speak to, comfort, greet, visit, find, gather, volunteer, volunteer with, broadcast updates, answer the families with, answer the families, reassure the families, respond to the families]
  - [the missing, missing families, missing family, family members, family member, the families, those families, community rescues, community rescue, rescue efforts, rescue effort, rescue volunteers, rescue volunteer, volunteers organizing rescues, rescue teams, rescue team, rescue groups, rescue group, local communities, local community, independent rescues, independent rescue, survivors' families, survivor families, missing survivors, living missing, still alive, community volunteers, community volunteer, rescue organizers]
```
New:
```yaml
  action_evidence:
  - [ask, talk to, call, contact, tell, inform, reach, join, help, organize, support, meet, work with, coordinate, speak to, comfort, greet, visit, find, gather, volunteer, volunteer with, broadcast updates, answer the families with, answer the families, reassure the families, respond to the families, send a message to the families, send a message to their families, send a response to the families, send a response to their families, send an update to the families, send an update to their families, send the names and locations to the families, send the names and locations to their families, send the captives' names and locations to the families, send the captives' names and locations to their families, send the prisoner records and names to the families, send the prisoner records and names to their families, broadcast a message to the families, broadcast a message to their families, broadcast a response to the families, broadcast a response to their families, broadcast an update to the families, broadcast an update to their families, broadcast the names and locations to the families, broadcast the names and locations to their families, broadcast the captives' names and locations to the families, broadcast the captives' names and locations to their families, broadcast the prisoner records and names to the families, broadcast the prisoner records and names to their families, send the families a message, send the families a response, send the families an update, send the families the names, send the families the prisoner records, send their families a message, send their families a response, send their families an update, send their families the names, send their families the prisoner records]
  - [the missing, missing families, missing family, family members, family member, the families, those families, community rescues, community rescue, rescue efforts, rescue effort, rescue volunteers, rescue volunteer, volunteers organizing rescues, rescue teams, rescue team, rescue groups, rescue group, local communities, local community, independent rescues, independent rescue, survivors' families, survivor families, missing survivors, living missing, still alive, community volunteers, community volunteer, rescue organizers, their families]
```

**new — initial free evidence:** In-memory copies of the actual projected
post-C candidates, real `_matches_all` and `uniquely_matched_authored_handoff`:

| Command | Revised eligible selection |
| --- | --- |
| Send the families a message confirming the captives are alive. | D2 |
| Send the families the names and locations of the rescued prisoners. | D2 |
| Broadcast the captives' names and locations to their families. | D2 |
| Broadcast the prisoner records and names to the families of the missing. | D2 |
| Broadcast a message to the families of the missing. | D2 |
| Tell their families that the captives are safe. | D2 |
| Broadcast music to the families. | none |
| Listen for any response from the families. | none |
| Send the families into danger. | none |
| Broadcast the reports to the families. | D1 only |
| Read the detention site reports and broadcast a message to the families. | D1 + D2; selector returns none |

**Risk and boundary:** Bare `broadcast` would turn report broadcasts into a
D1/D2 tie and music into a false D2; this proposal does neither. Do not add
`broadcast the reports to the families` to D2. A compound report-plus-message
continues to tie while both are eligible; if D1 is spent, D2 may correctly win.
Adding `their families` also pairs with every existing verb, including broad
`help`/`find`; negative controls must check unrelated physical actions, music,
wrong recipients and negated commands. Generic messages can have irrelevant
content, and lexical matching cannot prove their meaning. Do not claim universal
semantic safety from four controls. This same limitation exists in the current
`broadcast a message` arm. The general repair is authored communication aliases
with tests for that story's recipients and action, never changing shared rules.

**new — next free measured step (before billing):** Load the exact disposable
variation with the real loader; assert a single replacement and only D2 evidence
differs from pump. Extend `tests/test_3c_cue_chain.py` using the existing helper:
all-ten overlap, both-D eligible, D1-spent, D2-spent, neither, C2-only and both C
orders. Exercise all 34 alternatives and unseen imperative continuations; retain
whole-word, possessive, negation, #667 and E prerequisite controls. Pin the tell
compound as an existing tie. Check actual guarded commits with a stubbed provider
and hosted semantic-selection integration without making model calls. Reject
any newly earned unrelated action; do not weaken a guard or uniqueness to pass.
The initial table is not completion of those loader/state/commit checks.
Files: new `bench/variations/stage7-3c-families-v2.json`, existing arm registration,
checker and tests, cue-chain tests, fresh preregistration and Ringer task. Cost:
zero billed calls. Win: exact intended selections and no new false reveals.
That validation gates Step 8; drafting its preregistration is independent.

**Historical Round 4 specification (superseded as next work):** Keep its exact
strings and table for comparison with the measured three-phrase arm. Its old
synthetic/billed smoke instructions are complete or superseded by Step 8.

**corrected — original-arm status:** free checks DONE; carried smoke2 and n12
subsequently ran (Step 8). The originally proposed synthetic smoke was superseded. `bench/variations/stage7-3c-families.json`
(entry + custody + pump + the three scoped phrases) and the stateful tests in `tests/test_3c_cue_chain.py`
(33 pass with `tests/test_resolution_cascade.py`; includes music and unrelated-recipient negatives, D1/D2-spent, ties
return None, E needs both D). Mutation check: removing the aliases fails exactly two alias-selection tests. The hosted
semantic-selection check is still open and belongs with the smoke. Uncommitted; nothing in `data/`.

**Decision and exact source change:** Treat informing families through the
broadcast as the same intended act as contacting them. Do not add a bare verb
whose cross-product with the object group grants unrelated broadcasts. In
`knowledge.yaml`, only within `k_sl_3c_d_r2.action_evidence`, replace this
verb-group suffix (the rest of the group and the entire object group stay):

Old:
```yaml
reassure the families, respond to the families]
```
New:
```yaml
reassure the families, respond to the families, broadcast a message to the families, broadcast a response to the families, broadcast an update to the families]
```

This covers three communication forms, not six memorized transcript sentences.
The same defect in another story is an intended recipient-directed message
missing an authored paraphrase; review that story's evidence and negative
controls, without changing shared matching semantics. It does not cover every
possible grammatical variant. In particular, `broadcasting` is not stemmed to
`broadcast`, and `send word to` has no observed case here. Keep those limits
visible rather than expanding by guesswork.

**new — independently reproduced free evidence:** Real `_matches_all`, all
ten 3C reveals, current versus hypothetical bare versus scoped additions:

| Command | Current | Bare broadcast | Proposed scoped phrases |
| --- | --- | --- | --- |
| Broadcast the reports to the families. | D1 | D1 + D2 | D1 |
| Broadcast music to the families. | none | D2 (false positive) | none |
| Broadcast a message to the families about the released captives. | none | D2 | D2 |
| Read the detention site reports and broadcast a message to the families. | D1 | D1 + D2 | D1 + D2 |
| Listen for any response from the families. | none | none | none |

All six recorded `Broadcast ...` commands in pump 07/08/10 miss D2 now and
match it with the proposed phrases. Row 08 turn 12 also matches spent C2 in
the all-ten set: do not confuse that with live eligibility. At each of these
six turns D1 is already committed, so D2 is the remaining D candidate.
**corrected:** D1's current verb group has `broadcast the reports` and
`broadcast reports`, not bare `broadcast` as the prompt claims.

Before billing, extend the existing stateful tests, not only this static table:
all-ten overlap, both-D eligible, D1-spent/D2 eligible, D2-spent/D1 eligible,
neither eligible, C2-only, and both C orders. Call the real unique-selection
function; a genuine two-candidate exact match returns None, never two commits.
Check the hosted semantic-selection path too; a lexical table alone is not a
claim of a guarded commit. Confirm eligible single D2 selects only D2 and E
still requires both D steps. Keep #667, whole-word, possessive and negation
fixtures; add music-only and unrelated-recipient negative controls. Negated
strings belong only to deliberate matcher-safety tests, not player scripts.
Stop if the revised groups newly grant an unrelated action or break existing
unique D1 selection. Do not resolve ties by weakening uniqueness.

**Cheapest billed screen:** After those free checks, smoke n=1 per arm,
`pump` versus `families` (pump plus just the suffix above), synthetic `posta`,
A at turn 1, `Follow Rebecca.` at 2, raw continuation, semantic ON, deadline 14,
20 attempts. Freeze versions and caps; use the established 80 Cloudflare / 40
player smoke caps and fresh artifacts. Smoke win is valid provenance, isolated
payload diff, correct handling of any eligible family message, and no false
reveal; n=1 is not a rate. If the raw player never attempts the action, use the
free controlled case for mechanics; do not call the smoke an efficacy win.
Then go straight to Step 8 for the n=12 comparison, rather than buy another
synthetic rate. Expected files: a new variation JSON, `three_c_probe.py` and its
checker/tests for the arm, `tests/test_3c_cue_chain.py`, preregistration and
Ringer manifests. Only on adoption does the story's `knowledge.yaml` change.
No billed work is authorized by this planning update.

**Story-side alternative, not a second queued experiment:** Do not rewrite the
families cue to teach `tell` or `answer`: it already says families ask for word,
and the player gives them news. This is an action-recognition defect, not absent
material. A missing-result handoff is the earlier 3B office-entry technique;
Steps 3/4 already exercise it. Applying it to D2's statement cannot help a turn
that never earns D2. Keep the old broadcast/community replacement strings in C
as history, but do not resurrect either without its own recorded prompt cause.

### Step 8 — new: fresh carried-state scene acceptance before adoption

**RESULT — corrected (Round 6, latest):**
`bench/results/stage7-3c-carried-v2-n12/`, preregistration
`.plans/astra-3c-families-v2-prereg.md`: pump earned/deadline/none = 10/2/0,
families-v2 = 9/3/0. Both C by 10: 12/12 each; no rejections or clarifications.
Spend: 300/960 Cloudflare and 300/480 player requests. Pump passes the scene
bar; aliases fail. V2 earns at 11 in seven rows versus five for pump, but that
does not offset its failed rows or establish a relative benefit.

**DIAGNOSIS — new (Round 6):** V2 06 misses recipient-only broadcasts at 8
and 12; D1 is open at 8 and spent at 12. V2 10 misses prisoner *lists* at 9.
V2 12 misses its confirm-broadcast/give-word command at 9, earns D2 through
the existing answer-families alias at 12, then never tries the document.
Pump 02 also misses family broadcasts; pump 07 misses the names-to-families
command, recovers D2 at 12, then ignores E. Recognition is a demonstrated
remaining defect; extra time is not a demonstrated remedy.

**Semantic replay — new (Round 6):**
`bench/results/stage7-3c-semantic-replay/` and
`scripts/ringer/stage7/three_c_semantic_replay.py`: four missed commands
refused 12/12, exact control selected 3/3 without a judge call, music negative
refused 3/3; 15/40 Cloudflare calls, no player calls. Correct the earnwhen
preregistration's “messages refused 15/15”: three of those refusals are music.
D-R2's `earn_when: calls the families of the missing` is narrower than the
intended news-sharing act. This is a plausible source cause, not a measured
treatment effect. The semantic path's correct invocation does not prove that
the judge understands every intended paraphrase.

**Decision — corrected (Round 6):** Stop screening. Select pump for Step 9.
The run uses one authored canon-prefix history repeated across rows, not twelve
independent full games. Earlier pump 8/12 and latest 10/12 are separate runs;
one passing run is sufficient for this plan's operational staging choice, not
proof of repeatability or 80% quality. Read narration as well as commits:
latest pump row 01 turn 1 invents a study, drawers, a USB drive and a note while
the appended handoff still earns A. Zero rejected turns does not certify prose
or world consistency. Whole-game review must include these defects.
The rest of Step 8 retains the completed Round 5/6 protocols as history.

**corrected — harness COMPLETE:** `three_c_probe.py --start carried`, built in
Ringer run `stage7-3c-stuck-turns-20261020T013217Z-p970532`; dry artifacts at
`bench/results/stage7-3c-carried-dry/`. Each row replays the scripted 63-turn
1A–3B canon prefix on its own arm package, then crosses the real 3B→3C
transition. No checkpoint is loaded and no fingerprint is patched. `relay_open`
is committed at 3C entry. History is authored and shared, not a live-written
3B save. Prefix round-trip/crossing checks remain historical validation, not a
reason to rebuild it. The old preregistration still says draft/not approved;
the artifacts establish that its run occurred, not an approval audit.

**RESULT (2026-10-20), Step 8 carried n=12:** `bench/results/stage7-3c-carried-n12/`, 12 rows per arm, 302/960
Cloudflare and 302/480 player requests, no run-failure file. First smoke (`stage7-3c-carried-smoke/`) was invalid: the
probe's record-id diff failed because the engine trims `turn_records` to 24 and reuses ids (`engine.py:918-928`); fixed,
smoke2 clean. Earned endings: pump 8/12, families 9/12. **Both miss the 10/12 bar; the 1-row gap is not distinguishable.**
Every row earned A first attempt, B, C1 and C2 (both C by turn 10 in 24/24), 0 rejections, 0 clarifications, so the
opening/custody/pump stack works from carried state. The loss is now D2/E: D2 pump 9/12, families 11/12; E 8 vs 9;
deadline endings 4 vs 3. Several earned endings land on turn 14 (D2 at 12, E at 14). **corrected:** the initial checker failed with "carried row must not record scripted 3C reveals".
The corrected rule checks only `scripted_prefix`; n12 and smoke2 now both pass
the real checker, independently rerun during this review. The diagnosis is complete
and the revised Step 7 alias is the single next source change.

**DIAGNOSIS (2026-10-20), carried n=12:** `.plans/astra-3c-carried-diagnosis.md`; checker rule fixed (real n12 and smoke2
artifacts now pass). Primary causes of the 14 delayed rows: 7 matcher misses on clear family messages (pump 4, families 3:
`send the families a message ...`, `broadcast a message to the families of the missing`, `broadcast the prisoner records
and names to the families ...`), 1 no-attempt Br loop, 1 Site 3 detour, 1 turns-ran-out, 4 other (D2 before D1, van,
two compound E commands `Open the recovered document and trace ...` that tie E1/E2). **corrected:** the families arm already covers `broadcast a message to the families of the missing`;
those misses occurred in pump. Its gaps are `send`, roster broadcasts, and
`their families`. Suffix words do not defeat whole-phrase matching. Deadline 16 would plausibly change only 3 rows
(D2 at 14: families 2/5, pump 12), not recorded. Next-change candidate: a wider but still recipient-qualified D2 alias set
covering the observed send/broadcast forms, with the music/listening/danger negative controls. Free work first.

**corrected — diagnosis limits:** Seven of the 14 delayed rows have a primary
recognition miss; these are not seven failed endings. Pump 6 and families 1
already earned. Pump 2/7/11 and families 2/5 are the five failed rows exposed
to that repair. Pump 12 and families 8 are the other two failed endings.
The five non-matcher, non-E-tie delayed rows are pump 12 plus families
6/8/9/10; three of those five already earned. The 80% bar permits two failures
in 12, so do not queue a fix for every delayed but successful row.

**corrected — actual eligibility and tell:** The diagnosis's table often labels
both D candidates eligible although D1 was committed at turn 7. At the missed
message turns in pump 2/6/7/11 and families 1/5, D1 is already spent; families 2
still has both. The isolated post-C helper is not their recorded state.
`Tell the families that the captives are safe and the detention sites have been
exposed.` matches **both** D1 and D2, not neither: D1's `ask` expands to `tell`
through the existing synonym class, and `detention sites` satisfies its noun
group. The unique selector correctly refuses it. Adding another tell alias
cannot fix that tie. No matcher or D1 change is proposed.

**new — remaining movement and E decisions:** Accept these as residual costs
for this screen, not successes when they end by fallback. The Br loop, Site 3
detour, van and D2-first order do not establish a particular competing prompt
line to remove. A free prompt comparison could justify the proven 2C stale-recall
or 1A #668 subtraction later; no exact replacement is justified now. D2-first
is legal and families 9 eventually earns E. Compound E costs one turn in pump
10 and families 11, both earned at 12. Leave E1/E2 and uniqueness unchanged;
there is no demonstrated story-side fix worth another experiment. Accepting
one earned E alternative does not authorize composing two selected reveals.

**new — fresh screen specification and decision rule:** After revised Step 7
passes, freeze a new `families-v2` arm and fresh preregistration/manifests. The
next billed run is n=12 per arm, interleaved `pump` vs `families-v2`, start
`carried`, semantic ON, deadline 14, attempts 20, unchanged raw player. Use a
fresh result directory; cap 960 Cloudflare / 480 player requests (about 20
minutes; prior run used 302/302, not a guarantee). Reuse the validated prefix
procedure, not old 3C continuations. No extra billed smoke is needed for an
evidence-only arm after its free loader/selection/harness checks pass.
Files: new variation, existing probe/checker arm registration and focused tests,
fresh preregistration and one n12 Ringer manifest; no `data/` adoption yet.

Win is >=10/12 earned with no false reveals/new grounding failures. Report the
same A/B/C/D/E, rejection and deadline measures and read full responses. Relative
to 8/12 pump, two additional earned rows are needed; relative to 9/12 families,
one. Fresh rows are not paired counterfactual conversions. The 11/12 and 12/12
ceilings assume all exposed failures convert and all successes survive; they
are not forecasts. A one- or two-row gap remains inconclusive for improvement,
even if one arm passes the operational acceptance bar. If both pass within
that band, prefer pump. Passing does not prove 80% population success.

If revised aliases yield 9/12 again, declare failure and inspect the three
failed rows before another run. Do not add more aliases from those sentences
or pool runs. If at least one failed row has both D parts earned by turn 14,
E then eligible, no remaining recognition/guard failure, and the saved state
supports an E action within two turns, Step 6 becomes the next isolated screen
(same alias package, 14 vs 16, fresh n12 each). One additional success could
reach 10/12, but the counterfactual must be measured. If failures are still
recognition/ties or detours, deadline 16 is not supported; report the shortfall
and investigate one demonstrated source cause before specifying another edit.

**Historical Step 8 protocol, retained where still applicable:** The following
seed/smoke instructions describe the completed run; the fresh specification
above supersedes those completed acquisition and smoke tasks.

**Required:** A fresh full 3C run with actual 3B knowledge is needed before
entry, custody, pump or families is adopted. `posta` scripts A and the first B
action; it cannot test entry or the four Step 2 rows that never earn B. Synthetic
entry is also not carried state. Do not fix its guard errors by asserting every
3B reveal or silently changing old baselines.

Cheapest seed: find a compatible complete save immediately before a real 3B→3C
transition, with the actual committed reveal history, fact store, world parents
and player-visible transcript. Validate package/save compatibility. If no such
save exists, obtain one real sequential prefix through 3B and capture the
checkpoint; do not claim transcripts or asserted entry facts are a save. If a
source change invalidates a save, rebuild via the supported replay/load path
and verify the resulting state rather than patching a fingerprint. Enter 3C
through the real transition for each arm so its opening is actually rendered.
Freeze that common prefix; label reuse of one history as a limitation.

Run a carried-entry smoke n=1 each, then 12 fresh raw continuations per arm,
interleaved `pump` versus `families`, deadline 14, 20 attempts, semantic ON,
unchanged player prompt. Preserve the common prior transcript; no scripted A/B
or privileged knowledge. This compares only D2 evidence while testing the full
candidate stack under real entry conditions. Cap the main screen at the
established 960 Cloudflare / 480 player calls; preregister prefix acquisition
separately so it cannot consume an unbounded budget. Preserve partial results;
stop on transport/artifact failure, no replacement samples or pooling.

**Win:** >=10/12 earned endings, no false reveals or new grounding failures;
report pump baseline alongside it. A difference under three rows is not evidence
of an alias improvement. Also report first-attempt A, B reach, repeated case
commands, both C by 10, D1/D2/E turns, rejection provenance, and fair movement.
If both arms pass and differ by fewer than three rows, prefer pump without the
extra aliases; do not credit them with a completion win. This measures the
combined package, not the independent causal contribution of each old edit.
No claim of whole-game quality follows from one reused prefix.

Expected files: carried-start support in the existing probe, checker and tests,
a preregistration and Ringer manifests, immutable checkpoint/transcript artifacts;
no runtime or guard edits. Compare carried 3B knowledge and payloads with the
old starts to resolve the `relay open` question. Preserve the current ending
provenance definition below: story completion is the transition here; a missing
next scene or `transition_cause: none` is not failure by itself.

**corrected — historical movement audit:** The free read of synthetic pump
01/02/04/06 was completed before the carried screen. Full prompts were not
saved; replies/cues/parents showed movement contradictions and unanswered
appended cues in all four. That does not isolate a removable prompt line.
The original inspection specification follows as history: inspection of pump
01/02/04/06 was independent of alias tests and checkpoint discovery. Read their
full prompts beside plot 3C.3/3C.4, parents and cue stages; if prompts were not
saved, capture them from a reproducible state before asserting a cause. Row 01
also enters an invented building/console thread; it is not just tunnel travel.
Rows 04/06 already earn D1, so another reports hint is not the demonstrated need.
The cheap remaining lever is a *specific competing reusable line* removed or
scoped after its job is complete (2C stale-recall and 1A #668 precedent). It is
not another blind surface binding, C1 escape statement or generic cue rewrite.
No such new line has been established by the command-only check here, so there
is no justified replacement string or billed movement arm yet.

Accept one traversal as fair movement; do not accept repeated fictitious escape
as scene success. With C done at 5, nine accepted turns remain for three D/E
commits; the observed earners finish at 11. A 14-turn deadline is currently
adequate for that chain. If Step 8 misses 10/12, identify the dominant remaining
failure from its saved prompts and preregister **one** supported source change,
with a separate frozen baseline and >=10/12 fresh-entry earned win. Do not
schedule guessed wording or deadline 16 now. Alias free checks and carried-seed
preparation are independent; the smoke depends on alias checks; the carried
comparison depends on a valid seed and harness smoke; adoption depends on its
bar. This is the shortest supported path, not a guarantee of reaching 80%.

### Earned-ending bar and stopping rule — confirmed

Earned means `story_complete` through an eligible E after A/B/both C/both D,
with **no deadline event supplying a missing link**. E1/E2 are alternatives.
Use `deadline_event_ids`, committed reveal IDs, fact deltas and fired events;
never completion prose or `transition_cause: none` alone. At-deadline completion
is earned only if the full chain was player-earned and no fallback supplied it.
Unknown provenance is unknown, not earned. >=80% means **at least 10/12**.

Keep deadline, rejection, cap, no-completion and fair movement counts separate.
A component may justify a correctness repair without passing the scene quality
bar; say which claim passed. Stop adding fixes once fresh entry meets the bar.
After adoption, use the production-promotion guide's SHA-bound main CI/staging
flow and the bounded quality review in Step 12. **Corrected (Round 7):** the
three-run requirement is withdrawn. Small samples are regression evidence, not
an 80% estimate. An earlier-scene blocker remains a whole-game limitation.

### Step 9 — corrected: pump adoption and free gates complete

**corrected — final outcome (Round 7):** PR #674 merged the frozen fixture and
independent adoption pins. Final full suite: 2499 passed, 1 skipped, 92.71%
coverage; Ruff, frontend tests and build green. The first CI attempt failed
because three tests depended on ignored recordings. Only the required
`stage7-3c-matcher-table`, `stage7-3c-prefix`, and `stage7-3c-carried-dry` inputs
were force-added under `bench/results/`; second CI passed. The earlier partial
result below is history, not a request to rerun completed gates.

**Historical adoption work:**
The uncommitted package diff changes exactly `plot.md:831` (3C entry) and
`knowledge.yaml:2513` (B-R1 delivery) under
`data/stories/continuity-initiative/`, to the measured strings in Steps 2–4.
D2 evidence and earn_when are unchanged. Keep this candidate; do not reapply
the now-idempotent variation or undo unrelated work.

**Review finding:** The re-pins in
`bench/variations/stage7-3c-{pump-need,families,families-v2}.json` make both
entry and delivery replacements `old == new`. Ringer's
`scripts/ringer/stage7/3c-adopt-pump.json` check requires old strings to be absent,
so it necessarily fails. This is not proof of an incorrect story edit.
However, `tests/test_3c_adopted_package.py` now explicitly requires these
identities; it depends on a mutable variation rather than an independent
measured baseline. Passing that assertion alone is insufficient.

Prefer preserving screen-era variations at `8749e518` and applying them to an
explicit frozen pre-adoption package fixture for historical tests. Do not
silently make shipped pump the old control. Review and update affected fixtures
in `tests/test_3c_{entry_package,custody_result,pump_need,carried_start}.py`,
the other 3C variation tests and `scripts/ringer/stage7/test_three_c_probe.py`.
Any current-package diagnostic arm should be separately named. Compare the
complete resulting package with the measured pump package, recording hashes.
Make the adoption test and Ringer check independently pin that target, unchanged
D2 fields, successful loading, and B not granting either C fact. Replace the
failed assertion with this comparison; do not merely delete it to turn green.

Run affected 3C tests, prefix tests and harness tests together first; account for
the recorded standalone import-path issue. Then run the focused package,
projection, safety, matcher, pacing, canon, disclosure and resolution tests
listed in `3c-adopt-pump.json`. Regenerate `.plans/disclosure-matrix.{json,md}`
using `uv run python scripts/disclosure_matrix.py --out-dir .plans` and inspect
the diff; worker-reported zero changes are not a substitute for this review.
Capture stubbed payloads: 1A unchanged, 3C entry/post-B changed only as intended.

Finish with runbook section 1: `TMPDIR=/tmp uv run pytest -q --cov` (90%),
`uv run ruff check .`, `uv run ruff format --check .`, frontend Node tests,
`npm test` and `npm run build`. Record actual failures; do not treat the worker's
853 focused tests as a full gate. Cost: zero model calls, local test/build time.
Win: reproducible historical arms, measured pump shipped, all required gates
pass, generated artifacts reviewed. No billed rerun is needed for adoption.

**Step 9 result (2026-10-20, uncommitted, no model calls):**
- `tests/fixtures/continuity_initiative_pre_3c_adoption/` is a frozen copy of the
  package at `8749e518`. Its README lives outside the dir at
  `tests/fixtures/continuity_initiative_pre_3c_adoption.README.txt`: a file inside
  changes the package hash and breaks the recorded-artifact checks.
- The five screen-era variations (`entry-package`, `custody-result`, `pump-need`,
  `families`, `families-v2`) keep their original old/new strings and point at the
  fixture. `three_c_probe.py` and the entry/custody tests use an explicit
  `pre-adoption` control, not the shipped data dir.
- `tests/test_3c_adopted_package.py` pins the two shipped strings and shipped file
  sha256 values, reproduces them from fixture + pump variation, and requires every
  other file to match the fixture. `3c-adopt-pump.json` now runs that test.
- Fixed pre-existing branch faults: `pyproject.toml` `pythonpath` for
  `scripts/ringer/stage7` (3C tests failed to import `door_transport`); a
  `test_three_c_prefix.py` test that tampered the shared checkpoint (now a copy);
  lint in `three_c_semantic_replay.py`.
- Gates: ruff check/format clean; frontend `npm test` 155/155 and `npm run build`
  pass; disclosure matrix regenerated with no diff. Full `pytest --cov` last ran
  2498 passed, 1 skipped, 92.71%, with one prefix-test failure that the test fix
  above addresses; that file passes alone (4 passed) but the full suite has not been
  rerun since. Rerun it before the PR.
- Ringer run `adopt-gates-fixture` FAILED its check on lint outside its ownership;
  the worker also reformatted `2b_cue_probe.py` (out of scope; review before commit).

### Step 10 — corrected: PR, main, and SHA-bound staging complete

**corrected — outcome (Round 7):** #674 merged at
`f918c663d67d368645f9a24a47a28ffb29fb77d8`; branch deleted. Supplied workflow
results include Deploy staging, scene staging evaluation and Record staging
deployment. Saved API identity is `scene-v1`, `staging`, exact SHA; supplied
Pages `/dev/deployment.json` matches. Do not repeat this merge/deploy for the
plan edit. The following is the completed procedure, retained for a later
measured package change.

Review `8749e518` plus Step 9's adoption/test diff on
`3c-stuck-turns-screens`; exclude unrelated untracked door-grounded, blind and
astra work. Commit reviewed changes and the plan, push, open/review the PR,
and pass required CI. Describe latest 10/12, prior 8/12, failed aliases and
remaining prose/recognition risks. Merge to `main`, then wait for that merge
SHA's staging workflow. Do not deploy the branch directly.

Existing files: `.github/workflows/test.yml`,
`.github/workflows/deploy-frontend-pages.yml` and
`docs/railway-production-promotion.md`; no workflow change is proposed.
Require successful `staging-deployment`, matching Pages `/dev/`
`deployment.json`, and `/api/v1/version` reporting the exact SHA,
`runtime: scene-v1`, `channel: staging`. The workflow's scene evaluation runs
`tests/test_web_demo.py tests/test_cloudflare_transport.py`; it is not the
raw-player quality review. Git/PR actions cost no model calls;
CI/build/hosting cost infrastructure time and hosted checks can spend narration
calls. No fixed dollar cost has been measured.

### Step 11 — corrected: one staged whole-game regression run completed

**Result (2026-10-20):** Ringer `stage7-3c-staging-smoke`, artifacts
`bench/results/stage7-3c-staging-smoke/`: passed first attempt, two turns.
Its Ringer FAIL was the drift check counting eight pre-existing untracked plan
files, not observed worker drift. No call count was exposed. The separate raw
run used `scripts/ringer/stage7/3c-blind-raw-replicate-1.json`; report, prompts,
bundles and identity are in `bench/results/stage7-3c-blind-raw-f918c663/attempt-1/`.
It took 9.8 minutes and 79 turns. Its Ringer FAIL was missing `smoke-result.txt`,
not a failed browser execution. These checker issues do not erase the quality
failure recorded inside the otherwise passing browser test.

| Scene | Turns | No-reveal turns | Exit | Rejections / game breaks |
| --- | ---: | ---: | --- | --- |
| 1A | 8 | 5 | earned | 0 / 0 |
| 1B | 8 | 0 | earned | 0 / 0 |
| 1C | 7 | 1 | earned | 0 / 0 |
| 2A | 8 | 4 | earned | 0 / 0 |
| 2B | 8 | 5 | earned | 0 / 0 |
| 2C | 8 | 4 | earned | 0 / 0 |
| 3A | 9 | 0 | earned | 0 / 0 |
| 3B | 9 | 3 | earned | 0 / 0 |
| 3C | 14 | 9 | deadline ending | 0 / 0 |

3C earns A/B/C1/C2 on 1/2/3/5, never D1/D2/E. Turn 14's committed delta
supplies resolution facts, including both D results and the Phase Two result,
without a selected reveal. Together with the turn-14 deadline this establishes
fallback; `transition_cause: none` by itself would not. Replicates 2/3 were
cancelled as a gate. No “passes/misses 80%” statement is warranted from this run.

**Corrected diagnosis from the raw recording:**

- Turn 4 follows Michelle through the tunnel. It earns nothing; its bundle
  records semantic refusal. Turn 6's THINGS places Kristin, Michelle and the
  captives in the maintenance network. Movement is real progress even when
  the harness counts no reveal, so turn 4 alone is not a defect.
- Turns 6–10 say “Lead … through the surface gates”; 11–13 say “Watch … reach
  safety/emerge safely”. Turn 9 narration reaches Los Angeles, then turn 10
  returns to tunnel travel; turn 11 waits for the gate signal again. That
  repeated completion/reset is a concrete quality defect, not eight identical
  commands or proof of one source cause. Preserve raw commands as evidence,
  including the noncanonical final “Wait” command; do not use it as a new probe.
- The C1 and C2 statements recur in both SCENE and permitted NPC speech.
  SCENE also says “Expose the network and escape” and “Exposure and escape are
  both immediate under the collapsing operation.” These are competing pulls,
  not evidence that C1 alone causes the loop.
- D cues appear at 6/7 and again at 11/12. Turn 6's bundle reports
  `semantic_refusal`, universe/shortlist 2/2. The final narrator prompt offers
  no candidates after that refusal. This is not evidence that D is ineligible
  because Kristin left the chamber. D's authored requirements are truth plus
  `captives_reaching_surface`, not a chamber-parent requirement. Location may
  affect what the player pursues and what THINGS renders; it is not the
  demonstrated D eligibility blocker. No family-news command needs an alias here.

**New — history comparison without another whole-game bill:** The carried
harness replays authored 1A–3B output separately on each package, then starts a
raw player in 3C. It is one scripted history across rows. Live prior turns can
leave different custody/parents and a different player transcript; the narrator
receives projected facts rather than that transcript. Compare those two inputs
separately. The supplied scratch reconstruction after A/B/C1/C2 leaves Kristin
and Michelle in the chamber, unlike the hosted turn-4 detour. With surface
binding it moves only captives; SCENE is identical. That reconstruction is not
an exact restoration of the hosted turn-6 state and did not render THINGS.
It rules out a statement change from that binding, not a behavioral benefit.

Free next comparison: record parents, held case, committed facts, cue history,
turn index, D eligibility, full rendered prompt and player-visible transcript
at 3C entry and before turn 6 for both histories. Use the real matcher on the
recorded command and on `Check the reports from other detention sites.` and
`Answer the families' requests with the confirmed news of the liberated captives.`
as diagnostic positive controls. They are not instructions to the blind player.
Use an isolated reconstructed fact state through existing runtime APIs; do not
patch save fingerprints or represent the bundle's partial state as a full save.
A second offline counterfactual may change only Kristin's parent through the
world API and record exactly what projection changes. Label it synthetic and
do not transplant that placement into the package. Free comparison can prove
input/eligibility differences; it cannot prove what a model would do.

**Earlier scenes:** They matter to whole-game quality and deserve a read of
already-paid narration, but the report supports no earlier progression blocker
in this journey. No-reveal counts include movement and even earned exit turns
(1A turn 8, 2B turn 8). Do not open four repair projects from those counts or
claim the earlier scenes are polished. Record specific repetitions, contradictions
or misleading transitions in a quality review; only a demonstrated serious
failure changes this plan's priority. 3C is the observed earned-ending blocker.

### Step 11a — new: one bounded changed-context C1 screen, then continuation

**Order:** free comparison above, frozen-prompt screen, conditional continuation,
then package gates and one new staged journey. No C1+C2 bundle. This revisits
Step 5 only because there is now an exact failing hosted prompt after adopted
pump/custody and a real detour. Its prior loss is evidence against adoption.

1. **Free preparation.** Write `.plans/astra-3c-recall-live-prereg.md` and a
   separate `bench/variations/stage7-3c-recall-live.json` targeting shipped pump,
   using exactly section B's old/new C1 statement. Do not repurpose historical
   variations or fixtures. Proposed harness/manifest:
   `scripts/ringer/stage7/three_c_recall_replay.py` and
   `scripts/ringer/stage7/3c-recall-live-screen.json`; outputs
   `bench/results/stage7-3c-recall-live-screen/`. Test in
   `tests/test_3c_recall_live.py`: source replacement once, all repeated C1
   projections changed (including NPC speech), C2/delivery/effects/evidence
   unchanged, C1-only has no surface assertion, both C orders preserve D
   eligibility. Frozen prompt must otherwise be byte-identical. Stop if this
   isolation cannot be shown; do not pay to test a malformed reconstruction.
2. **Cheapest useful billed screen.** Replay recorded turn 6, same command,
   same THINGS, two interleaved arms: shipped pump versus C1-scoped pump,
   12 replies each. One normal request plus at most one recovery: hard cap
   **48 Cloudflare requests, zero player calls**; stop on budget response,
   preserve partial rows, no replacements. No semantic judge call is needed
   for this frozen no-candidate prompt. Read every reply by hand: does the
   requested passage finish, do people stay consistent with that action, does
   it reset pumps/gates or invent a new obstacle? Score prose, not just proposed
   item facts; never keyword-gate adoption. Candidate must finish coherently in
   at least 10/12 and exceed control by at least three replies, with no new
   story-breaking error. This is a triage rule, not statistical significance
   or a completion-rate estimate. Failure/tie stops C1, retaining Step 5's loss.
3. **Only after a screen win:** test whether changed replies actually change
   player behavior. Build a labelled reconstruction through turn 5 from the
   recorded facts, placements, cue state and player screen; same seed in both
   arms, no injected D command. If exact restoration is impossible, enumerate
   missing fields and call the seed synthetic. Use 12 fresh raw continuations
   per arm with semantic fallback ON, deadline 14 unchanged, maximum 12
   attempts per row (nine accepted turns remain). Extend `three_c_probe.py`
   and `check_three_c_probe.py` with an explicit start mode and tests in
   `scripts/ringer/stage7/test_three_c_probe.py`; do not silently redefine
   `carried`. Separate manifest `3c-recall-live-continuation.json`, output
   `bench/results/stage7-3c-recall-live-continuation/`. Hard total caps:
   **576 Cloudflare / 288 player calls**, including matching/recovery calls;
   the Cloudflare cap may stop a run before the attempt cap. Free dry run first.
   Operational win: candidate >=10/12 earned E, at least three more earned
   endings than control, no new serious prose/guard defect. Also report D1/D2/E
   timing, repeated travel, deadline/unknown/cap outcomes and all failures.
   No pooling with Step 5 or carried runs. This seed-specific screen cannot
   establish a whole-game rate. A carried n12 (960/480 two-arm caps) is the
   existing cheaper-to-build fallback, but tests a different history; do not
   buy both or substitute it silently for this continuation.
4. **Miss reading:** a prompt miss means no demonstrated C1 benefit in the
   failing context. A prompt win followed by continuation loss means better
   immediate prose did not solve player progression. Neither licenses adoption,
   a longer deadline, or more aliases. Read the surviving prompt for a specific
   remaining pull. C2 can be a separately preregistered subtraction only if
   that read implicates its repeated completed action; exact wording and
   controls must be reviewed then. If player commands reach D but recognition
   now fails, reopen Step 12's conditional earn_when investigation instead.
   Do not schedule a succession of speculative screens in advance.
5. **Win to staged playthrough:** adopt only C1's measured statement in
   `data/stories/continuity-initiative/knowledge.yaml`. Preserve the pump-only
   adoption evidence; update `tests/test_3c_adopted_package.py` so its existing
   all-other-files/hash assertion distinguishes the new reviewed delta rather
   than blessing arbitrary package drift. Run recall/harness tests plus
   `test_3c_cue_chain`, `test_resolution_cascade`, `test_knowledge_projection`,
   `test_markdown_story_package`, safety/leak and disclosure tests; regenerate
   disclosure matrix and inspect. Capture unchanged 1A and isolated 3C payloads.
   Finish runbook full coverage, Ruff and frontend gates (zero model calls).
   PR/main/SHA-bound staging as Step 10, then one new raw whole-game regression
   journey as Step 12. Only the new implementation needs these gates; the
   already-staged pump and this plan edit do not.

#### Step 11a free comparison result (2026-10-20)

Offline, zero model calls. `scripts/ringer/stage7/three_c_state_compare.py`, report in
`bench/results/stage7-3c-state-compare/report.{md,json}`, tests in
`tests/test_3c_state_compare.py`. LIVE is the hosted run; SCRIPTED is the carried 3C
entry state plus A-R1, B-R1, C1, C2 committed through the runtime API (synthetic: same
four reveals, not the live transcript). A first version built the scripted side on a bare
test state and was wrong; it was rebuilt and now asserts that the earlier-scene facts,
`relay_open`, parents, and Michelle/captive THINGS lines exist.

- **SCENE is byte-identical** in the two turn-6 prompts. The repeated C1, C2, A-R1 and
  pressure lines are the same in both histories.
- **D eligibility and the matcher are identical.** Both D reveals are eligible in the
  scripted state. The recorded command `Lead Michelle and the captives through the open
  surface gates to safety.` matches neither D reveal there either; the two diagnostic
  controls match D-R1 and D-R2. The live bundle recorded a semantic refusal (universe and
  shortlist 2/2). So the stuck turn is not a state/eligibility difference; it is the
  command not performing either D act.
- **The only prompt differences are places.** Live THINGS puts Kristin and Michelle in the
  maintenance network and lists `emergency surface gates` at Los Angeles surface; scripted
  puts both in the broadcast chamber and has no gates line. The captives are in the
  maintenance network in both. This is the turn-4 follow-Michelle detour, which the
  scripted prefix does not contain.
- **Synthetic Kristin-only move** (world.move to the maintenance network) changes THINGS
  and PLAYER only; SCENE and D eligibility are unchanged.
- **Facts:** LIVE 97 predicates (partial telemetry), SCRIPTED 90. Live-only 8 across
  3 families (four `wk_*` world-knowledge facts and others); scripted-only 1
  (`rebecca_experiment_approval_confronted`). Not read as a cause.
- **Open item:** the CONSTRAINTS diff lists three system-rule inserts on the scripted side,
  most likely a section-parsing artifact of the offline renderer; unverified.
- Cannot show: what a model does with either prompt, or any rate.

Reading: the history difference is location only, and it was already a plausible
explanation for the loop (people already in the tunnel, gates already open on the
surface). Two prompt screens with that location held fixed found no statement-scoping win.
No C1/A-R1 retest is warranted from this.

### Step 12 — new: production decision and conditional source work

**Corrected (Round 7) — recommendation and evidence:** Hold promotion of pump
as the completed quality repair: the only live-history journey exposes a real
loop and misses the earned D/E chain. The release workflow requires a successful
staged SHA and review; its guide does not mandate three raw journeys. The earlier
three-run rule was this plan's recommendation and is withdrawn. One subsequent
earned whole-game journey, reviewed narration, free regression gates and exact
staging identity can support a cautious promotion decision with explicit residual
risk. They cannot establish reliability, 80% completion, or absence of rare bugs.
A known serious quality failure must be fixed or explicitly accepted in that
decision; do not hide it behind a passing browser test or select the best run.

| Option | Incremental work/cost | What the decision may say |
| --- | --- | --- |
| Hold now (recommended) | Free artifact comparison/review, then only conditional Step 11a spend | Pump is staged; quality repair remains incomplete. |
| Promote existing pump with the known limitation | No new quality sample; production build/hosted smoke still costs time and model usage | Explicit acceptance of the observed loop; not successful remediation. |
| Test measured repair then decide (recommended path) | Step 11a caps, free gates, new staging deploy/smoke, one raw whole-game run | Observed earned journey and reviewed quality at the recorded SHA, with sample limits. |
| Extra whole-game regression journeys | Up to 200 player calls per session; hosted calls additional | Additional history coverage only; 1–3 runs do not establish a rate. Not required or queued. |

For the new single journey, reuse the verified manifest pattern in
`scripts/ringer/stage7/3c-blind-raw-replicate-1.json`, archive a fresh output
under `bench/results/stage7-3c-blind-raw-<new-sha>/`, and use
`E2E_BLIND_SCENE=all BLIND_PLAYER_PROFILE=raw E2E_BLIND_REPLICATES=1`.
Keep the existing 20-player-call scene / 200-call session limits and
`E2E_TURN_TIMEOUT_MS=90000`; record any cap stop. Review all narration and
handoffs, earned/fallback provenance, false reveals, movement/custody and earlier
scene issues. No replacement quality samples. A failure returns to its specific
recorded cause, not an automatic repeat. An earlier-scene failure can leave 3C
untested; a fallback ending is never an earned success.

**Dollar budget — corrected:** Hosted calls have no single exposed call counter.
`worker/src/index.js` reserves spend against `DAILY_BUDGET_USD` for both narrator
and Jev paths. The default is **$5 per UTC day shared by all staging traffic**,
not $5 for each test, run or arm; actual dashboard configuration may differ.
Before billed work record dashboard daily cap and current dollar usage with UTC
time; record usage after, separating concurrent traffic when possible. Stop on
429 `AI_DAILY_BUDGET_EXCEEDED`; do not raise the cap or retry around it. Include
CI/smoke and all other staging traffic in remaining headroom. Player-model
spend is separate and must also be recorded. Probe request caps above remain
useful bounds, not dollar prices or guarantees of finishing. No remaining
balance or actual spend is inferable from 79 turns/9.8 minutes. Dashboard dollars
were not read in this plan review; do not invent them or use the canon-neuron
estimate. No new endpoint is needed just for this plan.

After the review decision, promote only the exact successful staged SHA through
`.github/workflows/promote-production.yml` and the promotion guide; production
identity and hosted E2E remain required. This plan does not dispatch promotion.
A later documentation-only results edit needs no repeat deploy/E2E.

**Conditional D2 source candidate, still dropped:** Reopen
`.plans/astra-3c-earnwhen-prereg.md` only if the smoke shows eligible family-news
misses preventing quality completion. The exact isolated candidate is:

```yaml
# old
earn_when: calls the families of the missing
# candidate only
earn_when: calls, messages, or broadcasts news to the families of the missing
```

Otherwise leave it dropped. This follows the principle of correcting missing
authored material (3B handoff precedent), but there is no measured precedent
for an earn_when repair itself. Do not claim the analogy proves efficacy.
Do not change judge criteria/calibration. `cloudflare.py:570`, `:1043`, `:1526`
show effects on semantic input, example selection and narrator constraints;
capture all affected payloads before testing. Ties, eligibility, prose drift
and ignored E require their own diagnosis, not this sentence.

If reopened, first run the preregistered controlled semantic gate: four missed
commands, exact control, music/danger/wrong-recipient/report-overlap negatives,
three runs each, both D1 states where relevant. Cap 40 Cloudflare calls, zero
player calls; positives >=2/3, negatives refused 3/3, exact control bypassing
the judge. Preserve refusal of genuine two-candidate ties. Failure stops this
proposal. Passing proves mechanics only; only then consider fresh carried
pump-versus-earnwhen n12 (960/480 caps), followed by adoption/staging gates if
it wins. This branch is not in the active queue.

## Tests and generated artifacts

**confirmed:** Keep the new stateful #667 tests, both C/D orders, D2-alone not
ending, D1 supplying the canonical Charles gate, and E without deadline IDs.
Keep genuine all-ten ambiguity and whole-word/possessive/negation controls.
No matcher implementation edits or goldens that make every raw command succeed.

**new, when implementing each measured fix:**

- Binding: `tests/test_resolution_cascade.py` and
  `tests/test_late_scene_repro.py`: post-both-C and deadline parents, C2-only
  nonmovement, save/load, populated group membership, no move of unrelated
  people. Entry placement stays maintenance_network. Add a synthetic second
  package to cover generic fact-to-parent semantics if new coverage is needed;
  do not imply this story requires a shared-runtime change.
- Entry/custody/pumps: `tests/test_3c_cue_chain.py`, package loading and knowledge
  projection. Test semantic boundaries (B does not grant C; already-held case
  stays held under a no-move provider), not just a sentence's presence. First
  player-screen capture must show the varied entry. Live behavior remains live.
- Deadline: `tests/test_scene_relative_pacing.py`, `tests/test_pacing_handoff.py`,
  `tests/test_resolution_cascade.py`, `tests/test_story_ending.py`, and harness
  `scripts/ringer/stage7/test_three_c_probe.py`: 14 vs 16 provenance, the staged
  12/13/14/15 chain, fallback retained, and stop condition uses arm deadline.
  Revise 3C deadline-dependent fixtures only; do not loosen earlier scenes.
- `tests/test_disclosure_matrix.py` and `.plans/disclosure-matrix.{json,md}`:
  regenerate with `scripts/disclosure_matrix.py --out-dir ...` after an adopted
  package edit. Inspect whether changed statements alter generated content.
  No proposed edit adds leak terms/aliases; do not hand-edit projections or
  expect broad earlier-scene disclosure changes.
- Preserve `tests/test_leak_terms.py`, `tests/test_narration_safety.py`,
  `tests/test_shared_knowledge_guards.py`, `tests/test_markdown_story_package.py`,
  `tests/test_knowledge_projection.py`, and `tests/test_canon_journey.py`.
  Do not rewrite canon commands as a player-facing repair.
- Capture shipped payloads before/after with network stubbed. Baseline 1A
  capture must remain unchanged; inspect 3C separately at entry, after B,
  after C1 only, C2 only, both C, and D2-first. Binding should change parents
  only after the assertion; statements should change only earned recall.

**confirmed:** Follow `docs/testing-runbook.md` for focused checks and the full
required implementation gates. This planning change does not run deploy/E2E or
regenerate package artifacts. Future repeatable harness changes belong in the
existing runbook entry; measured results belong in this plan and the prereg.

## Risks, limits and resume point

**corrected (Round 4):** Custody reduced re-takes and pump improved C completion,
but neither raised earned completion. The measured record supersedes “#667 untested live,”
“binding untested offline” and “binding not measured live.” Both escape edits
lost on these starts; entry's opening gain did not improve completion. The
fresh-start bar was still missed in that round. **corrected (Round 6):** pump
now meets 10/12 in one carried screen; no alias has demonstrated improvement.

**new:** Risks generalize to any story whose completed transfer/evacuation is
still narrated as pending: bind physical facts, state earned results clearly,
and scope recurring material. These repairs do not resolve arbitrary language
ambiguity or missing carried history. Entry material can bias players too much;
review it as fiction, not a checklist. A new noun alias paired with a broad verb
list can grant an outcome for an unrelated action in any story; the negative
controls here demonstrate why evidence expansion is not automatically safe.

**confirmed:** 3A/3B risk is mainly shared parent effects, group members,
placements and visibility. Do not move the group early or pull Brandon from the
relay. Earlier-scene names/guards and entry text remain unchanged. Longer 3C
pacing affects whole-story time and costs, not earlier scene windows. Check
payloads and real journey regressions after adoption.

**Not verified — corrected (Round 7):**

- C1 is tested historically and lost; its effect on the exact hosted failing
  prompt is unmeasured. C2, scene-pressure lines, player history and location
  remain alternative explanations; one prompt establishes no sole cause.
- Surface binding's supplied scratch comparison is not an exact hosted-state
  replay. Full state restoration and isolated parent counterfactuals remain.
- Pump adoption/gates/merge/staging/smoke are complete. Latest carried 10/12
  does not establish repeatability or an 80% population rate. One live-history
  journey is now observed, with no earned D/E; quality success remains unverified.
- Earlier scenes earned their exits in this run. Their no-reveal counts alone
  neither establish defects nor certify prose quality; the detailed quality
  review remains. Custody's historical hand score remains absent, and the
  incomplete pump n10 must not be topped up or pooled with carried rows.
- No billed screen, new test suite, dashboard read, remote CI recheck or
  production promotion ran in this review. Dollar spend/remaining daily
  headroom are unknown; the default cap is not the available balance.
- Wider earn_when and deadline 16 remain unmeasured and unqueued. No family
  communication attempt in this run justifies either. Historical unrecorded
  rejection prose and unobserved turn-15/16 continuations remain unavailable.

**Resume here — Step 11a result (2026-10-20):** screen missed; no continuation, adoption or
staged journey follows. Open choices for Brandon: (a) [DONE: free state comparison, see its result block],
(b) [RAN 2026-10-20, MISSED: A-R1 scoped finished 5/12 vs shipped 7/12, no broadcast
drift in either arm; see `.plans/astra-3c-broadcast-live-prereg.md`; stopped], (c) hold/accept pump per Step 12. Nothing queued.

**Resume here — corrected (Round 7, superseded above):** Steps 9/10 and one Step 11 run are done.
Do Step 11a's free live-versus-scripted input comparison, then the single capped
C1 prompt retest if isolation holds. Carry forward the prior loss. Only a win
justifies the continuation screen, implementation gates and one new staged
whole-game regression journey. Step 12 defines the honest production decision.
Do not rerun completed gates, require three journeys, rebuild the old prefix,
top up old samples, bundle C2, revive aliases or extend the deadline by default.
This update is a written plan only; its proposed implementation and billed
measurements have not been executed.
