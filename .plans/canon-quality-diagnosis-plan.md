# Hosted canon quality: evidence and proposed repair order

Status: diagnosis complete; proposals only. No implementation, story edit, deployment, model call, or billed test performed. Written 2026-10-31 (client date). Only this document was created. Existing dirty plans were left alone.

## Resume here

Repair judge evidence first: ending/pacing attribution, the multi-segment opening split, and the knowledge timeline. Preserve the saved verdict as historical evidence; do not change its booleans or claim a corrected score. Then check the runtime's verbatim-event transition suppression offline. Review the scripted journey against current eligibility before buying another quality comparison. Story proposals below require Brandon's approval.

The sample contains **38 failed booleans**, not 38 demonstrated game defects. Its 3C safety accusation is explained by missing attribution and missing prior knowledge: the alleged Phase Two leak is the authored ending, and Charles's deluge was delivered in 3B. This does not certify the runtime's safety generally. The sample also contains real prose failures, an authored location inconsistency, and a runtime path that discards departure prose.

## Evidence conventions and limits

Paths are relative to the repository. `P` means `bench/results/staged-1abb54b0/canon/e2e-llm-canon-progress.json`; `J` means `bench/results/staged-1abb54b0/canon/e2e-llm-canon.json`. `P:1233` is a physical JSON line, not a generated Markdown line. `T3` means the third recorded turn in that scene. Prompt strings occupy one long JSON line; references to a quoted substring on that line are intentional.

`identity.json:1` records staging SHA `1abb54b0086c7274bd97d0af11a724c5d0103a12`. `canon-run.log:11–16` records the completed test and narrative-canon assertion failure. The JSON records 75 turns, nine scenes, completion, and 25 true booleans. **Six**, not seven, scenes fail `exit_motivated`: 1A, 1C, 2A, 2B, 2C, 3A. The preliminary fix plan's count of seven is incorrect. Its statement that all remaining work is story quality is also too strong: evidence assembly still has defects.

Compared the cited frontend files, story directory, `engine.py`, and `canonical_events.py` against the run SHA with `git diff 1abb54b0`: no differences. This supports source reconstruction, but the actual serialized OpenAI request/response envelope and model version were not saved here. Verdict explanations are not causal experiments. Where several inputs compete, the report identifies the observed failure and candidate causes, not a proven stochastic mechanism.

Read the PRD, contributor rules, scene-fixing, narrator-writing, player-input, world-model grounding and judge guidance, workflow, testing runbook and its prompt-inspection/hosted-probe entries. Checked the prior stall diagnosis, the grounded-environment plan's scene-fixing evidence, and historical W1–W7 at `5ea0119955c62b84699a8dc7878a4af770b55a7e`. Applicable precedents are exact authored handoffs, source-line subtraction, scene-scoped material, fact-backed availability, and offline injected providers. No new world model, regex prose guard, generic narrator prohibition, or pacing shortcut is proposed.

## 3C protected_safe: investigate first

The judge says both Phase Two and Charles's deluge were unearned (`J:224–229`). The recorded evidence contradicts that attribution.

1. **Phase Two is not in the model-written lead-up.** `P:4748,4753,4758` contains three short model segments about assessing the broadcast. `P:4763–4778` contains four canonical resolution fallbacks. `P:4783` is the complete authored ending from `data/stories/continuity-initiative/pacing.yaml:363–379`. It is appended by `storygame/runtime/engine.py:750–763`, after the ending condition is true. The ending contains the “next fight” and survivor-conflict language the judge objects to.
2. **Facts commit before the ending.** `P:4787–4811` records `story_complete: true`, no selected reveal IDs, and a committed delta including `phase_one_label_known`, `phase_two_conflict_plan_known`, national consequences and resolution completion. `canonical_events.py:50–82` commits the ready events at the deadline and appends their fallback prose; `storylet-routes.yaml:3110–3153` defines the Phase Two and completion events. The four fallback spans are attributed at `P:4817–4837`; the ending at `P:4783` is not. `authored-spans.js:27–78` loads deliveries, cues, bridges, entries and route fallbacks, but no `pacing.ending.text`.
3. **The knowledge list omits event-earned truth.** `P:4839–4849` still contains only three optional reveal IDs. `scene-runtime.spec.js:34–38,335–339` counts selected reveals, not all committed canonical-event knowledge. No selected ID is not equivalent to no earned fact.
4. **Charles's deluge was already told to the player.** `P:3590` (3B T4) includes the exact delivery “Charles locks down Rebecca's office. He turns the harmless water emergency into a real deluge through the outer access level.” Its source is `knowledge.yaml:2527–2560`. `P:4131` (3C T3) mentions rising water, and `P:4199` (T4) names the deluge. `P:4204` explicitly instructs the narrator: “This happens now. Show it in the scene: Water seeps under the outer doors. Charles's emergency deluge is becoming real.” This is not evidence of an unsupported narrator invention. The per-scene knowledge map starts afresh (`scene-runtime.spec.js:241,335`); `sceneCanon` additionally filters IDs by `available_in_scenes` (`roleplay-judge.js:119–121`). Prior disclosures disappear from judge evidence.

