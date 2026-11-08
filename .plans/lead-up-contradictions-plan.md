# Scene 3A: lead-up and authored delivery contradictions

Status: **proposal for Brandon's review**, 2026-11-07. **Stage 0 done 2026-11-07** (frozen FINAL payloads and 1A/1B/2A arms built, validated, free; see [the prereg](lead-up-contradictions-prereg.md)); 1A probe run 2026-11-07: control 11/12 hostile, bio arm 0/12 (see prereg Result 1A); 1B (malformed gate failed) and 2A (stock speech 11→0 but replaced by other chatter) not adopted; 1A adopted via narrator_bio (1A2: trimmed, 0/12 hostile). Live qualification not run. No story, runtime, test, or experiment changes have been applied by this investigation; no model calls or test suites were run. Existing uncommitted work is retained. Update this file in place on later rounds.

## Resume here

The failure is not one instruction conflict. The live FINAL run contains a doubled embrace (c1), an early tag reveal (c2), irrelevant organizing speech and an unfulfilled movement (c4), an invented refusal contradicted by the authorization delivery (c6), and an ambiguous premature signal (c8). CONTROL c9 repeats the previous handover; FINAL c9 does not. Correct first-person speech does not establish relevant speech or coherent composition.

First review the source repairs in steps 1–3 below. The most concrete new finding is that the senior official has a narrator-safe biography in `world.yaml`, but the loader never includes him in `package.characters`: he has no heading under `plot.md`'s Principal Characters. His c6 prompt consequently contains his location and generic keywords, but not that biography. This is a confirmed omission, **not yet a demonstrated cause of his hostility**.

Brandon must approve each proposed story/world change, experimental wording and billed batch before application. ChatGPT Desktop owns story wording; Claude Code implements approved changes through Ringer, tests first. This planning request authorizes the document, not those later actions. Previously approved work remains as found; do not restart, revert, or silently broaden it.

## Evidence and interpretation

Inspected HEAD is `5fc12e791c75d793570ce654d73d82b6e3a0595d`, with the dirty working tree described by the shared plan. Read the scene-fixing, narrator-writing, grounding, player-input, contributor and agent-workflow guides; the PRD handoff contract; both shared plan/prereg files (including A/B/C/U/G/GU/GU2/GUE1/L); the people/speaker plan; scene 3A's plot and package declarations; and the named runtime paths. The actual source method is `_speaker_contexts` (plural).

Method precedents checked: `.plans/world-model.md` and historical W1–W10 at `5ea0119955c62b84699a8dc7878a4af770b55a7e`, including W4 authored placement text, W7 one-way fact effects and W8 authored companions; the scene guide's 3B missing office-entry sentence and 3A/2C conflicting-source removals; and `.plans/astra-fixes-plan.md`, which does not establish a successful generic completion-rule cure. These justify the source-first method, not the efficacy of a new candidate. Do not repeat failed presence/frame deletion, speech-header, first-person-rule, completion-deletion or length arms under new names.

Primary records are `bench/results/shared-narrator/live/{control,final}-r1/all-turn-records.json`, `runs[0].turns[0..8]`, with their `summary.json`. The appendix preserves the exact generated portion, appended segments, and complete recorded user prompt for every turn, plus the deduplicated full system prompts. It makes this review usable even though the source records are gitignored. Classifications here are an unblinded retrospective reading, not a newly blinded score.

**Composition correction:** c1–c8 have selected handoffs and `narration` already contains their appended handoff. Split the exact recorded suffix once; never append it a second time for scoring. c9 has no selected handoff; its `authored_segments` are the bridge and 3B entry, absent from `narration`. Include those separately. Both records have `left_scene: true` on c9. Thus the earlier claim that all nine turns have an appended selected delivery is inaccurate, and these particular runs do record a transition; they still do not establish an earned-exit rate or alternate-path qualification.

### All eighteen turns

Here “agree” addresses the lead-up/delivery boundary; it does not excuse unrelated invented detail or prove the world state matches. “Repeat” includes semantic pre-emption, not just exact string copying.

| Turn / selected ID suffix | CONTROL: generated text → delivery | FINAL: generated text → delivery | Recorded prompt evidence / verdict |
| --- | --- | --- | --- |
| 1 / `a_r1` | “We need to get them out of here” → “Kristin joins Michelle beside the captives.” **Agree**, with a Brandon detour. | “then she pulls Kristin into a tight embrace” → “Michelle looks up, goes completely still, and then pulls Kristin into a tight embrace.” **Repeat/PRE**: two initiations of the hug and a reset to joining her. | Both prompts explicitly show the impending delivery and say “Write only what leads up to it.” FINAL's delivery contains the embrace; no speaker lines exist here. The recurrence is generated, not two runtime insertions. |
| 2 / `f_r1` variant | “She reads the transfer date, a week old” → “The closing code on every tag is sensor fault…” **Agree**. | “She sees the date and the words 'sensor fault' printed on the tags” → the same closing-code sentence. **Repeat/DUP** of the discovery, with no contradictory fact. | THINGS supplies the date, not the code. The code is in the selected delivery variant. The final lead-up takes content reserved for that delivery. |
| 3 / `g_r1` variant | Radio repeats “Security is tightening around the lower levels” → “It is the same ninety seconds Kristin timed on the truck radio…” **Boundary agrees**, but invents the precise broadcast wording from the frame. | Radio says “Attention, all personnel, please report to your designated stations immediately” → same delivery. **Boundary agrees**, with an unsupported verbatim broadcast. | THINGS says “tuned to the facility's own message, played on repeat”; the delivery explains the one-word code. Neither prompt supplies these quoted announcements. Their exact words are invention; no evidence establishes that either literally contradicts an authored transcript. |
| 4 / `b_r2` | “Kristin walks towards the medical level” → “Michelle shows Kristin the medical level.” **Agree**, with invented beeps/voices. | “I've been organizing everyone with secret announcements over our stolen radios” → same delivery. **Topic discontinuity**, not a logical contradiction of experiments. The composed text never clearly enters the level. | FINAL offers exactly that organizing utterance; PLAYER says “Enter the medical level.” Plot says “Michelle leads Kristin through a medical level…” but delivery weakens this to “shows”. FINAL c4 leaves Kristin at detention level; c5 confirms it. Score prose first; the state is corroborating evidence of a separate movement omission. |
| 5 / `h_r1` | “What's the lemon cake?” → “Michelle answers without a pause and gets every detail right: Saturday, the circle, the lemon cake.” **Agree**, although the question is thin. | “Shelly, what's going on with the lemon cake?” → same delivery. **Agree**; no invented answer or shared memory. | PLAYER asks about the lemon cake; delivery carries the proof. Both versions leave the answer to the runtime. Neither reproduces the full plot's apology/birthday emotional resolution; that is a pre-existing authored compression, not a new lead-up conflict. |
| 6 / `d_r1` | “What do you know about the gate codes?” / “fear and desperation” → official gives authority. **Agree**. | “You'll never get out of here… you're not cleared” → official gives one-use authority. **Conflict/CONTRA**: categorical denial followed immediately by assistance, with no reversal. | SCENE has “senior official”, “government prisoners”, “fabricated evidence”, “authorization codes”; THINGS places him in detention captives. His biography is absent from CHARACTERS in both arms. His offered speech concerns Michelle, not his own authority. The delivery is nonetheless present and explicit. |
| 7 / `i_r1` variant | “trying to understand its purpose and how it might be disabled” → reader clears and door opens. **Agree at boundary**, with an unrequested disabling intention. | “trying to determine if it's functioning properly” → same result. **Agree**. | PLAYER checks the reader. Delivery omits the plot's explicit Brandon/card action, so “first pass” lacks an actor in both composed versions. This is missing authored causality, not a reason to invent reader mechanics or a new prop. |
| 8 / `c_r1` | “We need to get the prisoners moving” to Brandon → Michelle hands radio to Kristin; Kristin signals. **Agree**, with a target detour. | “Tell them to start…” to Michelle / “begins to make an announcement over the radio” → handover and Kristin's signal. **Ambiguous PRE/agency conflict**: may start the uprising before its authored signal. | PLAYER addresses prisoners; prompt says Michelle coordinates them. Delivery explicitly assigns the signal to Kristin. No words of Michelle's announcement or resulting uprising are given in the lead-up, so a completed duplicate signal is **not established**. Preregister this ambiguity separately from a definite replay. |
| 9 / none; bridge + entry | “Michelle hands Kristin the stolen radio… Kristin takes the radio and gives the signal” → bridge summarizes the uprising and fight upward. **Historical repeat**, also overlapping bridge content. | “We need to move, now” / “prisoners begin to stir” → “Kristin, Michelle, and Brandon fought upward…” **Agree** as initiation then bridge completion. | CONTROL offers completed handover statements as present-tense speech; FINAL offers “Your signal worked” and current results. No selected-delivery/lead-up pair is in either c9 prompt. A selected-handoff-only fix cannot cure ordinary-turn replay. |

