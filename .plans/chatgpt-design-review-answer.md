# Diagnosis

Reviewed checkout `45a35cc3`, on 2026-10-11. This is a design review, not an implementation.

The core fact model is worth keeping. The expensive parts are the contracts around it.
Names double as secrets. Reveal actions have several competing descriptions. Recovery stops after one cue.
The tests then measure a narrower player and a more generous state than real play.
These are six ranked findings below. Confidence distinguishes source facts from predicted gains.

The brief needs three corrections. Scoped item aliases already exist. The corpus test already exists. Timer costs already exist in three places. Those fixes are incomplete, not absent. See [scoped resolution](/home/bcorfman/dev/freytag-forge/storygame/runtime/item_facts.py:684), [corpus state](/home/bcorfman/dev/freytag-forge/tests/test_narration_corpus.py:29), and [timer-cost follow-up](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1281).

I read the source and the recorded design/probe accounts. I did not rerun the suite, spend on live calls, or independently rescore the saved live replies. Reported live counts below are historical evidence, not newly reproduced results. I did not audit every exception or persistence path. I assume freeform play and the two-hour target remain product goals.

## 1. Name resolution and secrecy share a vocabulary

**Confidence: high in the diagnosis; medium in the proposed migration. Structural change, with an incremental compatibility path.**

**Evidence.** The loader indexes names and aliases for every location, NPC and item. The safety scan rejects those phrases when none of their owners is nameable, unless an authored-text or grounding exemption applies. This makes a world declaration change the language accepted elsewhere. The same loader derives protected phrases from identifiers, including the first word of a multiword identifier. Thus `phase_two` can guard ordinary `phase`. These are distinct paths; `leak_terms` fixes neither entity names nor this protected-term expansion. See [index compilation](/home/bcorfman/dev/freytag-forge/storygame/story_package/loader.py:321), [entity scan](/home/bcorfman/dev/freytag-forge/storygame/runtime/narration_safety.py:188), and [protected declarations](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/world.yaml:392).

Scoped aliases are a useful existing remedy for common words. They do not remove the canonical-name guard. They also have uneven consumers: the resolver handles items and groups, while recall uses ordinary surface forms. The base schema accepts the field on other entity types too. See [Entity](/home/bcorfman/dev/freytag-forge/storygame/story_package/models.py:160), [resolver](/home/bcorfman/dev/freytag-forge/storygame/runtime/item_facts.py:684), and [recall](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:58).

**Cost.** False rejections and unsafe authoring incentives. The recorded copied-files comparison found new rejections even for a declaration with no aliases. The chosen workaround was to leave a carried object undeclared, accepting custody risk. That is the wrong trade for a fact-owned world. See [2C declaration decision](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1334).

**Redesign.** Separate three questions: what a name resolves to, what the player may know, and what is physically present. Keep scoped resolution. Introduce explicit disclosure guards with `terms`, an audience, and an unlock fact or knowledge ID. Ordinary names need no disclosure guard. Hidden objects and secret identities do. Mentioning a known remote room must not imply moving there.

Use **globally enforced, fact-gated secrets**, not global guards inferred from every noun. Do not stop guarding a secret merely because its introductory scene has passed: the player may have missed it. Scene scope may restrict a local alias; it must not replace knowledge state. This is the smallest model that removes the declaration trap while preserving early-leak checks. It does not prove that arbitrary paraphrases cannot leak; lexical scanning cannot provide that guarantee today either.

**Migration.** Preserve the legacy compiler for unreviewed records. Review the shipped story's guards in batches. Mark ordinary terms public, and give genuine secrets explicit unlock conditions. Retain `leak_terms`, hidden placement and `named_by`. Remove identifier-derived fragments only after explicit replacements cover their secrets. New declarations under the new schema must choose a disclosure policy. Never silently make every existing name public.

This changes the concepts in `loader._compile_knowledge_indexes` and the three safety loops. It does not require replacing worldkeeper. More scene exemptions cannot finish this job: they retain the premise that every name is secret.

**Estimated cost:** three worker tasks for schema/compiler, scan migration, and consumer consistency; one author review round for the shipped guard list. **Losing risk:** an omitted secret becomes public during migration.