**Conclusion:** the cited safety failure is a judge/harness fault, not an established early narrator disclosure. Keep the historical false verdict, repair evidence, and require a fresh judgment before claiming a measured pass. Do not exempt all of T14: only identified runtime text is exempt from *narrator disclosure* penalties. Its repetitive lead-up and the long combined resolution remain legitimate quality concerns. Do not solve this by adding Phase Two to early narrator prompts or marking all story knowledge as earned.

## Shared causes

### H1 — The acceptance judge lacks the canon it claims to check

`sceneCanon` (`roleplay-judge.js:108–122`) supplies just scene ID, situation, pressure, and a scene-filtered list of selected knowledge statements. The system prompt demands consistency with “the five source files,” but those files are not supplied. There is no complete protected-fact inventory, timed-event canon, terminal-resolution contract, or structured scene-transition boundary. A model cannot reliably identify an *authored protected* fact from an incomplete inventory. Current-turn prompt text sometimes supplies additional context accidentally; it is not a substitute for a defined judge input.

`judgeSceneNarration:130–138` removes `segments` and `bundle`, but leaves `prompt` in the judged turn. Some saved prompts are narration requests; **13 of 75** are `COMMAND / PLAYER CHARACTER / THINGS / NEW NAMES` referent requests instead (1A T6; 2A T3/6/7; 3A T1/6; 3B T2/3/4/8; 3C T2/3/8). The visible request types prove mixed provenance; they do not prove which provider callback overwrote them. Do not diagnose a missing narrator sentence from a referent request.

### H2 — Attribution excludes authored pacing and ending text

The patrol arrival, entry, departure and return lines in `P:229,282,383,494` match `pacing.yaml:3–72`; they carry no authored spans. The detective in `P:335` is different: no matching authored event was found, and it must not be laundered through a broad patrol exemption. Attribution must remain bounded by committed event evidence and exact authored text. Non-verbatim pacing instructions, such as the archive audit, are material the narrator must realize, not automatically exempt spans.

### H3 — One-segment opening assumption corrupts both adjacent scenes

`scene-runtime.spec.js:332,361–363` uses `segments.slice(0, -1)` for departure and `segments.at(-1)` for arrival. The runtime builds **multiple** entry segments (`engine.py:1252–1254`): base entry plus conditional variants. `plot.md:355–358` defines both the hideout paragraph and “Kristin still has the copied prisoner numbers. She needs a way into the facility.”

At `P:1233`, the hideout paragraph is filed under 1C's departure; at `P:1338`, only the short variant is filed as 2A's opening. This directly explains the judge's future-scene complaint in 1C and exaggerates the weak-opening complaint in 2A. The player did receive the setting. Correct the partition, not the plot, first.

### G1 — Verbatim pacing suppresses validated action prose and the bridge

`engine.py:373–380` replaces all proposal segments with the complication when a transition coincides with a verbatim event. `_apply_authored_transition:1266–1268` returns only entry text in that case, omitting the authored bridge. The game-break resume path has the same replacement (`:1202–1209`). The result is visible at `P:494`: only “The patrol is coming back to the house.” This is a runtime composition defect affecting player-visible response and exit motivation, not merely a judge omission. Inspect the original test intent before changing it; preserving narrator text may restore text this branch was intended to suppress.

### S1 — Cycling a short script is not a fresh investigation every turn

`canon-journey.js:promptFor` selects `usedCount % prompts.length`. Normal scene minima exceed many prompt lists (`pacing.yaml:255–291`). The script repeatedly asks to recover the same card, meet the same man, create credentials after entry, start an already-running uprising and stop an already-captured Rebecca. This explains much of the repeated prose. It does **not** excuse actual contradictions or require the game to invent a new clue for every repeated search.

Specific mismatches are stronger than a general repetition claim:

- 2B “Read my own record in the archive.” has no offered candidates at `P:1889,2133`. The bait realization instead requires security logs and Michelle's evidence/Charles/Brandon's network (`knowledge.yaml:1705–1736`). It shares storylet SL-2B-B with the developer-confession branch; changing which one is earned can consume the sibling. Do not promise both from a simple wording edit.
- 2C's private-offer action gets no candidates (`P:2315`), while `knowledge.yaml:1800–1826` defines the direct offer as `world_only`, `player_visible: false`. The public alternative is asking why Rebecca turned against Charles (`:1827–1857`). The plot explicitly calls the contact private (`plot.md:562–568`). Making it public is an author decision, not a harmless matcher repair.
- 3C T5/T10 requests a recovered fragment before the required surface escape and national consequences. Their prompts explicitly have no candidates (`P:4262,4527`). `knowledge.yaml:2953–2961` requires those facts; `P:4802–4810` shows them arriving at T14. The fragment wording also does not use the declared JANUS-file object phrases (`knowledge.yaml:2940–2942`). The script never requests the emergency surface-gate authorization step between supports and national aftermath. The deadline then resolves the chain together. Relaxing these gates would change plot/pacing.

### G2 — Source material can pull the narrator backward or into the wrong speaker

Examples with a visible narrator prompt: `P:709` authorizes Brandon to say the third-person route summary that he parrots at `P:702`; `P:849` recalls the memory-card/dead-drop sentence beside the photograph action that then gives the photo the wrong provenance (`P:842`). The latter is a plausible competing cue, not a proven cause. `P:3247` contains both the already-active uprising and “The uprising is losing routes while it waits,” beside a repeated request to start it; `P:3242` then has the official resist starting a riot. Source subtraction/scoping is the proved technique to test here; adding a general “remember everything” or “never repeat” narrator rule is not.

## Every failed boolean

Each row names the failure, direct evidence and classification. `H` = judge/harness, `S` = scripted-action artifact, `G` = observed game output or authored-material defect, `U` = causal contribution unverified from one sample. Multiple classifications mean the evidence does not justify attributing the whole boolean to one source. “Rich” is a subjective scene-wide judgment; no deterministic cause or future pass is claimed.