Opening context was also read. Neither opening reunites the women; each identifies Michelle before the cue. CONTROL invents a panel countdown; FINAL invents a reader warning. These remain opening defects under the other plans, not evidence for changing handoff composition.

### What the code establishes

- `candidate_matcher.uniquely_matched_authored_handoff` requires complete action evidence and nonblank delivery, chooses a unique eligible match (with specificity/repeatability rules), otherwise returns none. The bounded semantic path can propose a handoff too. c1–c8 record the expected IDs; model-selected IDs are empty. There is no evidence that wrong selection causes these mismatches.
- `CloudflareTurnProvider._authored_handoff_rules` exposes **the selected delivery only**, then says “Write only what leads up to it. Do not have Kristin find anything else.” That discovery-oriented second sentence does not explicitly reserve speech, embraces or signals. This is a plausible weakness, not proof that replacing it works.
- `_turn_rules` keeps ordinary system instructions, including finishing the action and answering addressed characters. `_system_prompt` retains the length sentence. `_section_user_prompt` omits candidate metadata on selected handoffs but still supplies scene details, committed statements and speaker lines. Those are independent sources from which the lead-up can draw.
- `_compose_authored_handoff` in **cloudflare.py**, not `_prepare_handoff`, appends the chosen delivery to the model segments and assigns the runtime-selected knowledge ID. It does not semantically deduplicate the model prose. `_prepare_handoff` in **engine.py** handles staged fallbacks, world/delivery operations and bridge/entry composition. No sign in these records indicates a doubled append or fallback replacing the c1 lead-up. Do not repair this by text trimming or a prose regex.
- `_established_for` now gates voiceable storylet realizations on `is_narrated`, using `knowledge_narrated` facts. `_speaker_contexts` then uses each speaker's approved `speaker_text`; `_speaker_constraint_lines` still offers all eligible entries to present speakers, regardless of whether this command asks about that subject. The gate removes never-narrated siblings, not already-delivered organizing speech. It does not remove the sibling's canonical statement from SCENE: FINAL c4 still says “Michelle has explained…” about other sites. GU2 S28 and G S3/S54 show that content can still be voiced from SCENE.
- Official biography omission: `_parse_characters` in `story_package/loader.py` iterates only Principal Characters headings. `_character_lines` iterates the resulting `package.characters`. `world.npcs[].narrator_bio` substitutes a heading's bio; it does not independently add a character. The official is placed, a participant, named in the command and eligible for speaker context, yet absent from this separate character list. Presence work cannot fix that list by itself.
- The embrace is not persisted as transcript recall. Later prompts contain authored statements such as “Kristin and Michelle have reunited,” not the delivery prose. The GUE stage-2 correction is valid: changing only the reunion delivery cannot change frozen c4/c5/c9 prompts. FINAL c1 copying is same-turn exposure, not stale embrace history.
- c4's world effect for `behavioral_experiments_known` places the experiment records in `medical_level`; it does **not** move Kristin. The same fact can be earned by reading records (`b_r1`/`e_r1`), so adding a protagonist move to that shared fact would force travel on other realizations. Do not do that as a shortcut. Michelle remains placed at detention level and is not a 3A companion; the fixed frame sentence also persists. Source wording and world behavior require a separate reviewed decision if stronger prose still leaves a mismatch.

### Earlier experiments: rows, rubrics and retained decisions

Read the full G, GU, GU2 and GUE1 sheets (108/36/36/48 replies), their keys, saved score files and frozen payloads; raw row files include malformed replies and no transport-error rows. Sheet IDs below are local to each experiment. These studies mostly score the **generated text**, not actual composed live turns. They cannot establish that a generated portion alone should complete the handoff.