**Cheapest offline check:** a before/after matrix at early, earned and skipped-reveal states in all nine scenes. Include ordinary narration and deliberately premature disclosures. Assert that adding a public object leaves unrelated verdicts unchanged. Include resolution and recall, not just scanning. **Smallest live check:** three linked 2B→2C runs, including a Michelle-first start; inspect rejection, naming, custody and premature disclosure. This is a smoke check, not a secrecy proof.

## 2. Recovery is keyed to having shown a cue, not to unresolved progress

**Confidence: high that the gap exists; medium that repetition improves play. Incremental first.**

**Evidence.** `delivered_cue_ids` excludes a cue after delivery. Eligibility is rechecked, but an ignored cue has no new stage. `nudge_after_turns` is validated by the schema and absent from the scheduling code. At the deadline, `_prepare_handoff` supplies missing delivery operations and may replace the narration with fallback text. See [cue scheduling](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:412), [cue consumption](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:207), [pacing schema](/home/bcorfman/dev/freytag-forge/storygame/story_package/models.py:472), and [forced handoff](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:598).

**Cost.** A player who misses the useful sentence can spend the rest of the scene following invented leads. The 2A forms case supports this failure path; it does not establish how often it occurs. See [Reach-the-reveal round](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1326).

The older timer audit's claim of no lasting cost is obsolete. Handoff costs now assert evidence gaps, and 3C reads them. The copy-check cost was removed because it described an unsupported opportunity. Keep that correction. See [handoff costs](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/handoffs.yaml:82), [later consequences](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/pacing.yaml:50), and [copy-check removal](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1281).

**Redesign.** Build the nudge field. Keep the first eligible cue early. At the nudge threshold, offer one stronger pointer for an eligible, unresolved reveal. Store the stage and last delivery turn per scene visit. Do not consume a stage on rejection. Stop when its fact is earned or its source is spent. A new eligible thread gets its own schedule. Tie the cue directly to its reveal rather than rediscovering ownership from overlapping fact effects.

Start with one escalation, not an indefinitely repeated hint. Use the existing cue as its fallback text. Authors can later supply a stronger pointer. Append it through the existing authored path; do not ask the narrator to remember it.

Keep forced delivery as an explicit continuity backstop for this story. Record it as assisted progress. Use an existing authored cost where the story supports one. A timer that merely says what was lost is insufficient when the next scene requires the missing knowledge. Do not invent a penalty for every delay.

**Migration.** Reuse current fact IDs, cue text, delivery text and deadlines. Add optional reveal links and escalation text. Convert existing delivered flags to stage-one history when loading a compatible save. Keep old saves explicitly versioned if that conversion cannot be guaranteed.

**Estimated cost:** two worker tasks for state/scheduling and explicit cue links; one story round for 1A, 2A and 2C pointers. **Losing risk:** the escalation feels like a command script and reduces player agency.

**Cheapest offline check:** ignored cue, earned reveal, spent alternative, rejection, save/load and scene re-entry timelines. Verify that no pointer names an unrevealed secret. **Smallest live check:** three targeted recoveries per affected scene, each starting with the documented detour; compare existing behavior and escalation. Measure turns from pointer to earned reveal and read the prose for unwanted coercion.

## 3. Reveal meaning is authored twice, then filtered through a prompt-sized candidate list

**Confidence: high in the mechanics; medium in the best replacement. Structural authoring change.**

**Evidence.** Exact matching requires every group, expands fixed synonym classes and returns nothing on ties. Its global negation set includes even `do`. The 2C copy reveal has a long verb list, while `earn_when` still says only “checks, secures, or copies.” Exact and semantic paths therefore need not mean the same thing. See [matcher](/home/bcorfman/dev/freytag-forge/storygame/runtime/candidate_matcher.py:40) and [2C reveal](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:1616).

The semantic fallback is already real. It runs after an exact miss or tie. It requires complete handoff data, skips established candidates and negated inputs, and accepts exactly one positive answer. It judges the command against `earn_when` or `statement`, plus names and placement text. It does not infer missing prerequisites or recover an ignored pointer. See [dispatch](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:286), [fallback](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:391), and [Jev question](/home/bcorfman/dev/freytag-forge/storygame/runtime/jev_questions.py:60).