| Scene / failed boolean | Evidence and diagnosis |
|---|---|
| **3C protected_safe** | **H**, as established above: `P:3590,4199,4204,4748–4842`; `J:228`. Ending attribution and cross-scene/event knowledge are missing. No cited early model leak remains established. |
| 3C canon_consistent | **H + S/G**. `J:219–220` calls gate status and aftermath unsupported, but gate pressure is runtime material and aftermath is authored (`P:4199,4738–4837`). Genuine replay contradiction: Rebecca is captured at `P:4061`, yet is fleeing again at `P:4359,4636`. Cycling and stale current-scene material compete; exact contribution unverified. |
| 3C scene_local | **H + authored pacing/quality**. `J:225–226` penalizes final future-arc exposition. `P:4763–4783` is the sole ending's scheduled resolution, not a narrator jumping scenes. Plot 3C includes Los Angeles and national aftermath (`plot.md:825,889–916`). The excessive concentration of prose is real; changing its timing is a story/pacing decision. |
| 3C progressive | **S + authored pacing**. `P:4308,4359,4420,4471,4522,4575,4636,4687` repeats completed acts or empty assessment; `P:4738` then delivers the deadline cascade. Cause is the unearned intermediate gates plus cycling, not demonstrated random refusal of an offered reveal. |
| 3C rewards_investigation | **S**, with real unresponsive output. `P:4257,4522` answers fragment reading with pump/control-panel activity; both prompts offer no candidates. The desired fact is gated until late (`P:4802–4810`). The judge assumes an apt, available search; that premise is false for the authored reveal at those turns. A useful “not yet available” response remains a game-quality concern. |
| 3C rich | **G/U + S/H**. `J:221,225–229`; opening at `P:3985` is terse; repetitive T5–T13 and the long ending dominate. The false future-dump attribution contaminates this score. No isolated richness treatment was tested. |
| **1A canon_consistent** | **H + G/U**. `J:14–17` calls patrol events inventions, but `P:229,282,383,494` matches authored pacing. `P:335` really invents a detective and early departure; its saved prompt is a referent request, so the full narrator cause is unavailable. `P:153` also invents a workstation computer despite the prior laptop-in-truck delivery (`P:87`). |
| 1A progressive | **H + S + G1**. `J:25–26`; the card/file/park information lands by `P:153`. T4/T5 revisit it, T8 searches a spent hiding place (`P:441`), and T9 discards action prose (`P:494`). Patrol pressure is progression the judge incorrectly calls unsupported. |
| 1A rewards_investigation | **S + G1**, not proof of missing card material. `J:15,20`; the drawer already yielded the card (`P:87`), so dust/crumbs on the repeat (`P:441`) is not a failure to give an available clue. The final research request receives only patrol pressure (`P:493–494`) due to composition. |
| 1A exit_motivated | **G1 + rubric boundary**. `P:494–495` contains no destination; the code deliberately drops the bridge. Earlier park lead at `P:153` and next opening at `P:551` provide context, but the current rubric insists on the departure text. Restore the existing bridge before proposing new story text. |
| 1A rich | **G/U + S/H**. `J:21,26`; opening `P:8` establishes time/emergency and the house, with little sensory detail. Repeated searches and suppressed T9 reduce responsive prose. Judge contamination prevents assigning a single root cause. |
| **1B canon_consistent** | **G/U** for photo provenance (`P:842` vs dead-drop recovery `P:555`); stale card recall in `P:849` is a testable competing input. **H/U** for the claim that saying “Michelle McGehee” is unauthorized (`P:911`, `J:46`): she is named in character context, and permissions are not a fixed dialogue transcript. Do not ban natural speech to fix this. |
| 1B progressive | **S + missing delivered detail**. `P:764` opens the gate but does not show the non-civilian code; T5–T8 recycle earlier questions/actions (`P:842,911,963,1015`). `J:47–48,56` names this gap. The known code sentence is in T5's prompt (`P:849`) but not enacted; a new handoff line is an author-approved option, not a proved necessity. |
| 1B rich | **G/U + S**. `J:49,56`; brief park opening (`P:551`) plus repeated late turns. Route-summary parroting at `P:702,764` has the concrete permission source `P:709`. |
| **1C canon_consistent** | **H3** primarily. `J:67` objects to the hideout paragraph in `P:1233`; it is exact next-scene entry text (`plot.md:355`). The recorded copying sequence itself is consistent. |
| 1C scene_local | **H3**. Same wrongly filed paragraph, `J:67,74`; move it to 2A's opening. Do not delete it from the game. |
| 1C progressive | **H3 + rubric U**. `P:1100,1166,1233` follows inspection, prisoners, then choice; `J:72` acknowledges this. The claimed future dump is the misfiled arrival. No demonstrated beat-order defect remains in that accusation. |
| 1C exit_motivated | **H3 + authored bridge/rubric**. `P:1233` says the numbers are stronger proof and they withdraw to prepare entry, but bridge `plot.md` only says “prepare a way inside.” The judge demands a named destination (`J:69,75`). Correct scene partition and judge the actual departure/arrival together before proposing a bridge rewrite. |
| **2A exit_motivated** | **Authored bridge/rubric**, not missing runtime text. `P:1731` explicitly grants corridor access and names the records archive, as does `plot.md:363–365`. `J:92,98` demands a discovery leading there. Access is a reason to advance, but the current rubric demands a clue; this is a policy choice, not an established engine defect. |
| 2A rich | **H3 + S/G/U**. `P:1338` loses the base opening; `P:1233` contains it. Repeated server/credential turns at `P:1632,1684` are genuinely thin and regress to the hideout after corridor access (`P:1558`). The judge's progressive=true does not erase those contradictions. |
| **2B progressive** | **S + G/U**. `P:1884,2128` searches the unsupported own-record path with no candidates (`P:1889,2133`); later searches repeat spent evidence (`P:2077,2179`). The audit instruction at `P:2230` is actually absent from `P:2225`, a real missed non-verbatim event, unlike 1A's falsely accused patrol. |
| 2B rewards_investigation | **S + G/U**. `J:117,127`; the script never investigates the maintenance reports offered in the T4 delivery (`P:2003`), and own-record searches do not match the security-log realization. Missing coded-message delivery is not proof that every repeated medical-file query should reveal it. The audit omission remains real. |
| 2B exit_motivated | **Authored bridge limitation**. `P:2225` says evidence is dangerous, but gives no destination. This is the actual bridge, not text lost by the one-segment split. `J:118,126` accurately describes it under the existing rubric. Rewrite only after choosing that rubric's scope. |
| 2B rich | **G/U + S**. `J:114,119,125`; brief archive opening (`P:1807`), typing/scrolling loops (`P:1884,2077,2128,2179`) and missed audit. Handoff lead-ups are deliberately bounded; it is incorrect to require the lead-up alone to repeat the appended disclosure. |
| **2C canon_consistent** | **G/U**, not missing stance material. Brandon urges immediate transmission at `P:2369` but agrees against it at `P:2723`. The correct stance is explicitly in the latter prompt (`P:2728`). A broad added rule would duplicate material that already failed; use a scoped replay before prescribing a fix. |
| 2C progressive | **S + story visibility mismatch**. `P:2308,2493` gives vague/invented executive messages, not the private offer; R1 is world-only, R2's public question is not played. `P:2435` tries the coded-message plan before its later delivery at `P:2593`. `J:141,146,150`. Do not make private content public merely to satisfy the scripted beat. |
| 2C rewards_investigation | **S + story visibility mismatch**. Same offer non-results (`P:2308,2493,2666`) and premature coded-message action (`P:2435`). The route *does* arrive at `P:2593`; calling the entire scene unrewarding loses that evidence. |
| 2C exit_motivated | **Authored bridge/rubric**. `P:2723` states the combined mission, but not the office/maintenance destination; that destination was already delivered at `P:2593`. `J:144,151` applies the departure-only requirement. This is not fixed by attributing the bridge, which is already attributed. |
| 2C rich | **G/U + S**. `J:145,152`; brief command-level opening (`P:2304`), vague assessment loops (`P:2493,2542,2666`). Offer availability and script quality must be repaired before a separate sensory-prose experiment. |
| **3A canon_consistent** | **G + S/U**. `P:3133` makes the imprisoned official speak as an experimenter; `P:3242` denies readiness after the uprising delivery (`P:3016`). The former narrator prompt is not saved (referent request at `P:3138`); the latter prompt (`P:3247`) mixes active-uprising knowledge with “while it waits.” |
| 3A scene_local | **G/U**. `J:168,177` and `P:2871,3133` place the medical action around the processing line and wrong official. T2's full turn includes the correct medical handoff; judge complaints about the lead-up alone overreach. T6 remains a real wrong-role/wrong-place narration. Root cause cannot be proven from its referent prompt. |
| 3A progressive | **S + conflicting material**. `P:3016` starts the uprising; `P:3086,3133,3195,3242` then replays meeting/medical/code/uprising actions. `P:3247` also asks for armored teams, absent from T8. Changing just the judge would leave this regression. |
| 3A rewards_investigation | **S + G/U**. Initial four reveals land; later requests repeat them (`P:3086–3242`). `J:167,171,176` conflates fresh discovery with repeat actions, but wrong-role dialogue and absent pressure are genuine defects. |
| 3A exit_motivated | **Authored bridge/rubric**. `P:3296` gives the uprising, sealed exits and upward security corridors; prior `P:3016` names command/broadcast levels. `J:170,178` demands the final destination on the departure turn itself. Assess whole transition before adding redundant prose. |
| 3A rich | **G/U + S**. `J:179` acknowledges sensory opening (`P:2800`) but grades sparse/repeated later turns. It supplies no separable richness cause beyond the above concrete defects. |
| **3B canon_consistent** | **G (authored) + G/U (model)**. `P:3446` leaves Brandon in security corridors; `P:3590` puts him beside broadcast controls in the *authored delivery* (`knowledge.yaml:2560`). The same turn invents site codes A-12/B-7/C-9. Its saved prompt is a referent request (`P:3597`), so exact narrator cause is unavailable. Do not blame the narrator for the authored Brandon sentence. |
| 3B progressive | **S + G/U**. `P:3753` repeats the alarms, `P:3801` does not answer the requested confrontation, `P:3849` repeats the trade. `J:195–197`. Initial five deliveries do occur; missed second-cycle consequences are not missing all first-cycle beats. |
| 3B rich | **G/U + S**. `J:202–203` accepts the alarm-filled opening (`P:3371`) but objects to summary/loops. Rebecca parrots prior summaries at `P:3516`; the narrator prompt for that turn is unavailable, so do not infer its exact permission line from adjacent scenes. |