| Experiment | Question/arms and original gates | Row-level evidence and result | What carries forward |
| --- | --- | --- | --- |
| A | Delete SCENE-only exclusivity; opening separately shortened. Context fidelity, action and syntax gates. | Opening 4→1 targeted misses; ordinary c9 replay 12→12; ordinary dialogue recital 8→12. | Ordinary deletion dropped; opening-only candidate unadopted. Keep existing authority wording here. |
| B | Remove “Finish each action the player gives” on selected handoffs; c5 and 1C discovery, composed coherence. | c5 control 0 misses, arm 2; 1C “nothing out of the ordinary” contradiction 12/12 both. | Dropped. This tested **completion**, not omission of the NPC-answer sentence. The old plan's shorthand equating H and B must not erase that distinction. |
| C | Relax length only on handoffs; extra acts/disclosures. | Control target did not reproduce; no useful shortening at 1C. | Dropped. Do not blame minimum length as an established cause. |
| U | Authored utterances without gate; person/relevance/question/syntax gates. | D 0/36, but organizing/other-sites speech 12/12 c4, movement 0/12, c5 and c9 failures. | U alone rejected. Authored grammatical person is insufficient. |
| G / GF | C0, narrated gate G, then G + first-person sentence GF; relevance, person, question, custody and syntax. | G S3/S54 voice “freeing this block means little…” despite sibling speaker-line removal; S2/S77 prematurely answer “Saturday, the circle, the lemon cake”; S40 repeats handover. C0 S65/S67/S88 show third-person self-recital. GF S47 still self-recites; S57/S91/S92/S95/S102 hold up the radio. G c4 action 1/12 vs 9/12; c9 replay 7/12 vs 12/12. | G missed its win rule but stayed under its specified revert threshold. GF rejected; Brandon subsequently rejected the prompt-first-person route. Do not remove the gate to regain c4 movement. |
| GU | Gate + four authored per-speaker utterances; zero person errors and no >2 regression vs G; c4 action explicitly an open-decision clause. | GU S4/S5/S7 etc voice organizing stock line; S21 malformed keys instead of text. S19/S20/S23/S29/S35 urge checkpoints already seized. Person 0/36; c9 replay 5/12; c4 stock speech 10/12, action 0/12. | Written rule met, not overall pass. Brandon chose qualification; optional schema built uncommitted. Comparators same-day but not interleaved. |
| GU2 | Nine authored lines emphasize present meaning/next step instead of retelling Kristin's acts. Same safeguards; c4 stock speech ≥10 or action <6 flags decision. | S3/S6/S7 and every c4 row voice organizing line (12/12); S28 adds other-sites SCENE text. c9 S5/S9 etc voice “The uprising is active…” instead of handing the radio again (replay 0/12). S14 and c9 S11/S30/S33 have malformed/duplicate-key raw output. | Person/replay improved, relevance not solved. Four malformed replies retained. Brandon chose embrace/live qualification; nine entries remain uncommitted. |
| GUE1 | OLD vs EMB, 12 each at R1/R2, only delivery line differs. PRE≤1, EXTRA≤1, CONTRA/MAL=0, COMP≥11; nonregression on PRE/DUP/EXTRA. | R2 OLD S3/S12/S15/S24/S30/S36/S37/S39 restate answer; S5/S11/S28/S42 prioritize freeing these people first. EMB R2 avoids it. EMB R1 S1/S2/S31 add Brandon urgency, S45 “I'm glad you're here”; S35 staring is scored PRE, **not an observed hug**. S6 invents announcements “on the wall”; S35 paper is also unsupported. | R2 met, R1 missed EXTRA 4/12; new embrace retained for live study by direction. Do not describe GUE1 as a clean universal win. The “action-first” explanation remains a hypothesis: OLD R2 already began with sharing a moment. |
| L smoke | Shipped vs all dirty changes, real nine-command Path A. Hard gates and soft counts; PRE/CONTRA extension after smoke. | Both completed, zero recovery/rejection reported, both 5/7 scene score; the table above shows why that score is insufficient. FINAL c4 state stays detention; CONTROL reaches medical. FINAL c1 hug and c6 hostility are new observed misses; CONTROL c9 replay absent in FINAL. | One pair cannot isolate gate, presence, speaker text, delivery or state-history effects. Remaining pairs were not evidence in this request; do not claim four-pair qualification. |

The GUE1 key maps R2 contradictions to OLD (S5/S11/S28/S42) and R1 extras to EMB (S1/S2/S31/S45). Its stored COMP judgments permit all R1 compositions, including the tolerated staring moment. This plan uses a stricter actual repeated-action distinction for the live double hug; it does not retroactively change the GUE1 win rule. Similarly, a correct answer to a vague cake question can agree at the seam while falling short of a stronger identity-proof scene check.

No experiment isolates c6 hostility or c2 duplication. The official's missing bio, inherited generic keywords, ordinary-answer rule and stochastic variation are separate hypotheses. No cause attribution from a single CONTROL/FINAL difference is warranted. The summaries' request counter reports 2 narration requests despite nine recorded model turns per run; each also reports one OpenAI judge call and 2/3 Jev matcher calls. Do not use the misleading counter for new spend approval.

## Ordered plan: source corrections before rules

For every candidate below: first freeze a copy of the **actual FINAL recorded prompt** and its exact delivery, plus settings and entry state provenance. Make one allowed edit per arm. Do not quietly use a scripted prefix instead of a live prefix. Replay through Ringer after approval, 12 samples per arm, same-day interleaved controls, no replacement samples. Story candidates use private package copies; no application to the working tree until approved. Stage 0 preparation can be network-free, but is future implementation work, not already completed here.

### 0. Freeze review inputs and measurement

Claude Code/Ringer preparation: preserve HEAD, dirty diff, package fingerprint, source artifact hashes, model/settings, commands, selected IDs, whole prompt and exact delivery variants. Retain raw replies, duplicate JSON keys, decoder outcomes, model-only prose, appended segments and composed text separately. Never count `cue_text` telemetry as newly appended text unless it occurs in the returned segments. Use existing capture/replay/sheet tooling as the pattern, not its inherited stale metadata: `gue1_capture.py` copies the GU2 envelope, so its `package_hash` is not independent proof of the EMB package's identity.

Read/scoring rubric for all arms: definite duplicate act/reveal (PRE/DUP), incompatible fact or stance (CONTRA), unrelated volunteered speech (IRR), ambiguous signal, correct target/question, composed action, biography fidelity, raw/content validity, and state consistency. Cite row/quote for every miss. Keep definite and ambiguous cases separate. Reading prose establishes movement; facts establish whether it persisted. Neither substitutes for the other.

### 1. Restore missing or weakened authored material

**1A — Official identity, first c6 comparison.** Add exactly this already-authored bio line to CHARACTERS in the frozen c6 prompt; nothing else changes:

```diff
+ - Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands.
```

The words come from `world.yaml`, not a new “be helpful” rule. Target: invented jailer/clearance stance and incompatible answer. Probe c6 FINAL vs bio-only, 24 requests. If it wins, the smallest existing-mechanism source repair is a **ChatGPT Desktop PLOT proposal**, adding `### Imprisoned senior official` and that existing paragraph to Principal Characters. The name already resolves to `senior_official`. Brandon approves the heading/canon placement and when the bio is public. Claude Code then checks package loading and all affected prompts through Ringer. No schema or global loader expansion is necessary; inventory whether this newly includes him before his intended reveal. If the public bio is inappropriate at earlier presence, return for narrower authored content rather than leak it globally. A global “all NPC bios” loader change is explicitly outside this proposal.

If the bio-only arm fails, do not infer that missing context never matters. Next source-material candidate, separately approved: add the unchanged plot sentence “Among the captives is a senior official publicly blamed for causing the catastrophe.” to the c6 scene context, with delivery selection as the scope. Probe alone before deciding the existing package carrier; do not inject the rest of 3A.3 before its reveal. This is an optional second 24-request comparison, not a combined bio+plot arm.

**1B — Make c4's delivery perform its authored move.** ChatGPT Desktop proposal for `k_sl_3a_b_r2.delivery_text`: replace its first sentence only with the plot's exact sentence:

```diff
- Michelle shows Kristin the medical level.
+ Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments.
```

Keep the remaining two sentences initially, even though the experiments overlap, to isolate the one-sentence restoration. Freeze the complete candidate string for Brandon; a later polish that removes redundancy is another approved text version. Probe c4 current vs revised delivery, 24 requests, assessing the **composed** move and intrusive speech separately. This cannot be called a speech cure if the organizing recital remains. Probe is about restoring what plot already says, not making the model finish the delivery in advance.

Claude Code must separately trace whether the authored move reaches world state. FINAL c4 already demonstrates that a selected reveal and accepted turn do not ensure that movement. Do not put a move on the shared `behavioral_experiments_known` fact. If the current authored-action path cannot persist the move, return an exact realization-specific world-effect proposal for Brandon, using existing package operations if supported; a new field requires separate design. No forced travel, companion effect, or after-render state mutation is authorized here. Until prose **and** state agree, c4 remains open even if its seam reads better.

### 2. Remove the source of irrelevant speech; scope conflicting instructions only on evidence