Both paths receive the projected candidates. The default projection keeps four, sorted by reference, priority and ID. The fallback's six-candidate ceiling does not restore candidates already removed. This couples reveal correctness to a narrator-context budget. See [limits](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:84) and [candidate selection](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:265).

There is also a budget mismatch. The 40-call counter belongs to the provider instance. The normal web route builds a new provider per request. It is not a persisted session limit on that path. The PRD meanwhile forbids model intent outright. See [counter](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:249), [provider construction](/home/bcorfman/dev/freytag-forge/storygame/web_demo.py:233), [turn route](/home/bcorfman/dev/freytag-forge/storygame/web_demo.py:326), and [PRD](/home/bcorfman/dev/freytag-forge/docs/PRD.md:29).

**Cost.** Missed natural commands, growing synonym lists, ambiguity introduced by widening, and uncertain fallback coverage. The recorded 2C patch explicitly accepts a new tie. A later 3/3 run never exercised its new verbs, so it did not validate that behavioral change. See [copy-step patch](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1320) and [1c10272f run](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1324).

**Redesign.** Make an authored action contract the primary surface: target references, a short required act, prerequisites, and a few positive and near-miss examples. Support a story-safe named target when no physical entity is appropriate. Derive the semantic question from this one contract. Keep exact matches as a cheap, tested fast path. Semantic interpretation proposes one eligible action; deterministic validation still owns effects. A tie remains ambiguous unless a separately validated disambiguation succeeds.

Evaluate exact matching over all eligible reveals. Give semantic matching a separately bounded shortlist with explicit coverage telemetry. Do not reuse the narrator's four-item list as the universe of valid actions. Log no eligible action, shortlist exclusion, exact tie, semantic refusal, provider error and budget exhaustion separately.

This is a typed intent layer, not a fixed player-command table. Arbitrary commands remain possible. Move reveal selection out of prompt assembly into a shared selection service. Keep the narrator as the renderer. Update the PRD to describe this bounded model proposal honestly. Use a persisted operational budget, separate from rollback of story facts, if the session cap is intended to limit billed attempts.

**Migration.** Import current evidence groups unchanged as legacy fast paths. Add contracts one reveal chain at a time. Run the semantic contract in shadow before letting it own new matches. No plot rewrite is needed.

**Estimated cost:** three worker tasks for selection/telemetry, schema/shadow matching, and budget lifecycle; one author round per migrated chain. **Losing risk:** semantic false positives grant an unearned reveal.

**Cheapest offline check:** saved commands labeled by eligible state, with positive, wrong-target, partial-action and ambiguous cases. Include more than four eligible candidates and request reconstruction. Mock semantic responses to test validation; mocks cannot establish intent accuracy. **Smallest live check:** ten samples for each of six hard commands against both contracts, followed by three targeted 2C continuations. Score false grants before recall. Keep the current path if false grants increase.

## 4. Measurement records proxies where the decision needs causes

**Confidence: high. Incremental tooling changes.**

**Evidence.** The corpus is valuable, but it constructs one late state per scene and asserts earlier/current knowledge. It does not restore each narration's actual pre-turn state. Its principal regression test checks formerly accepted entries; it does not require formerly rejected entries to remain rejected. See [state construction](/home/bcorfman/dev/freytag-forge/tests/test_narration_corpus.py:29) and [golden gate](/home/bcorfman/dev/freytag-forge/tests/test_narration_corpus.py:90).

The blind-player report derives `play` versus `timer` from the transition turn relative to the deadline. A late earned exit can therefore be labeled timer. Its stuck-turn heuristic can miss a loop that keeps naming an affordance. Prompt capture stores one untyped prompt value; the plan records a diagnosis blocked because saved prompts were name-matching prompts. See [analysis](/home/bcorfman/dev/freytag-forge/frontend/e2e/blind-player.js:173), [capture format](/home/bcorfman/dev/freytag-forge/frontend/e2e/blind-player.js:121), and [capture finding](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1326).

**Cost.** Cheap tests can miss the relevant state. Expensive runs can pass without exercising the fix. Repeated full runs consume review time while mixing player choice, narration, matching and prior-scene history. The four reported full-run totals are not controlled estimates of a single change. See the [80f5c64c record](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1321) and [1c10272f record](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1324).