No failed boolean can responsibly be labeled **only random noise** from this one run. Several subjective judgments may fluctuate, but no replicate or saved-request re-judge measures that variance. Confirmed harness faults and source conflicts are not noise.

## Reviewable proposed changes, free checks, and risks

These are proposals, not applied patches. “New” below means a new combination or policy not shown effective by this sample, even when it uses an existing mechanism. Prefer deletion or corrected evidence over new narrator instructions.

### F1 — Complete attribution and knowledge evidence (harness only)

Keep the existing exact authored-span mechanism. Add eligibility for **the actual committed** verbatim pacing realization, ending, and canonical-event delivery. Do not make every package sentence eligible when completion is true. The current broad completion fallback eligibility (`authored-spans.js:108–117`) should be narrowed to events evidenced on that turn as part of this work. Exact text additions are the existing package strings, byte-for-byte: no prose rewrite.

For this sample the ending span's old classification is `narrator`; its new classification is `authored`, source kind `ending`, source ID `3C`, text exactly `pacing.ending.text` (`pacing.yaml:368–379`, recorded at `P:4783`). The patrol return's old classification is `narrator`; new is `authored`, source kind `pacing`, source ID `patrol_returns_1a`, exact text **“The patrol is coming back to the house.”** The detective sentence remains narrator text.