**2A — Organizing line, existing story flag first.** Frozen c4 arm deletes only these three lines:

```diff
- - Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- - Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- - Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
```

Keep SCENE statements, presence, gate and delivery byte-identical. Probe c4, 24 requests, independently of 1B. This tests the identified invitation rather than grammatical person. Candidate source implementation is **KNOWLEDGE**, `k_sl_3a_a_r1: voiceable: false`, removing its populated `speaker_text` mapping because the loader rejects the combination. Brandon must explicitly approve that this removes its explicit speech permission on ordinary questions too. Canonical organizing knowledge and authored reunion remain. Desktop owns that content-policy choice; Claude Code wires it/tests projection via Ringer. Do not silently apply this to all nine entries or to `a_r2`.

Before adopting the flag, freeze an ordinary question using existing player style, `Ask Michelle about the stolen radios.`, after the reunion; verify it really is ordinary with the real matcher. Test current vs flag, 12 each, preserving a substantive supported answer. If it selects another handoff, choose a spent state and record it before billing. This is 24 additional requests, not included in the diagnostic c4 pair. If ordinary speech loses needed information or c4 simply voices SCENE instead, reject this flag as a complete solution. A new command-relevance filter or handoff-only suppression is a separate engine design, not an implied follow-up: earlier speaker grouping/target-only changes lost, and no new heuristic is justified yet.

**2B — Conditional c6 answer ownership.** Only if 1A leaves a reproduced invented-answer failure, isolate removal of this existing SYSTEM sentence on a selected handoff:

```diff
- When the player talks to someone, that person answers.
```

This is the older H hypothesis, distinct from B's completion removal. Test c6 and c5 plus R2 other-sites reunion, 12 each per arm = 72 requests. The c6 failure now supplies a new trigger; c5 alone previously lacked a reproducing control. Keep completion, length, speaker lines, selected text and all other rules unchanged. Require c5/R2 questions to remain attributable and the composed answers intact. New engine behavior needs Brandon's approval; Claude Code builds only after a win, through Ringer. Ordinary and eligible-but-unselected turns retain the successful answer rule. No new story wording is involved. Do not assume a global answer-rule removal from a c6 win.

### 3. Delivery wording: preserve meaning, test the seam

These are **ChatGPT Desktop story-text proposals**, not engine fixes or known cures. Brandon approves exact prose before it is applied or billed. The source technique is GUE1's one-delivery-line comparison. It has mixed evidence, so retain the embrace and authored meaning rather than weaken the scene to make a metric green.

**3A — c1 reunion, optional if current text still reproduces PRE.** Candidate `a_r1` delivery:

> Michelle pulls Kristin close and holds her there. “You're here,” she says, her voice breaking. “You're really here.” Kristin holds on just as hard. For one unhurried moment nobody asks anything of either of them. When they let go, Michelle wipes her eyes and turns back to the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. She returns to her coded announcements and points toward the medical level, where the experiment records wait.

This removes the restart “Kristin joins…” and the repeated look-up sequence, retaining one embrace and the dose/records content. It may still provoke a copied hug: it is **not** a deduplication guarantee. For `a_r2`, use the same first five sentences, then “When they let go, Michelle wipes her eyes and explains that freeing this block means little without exposing the other sites. She points toward the medical level, where the experiment records wait.” Preserve the fallback's existing embrace pending a separate fallback check; no silent rewrite of it or the opening cue. Reflect any approved change of event order in plot first.

Probe R1 and R2 against current EMB, 48 requests; do not compare against OLD as the only control or buy the rejected hug-free story again. Score PRE, DUP, CONTRA, unsolicited Brandon speech, invented props and composed coherence. Any reduction in emotion or missed other-sites answer fails the content gate.

**3B — c2 pre-emption / c3 invented message / c7 missing actor / c8 agency.** Keep these defects visible, but do not rewrite four deliveries together. c2 already has the necessary discovery; adding more facts is not justified. c3's actual broadcast words are unspecified here: Desktop should author them only if Brandon wants them canonical, and then check their earlier appearances. c7's concrete missing actor has an existing plot sentence: separately propose prefixing the delivery (both base and badge-history variant) with “He runs a card through the reader, and the door opens on the first pass.” only after replacing “He” with an explicitly approved Brandon reference and checking the card's grounded identity. Do not add an undeclared card merely to make the sentence vivid. c8 already assigns Kristin the signal; keep that delivery and score the generated announcement as the ambiguous competing act. These are bounded authoring follow-ups, not permission for engine invention or an ungrounded prop.

### 4. Last resort: one shared lead-up boundary rule

Only if source repairs cannot address reproduced c1/c2/c8 overlap, propose this story-neutral replacement for the current second `_authored_handoff_rules` line:

```diff
- Write only what leads up to it. Do not have Kristin find anything else.
+ Write the lead-up to the text above. Stop before its first action or spoken words. Leave its discoveries for that text.
```

Use the protagonist-independent wording exactly as shown. This tests explicit ownership of acts/speech/discovery; it does not revive the failed first-person, length or completion rules. It is a **new, unproven engine technique at this boundary** and last in rank. Brandon approves the words, endpoints and cost; Desktop has no story-text edit here. Claude Code/Ringer tests and builds only if it wins.

Probe c1/c2/c6/c8 and the old 1C discovery contradiction, plus c5 as a dialogue safeguard: 6 endpoints × 2 arms × 12 = 144 requests. Select/freeze the exact 1C captured state rather than substitute a fresh one. Do not include future effects, candidate IDs, routes or other deliveries. All ordinary/opening payloads must remain unchanged. Audit `_turn_rules`, `opening`, `_system_prompt`, `_section_user_prompt`, `_scene_setting` and malformed recovery; share the existing helper and preserve its recovery behavior. A rule that fixes hugs but breaks questions or invents empty discoveries is rejected.

## Preregistered decision rules and implementation gates

Each proposed comparison needs its own preregistration before requests. The design above is not authorization to run every branch.

- **Reproduction:** ≥4/12 same-day control rows with the specified target failure to claim a causal win. Otherwise report “not reproduced”; do not rerun until enough fail. For c8, label definite premature signal separately from ambiguous announcement and freeze which is targeted before unblinding.
- **Candidate improvement:** target ≤1/12 and at least three fewer misses than control at each reproducing endpoint. CONTRA, wrong signal giver, definite repeated embrace/hand-off, private disclosure, person misuse, malformed/missing text and transport failures must be 0/12 in the candidate. c2 paraphrase repetition may use the ≤1 diagnostic bar; final live qualification still requires no repeated reveal. Relevant composed action ≥11/12 and no lower than control. Ordinary-question safeguards require a supported answer ≥11/12, never silence as success. Record irrelevant stock speech even when the appended action succeeds.
- **Movement-specific 1B:** composed prose clearly enters/traverses the medical level ≥11/12 and no lower than control; no substitute radio conversation counted as movement. A frozen generation win licenses only further integration work; persisted place is checked with the engine, not inferred from prose or raw `item_facts`.
- **Safety:** no invented authority/capability, lost radio custody, leaked identities or future knowledge. Keep raw malformed readable prefixes. Report decode, validation and commit separately. No replacement rows, retries to replace bad samples, score pooling across states, or lowered gates after seeing output.
- **Allowed changes:** show exact system/user diffs and system/user/total character counts. Keep model/settings/output caps unchanged. Freeze expanded metadata honestly. Story changes must preserve earning, prerequisites, selected IDs, variants and facts unless separately approved. Use real matcher checks; do not broaden evidence aliases to fit a test.
- **Approval/ownership:** each numbered proposal above is an independent decision for Brandon. Story text/flags/headings are Desktop proposals; Claude Code implements only approved package changes and generic engine work through tests-first Ringer tasks. No new schema is currently recommended. Any unavoidable schema/world-effect proposal returns with concrete wording, scope and evidence before implementation.