**Redesign.** Record immutable attempt bundles: code/package/config identity, pre-state, command, typed request/reply stages, selected reveal, committed delta, cue stage, and explicit transition cause. Keep rejected attempts too. Do not overwrite one prompt slot with another call. Record operational failure separately from a gameplay miss.

Retain the existing corpus as a broad language regression check. Add a small state-exact set for secrets, ignored cues and disputed commands. Include must-reject cases. Review expected verdict changes; do not regenerate them merely to make a gate green.

Measure a funnel per reveal: eligible → cue shown → relevant attempt → match → delivery → earned exit. Report missed attempts, false grants, rejected attempts per attempted turn, turns without fact progress, assisted deliveries, and call count/latency. Inspect the final delivered text, not only `item_facts`.

Use this cadence: deterministic replay on each affected change; targeted live arms when a model behavior changes; three scene continuations as a smoke gate; a full journey after a batch or a change to shared progression. Start stochastic diagnosis at 10–15 replies per arm for a fixed prompt, then test different states. For a decision about a scene's success rate, start with 12 paired entry scenarios per arm and report uncertainty. Extend only against a declared effect size and sample cap. Do not pool different scenes as independent replicates of one behavior. Three clean runs establish a smoke result, not reliability.

**Migration.** Version new bundles. Label old corpus entries as synthetic-state checks. Reuse the current bench variations and live scripts. The runbook already distinguishes bare from realistic play states and warns about variance; make that distinction machine-readable. See [runbook, live bench](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:93).

**Estimated cost:** three worker tasks for bundles, state-exact replay and causal reporting. **Losing risk:** snapshot maintenance becomes a second implementation of the runtime.

**Cheapest offline check:** replay bundles through the real engine, with model calls stubbed. Verify late earned exits and repeated-affordance loops receive the right classification. **Smallest live check:** one successful and one rejected turn plus one short forced-handoff continuation; confirm all request stages and causes survive recording. Larger behavior studies then use these records.

## 5. A scene's executable meaning has too many authors

**Confidence: high in duplication; medium in consolidation benefits. Structural compiler change.**

**Evidence.** Plot metadata, knowledge, routes, handoffs and pacing hold different pieces of one reveal. The 2C knowledge record names a route realization, defines its own requirements and effects, and separately carries action and delivery wording. Handoffs supply another delivery for related facts. The loader coordinates these representations. See [2C record](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/knowledge.yaml:1616), [handoffs](/home/bcorfman/dev/freytag-forge/data/stories/continuity-initiative/handoffs.yaml:163), and [loader](/home/bcorfman/dev/freytag-forge/storygame/story_package/loader.py:1081).

The resulting prose can compete. The 3B probe found that removing the entry claim stopped the relay pull on neutral commands, but other arms made premature relay success easier. The 2C file sentence did not redirect the tested commands. Those results support competing responsibilities and context, not a universal claim that the model cannot use scene text. The successful 1C shaft probe is the counterexample. See [3B probe](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1111), [2C probe](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1330), and [1C probe](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1291).

**Cost.** A local scene repair needs several file edits and broad review. A prompt-only fix may trade one defect for another. The narrator is expected to finish the command while also steering toward an unrelated plot step. Its actual rule explicitly limits protagonist action to the player's command. See [turn rules](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:520).

**Redesign.** Keep world declarations global. Put each scene's executable reveal contracts in one authored module: source beat reference, requirements, action contract, effects, safe cue stages, earned delivery and deadline delivery/cost. Keep plot prose as the literary source. Compile the current runtime structures from those modules. Do not merge everything into one giant YAML file.

The engine owns eligibility, action selection, cue scheduling and commits. Story data owns the action's meaning, available observations, delivery and consequences. The narrator renders the selected action within current state. The engine appends the authored pointer when it is due. This extends the already proven handoff technique; it does not ask the narrator to choose a plot direction.

A scene fix should normally touch one reveal definition. New world objects and genuine plot changes can still require a world or plot edit. “One file for every possible scene change” is not a useful invariant.

**Migration.** Start with a read-only assembled scene view, including source provenance and conflicting declarations. Then import one chain into the new authoring form and compile the old structures. Keep IDs, effects, prose and order identical. Choose exactly one source mode per migrated chain; never maintain both by hand. Differential package and prompt comparisons gate each migration.