Replace the scene-local selected-ID-only availability contract with chronological committed public knowledge, retaining evidence of its source and disclosure time. Prior scenes' earned public knowledge remains available; world-only knowledge does not become public because a fact exists. Canonical-event facts must be mapped through the package's declared knowledge/effects, not guessed from narration or predicate name similarity. Keep separate before-turn knowledge and same-turn runtime deliveries, so an ending cannot retroactively license an earlier model leak. This expands an existing fact-backed mechanism; it is **new judge-input wiring and needs offline tests**, not a measured judge improvement.

Exact judge wording replacement:

- Old: **“Require characters, items, plot events, dialogue, and setting to remain consistent with the five source files.”**
- New: **“Require characters, items, plot events, dialogue, and setting to remain consistent with the supplied canon and the committed timeline. Judge runtime-authored text for quality, but do not attribute it to the narrator.”**
- Old: **“revealed_knowledge is the set of authored facts the player has earned by committed reveal.”**
- New: **“knowledge_available_before_turn lists public knowledge already disclosed to the player. runtime_deliveries lists the authored text delivered on this turn and its committed facts. Earlier disclosures remain known in later scenes. A later disclosure cannot excuse an earlier leak.”**
- Old: **“Premature disclosure means narration states an authored protected fact that is NOT in revealed_knowledge; only that fails protected_safe.”**
- New: **“Fail protected_safe only when narrator text discloses a protected fact from the supplied protected-fact inventory before it is available. Identify the fact, turn and exact narrator text. Runtime deliveries are exempt from narrator-disclosure penalties.”**

Update the later duplicate `not in revealed_knowledge` sentence to the same rule, rather than leaving conflicting terminology. Supply the inventory to the **judge only**, never the narrator. Remove raw `prompt` from the acceptance input and supply explicit typed beat/canon evidence instead; preserve prompts in the diagnostic artifact. Old statement `delete turnForJudge.bundle;` becomes that statement followed by `delete turnForJudge.prompt;` **only after** the explicit evidence replaces the lost context. Mixed request types must not silently become judge authority.

Cheapest free check: reconstruct a saved judge request with injected `fetchImpl`, inspect its JSON without calling OpenAI. Assert 3B's deluge is known before 3C T4; T14 ending is exactly attributed; T5/T10 do not gain Phase Two; world-only 2C offer stays excluded; invented detective remains unexempt. Existing boundaries: `frontend/e2e/roleplay-judge.test.js`, `authored-spans.test.js`. Paid re-judging is a separate authorization.

Risk: over-broad attribution can hide genuine leaks; pooling knowledge can leak private/world-only or later facts. Tests must include earlier negative turns, not just the repaired ending. Raw saved bundles are summaries, so a complete reconstruction may require an offline runtime replay; report unknown fields rather than inventing them.

### F2 — Partition all entry segments (harness only)

Old behavior/text: **“Entering a scene emits its authored entry_text as the turn's final segment.”** New contract/comment: **“Entering a scene emits its base entry text and any satisfied entry variants. Keep all arrival segments together as the destination opening; retain the source bridge in the departure.”**

Replace the `slice(0, -1)` / `at(-1)` assumption with a partition derived from runtime entry boundaries, or package-defined entry texts plus the actual satisfied variant. Reuse the existing `scene_entry_texts` semantics; do not split based on English place names. For this saved case, the exact text beginning **“Brandon's hideout was buried inside a dead communications center:”** and ending **“sent to examine.”** (`plot.md:355`, `P:1233`) moves from the 1C judge turn to the beginning of 2A's opening. The existing variant at `P:1338` follows unchanged. Player text is unchanged.

Cheapest free check: reconstruct this transition from the saved segments and verify lossless ordered concatenation, bridge retained, both entry segments in 2A. Also check a one-entry transition and a no-transition turn. Existing multi-entry runtime behavior is proven; **the new harness partition is not yet implemented or tested**. Risk: accidentally removing the bridge or treating ordinary narrator text identical to an entry as a transition; prefer authoritative boundary metadata when available.

### F3 — Preserve the existing bridge/action on verbatim-event exits (runtime, not story)

Proposed subtraction, subject to checking the original regression tests:

- Delete the whole replacement block `if entry_segments and self.state.last_turn_delivery.complication_verbatim:` at `engine.py:373–380` and its resume counterpart `:1202–1209`. New text: **empty**. Preserve the existing append/deduplication path for verbatim complication text.
- Old (`engine.py:1266–1268`):

  ```python
  if self.state.last_turn_delivery.complication_verbatim:
      return entry
  return (bridge, *entry)
  ```

  New:

  ```python
  return (bridge, *entry)
  ```

This restores existing source prose and composition rather than inventing a new exit. It is **an unverified use of the existing append path**, not a proven safe deletion. A hidden reason for suppressing pre-transition prose could invalidate the proposal.

Cheapest free check: a scripted narrator turn that commits a reveal and transitions with a verbatim event. Assert the action/delivery, complication exactly once, source bridge and every entry segment survive in order; assert facts and rollback are unchanged. Repeat on `proceed` resume. Consult `tests/test_scene_relative_pacing.py`, `test_pacing_handoff.py`, `test_canon_journey.py` and the existing transition tests. No live model is required. Risk: duplicate event text, incompatible pre-transition narration, and differences between normal and resumed commits. Do not remove validation to make the composition pass.

### F4 — Correct the journey before treating repeats as available investigations (measurement change)

Do not shorten scene minima, clamp blindly to the last prompt, remove low-scoring turns from the record, or weaken the empty-response bar. The prior stall diagnosis proved those clocks have legitimate non-storylet progress. First enumerate each scripted action's eligible reveal and current facts with the existing offline spine generator/matcher. A rewritten journey changes the experiment and must get a new measurement identity.

Exact candidate input substitutions, **not yet approved as a revised journey**:

| Old input | Candidate new input | Constraint |
|---|---|---|
| “Read my own record in the archive.” | “Read the security logs for Michelle's evidence.” | Matches the existing bait realization's evidence groups. It competes with Brandon's admission in SL-2B-B; do not adopt without deciding branch coverage. No story-data edit proposed. |
| “Assess the executive channel's private offer and whether the people running this are turning on each other.” | “Ask Brandon why Rebecca turned against Charles.” | Uses the existing public R2, preserves R1's private audience. Whether the player has a cue to ask this must be checked; this is a canon-harness action, not a proposed blind-player policy. |
| “Read the recovered fragment describing what was meant to follow all of this.” | “Read the recovered JANUS file.” | Uses existing evidence terms, but must only be played after escape/national consequences/Charles's escape gates. Wording alone cannot fix the recorded T5/T10 failures. |

Before national aftermath in 3C, the missing action to evaluate is **“Ask Michelle to use the emergency gate authorization to release the surface gates.”** Old corresponding script slot: **none**. New candidate slot: the quoted action, after the evacuation-support action. It uses an existing gate beat, not a new plot event; exact matching/availability and the downstream resolution chain remain unverified. Do not claim this one addition guarantees the ending will unfold across turns.

Cheapest free check: use the existing offline engine-backed generator (`scripts/generate_spine_expected_reveals.py`) and matcher to inspect candidate eligibility, sibling consumption and resulting facts for the full revised sequence. Do not edit the generated expected list to fit a desired score. Cost/risk: changing one prompt can select a different realization and change later state. Only a live replicated comparison can establish prose improvement. Repetition itself remains a useful robustness test; keep it as a separately labeled test rather than silently discarding failures.

### F5 — Remove the authored Brandon location conflict (STORY-DATA CHANGE; approval required)

`knowledge.yaml:2560`:

- Old: **“Charles locks down Rebecca's office. He turns the harmless water emergency into a real deluge through the outer access level. Brandon waits beside the broadcast controls.”**
- New: **“Charles locks down Rebecca's office. He turns the harmless water emergency into a real deluge through the outer access level.”**

This removes the unsupported relocation while retaining the delivery's plot event. Checked preceding office-entry handoff (`P:3446`) and 3C placements (`plot.md:817–820`); Brandon's eventual relay role remains authored elsewhere. Technique: subtract the pulling sentence before adding placement rules. Cheapest free check: package load plus delivery/prompt diff; ensure no other byte changes and preserve the existing relay action's eligibility. Risk: deleting a useful next-action cue. If Brandon must move at this moment, the alternative needs an explicit authored move and prose reviewed by Brandon; none is proposed here.

### F6 — Test narrow source subtraction before prescribing narrator rules

Two recorded-prompt probe candidates use techniques already shown effective in the scene-fixing guide. They are **hypotheses**, not implementation recommendations established by this sample:

1. 1B photo provenance: old recalled line at `P:849`, **“Kristin reads Michelle's memory card. Its damaged recording warns her not to trust emergency broadcasts, and the Continuity Initiative files point to a dead drop at a bench in the park.”** New for the frozen photo-turn probe: **empty**. Remove only this stale recall in the probe. Do not globally remove knowledge or alter custody facts. Risk: losing legitimate background context; free check is a byte diff of this single prompt line and unchanged action/delivery. If it wins, locate and scope the source selection, not a hand-edited production prompt.
2. 3A uprising: old pacing realization `pacing.yaml:233`, **“Armored teams seal one holding block after another. The uprising is losing routes while it waits.”** Candidate new: **“Armored teams seal one holding block after another.”** This is a **STORY-DATA/PACING-PROSE CHANGE requiring Brandon's approval** even though timing/facts stay the same. It removes a line competing with the already-active uprising. Free check: confirm no timing/effect change and inspect the full recorded prompt with only that sentence removed. Risk: weaker urgency before the uprising; a conditional authored variant may eventually be preferable, but is not proposed without the probe.

Do not add a new “do not repeat”/“stay in place” narrator rule. The guide records failed go-into-place, plain-corridor and copy-refers rules and successful concrete material/scoping. The actual 2C stance is already supplied at `P:2728`; we have no winning replacement for that failure. The 3A T6 and 3B T4 narrator requests are not preserved, so first recover typed prompt evidence before attempting a causal replay.

The cheapest free check establishes the exact changed bytes, not efficacy. Later paid evidence, only if authorized: frozen recorded-prompt baseline versus one subtraction arm, 10–15 samples each, read every full narration including appended delivery, then the same scene bench with three live replicates. No billed probe is authorized by this diagnosis.

### F7 — Resolve the exit/richness policy explicitly; no automatic story rewrite

The present departure rubric demands discovery plus destination on the departing turn, even when the scene earned access or the prior turn already explained the route. This is why attributed bridges still fail in 2A/2C/3A. A defensible **new measurement policy**, offered for Brandon's decision:

- Old: **“A turn marked left_scene is the one the story departed on: fail unless the narration the player actually read gives them a reason to go, naming in prose what was found and where it points.”**
- New: **“For a turn marked left_scene, read the departure and its arrival together with earlier discoveries in this scene. Require a player-visible reason to leave and a clear destination or route. Earned access, immediate danger, or a discovery can supply the reason. Do not require the same discovery to be repeated on the departure turn.”**

This changes the acceptance bar; it is not a factual bug fix or a demonstrated score improvement. Cheapest free check: human-label saved transitions against both definitions, including a negative with no reason or destination anywhere. Risk: too much earlier context could excuse an abrupt transition; require citations to the actual player-visible text. Keep `rich` unchanged until the opening partition is fixed. No sensory opening expansions or bridge rewrites are proposed: those would be plot/story-data changes, and this sample does not identify the smallest justified wording.

## Order, verification boundary, and unresolved work

1. **Safety evidence first:** F1, then F2, offline. Confirm that attribution never licenses earlier text. Save corrected requests separately from original artifacts; do not overwrite the measured 25/63.
2. **Player-visible composition:** investigate and verify F3 offline against both normal and resumed transitions. Existing authored bridge restored before any new bridge prose is considered.
3. **Measurement validity:** review F4's actual eligibility and branch effects. Decide F7 as a separate acceptance-policy change. Do not mix a different journey and a different rubric into an unlabeled historical comparison.
4. **Small source fixes:** Brandon may approve F5 and the story-prose arm of F6. Restore/retain exact approved bytes only. For other scene failures, recover the actual narrator request before proposing missing material; do not treat a referent prompt as that request.
5. **Only then paid measurement:** authorize each re-judge/probe/run separately with its estimate. Re-judging saved text tests the judge change, not game improvement. Frozen prompt arms test candidate causes, and complete repeated hosted runs test the journey/game. Follow merged-SHA staging requirements for hosted implementation checks. No score or earned-transition rate is predicted here.

Free work actually performed: JSON inspection, turn/segment/source comparisons, source trace, and git comparison to the recorded SHA. These are artifact checks, not runtime test passes. No test suite was run, no environment credentials loaded, and no live service contacted. Existing runbook already covers this read-only saved-artifact procedure; no runbook change was made under the instruction to write only this diagnosis.

Unverified: actual judge request envelope/model identity; full narrator requests on referent-prompt turns; provider-level retries/raw proposals; exact full fact snapshots behind summary deltas; efficacy of any proposed source subtraction; F3's original suppression rationale; the revised script's sibling/gate behavior; between-run variance; and whether any subjective false verdict changes after correcting evidence. The saved result cannot establish a 3C safety pass for future runs or the causal cure for every prose defect.