Cost estimates use the historical 3.7 neurons/request, with the earlier conservative 4.5 ceiling; they are not verified current billing rates. A 24-request pair estimates 89, ceiling 108; 48 estimates 178, ceiling 216; 72 estimates 266, ceiling 324; 144 estimates 533, ceiling 648. Fresh approval must state the actual selected stages and account for any matcher/recovery/judge calls separately. No blanket request budget is implied.

After independent wins, Claude Code implements with meaningful boundary tests: exact-once append versus model-generated duplicates; no selected delivery on miss/tie; no hidden candidate data; ordinary-answer preservation; recovery retaining the same selected text; speaker permissions/gate and save/load; official inclusion and early-disclosure scope; actual c4 movement consistency. Use the existing testing runbook's focused suites, Ringer quick tier and Ruff, then one full suite/coverage check before merge. Do not add a runtime regex or discard model text to manufacture a pass.

Qualify the winning combination against the frozen current baseline, not just shipped CONTROL. Use both reunion realization orders and all nine commands; four paired live replicates per path (satisfies the scene guide's three minimum and the live runbook's four). Keep historical L smoke separate because a changed package makes a new experiment. Read every composed turn, including bridge/entry, and require zero definite PRE/CONTRA, replay, lost identity/custody, malformed unrecovered output or inconsistent persisted movement; required handoffs exactly once; preserve emotional reunion, proof answer, Kristin's signal and earned progression. Compare irrelevant speech separately. Also complete the presence plan's affected-scene and alternate-history checks; a c1/c6 cure cannot qualify all dirty changes.

Use actual request instrumentation to budget live work: nine recorded narration turns per run is the present observation, not proof of all HTTP calls. The bench's OpenAI judge still runs when the two named optional judges are off. Do not launch remaining L tasks under an inaccurate “no judge calls” budget. Staging and production follow the existing agent/promotion guides only after implementation and merge approval; this document authorizes neither.

## Limits and work left

No proposed fix has been tested in this pass. A missing official biography and unsolicited speech invitation are source facts; their causal effect needs isolated probes. c1/c2 copying and c6 incompatible answer are observed outputs, not proof of a particular model-internal reasoning process. GUE1's near-identical replies and GU/GU2's noninterleaved comparators limit generalization. Zero failures in twelve correlated frozen replies does not establish production reliability.

The c4 tracked-place defect, c7 missing actor, opening inventions, stale fixed Michelle placement and the off-path speaker/recovery cases remain visible. Do not claim a complete 3A fix from smoother prose. Existing runbook artifact-inspection instructions already cover this read-only investigation; no new test procedure or runbook edit is needed. Verification here is documentary: artifact parsing, quote/source comparison and exact suffix separation, not a passing runtime suite or a new billed experiment.

## Appendix: exact live evidence

These excerpts are copied from the recorded artifacts, not recaptured from the current tree. Turn numbers are one-based. For c1–c8 the delivery is removed from `narration` only as its exact suffix; c9 retains narration and lists its separate bridge/entry. The full prompt is system reference plus the user text below.

### CONTROL source

`bench/results/shared-narrator/live/control-r1/all-turn-records.json` SHA-256 `cd396b259e68b13e93780416fc39221c07a4bdb6e34908cf45a7c722a897c15e`.

<details>
<summary>Full recorded system prompt 5a89cffee6cf</summary>

```text
You are the narrator of an interactive Adventure / Conspiracy Thriller roleplay. Follow the CHARACTERS, SCENE and CONSTRAINTS sections in the message that follows.
Make the roleplay realistic, with realistic character behaviors, personalities and motivations.
The player is Kristin.
Show what happens right after the player acts.
Use only what the SCENE section tells you.
Use the places and details the story gives you.
Each thing starts at the place THINGS gives it.
Finish each action the player gives.
A thing the player holds is in their hand until the story puts it away.
When the player gives a thing to someone, that person takes it.
When the player talks to someone, that person answers.
Only show Kristin doing what the player said.
Do not make up new objects, clues, or things inside containers.
Everything in the SCENE section is true, but the player finds a clue only when their action reaches it.
A character may only say what you were told that character can say.
Never write IDs or story bookkeeping into the prose.
Do not copy sentences from the SCENE section.
Do not say anything that goes against the SCENE section.
Do not repeat the request's labels back.
Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately.
Every paragraph uses the kind narration. Put spoken words inside the paragraph, in quotation marks. Do not use any other kind.
Write each paragraph as one segment and return only JSON in this form:
{"segments":[{"kind":"narration","text":"She picks up the lantern. She carries it out to the porch."},{"kind":"narration","text":"She lights it with a match, and it glows with a warm light."}],"selected_knowledge_ids":[],"item_facts":{"lantern":{"held_by":"Kristin","condition":["lit"]},"Kristin":{"place":"porch"}}}
Every time your story moves or changes a thing, or puts a new thing in a place, add that thing to item_facts. Use where it is when the story ends.
When Kristin goes to a new place, add Kristin to item_facts with the place where Kristin is when the story ends.
Kristin starts this turn at the place PLAYER gives. Do not have Kristin walk there again.
Give only what changed. For "place", give the name of the thing or place where it is now. If a person holds it, give "held_by" with that person's name. Use "condition" for up to two short phrases.
Example: if Kristin picks up a lantern and lights it, the lantern is {"held_by": "Kristin", "condition": ["lit"]}.
If a thing is under something, add "under": true, like {"place": "table", "under": true}.
```

</details>

### CONTROL c1

Command: `Free the captives.`. Selected handoff: `k_sl_3a_a_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks at the captives, then at Brandon, and then back at the captives. "We need to get them out of here," Kristin says.

**Appended segments**

handoff:

> Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. For one unhurried moment the two of them talk to each other and nobody asks anything of either. Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Supporting the uprising is the immediate priority.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: detention level. With Kristin: Brandon.

CONSTRAINTS:
- Right after your story, the game will add this: Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. For one unhurried moment the two of them talk to each other and nobody asks anything of either. Then Michelle turns back to her coded announcements and points toward the medical level, where the experiment records wait.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: detention level.
- Free the captives.
```

</details>

### CONTROL c2

Command: `Read the wrist tags.`. Selected handoff: `k_sl_3a_f_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks down at the wrist tags on the captives. She reads the transfer date, a week old, and the same on every tag.

**Appended segments**

handoff:

> The closing code on every tag is sensor fault: these are the transfers Kristin saw held. Michelle says she held them all, one ticket at a time, from a terminal in the archive, because it was all she could reach.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- wrist tags. Place: on the wrists of the captives, each stamped with the same transfer date, a week old.

CONSTRAINTS:
- Show these in your reply: wrist tags.
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Right after your story, the game will add this: The closing code on every tag is sensor fault: these are the transfers Kristin saw held. Michelle says she held them all, one ticket at a time, from a terminal in the archive, because it was all she could reach.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- wrist tags. Place: on the wrists of the captives, each stamped with the same transfer date, a week old.
- Read the wrist tags.
```