This requires rewriting the authoring/compiler seam, not the fact engine. More cross-file lints help detect drift but cannot remove duplicated authority. The current grounding decisions cover placements, effects and companions; they do not provide this authoring unit. This consolidation is a new proposal after checking W1–W14, the grounding guide, and the earlier scene handoffs.

**Estimated cost:** one worker task for the assembled view; two for a one-chain compiler pilot; one story round. **Losing risk:** the compiler hides causality and makes debugging harder.

**Cheapest offline check:** semantic equality of compiled packages, IDs, effects and rendered prompts for the pilot chain, plus a second-story fixture. **Smallest live check:** one existing scene script before/after migration. Broaden only if the compiled result changes behavior.

## 6. The player-input rule suppresses the distribution it claims to test

**Confidence: high in the filtering defect; unknown in its real-player frequency. Incremental process and harness change.**

**Evidence.** AGENTS requires imperative input in every test, probe and example. It correctly says activity cannot be decided from a verb alone. The blind-player prompt nevertheless bans mere listening, and its validator rejects every command starting with `listen`, including an action on a real recording. It also excludes first-person commands and any restraint clause before they reach the game. See [input rules](/home/bcorfman/dev/freytag-forge/AGENTS.md:30) and [blind-player filter](/home/bcorfman/dev/freytag-forge/frontend/e2e/blind-player.js:3).

**Cost.** The model player is useful but is not evidence that ordinary people will use the same command style. The blanket lexical negation check in the matcher is less likely to be challenged by a harness that forbids negation. This is a coverage gap, not proof of a measured human failure rate. See [matcher rejection](/home/bcorfman/dev/freytag-forge/storygame/runtime/candidate_matcher.py:128).

**Redesign.** Keep imperative scripts as controlled action probes. Amend the rule to permit a separate robustness corpus with real player wording, polite requests, pronouns, corrections and scene-valid listening. Preserve raw input beside any normalization. Remove the lexical claim that all listening is a non-event. Judge whether an action changes the relevant scene, or compare it with a null control as AGENTS already suggests.

Do not broaden runtime matching blindly. First reveal the gap. Label cases requiring clarification separately from commands with a clear intended act. The exact path may conservatively abstain on mixed clauses; the bounded semantic path can be evaluated for them.

**Migration.** Existing scripts remain valid. Add the second corpus and a distinct live player profile. Update AGENTS to distinguish canonical probe style from supported player language. No story rewrite is needed.

**Estimated cost:** one worker task plus one author review of labels. **Losing risk:** synthetic “natural” wording is no more representative than the current imperative profile.

**Cheapest offline check:** paired command variants in the same state, including meaningful listening and unrelated restraint clauses. **Smallest live check:** three matched scene starts per profile. Later validate the distribution with human play rather than treating another model profile as proof.

## What to stop

- Stop widening aliases as the default secrecy repair. It changes resolution and recall as well as narration safety. Findings 1 and 3 show the coupling.
- Stop treating a nine-scene triple as the first check of a local wording change. Test the failed path first. Finding 4 explains the missing signal.
- Stop claiming that a green run exercised a patch when its commands never used the patch. Keep the explicit caveat already present in the 1c10272f record.
- Stop asking background frame sentences to perform cue scheduling. Preserve successful scene grounding such as 1C; use authored delivery for guaranteed pointers. Findings 2 and 5 distinguish them.
- Stop maintaining contradictory current rules. The PRD's ban on semantic intent disagrees with runtime. The authoring guide says cues wait for the nudge, while scheduling starts earlier. See [PRD](/home/bcorfman/dev/freytag-forge/docs/PRD.md:29) and [cue documentation](/home/bcorfman/dev/freytag-forge/docs/markdown-story-authoring.md:152).
- Stop using “recommend only proven techniques” as a veto on redesign. Keep it as a prior-art requirement. The review must be allowed to replace a proven local workaround when repeated evidence shows its cost. See [AGENTS, Fixing a Scene](/home/bcorfman/dev/freytag-forge/AGENTS.md:88).

## What to keep

- **Fact-owned state and typed validation.** Keep cloned candidate state, explicit effects, snapshots and rollback as core contracts. They give proposed interpretation a bounded consequence. This review does not establish that every path fully satisfies that contract. See [turn boundary](/home/bcorfman/dev/freytag-forge/storygame/runtime/engine.py:85) and [snapshots](/home/bcorfman/dev/freytag-forge/storygame/runtime/state.py:128).
- **Worldkeeper and one-way story-to-world effects.** W7 and W8 already solve custody and companion movement without story-named runtime branches. Keep them. See [W7–W8](/home/bcorfman/dev/freytag-forge/.plans/world-model.md:5324).
- **Authored reveal delivery.** Keep withholding handoff content from the narrator and composing the earned delivery in the runtime. It reduces dependence on the small model reproducing an exact claim. See [handoff fields](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:25) and [runtime-owned candidates](/home/bcorfman/dev/freytag-forge/storygame/runtime/cloudflare.py:359).
- **Eligibility as a shared explanation.** Build on `explain_reveal`, already used by candidate projection. Do not invent separate progression logic for a new selector or cue scheduler. See [projection](/home/bcorfman/dev/freytag-forge/storygame/runtime/knowledge.py:265).
- **Recorded-prompt probes and human reading.** Keep comparison arms and reading narration plus delivery. Correct the record fidelity and sampling claims. The 2C regex false positives show why prose review matters. See [2C probe](/home/bcorfman/dev/freytag-forge/.plans/scene-affordance-e2e.md:1330).
- **Ringer's executable checks and SHA-bound staging evidence.** Keep the worker/orchestrator split. Improve the check's behavioral oracle before changing worker models. Keep the deployment identity check. See [staged gate](/home/bcorfman/dev/freytag-forge/docs/testing-runbook.md:145).

## Sequenced plan

These are proposed tasks, not completed work. The order favors cheap evidence and direct rejection/stall reduction. The compiler pilot is deliberately last.

| Step | One task or story round | Evidence that it worked |
| --- | --- | --- |
| 1 | Add six state-exact regression fixtures: ordinary-name acceptance, a premature secret, a skipped reveal, a missed pointer, a matcher tie, and more than four eligible reveals. Keep current expected defects explicit. | Each case reproduces its intended boundary without network calls. No fully-earned substitute state. |
| 2 | Make one typed attempt bundle for the hosted path, including all model stages and explicit earned/forced transition cause. | One accepted, one rejected and one forced continuation can be replayed and classified from their records. |
| 3 | Review the shipped disclosure vocabulary in one author round. Use existing `leak_terms` and scoped aliases where sufficient. Specify the remaining canonical-name guards. | Nine-scene ordinary/secret matrix shows only intended changes; genuine premature disclosures stay rejected. |
| 4 | Implement opt-in explicit entity disclosure guards with legacy defaults. Migrate only the reviewed copied-files declaration as the pilot. | Declaring that public object adds no unrelated rejection; secret fixtures still fail; custody is tracked. |
| 5 | Add one unresolved-cue escalation at `nudge_after_turns`, with snapshot-safe stage history and current eligibility checks. | Timeline tests show one reminder, no reminder after earning/spending, and no cue consumption on rejection. |
| 6 | Run a story round on the documented 1A, 2A and Michelle-first 2C detours. Reuse approved pointers before writing new text. | Each run actually exercises recovery; report turns to reveal, assistance and false disclosure against baseline. Three per path is smoke evidence. |
| 7 | Separate the eligible reveal universe from narrator truncation. Add match-reason telemetry without changing semantic policy. | Candidate five remains exact-matchable; exact ties, semantic misses and exclusions have distinct records. |
| 8 | Pilot one typed action contract for the 2C copy step in shadow, using the existing semantic provider. | Labeled hard commands improve recall with no observed new false grants; ten samples per command precede three targeted continuations. Activation is a later decision if evidence is inconclusive. |
| 9 | Add the raw-language robustness profile and remove blanket listening rejection. Amend the input rule and stale matching/cue documentation. | Clear command variants preserve intended outcomes; ambiguous ones are identified; real listening reaches the game. |
| 10 | Build a read-only scene contract view with provenance and duplicate-value warnings. | A reviewer can trace cue → eligible action → delivery → effect → exit for 2C from one report. Use the report to scope a later compiler pilot. |

The larger compiler migration and persisted semantic-budget change are separate follow-ups, not hidden inside these ten tasks. Their costs and checks are specified above. Do not begin the compiler rewrite until the scene view demonstrates that it removes real authoring work.