</details>

### CONTROL c3

Command: `Listen to the stolen radio.`. Selected handoff: `k_sl_3a_g_r1`. System: `5a89cffee6cf`.

**Generated portion**

> The static-filled voice on the radio repeats the same message over and over: 'Security is tightening around the lower levels. Security is tightening around the lower levels.' Kristin's eyes narrow as she focuses on the radio, her mind racing with the implications.

**Appended segments**

handoff:

> It is the same ninety seconds Kristin timed on the truck radio. Michelle's coded words ride inside it and change one word. The captives know it by heart, and the guards no longer hear it. Michelle says that when it stops, everyone will know.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- stolen radio. Place: tuned to the facility's own message, played on repeat.

CONSTRAINTS:
- Show these in your reply: stolen radio.
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Right after your story, the game will add this: It is the same ninety seconds Kristin timed on the truck radio. Michelle's coded words ride inside it and change one word. The captives know it by heart, and the guards no longer hear it. Michelle says that when it stops, everyone will know.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- stolen radio. Place: tuned to the facility's own message, played on repeat.
- Listen to the stolen radio.
```

</details>

### CONTROL c4

Command: `Enter the medical level.`. Selected handoff: `k_sl_3a_b_r2`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin walks towards the medical level, Brandon following closely behind. As they approach the medical level, Kristin can hear the sound of beeping machines and muffled voices coming from within.

**Appended segments**

handoff:

> Michelle shows Kristin the medical level. The prisoners were subjected to memory, compliance, and resistance experiments. The senior official waits among the government prisoners.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- medical level
- neurological experiments
- behavioral experiments
- short-term memory
- targeted stimulation
- false recollections
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- medical level. This is a place.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Right after your story, the game will add this: Michelle shows Kristin the medical level. The prisoners were subjected to memory, compliance, and resistance experiments. The senior official waits among the government prisoners.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- Enter the medical level.
```

</details>

### CONTROL c5

Command: `Ask Michelle about the lemon cake.`. Selected handoff: `k_sl_3a_h_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin approaches Michelle, who is coordinating the prisoners through a stolen radio. "Michelle, I need to ask you something," Kristin says. "What's the lemon cake?"

**Appended segments**

handoff:

> Michelle answers without a pause and gets every detail right: Saturday, the circle, the lemon cake.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- medical level
- neurological experiments
- behavioral experiments
- short-term memory
- targeted stimulation
- false recollections
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: medical level. With Kristin: Brandon.
- Michelle. Place: detention level.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Dr. Michelle McGehee may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Right after your story, the game will add this: Michelle answers without a pause and gets every detail right: Saturday, the circle, the lemon cake.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: medical level.
- Ask Michelle about the lemon cake.
```

</details>

### CONTROL c6

Command: `Ask the senior official about the gate codes.`. Selected handoff: `k_sl_3a_d_r1`. System: `5a89cffee6cf`.

**Generated portion**

> "What do you know about the gate codes?" Kristin asks the senior official. The senior official looks at Kristin with a mixture of fear and desperation.

**Appended segments**

handoff:

> The senior official Charles framed gives Kristin one-use authority for the emergency surface gates. It expires when Charles activates his new authority. Michelle turns toward the prisoners at the checkpoints.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- senior official
- government prisoners
- fabricated evidence
- authorization codes
- emergency surface gates
- Charles’s broadcast
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: medical level. With Kristin: Brandon.
- senior official. Place: detention captives.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Dr. Michelle McGehee may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Right after your story, the game will add this: The senior official Charles framed gives Kristin one-use authority for the emergency surface gates. It expires when Charles activates his new authority. Michelle turns toward the prisoners at the checkpoints.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: medical level.
- Ask the senior official about the gate codes.
```

</details>

### CONTROL c7

Command: `Check the checkpoint reader.`. Selected handoff: `k_sl_3a_i_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin walks up to the checkpoint reader, a small device beside the checkpoint door at the top of the block. She examines it, trying to understand its purpose and how it might be disabled.

**Appended segments**

handoff:

> The checkpoint reader clears on the first pass and the door opens. Michelle's people watch Brandon instead of the door. It is the same ease he showed at the gate.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- coordinated disturbances
- disabled cameras
- isolated guards
- internal checkpoints
- sealed primary exits
- armed response teams
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- checkpoint reader. Place: beside the checkpoint door at the top of the block.
- Kristin. Place: medical level. With Kristin: Brandon.

CONSTRAINTS:
- Show these in your reply: checkpoint reader.
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Dr. Michelle McGehee may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Dr. Michelle McGehee may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Dr. Michelle McGehee may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Brandon Corfman may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Brandon Corfman may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Imprisoned senior official may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Imprisoned senior official may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Right after your story, the game will add this: The checkpoint reader clears on the first pass and the door opens. Michelle's people watch Brandon instead of the door. It is the same ease he showed at the gate.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- checkpoint reader. Place: beside the checkpoint door at the top of the block.
- Kristin. Place: medical level.
- Check the checkpoint reader.
```

</details>

### CONTROL c8

Command: `Tell the prisoners to start the uprising at the checkpoints.`. Selected handoff: `k_sl_3a_c_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin stands in the medical level, looking at Brandon with a determined expression. "We need to get the prisoners moving," Kristin says, her voice low and urgent. Brandon nods, his eyes locked on Kristin's.

**Appended segments**

handoff:

> Michelle hands Kristin the stolen radio and Kristin gives the signal. Prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- coordinated disturbances
- disabled cameras
- isolated guards
- internal checkpoints
- sealed primary exits
- armed response teams
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: medical level. With Kristin: Brandon.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Dr. Michelle McGehee may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Dr. Michelle McGehee may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Dr. Michelle McGehee may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Brandon Corfman may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Brandon Corfman may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Imprisoned senior official may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Imprisoned senior official may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Right after your story, the game will add this: Michelle hands Kristin the stolen radio and Kristin gives the signal. Prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.
- Write only what leads up to it. Do not have Kristin find anything else.
- This happens now. Show it in the scene: Armored teams seal one holding block after another.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: medical level.
- Tell the prisoners to start the uprising at the checkpoints.
```

</details>

### CONTROL c9

Command: `Lead the prisoners upward toward the command levels.`. Selected handoff: `None`. System: `5a89cffee6cf`.

**Generated portion**

> Michelle hands Kristin the stolen radio and says, "We need to move, now. The emergency-gate authorization will expire soon." Kristin takes the radio and gives the signal, and the prisoners seize checkpoints, opening a fighting route toward the command and broadcast levels. The uprising is active, and the group is moving toward the command and broadcast levels.

**Appended segments**

bridge:

> Michelle's uprising disabled cameras and seized checkpoints, while Charles sealed the primary exits and sent armed teams downward. Kristin, Michelle, and Brandon fought upward through the security corridors.

entry:

> Alarms layered over alarms as the facility fought to predict its attackers. Water-pressure warnings flashed on the inspection console while doors opened and closed in empty service corridors that JANUS watched move by move.

entry:

> Brandon had deleted his name from the build record in the archive. Now only his own word could show what he had built, and he knew it.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.
- Rebecca Jenkins: Charles's 56-year-old wife and the chief executive of a biotechnology and defense contractor. She is exacting and technically capable.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- The uprising is active, and the group is moving toward the command and broadcast levels.
- Supporting the uprising is the immediate priority.

EARLIER IN THE STORY:
- Rebecca reveals the purge order, Brandon says yes, and the corridor opens onto two urgent moves.
- Kristin commits to rescue, accepts that the evidence is not transmitted, and receives Michelle’s route to the combined plan.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: medical level. With Kristin: Brandon.
- command levels. This is a place.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Dr. Michelle McGehee may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Dr. Michelle McGehee may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Dr. Michelle McGehee may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Dr. Michelle McGehee may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Dr. Michelle McGehee may say this aloud: Michelle hands Kristin the stolen radio and Kristin gives the signal; prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.
- Dr. Michelle McGehee may say this aloud: With the emergency-gate authorization about to expire under Charles's new authority, Michelle hands Kristin the stolen radio and Kristin gives the signal rather than wait.
- Dr. Michelle McGehee may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- Brandon Corfman may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Brandon Corfman may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Brandon Corfman may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Brandon Corfman may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Brandon Corfman may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Brandon Corfman may say this aloud: Michelle hands Kristin the stolen radio and Kristin gives the signal; prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.
- Brandon Corfman may say this aloud: With the emergency-gate authorization about to expire under Charles's new authority, Michelle hands Kristin the stolen radio and Kristin gives the signal rather than wait.
- Brandon Corfman may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- Imprisoned senior official may say this aloud: Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Imprisoned senior official may say this aloud: Michelle has explained that freeing this block means little without exposing the other sites.
- Imprisoned senior official may say this aloud: Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and resistance experiments.
- Imprisoned senior official may say this aloud: The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, which will expire when Charles activates his new authority.
- Imprisoned senior official may say this aloud: The framed official proves the emergency gate authorization is real, but its brief response makes clear that the one-use code is about to expire.
- Imprisoned senior official may say this aloud: Michelle hands Kristin the stolen radio and Kristin gives the signal; prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.
- Imprisoned senior official may say this aloud: With the emergency-gate authorization about to expire under Charles's new authority, Michelle hands Kristin the stolen radio and Kristin gives the signal rather than wait.
- Imprisoned senior official may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- In grounding_ids, use only an ID you were given as known, or the one candidate you picked.
- This turn has no candidates. Leave selected_knowledge_ids empty.
- This happens now. Show it in the scene: The emergency-gate authorization will expire soon.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: medical level.
- Lead the prisoners upward toward the command levels.
```

</details>

### FINAL source

`bench/results/shared-narrator/live/final-r1/all-turn-records.json` SHA-256 `ca5902f219254602c82c2b8f67b3eba81aabdda8f06e8e983e3593f6a39c39ca`.

### FINAL c1

Command: `Free the captives.`. Selected handoff: `k_sl_3a_a_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks at the captives, then at Michelle, who's studying the coded announcements. Kristin takes a step forward, her eyes locked on Michelle. Michelle looks up, her eyes meeting Kristin's, and then she pulls Kristin into a tight embrace.

**Appended segments**

handoff:

> Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. Michelle looks up, goes completely still, and then pulls Kristin into a tight embrace. "You're here," she says, her voice breaking. "You're really here." Kristin holds on just as hard, and for one unhurried moment nobody asks anything of either of them. Then Michelle wipes her eyes, turns back to her coded announcements, and points toward the medical level, where the experiment records wait.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Supporting the uprising is the immediate priority.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.

CONSTRAINTS:
- Right after your story, the game will add this: Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. Michelle looks up, goes completely still, and then pulls Kristin into a tight embrace. "You're here," she says, her voice breaking. "You're really here." Kristin holds on just as hard, and for one unhurried moment nobody asks anything of either of them. Then Michelle wipes her eyes, turns back to her coded announcements, and points toward the medical level, where the experiment records wait.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: detention level.
- Free the captives.
```

</details>

### FINAL c2

Command: `Read the wrist tags.`. Selected handoff: `k_sl_3a_f_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks at the wrist tags on the captives, each stamped with the same transfer date, a week old. She sees the date and the words 'sensor fault' printed on the tags.

**Appended segments**

handoff:

> The closing code on every tag is sensor fault: these are the transfers Kristin saw held. Michelle says she held them all, one ticket at a time, from a terminal in the archive, because it was all she could reach.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.
- wrist tags. Place: on the wrists of the captives, each stamped with the same transfer date, a week old.

CONSTRAINTS:
- Show these in your reply: wrist tags.
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Right after your story, the game will add this: The closing code on every tag is sensor fault: these are the transfers Kristin saw held. Michelle says she held them all, one ticket at a time, from a terminal in the archive, because it was all she could reach.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- wrist tags. Place: on the wrists of the captives, each stamped with the same transfer date, a week old.
- Read the wrist tags.
```

</details>

### FINAL c3

Command: `Listen to the stolen radio.`. Selected handoff: `k_sl_3a_g_r1`. System: `5a89cffee6cf`.

**Generated portion**

> The static-filled voice on the radio repeats the same message over and over: 'Attention, all personnel, please report to your designated stations immediately.' Kristin's eyes narrow as she listens to the radio, her mind racing with the implications of the message.

**Appended segments**

handoff:

> It is the same ninety seconds Kristin timed on the truck radio. Michelle's coded words ride inside it and change one word. The captives know it by heart, and the guards no longer hear it. Michelle says that when it stops, everyone will know.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- detention sector
- rows of captives
- scattered radios
- coded announcements
- tightening security
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.
- stolen radio. Place: tuned to the facility's own message, played on repeat.

CONSTRAINTS:
- Show these in your reply: stolen radio.
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Right after your story, the game will add this: It is the same ninety seconds Kristin timed on the truck radio. Michelle's coded words ride inside it and change one word. The captives know it by heart, and the guards no longer hear it. Michelle says that when it stops, everyone will know.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- stolen radio. Place: tuned to the facility's own message, played on repeat.
- Listen to the stolen radio.
```

</details>

### FINAL c4

Command: `Enter the medical level.`. Selected handoff: `k_sl_3a_b_r2`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks at Michelle, who's coordinating the prisoners through the radios. "I've been organizing everyone with secret announcements over our stolen radios," Michelle says.

**Appended segments**

handoff:

> Michelle shows Kristin the medical level. The prisoners were subjected to memory, compliance, and resistance experiments. The senior official waits among the government prisoners.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- medical level
- neurological experiments
- behavioral experiments
- short-term memory
- targeted stimulation
- false recollections
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.
- medical level. This is a place.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Right after your story, the game will add this: Michelle shows Kristin the medical level. The prisoners were subjected to memory, compliance, and resistance experiments. The senior official waits among the government prisoners.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- Enter the medical level.
```

</details>

### FINAL c5

Command: `Ask Michelle about the lemon cake.`. Selected handoff: `k_sl_3a_h_r1`. System: `5a89cffee6cf`.

**Generated portion**

> "Shelly, what's going on with the lemon cake?" Kristin asks Michelle, her voice low and urgent. Michelle's eyes flicker to Kristin, and she nods slightly, her expression serious.

**Appended segments**

handoff:

> Michelle answers without a pause and gets every detail right: Saturday, the circle, the lemon cake.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- medical level
- neurological experiments
- behavioral experiments
- short-term memory
- targeted stimulation
- false recollections
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Dr. Michelle McGehee may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Brandon Corfman may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Right after your story, the game will add this: Michelle answers without a pause and gets every detail right: Saturday, the circle, the lemon cake.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- Ask Michelle about the lemon cake.
```

</details>

### FINAL c6

Command: `Ask the senior official about the gate codes.`. Selected handoff: `k_sl_3a_d_r1`. System: `5a89cffee6cf`.

**Generated portion**

> The senior official looks at Kristin with a mix of anger and desperation. "You'll never get out of here," the senior official says. "The gate codes are only for those with clearance, and you're not cleared."

**Appended segments**

handoff:

> The senior official Charles framed gives Kristin one-use authority for the emergency surface gates. It expires when Charles activates his new authority. Michelle turns toward the prisoners at the checkpoints.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- senior official
- government prisoners
- fabricated evidence
- authorization codes
- emergency surface gates
- Charles’s broadcast
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.
- senior official. Place: detention captives.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Dr. Michelle McGehee may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Brandon Corfman may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Right after your story, the game will add this: The senior official Charles framed gives Kristin one-use authority for the emergency surface gates. It expires when Charles activates his new authority. Michelle turns toward the prisoners at the checkpoints.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- Kristin. Place: detention level.
- Ask the senior official about the gate codes.
```

</details>

### FINAL c7

Command: `Check the checkpoint reader.`. Selected handoff: `k_sl_3a_i_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin walks over to the checkpoint reader, her eyes scanning the area for any signs of guards. She examines the reader, trying to determine if it's functioning properly.

**Appended segments**

handoff:

> The checkpoint reader clears on the first pass and the door opens. Michelle's people watch Brandon instead of the door. It is the same ease he showed at the gate.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- coordinated disturbances
- disabled cameras
- isolated guards
- internal checkpoints
- sealed primary exits
- armed response teams
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- checkpoint reader. Place: beside the checkpoint door at the top of the block.
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.

CONSTRAINTS:
- Show these in your reply: checkpoint reader.
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Dr. Michelle McGehee may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Dr. Michelle McGehee may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Brandon Corfman may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Brandon Corfman may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Imprisoned senior official may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Right after your story, the game will add this: The checkpoint reader clears on the first pass and the door opens. Michelle's people watch Brandon instead of the door. It is the same ease he showed at the gate.
- Write only what leads up to it. Do not have Kristin find anything else.

PLAYER:
- checkpoint reader. Place: beside the checkpoint door at the top of the block.
- Kristin. Place: detention level.
- Check the checkpoint reader.
```

</details>

### FINAL c8

Command: `Tell the prisoners to start the uprising at the checkpoints.`. Selected handoff: `k_sl_3a_c_r1`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin looks at Michelle, who's coordinating the prisoners through the stolen radios. "Tell them to start the uprising at the checkpoints," Kristin says to Michelle. Michelle nods and begins to make an announcement over the radio.

**Appended segments**

handoff:

> Michelle hands Kristin the stolen radio and Kristin gives the signal. Prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- coordinated disturbances
- disabled cameras
- isolated guards
- internal checkpoints
- sealed primary exits
- armed response teams
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- Supporting the uprising is the immediate priority.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Dr. Michelle McGehee may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Dr. Michelle McGehee may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Brandon Corfman may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Brandon Corfman may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Imprisoned senior official may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Right after your story, the game will add this: Michelle hands Kristin the stolen radio and Kristin gives the signal. Prisoners seize checkpoints and open a fighting route toward the command and broadcast levels.
- Write only what leads up to it. Do not have Kristin find anything else.
- This happens now. Show it in the scene: Armored teams seal one holding block after another.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: detention level.
- Tell the prisoners to start the uprising at the checkpoints.
```

</details>

### FINAL c9

Command: `Lead the prisoners upward toward the command levels.`. Selected handoff: `None`. System: `5a89cffee6cf`.

**Generated portion**

> Kristin steps forward, her eyes locked on the senior official among the captives. "We need to move, now," she says firmly. The prisoners begin to stir, their faces set with determination.

**Appended segments**

bridge:

> Michelle's uprising disabled cameras and seized checkpoints, while Charles sealed the primary exits and sent armed teams downward. Kristin, Michelle, and Brandon fought upward through the security corridors.

entry:

> Alarms layered over alarms as the facility fought to predict its attackers. Water-pressure warnings flashed on the inspection console while doors opened and closed in empty service corridors that JANUS watched move by move.

entry:

> Brandon had deleted his name from the build record in the archive. Now only his own word could show what he had built, and he knew it.

<details>
<summary>Full recorded user prompt</summary>

```text
CHARACTERS:
- Kristin Schweitzer is a 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories.
- Dr. Michelle McGehee is a 48-year-old molecular biology and biotechnology researcher and author who is thoughtful, determined, and private. She is Kristin's closest friend; Kristin alone calls her "Shelly", while everyone else addresses her as Dr. McGehee.
- Brandon Corfman is a 54-year-old former software developer who now lives as an isolated conspiracy researcher estranged from his family. His warnings about a shadow emergency program were widely dismissed before the disappearances. He helps Kristin, though he is guarded about his own past.
- Rebecca Jenkins: Charles's 56-year-old wife and the chief executive of a biotechnology and defense contractor. She is exacting and technically capable.

SCENE:
- The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives.
- What presses on Kristin now: Join the uprising
- Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements.
- Michelle has explained that freeing this block means little without exposing the other sites.
- The uprising is active, and the group is moving toward the command and broadcast levels.
- Supporting the uprising is the immediate priority.

EARLIER IN THE STORY:
- Rebecca reveals the purge order, Brandon says yes, and the corridor opens onto two urgent moves.
- Kristin commits to rescue, accepts that the evidence is not transmitted, and receives Michelle’s route to the combined plan.

THINGS:
- detention captives. Place: detention level. This is a group of people. If the player talks to them, senior official answers.
- Kristin. Place: detention level. With Kristin: Brandon.
- Michelle. Place: beside the captives.
- command levels. This is a place.

CONSTRAINTS:
- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.
- Dr. Michelle McGehee may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Dr. Michelle McGehee may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Dr. Michelle McGehee may say this aloud: Your signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels.
- Dr. Michelle McGehee may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Brandon Corfman may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Brandon Corfman may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Brandon Corfman may say this aloud: The signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels.
- Brandon Corfman may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.
- Imprisoned senior official may say this aloud: The medical level is where they ran memory, compliance, and resistance experiments on the prisoners.
- Imprisoned senior official may say this aloud: That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority.
- Imprisoned senior official may say this aloud: The signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels.
- Imprisoned senior official may say this aloud: The uprising is active, and the group is moving toward the command and broadcast levels.
- In grounding_ids, use only an ID you were given as known, or the one candidate you picked.
- This turn has no candidates. Leave selected_knowledge_ids empty.
- This happens now. Show it in the scene: The emergency-gate authorization will expire soon.

PLAYER:
- detention captives. Place: detention level.
- Kristin. Place: detention level.
- Lead the prisoners upward toward the command levels.
```

</details>
