# Scene 3A: people, facts, and permitted speech

Status: IN PROGRESS, last updated 2026-11-07. Presence work applied (uncommitted) on `main` at `5fc12e79`; the speech and c9 questions are open. This file is the active plan for this investigation; update it in place. The older open-issues plan remains the historical implementation record; per-experiment rules and results are Amendments 19 and 20 in `.plans/richer-3a-probe-prereg.md`.

## Resume here

### Superseding update (2026-11-07, later): speech work now runs through the shared plan

The speech sections below (S, H, U, the "Next steps" list) are partly stale. Current facts, recorded in
[the shared plan](shared-narrator-instruction-conflicts-plan.md) and
[its prereg](shared-narrator-instruction-conflicts-prereg.md):

- **S missed** (Amendment 20) and **U missed** on relevance (frozen-substitution probe, 72 requests): the D gate was met (0/36
  unquoted third-person self-reference) but authored lines were voiced 12/12 at c4 and the commanded medical-level action vanished.
  U is not built. U as written also covers only 2 of Michelle's 5 third-person statements.
- **Narrated-prerequisite gate built offline, uncommitted** (shared plan, "Narrated-prerequisite gate"). A `storylet_realization`
  entry is sayable only after it was narrated, so sibling realizations (`a_r2`, `d_r2`, `c_r2`) stop being offered. This addresses
  reading 6 (facts doing two jobs). It does **not** fix grammatical person or the c9 replay: delivered `a_r1`, `b_r2`, `d_r1`, `c_r1`
  stay offered.
- **H** (omit the answer rule on selected handoffs) is the same idea as shared-plan B, which was dropped (control did not reproduce).
  Retire H unless a c5 invented-answer failure reproduces.
- **Authored deliveries are not a person problem.** All 13 `k_sl_3a_*` `delivery_text` values and the three 3A handoff fallbacks are
  indirect narration with no quoted utterance. The defect is only the `may say this aloud:` speaker-line template.
- Do not delete the SCENE-only line while speech is open: removing it raised verbatim recital 8/12 to 12/12.

**Experiment G ran (2026-11-07)** and step (1) below is done: the first-person sentence failed (dropped); the gate alone cut the c9 handover replay
12/12 to 7/12 but flipped c4 (medical level 9/12 to 1/12) and added c5 premature answers; adoption of the gate is Brandon's call. See the shared plan's
"Step 1 result". Steps (2) to (4) stand, with (2) now: `voiceable` on completed handover statements, or non-speakable self-describing statements.

**Original agreed order:** (1) one billed replay at c4, c5, c9 of control / gate / gate + the shared first-person sentence
(needs a preregistration and spend approval); (2) branch on the result: first-person sentence passes, or `voiceable: false` on
completed signal and handover statements (needs Brandon's approval; it is this plan's c9 step 1), or make self-describing statements
non-speakable to their own subject; (3) add the A-opening arm to this plan's other-scene opening checks; (4) one combined
qualification for both plans, not two.

### Current state (nothing is committed; all of it is in the working tree)

**Kept (state "P"):**
- `World.people_alongside` (`packages/worldkeeper/src/worldkeeper/model.py`), tests in `packages/worldkeeper/tests/test_people_alongside.py`.
- Shared `_person_line` and entity-identity dedup in `storygame/runtime/item_facts.py`: visible people at the player's spot get a THINGS line with authored placement text; present-only people get the ordinary state wording, referred people the change-reporting wording. Tests in `tests/test_referred_reach.py`. Applied patch kept at `scripts/ringer/3a-open-issues/things-people-applied.patch`.
- P1: `data/stories/continuity-initiative/plot.md` 3A `michelle: {parent: detention_level, text: beside the captives}`.
- 1B opening golden updated by one line (the man watching Kristin; Brandon approved) in `tests/fixtures/place_feed/baseline_prompts.json`; pin updated in `tests/test_bench_item_facts.py`.
- Frame sentence " Michelle is beside the captives." stays in `knowledge.yaml` (K1 reverted).

**Tried and reverted, with evidence:**
- K1 (frame sentence removed), Amendment 19 arm L: c4 reunion line spoken 11/12 (shipped 3/12), 2 malformed, c5 invented "what you said earlier" 5/12.
- S (speaker-line template `may talk about this fact:`), Amendment 20: worse at every endpoint (c4 medical level 0/12 against 9/12, 3 malformed, bookkeeping spoken 12/12; c5 question clearly asked 5/12, premature answers 2/12; c9 repeat 12/12 in both arms). Rejected patch kept at `scripts/ringer/3a-open-issues/speech-template-rejected.patch`.

**Decision pending from Brandon:** none. He chose "keep P as-is" knowing two known flaws (below).

### Known flaws in the kept state
1. Opening wording: P opening has Kristin "scanning the faces for Michelle" before spotting her in 6/12 (shipped 0/12). Cosmetic/borderline; Michelle is identified 12/12.
2. c5 cake question asked 11/12 (shipped 12/12; #5 has Michelle ask it).
3. **c9 replays the completed handover and signal in 12/12 (O4), in every arm tried.** This blocks a correct game and is the next thing to fix.
4. 1B, 2A, 2B and 2C openings now carry a person line (inventory at `~/dev/ringer-work/3a-things-people/inventory.txt`: 1B man +107 chars, 2A supervisor +96, 2B supervisor +79, 2C Rebecca +71, 3A Michelle +36; 1A, 1C, 3B, 3C unchanged). Only checked offline; no billed narration for any of them. 2B is the pacing risk: verify no immediate confrontation or early revelation of the supervisor's allegiance, both entry variants.
5. Not yet run: later-turn state checks (3B office co-location, 3C Rebecca co-location, movement), A-r2-first and 2C transmit/alarm histories, full nine-command 3A runs, matcher/recovery, full suite and ruff gate.

### Next steps, in order
1. **c9 (O4), free first:** read the c9 payload. The speaker lines (all three speakers) carry "Michelle hands Kristin the stolen radio and Kristin gives the signal..." and "The uprising is active..." as present-tense speech, and SCENE carries the same completed facts. Candidate (Amendment 10's untried follow-up): make the c9 signal/authorization statements non-sayable (`voiceable: false` or the equivalent authored flag; check `knowledge.py` projection so truth and SCENE are unchanged). Preregister, then replay c9 C/candidate, 12 each = 24 requests, ~88.8 neurons. Win: item 1 at most 2/12 and at least 4 fewer than a reproducing control; items 3 12/12, 4 and 5 0/12.
2. **Opening wording (optional):** only if Brandon wants it; no proven cure. Do not repeat Amendment 16's "Michelle was among them".
3. **U (authored `speaker_text`), only if recitation returns:** schema change, tests first, probe the six replacement lines as frozen payload substitutions before building. Recitation is low under P at c4 (1/12 and 2/12), so U is not urgent.
4. **Other-scene checks:** billed paired 12-sample checks at 1B, 2A, 2B (both variants), 2C openings and 3B/3C co-location states (plan section "Every affected scene"), after the c9 fix so they run once on the final state.
5. **Qualify:** combined C/final frozen check at opening, c4, c5, c9, then full nine-command 3A scripts (12 replicates), then the deterministic suite and Ruff gate, one full run at the end. Staging follows merge; production is a separate authorized action.

### How to rerun things
- Ringer manifests and generators: `scripts/ringer/3a-open-issues/` (`things_people.py`, `speech_template.py`, `location_capture.py`/`location_replay.py`/`location_probe.py`, `speech_capture.py`/`speech_replay.py`/`speech_probe.py`). Probe tasks are placeholder workers whose check performs the replay; each refuses to re-bill if its rows file exists.
- Frozen payloads and rows: `bench/results/richer-3a-probe/loc/` (C/P/L opening, c4, c5) and `speech/` (C/S at c4, c5, c9), untracked. Variation `bench/variations/richer-3a-loc-P.json` supplies the replay transport.
- Run from the repo root with `TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python ...`. Keep Ringer workers on the documented workaround (main `.venv`, own `PYTHONPATH`).
- Replays drift day to day; always run a same-day interleaved control.

**Approval boundary:** every proposed PLOT, KNOWLEDGE, WORLD, or SCHEMA change below is a proposal for Brandon's approval before application. This planning request authorizes writing this document, not implementing those changes or billing probes. ENGINE changes and tests are future Ringer tasks, tests first. Nothing in this plan authorizes widening the scope to repair all prompt conflicts.

## Findings and evidence corrections

Paths in this section are relative to `bench/results/richer-3a-probe/`. Sample numbers mean the saved `sample` field; opening samples mean `i + 1`. I read the narration in the saved rows, including malformed rows' readable prefixes, rather than relying on the result tables. Identical prose was grouped with its sample numbers for inspection. I also compared the frozen wire prompts and read the current source, story, preregistrations, and retained patch.

### The two problems and the six proposed readings

| Question | Established mechanism and evidence | Defect and appropriate technique |
| --- | --- | --- |
| Missing people in THINGS; reading 1 | `item_facts.py:153` `_view` excludes non-protagonist characters. `_thing_names` at 553 cannot select absent character entries. `_referred_lines_for_command` at 1085 independently adds a visible, reachable/unplaced named NPC; `prepare_turn` at 1987 initializes these lines. `bio/frozen-candidate-c4.json` has Kristin and medical level only; c5 already has Michelle. CHARACTERS does name Michelle at c4, but does not locate her. | A structural omission in this proposed presence contract, not proof that every current reply is wrong. The frame currently compensates. Existing technique: give concrete world material before instructions, preserve authored placement text (grounding guide, Prompt inputs/outputs; historical W4/W8). Extending automatic narration coverage to people is **new, unproven**, with partial Amendment 18 support. |
| Parent-only labels; reading 2 | The shipped named-person branch at `item_facts.py:1125` and patch helper `_referred_person_line` use `world.name(parent)`, not `World.place_label`. Ordinary `_view` uses `place_label`. Plot placements at 199, 416, 504 and 613 carry the four descriptions listed in the prompt. Michelle at 722 has no text. | Confirmed information loss, also present on the existing named-person path. Use the established placement-text lifecycle, not newly composed location prose. Restoring the 2B text is necessary but does not prove that listing its supervisor preserves the audit's pacing. |
| Automatic state instruction; reading 3 | The saved patch calls `_state_text(..., narration=True)` for everyone it adds. Existing `_things_block` at 502 scopes that form to referred things. Thus merely being visible gives 1B's man an instruction to report unconsciousness. | A concrete violation of the command-scoped state-guidance contract, not evidence that this particular patch actually knocked him out. Keep the state and ordinary alternative-pole description; reserve `If it changes, give "state"...` for a referred person. Proven precedent: historical `.plans/world-model.md` at `5ea01199`, “scoped” state-field experiment and “Built/Kept (Brandon chose, 2026-10-03)”; `docs/world-model-grounding/prompt-outputs-and-judges.md`, “Show state guidance only for named things.” |
| 1B golden; reading 4 | `tests/test_place_scoped_feed.py` and `tests/fixtures/place_feed/baseline_prompts.json` pin the old opening. The patch adds the unnamed man. Its worker report and Amendment 18 record the failure. Source explains why 1A's opening has no corresponding addition. | An expected changed contract requiring review, not permission to overwrite all fixtures. No tests were run in this planning pass; failure is recorded evidence, not newly reproduced. Review the 1B prompt and discovery behavior before updating only its approved golden lines. Keep 1A byte-identical to the current baseline. |
| Third-person facts offered as speech; reading 5 | `cloudflare.py:1622–1640` formats every eligible entry as `<Name> may say this aloud: <statement>`. `_section_user_prompt` at 1642 also prints the same established statements in SCENE. `knowledge.yaml:2381,2412` are third-person bookkeeping, not utterances. `people/candidate-c4-rows.json` samples 1–3, 5, 7–12 make Michelle recite the reunion, including malformed sample 8. | Real narration defect. The source creates an invitation to copy, despite the no-copy instruction. Source subtraction/replacement before extra instructions is proven workflow (`docs/scene-fixing-guide.md`, steps 1–3). Neither a new header nor separate authored speech has proven outcome evidence here: both are **new, unproven** candidates. |
| Facts doing two jobs; reading 6 | `knowledge.py:238` projects committed and sayable material separately; `_effect_item_ids` at 300 hides effect-backed statements only from SCENE. `_established_for` at 312 still supplies eligible speech. Both A realizations establish the same facts, so both can be projected after either was earned. Amendment 14 removes speech copies and leaves SCENE copying; 15 removes SCENE copies and leaves reunion speech. | Confirmed coupling of truth, recap, and permission. It is not safe to delete either whole channel on the current evidence. Keep the established truth and Michelle's organizing role while changing how speech permission is expressed. No proven single cure covers both problems. |

The shared architectural issue is that stable identity, physical presence, completed events, current activity, and usable speech are not clearly separated in the material given to this small model. The **proximate causes differ**: THINGS selection omits a person; speech formatting offers third-person facts as words to say. Amendment 18 locates Michelle without reducing recitation, so presence alone is not a supported cure for speech.

### Row audit: retain the misses, correct the claims

| Record | What the rows support and what needs correction |
| --- | --- |
| Amendment 9, `d1v/` | Removal leaves opening-picture narration at c4 samples 2–5, 7, 9–11; c5 samples 1, 3–5, 7, 10 turn toward plans. The seven cake questions and malformed c5 samples 2/5 support the miss. The saved D1 control visibly moves toward the medical level in c4 samples **7, 8, 9, 12 (4/12)**, rather than the table's 3/12. Do not reuse that aggregate without row scoring. |
| Amendment 11, `reunion/` | Candidate c4 samples 1, 4, 6, 8–11 greet Michelle as newly reached (7/12); all twelve rebuild the detention picture. Sample 1 is malformed. The companion effect plus SCENE deletion was confounded and failed. |
| Amendment 12, `a1/` | The trim removes the organizing role as well as copyable text. Candidate c4 samples 2, 5, 8, 9 treat Michelle as someone to rescue; c5 samples 2, 4, 5, 12 replay reunion. c5 samples 3, 4, 8, 10, 12 ask about cake. This is a failed removal, not a nearly accepted solution. |
| Amendment 13 stage A, `bio/trim-*` | New bio c4 keeps Michelle present and avoids the three old-bio malformed outputs; c5 still greets in samples 3/4. Sample 5 also has a long unrelated discussion, so a plan-exchange count of only two is too generous. Ten candidate cake references do not make the whole turn sound. |
| Amendment 13 stage B, `bio/{control,candidate}-c*-rows.json` | New-bio c4: Michelle acts/speaks 12/12, verbatim reunion speech 8/12 (2, 3, 6, 8–12), malformed 0/12. **None of these new-bio c4 narrations heads into or mentions the medical level.** The often-repeated 3/12 is from another run/control, not these rows. c5 asks about cake 12/12, but sample 8 adds a long planning conversation and anticipates the proof answer. Old-bio c5 sample 5 invents the cake as a memory trigger/test. Those are substantive failures outside a cake-keyword count. |
| Amendment 14, `d1v-bio/` | Candidate Michelle's reunion recitation 0/12; Kristin voices the other-sites content in 1, 6, 7, 9–11 (6/12, including malformed 1/6/10); detention re-staging in 2–5, 8, 12 (6/12). No medical lead. Same-day control has medical intent in 4/6/12; that must not be attributed to the saved stage-B candidate. Miss remains. |
| Amendment 15, `reunion-bio/` | Candidate rebuilds the opening in all twelve; reunion recitation in 1, 2, 10–12; sample 2 malformed. Greeting improvement does not cure restaging. Same-day control has malformed 4/6/10/12, illustrating variability without proving the candidate safe. |
| Amendment 16, `frame/` | Candidate opening 7 greets “I'm glad you're here”; opening 2 lacks the final radio cue. Miss confirmed. “Control eye contact 0/12” is too broad: control opening 4 explicitly has Michelle's eyes locked on Kristin and mouths “wait.” Separate operational acknowledgment from an emotional reunion; bare eye contact is not an automatic failure. The candidate was also a **rewording** to “Michelle was among them,” not a literal move of the old frame sentence. |
| Amendments 10/17, `radio/`, `c9bio/` | Old-bio radio candidate signals again in 2/9/10, but avoids the handover. New-bio c9 repeats a handover or signal in 2–12. The run crosses days and cannot identify bio causation. Some expiry speech repeats a current required complication, not just a historical statement: do not mark every such utterance a defect. |
| Amendment 18, `people/` | Confirmed exact wire diffs: c4 removes the frame sentence and adds one Michelle line; c5 **only removes the frame sentence**. System/settings unchanged. c4 sample 8 is malformed with repeated item-fact keys; sample **11**, not 12, contains an extra dialogue segment with **missing `text`**, not an explicit JSON null. c4 opens with Brandon first in **10/12**, including malformed 8, not 9/12. Recitation 10/12 remains. Samples 4/6 express medical intent but do not actually enter. Sample 6 invents the extraction radio call. c5 asks the cake question 12/12; Michelle herself acts in **8/12**, not 12/12 (2/5/7/8 only describe Kristin asking). |

These corrections do not retroactively change any preregistered verdict. Amendment 18 missed; valid JSON was also an insufficient content gate. Its saved control was from the previous day. Say “promising presence evidence at these endpoints,” not “the truncation was noise” or “the location problem is solved.”

## Conflicting prompt lines: central hypothesis, with limits

Brandon specifically asked whether the earlier Kristin/Michelle conflict explains today's failures. It explains part of the history; it does not explain all current behavior.

1. **Proven stale-goal conflict:** Kristin's old biography said she wanted to find Michelle while SCENE said they had reunited and Michelle's biography called them closest friends. Amendment 13 tests deletion of the goal alone. Keep that deletion. It helped the trimmed prompt, but c5 greetings remained and the new-bio shipped prompt still recited. Do not reintroduce the goal to make c9 look better.
2. **Current speech conflict:** system `cloudflare.py:906` says “Do not copy sentences from the SCENE section.” Speaker lines at 1639 offer those same sentences as speech. The permission is not logically an order, but it supplies exact third-person wording next to a prohibition on copying it. The rows repeatedly follow the local wording. This is the first speech mechanism to test, before inventing more story text.
3. **Current c5 ownership conflict:** system line 894 says “When the player talks to someone, that person answers.” The handoff at 942–943 tells the narrator that the game will append Michelle's answer and to write only the lead-up. The composed turn should answer; the generated lead-up should not manufacture a competing memory. `bio/control-c5` sample 5 and candidate sample 8 illustrate the risk. The generic answer rule has a winning earlier probe, so do not delete it globally. Only if residual c5 answer invention is reproduced, test omission of this rule on already selected authored-handoff turns as its own arm. This scoping is **new, unproven**.
4. **Goal competition is not automatically contradiction:** “Join the uprising”/“Supporting the uprising is the immediate priority” and “Enter the medical level” can both be true; plot 3A explicitly uses the records to support the uprising. Planning talk displacing the typed action is a failure, but the record does not establish that the pressure line causes it. R rewording already failed to cure later re-spotting. Do not repeat that arm unchanged.
5. **Location/role conflict requires provenance:** the frozen c5 payload still places both women on the detention level although c4's appended delivery shows Kristin the medical level. `bench/frozen_prompts.py:63–89` scripts the prefix with delivery text and no narrator world deltas. That can create a location mismatch in a frozen state; it does not prove the live engine lost a move. Capture and compare actual live post-c4 facts before changing world effects. Likewise, “beside the captives” can become stale when either party moves. A THINGS projection with invalidating placement text addresses that source risk.
6. **Current c9 tension:** SCENE says the uprising is active while speaker lines describe handing over the radio and starting it in present tense. `_effect_item_ids` removed only the SCENE event copies. The radio is held by Kristin in the match payload, but **not listed in narrator THINGS** at c9. Do not claim the narrator ignored a custody line it never received. This is a related completed-event/speech problem, not proof that Michelle needs a different biography.

Neither a bare “spots” nor being thoughtful/private while organizing prisoners is a contradiction under Brandon's rulings. Nickname permission is consistent: Kristin may say Shelly. Do not rewrite either biography speculatively.

### Separate-study notices only (requested by Brandon)

These are present in the inspected shared prompts. They are **not additional fixes in this work**:

- `cloudflare.py:887`: “Use only what the SCENE section tells you” versus the system's CHARACTERS/CONSTRAINTS direction and the THINGS starting-place instruction. This creates competing source authority across sections.
- `cloudflare.py:891` versus `:942–943`: “Finish each action the player gives” versus “Write only what leads up to it” on handoff turns. There is an intended division of labor, but the prompt does not scope the general instruction to the composed result.
- The fixed 2–3 paragraphs of 2–3 sentences requirement in the saved system payload can compete with a short handoff lead-up and the ban on extra actions. This is a pressure to elaborate, not an established cause.

The first two recur wherever those shared builders are used, beyond 3A. This was a focused inspection, not a complete audit of every project prompt. No broad prompt rewrite, new judge rule, or multi-scene conflict cleanup is authorized by this plan.

## Holistic design

### Presence and identity

**ENGINE:** THINGS carries current physical location for the protagonist and visible people at the same spot, plus the existing command-referred material. CHARACTERS carries the existing bounded, narrator-safe biographies. SCENE carries atmosphere, current pressure, earned truth and selected story material. Opening cue and earned reunion retain distinct jobs: identify Michelle working nearby first; deliver the quiet reunion only when earned.

Use `World.alongside`, not the broader `together`, for automatic people. `alongside` compares spots; `together` accepts nested areas. Neither means someone is conversing with Kristin. World-only candidate selection belongs in a `World` method with tests in `packages/worldkeeper/tests/`. Rendering, story labels, command references and deduplication belong in `item_facts.py`. Do not move tree walking from the saved patch straight into shared runtime.

Preserve the existing compact companion and group behavior for this bounded change. A companion actually alongside is already on Kristin's line; group members are not automatically promoted to named solo lines. Explicitly referred people still receive their own line. Keep the official among the captives; do not reveal him as a new standalone opening presence. Test split companions and actual group-member behavior rather than assuming a membership flag establishes co-location. Deduplicate by entity identity, including observation lines and referred lines, not rendered prefix matching.

Render a person's placement with the existing `World.place_text`/`place_label` lifecycle: verbatim valid authored text, then a safe parent label after movement. Preserve unnamed-character labels for a person and a character parent; never expose a hidden real name through the fallback. `place_text` at `model.py:884` stops applying after the entity or an ancestor moves. No synthesized English from containment.

Keep ordinary state information for passively present people; emit change-reporting guidance only when referred. The automatic people list is narration context, not a new mutable item store or a change to name-matcher scope. Test opening, normal turn and recovery assembly for the same contract.

**PLOT proposal P1**, `plot.md:722`, under 3A `character_placements`, exact replacement:

```yaml
  michelle: {parent: detention_level, text: beside the captives}
```

This preserves the existing plot sentence's spatial detail using established placement syntax. No new entity, relation, companion effect, reveal, or schema field. Existing other-scene placement text is retained verbatim.

One limitation needs an explicit check: the captives are Michelle's neighbors, not her ancestors. Their independent movement does not automatically invalidate her placement text. Include that split in the offline state checks. If P1 would keep saying “beside the captives” after they leave, do not claim the existing lifecycle solves it; use the already tested bare `Place: detention level.` candidate for the location probe and leave P1 unapplied, or return with a separately scoped proposal. Do not add a new relation parser to preserve the phrase.

**KNOWLEDGE proposal K1**, `knowledge.yaml:398`, exact replacement:

```yaml
  situation: "The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels."
```

Apply only after the presence carrier has passed its opening and later-turn gates. Leave `plot.md:723` entry text and the prose sentence in 3A.1 unchanged; do not repeat Amendment 16's “Michelle was among them.” Keep `handoffs.yaml:358` reunion cue/delivery contract and both knowledge deliveries unchanged.

### Truth and speech

**Preferred ENGINE-only experiment S:** retain one line per eligible speaker per fact, its order, existing presence-or-command filtering, and the exact fact text. Replace only the template:

```text
<Name> may say this aloud: <statement>
```

with:

```text
<Name> may talk about this fact: <statement>
```

This removes the invitation to utter the statement literally while retaining permission and context. It is **new, unproven**; wording alone may fail on a small model. Do not call it a demonstrated cure, or add a new prohibition when it misses. Keep the SCENE reunion summary and organizing role in this experiment: deleting them already failed. Do not group speaker names or trim to the addressed speaker; those arms lost. No biography, truth eligibility, grounding, `voiceable`, handoff, or schema changes belong in S.

**Conditional ENGINE experiment H, only for residual c5 answer invention:** omit the exact existing sentence “When the player talks to someone, that person answers.” from the narrator request when an authored handoff has already been selected. Keep it for every other turn. Change no story words or other rules. Test separately against the winning S/presence state; if it loses, retain the original rule. This narrows an existing rule rather than adding a competing one. It is not a mandate to repair all the shared conflicts noted above.

### Optional authored utterances if S fails

**SCHEMA proposal U, new, unproven:** optional immutable `speaker_text` mapping on `KnowledgeDefinition` (`storygame/story_package/models.py:164`). Keys are declared character IDs; values are nonblank speaker-specific utterances. It is omitted from serialization when absent. Unknown speakers, blank values and wrong types fail loading. A populated map on `voiceable: false` should be rejected as contradictory authoring.

Semantics: `statement` remains the canonical claim used for truth, audience/reach eligibility, grounding, leak rules and SCENE. A speaker-text override is presentation only, never a fact, effect, new permission, reveal matcher alias, or `must_convey` replacement. Absent map preserves old rendering; a present map explicitly lists the speakers with authored speech for that entry. Intersect with the existing sayable projection and present-or-named filter; never give any speaker another speaker's first-person line. A public fact remains true and usable for validation; an absent utterance is not lost world knowledge.

Keep per-speaker/per-entry formatting. For an override, render exactly `<Name> may say this aloud: <utterance>` instead of the statement. Do not insert both copies. Do not change all stories or auto-convert third person to first person. Resolve overrides only after the current speaker's allowed knowledge is known; do not expose the whole mapping to every audience. `ProjectedKnowledge` at `knowledge.py:21` need not grow if the formatter performs a safe lookup by already-permitted item ID and speaker ID. If projection carries text instead, it must carry only that audience's override. Test both absence of leaks and compatible serialization/fingerprints.

**KNOWLEDGE proposals U1/U2**, add the following exact fields to the two entries at `knowledge.yaml:2380` and `:2411`. Keep their existing statements, actions, facts and deliveries unchanged:

```yaml
# k_sl_3a_a_r1
  speaker_text:
    michelle: "I'm coordinating the prisoners through stolen radios and coded announcements."
    brandon: "Michelle is coordinating the prisoners through stolen radios and coded announcements."
    senior_official: "Dr. McGehee is coordinating the prisoners through stolen radios and coded announcements."

# k_sl_3a_a_r2
  speaker_text:
    michelle: "Freeing this block means little unless we expose the other sites."
    brandon: "Freeing this block means little unless we expose the other sites."
    senior_official: "Freeing this block means little unless we expose the other sites."
```

These are candidate words supplied for review, not an instruction to say them every turn. They deliberately do not turn reunion into another greeting. The third-person reunion stays as established truth in SCENE. A model may still copy that SCENE line or repeat these utterances unprompted; the probe must reject that outcome. If U fails too, retain the shipped speech mechanism with its known defects and return with evidence, not another untested rule.

**WORLD changes: none proposed.** Retain the correct radio custody effect and new Kristin bio. Do not reinstate `michelle_reached → accompany` just to hide SCENE statements. **PLOT changes beyond P1: none.** **Handoff text changes: none.** Presence, P1/K1, S and conditional H can all be done without U's schema change.

## Every affected scene and boundary

The table separates scene starts from later reachable states. An opening-only inventory is insufficient for a global rule. Enumerate other loaded story packages in the free capture report too; the engine is not limited to Continuity Initiative.

| Scene | Expected new information / unchanged information | Pacing/discovery gate |
| --- | --- | --- |
| 1A | No automatic NPC addition at the normal opening; Michelle is absent. Existing name/biography behavior stays. | Byte-identical presence-only payloads; do not refresh its golden as collateral damage. Later freely moved/created people use the general rule, not a scene exception. |
| 1B | `- the man watching Kristin. Place: watching Kristin in the park.` plus passive conscious-state wording. After identification use the existing revealed label; companion dedup then applies. | No premature “Brandon,” background disclosure, forced conversation, attack or skipped bench discovery. Seeing the watching man is authored in 1B.2; verify that earlier listing does not advance the sequence. Update the 1B opening golden only after reviewed expected differences and probe evidence. |
| 1C | Brandon stays on the companion line; Michelle has no physical placement here. Captives are a group elsewhere below the observation position. | No Michelle standing beside Kristin; preserve the glimpse/message and prior stale-placement fix. Check the earlier bio change separately from this presence delta. |
| 2A | Supervisor gets `Place: walking out from the facility gate with a tablet and the work order.` Brandon stays compact. | Consistent with the opening challenge. After moving inside, drop stale walking-out text; do not have the supervisor magically accompany Kristin or repeat the entrance demand. |
| 2B | Supervisor gets `Place: leading the audit sweep between the archive stacks.` Michelle remains remote. | **Highest presence risk:** same modeled area is not immediate contact. Keep approaching footsteps, whispered investigation and the audit clock; no immediate confrontation, helpful supervisor speech, or revelation of his allegiance. Both ordinary and `cover_suspected` entry variants need coverage. If this fails, stop the global rollout; don't hide the failure with a scene-ID exception or invented room. |
| 2C | Rebecca gets `Place: standing between her guards in the command corridor.` | Fits her face-to-face offer. After her departure, no persistent Rebecca beside Kristin. Michelle's maintenance-network contact stays remote; no premature physical reunion. |
| 3A | Michelle gets `Place: beside the captives.` at entry and while placement text remains valid; then current safe parent label. Official stays represented through the existing group/referred path. | Opening identifies Michelle and radio work without greeting/reunion; c1 earns the quiet moment once; c4/c5 preserve proof and handoff boundaries. Verify movement, both A realization orders and 2C rescue/transmit/alarm histories. |
| 3B | Normal opening adds no solo Rebecca: she is in the office, Kristin in security corridors, Michelle/Brandon companions. **After office entry**, Rebecca becomes automatically listed when alongside; no placement text, so `Place: executive office.` | Do not reveal office/Charles material early; do not pull Brandon away from holding off security. Remote Charles never becomes physically present. |
| 3C | Start: Kristin in broadcast chamber, Rebecca in its parent executive office, Brandon at relay; `alongside` does not add them merely because `together` could. Michelle remains companion. **Later co-location** with Rebecca or Brandon can add a solo line. | Preserve the relay split, Rebecca's capture and carried-archive state, and escape path. No phantom reunion or forced movement of companions. |

The presence rule changes references to people already named by commands if their placement rendering is corrected; inspect those turns in **all nine scenes**, not only the five new opening lines. S changes speaker-line wording wherever speech facts exist, so its regression scope is wider than the presence rule. U confines new authored text to two entries, but loader/schema compatibility still covers all packages.

## Ordered implementation and experiment plan

### 0. Freeze evidence and repair measurement, free

Record HEAD, dirty diff, package fingerprint, model/settings, script, entry facts, payload hashes and output paths under a new directory; do not overwrite the historical rows. Update only the affected result notes/preregistration with the corrections above when implementation work begins. No test counts pinned.

Score raw syntax, content shape, decoded proposal, validation, and committed facts separately. A parseable object with missing segment text is not clean; a self-custody proposal is not proof that self-custody committed. Use existing `bench/frozen_decode.py` for a network-free decode/validation check in the intended state. Inspect duplicate-key/malformed raw text before any permissive decoder discards it. No production prose regex gates.

Freeze human labels for: new emotional reunion/search/stranger/rescue; harmless approach/acknowledgment; actual medical lead versus stated intent; question fidelity; invented shared memory; unrelated plan exchange; bookkeeping recitation regardless of speaker or segment kind; raw/content validity; cue/delivery echo; real plot-breaking inventions. Every score cites sample and quote. Fix known judge/provenance faults before paid judge comparisons. Preserve the distinction between generated text and appended delivery/cue/bridge.

In particular, do not require the c4 narrator to perform the medical delivery itself. The **composed** turn must fulfill the action; the lead-up must be compatible and avoid a substitute conversation. The same holds for c5's answer. This corrects the measurement boundary, not the old failed gates.

### 1. Ringer presence implementation and offline inventory, free

Files: `packages/worldkeeper/src/worldkeeper/model.py` near `alongside`/visibility queries; matching worldkeeper tests; `storygame/runtime/item_facts.py` `_things_block`, named-person rendering, `_referred_entity_label`, `prepare_turn`; `tests/test_referred_reach.py`, `tests/test_place_scoped_feed.py`, `tests/test_world_placements.py`; approved P1 in `plot.md`; eventual K1 in `knowledge.yaml`.

Tests first: visible same-spot person; distant/nested-area exclusion; hidden/shut-away exclusion; unnamed label and protected parent name; command-named dedup; observation dedup; companion alongside/split/rejoin; group member versus direct reference; placement-text invalidation after self/ancestor movement; passive versus referred state wording; actual opening and turn payloads; unchanged non-narration/matcher context and facts. Preserve package isolation. Add only meaningful boundary tests, not every implementation detail.

Use the focused suites above, then the Ringer quick tier with relevant journeys and Ruff per `docs/testing-runbook/local-checks.md`. Set `TMPDIR=/tmp`, use `uv run python`, and set worktree `PYTHONPATH` to its own `packages/worldkeeper/src` so the main checkout's symlink cannot silently supply World. Verify installed Ringer timeout support before using the documented 900-second check allowance.

Free captures: current control C; P = corrected people projection plus P1, frame still present; L = P minus frame sentence (K1). Exact P→L difference is the frame deletion. Inventory all starts and the later states in the table; report system/user/total characters and source of every added line. No ceiling increases. Inspect 1B fixture change before updating it. Do not use the 1A-only prompt-capture script as evidence for all scenes.

### 2. Presence/location probes

Preregister C/P/L on opening, c4 and c5, **12 samples per arm per endpoint: 108 requests, ~399.6 neurons**. Run same-day controls, interleave arms, identical model/settings/script/entry facts. P isolates adding correct presence information; L versus P isolates frame removal. This differs from rejected Amendment 18 by preserving authored placements, scoping state instructions correctly, testing the opening, and separating causes. Do not infer c5's THINGS addition from c4: compare its actual diff.

Location gate for L: opening identifies Michelle 12/12; radio cue exactly once 12/12; no look-alike, rescue, greeting or unearned emotional reunion. c4/c5: no search, stranger, second reunion or incompatible location; c5 cake question at least 10/12 and no fewer than same-day control; unrelated c5 plan exchange at most 1/12. Raw malformed and missing/invalid segment text 0/12 at each endpoint; no story-breaking invention or committed impossible state. Ordinary acknowledgment is not a failure. Record recitation without claiming this arm should cure it. If P passes and L fails, retain the frame pending a new diagnosis; do not ship the intended frame removal anyway.

### 3. Speech mechanism probe, before building a schema

Prepare frozen C/S payloads changing **only** the speaker template above. Keep the current bio, SCENE, facts, handoffs and presence constant within this comparison. Ringer owns the small formatter/test change (`cloudflare.py:1622`, speaker-line tests, knowledge/prompt tests). Exact byte diffs must show only that template replacement; verify the filtering and one-line format remain intact. This is source replacement using the proven subtractive workflow, with an unproven new header.

Endpoints c4, c5, c9; 12 samples × 2 arms × 3 endpoints = **72 requests, ~266.4 neurons**. A same-day control must reproduce bookkeeping recitation at least 4/12 at c4; otherwise report “not reproduced,” not a causal win. Win: c4 bookkeeping recital at most 1/12 and at least four fewer than control; c5 no invented memory or premature answer, question at least 10/12 and no fewer than control, unrelated plans at most 1/12; c9 repeated handover/signal at most 2/12 and at least four fewer than a reproducing control. All identity, content-validity and story-breaking-error gates from step 2 apply. Current expiry dialogue is allowed; historical handover replay is not. A c4-only win does not close O4.

If S passes some endpoints but fails others, report separately; no global adoption on an averaged score. Do not roll out a universal template that worsens another scene just because it saves characters.

### 4. Conditional experiments; choose from evidence, do not run all

- **H (handoff answer ownership):** only if residual c5 answer invention reproduces. C/H at c5, 12 each = **24 requests, ~88.8 neurons**. Require the control to show at least 2/12 competing answers/false memories; candidate 0/12, correct lead-up and composed answer 12/12, no new syntax/content/identity failures. Existing ordinary-NPC dialogue tests must still pass. Keep all other instruction conflicts for separate study.
- **U (authored utterances):** if S fails the recitation gate, test the exact six replacement utterances first as frozen payload substitutions, without building the schema. C/U at c4/c5, 12 each = **48 requests, ~177.6 neurons**. Same recitation/proof gates as S; no new unrelated speeches or repeated reunion. A win licenses a tests-first schema/loader implementation, not immediate adoption. Target `models.py:164`, `loader.py:1493` load/validation path, `knowledge.py` only if needed for audience-safe projection, and `cloudflare.py:1622`; tests in package loading, voiceable knowledge, knowledge projection/leakage and transport. Prove absent-field fingerprint compatibility, unknown/blank-speaker rejection, audience isolation, unchanged facts/guard permissions, and byte-identical implemented-versus-probed payloads. No automatic migration of other statements.
- **Historical truncation check, only if useful to a decision:** exact saved Amendment 18 C/L c4 payloads, fresh same-day 12 each = **24 requests, ~88.8 neurons**. This measures the old two-change arm, not the corrected candidate. Retain sample 8 and missing-text sample 11 in the historical result. If new sample failures recur, inspect token limits, repetition, raw shape and decode outcomes; do not increase the output cap or silently drop failures. One clean batch cannot prove the prior failure was noise. At most one preregistered confirmatory pair; no rerun-until-green loop.

All optional runs require their own written preregistration and billed authorization. No retries/replacements in diagnostic replay; retain transport errors as outcomes. If a changed candidate is retested later, both arms get the same script and twelve samples again.

### 5. Combine, then qualify

Free first: capture the independently supported combination at opening and every command, both A realization orders, all affected scenes, and key movement states. If neither speech candidate wins, do not present the combined objective as complete. Test scene-global filtering, no private text leakage, preserved authored handoffs, radio custody, unchanged reveal earning and rollback/save-load.

Combined C/final frozen check: opening, c4, c5, c9 × 12 × 2 = **96 requests, ~355.2 neurons**, same-day controls. Require all corresponding endpoint gates above. This detects interactions; isolated wins do not guarantee a combined win.

Other-scene behavior checks: C/final paired 12 at each initially changed scene opening (1B, 2A, 2B, 2C) and two material later states (3B office co-location, 3C Rebecca co-location): **144 requests, ~532.8 neurons**. Apply the table's gates with zero early disclosure, forced confrontation or contradiction, plus valid content 12/12. Both 2B entry variants must be represented in the preregistered state set (six of each per arm); this does not give twelve independent samples for each variant. Include normal NPC answer fidelity if S changes the global template. Expand endpoints only if the offline inventory discovers another changed behavior; state added costs before billing.

Then identical full nine-command 3A scripts, **12 replicates per arm**, including opening: minimum **240 narration requests, ~888 neurons**, plus separately budgeted matcher/recovery/judge requests. Read every composed turn. Correct question and proof answer, quiet moment once, required reveals and earned exit in every replicate; zero repeated reunion, invented shared memory, committed impossible state, or repeated c8 handover/signal. Record harmless staging/cosmetic detail separately. The frozen c9 allowance of 2/12 is a diagnostic improvement gate, not closure of a completed-action replay in a release qualification.

Alternate A-r2-first and 2C transmit/alarm histories require matched journey coverage too before claiming those paths qualified; prepare their exact existing/approved scripts and request counts in the preregistration. They are not covered by the primary-script cost above. Do not claim a full-story outcome from the primary rescue-path run.

**Cost planning:** core steps 2/3/5 above total 660 narration requests, about **2,442 neurons**, excluding conditional H/U/truncation work, additional branch journeys, matchers, recovery and judges. This is a staged maximum for those listed batches, not a request to run everything now. Stop an unsuccessful route before paying for its downstream qualification. Prefer the free payload/provenance work first.

Finish with the full deterministic suite/coverage gate and Ruff per the runbook, at most one full-suite run at the end unless a new failure/change justifies another. Refresh shard metadata for new tests; do not increase prompt-size limits. Update the applicable testing-runbook entry if a procedure changes, not with dated counts. Keep detailed results and remaining work here. Staging follows merge to `main` and the SHA-bound staging deployment; production promotion is a separate authorized action under `docs/railway-production-promotion.md`.

### Limits of the evidence

Twelve replays of one prompt are correlated and often collapse to a handful of text paths. Even under independent sampling, zero failures out of twelve gives roughly a 22% one-sided 95% upper bound, not evidence of a near-zero production error rate. One truncation versus zero does not distinguish a prompt regression from sampling variation. Matched same-day arms, preserved raw outcomes, and stateful qualification provide better evidence; none warrants discarding the original miss. Do not merge counts across different bios, prefixes, prompt forms or days into one claimed rate.

## Shortest path to a pull request

The older plan reports an existing draft PR; this pass did not query GitHub. Continue that review branch if it still exists rather than assuming a new PR is needed. A documentation-only plan can be reviewed now. A presence-only draft is also reviewable after deterministic checks, clearly marked unqualified, but it does not satisfy the holistic goal.

For implementation readiness:

- **Block:** leaked identity/knowledge; missing opening identity/cue; 2B audit pacing broken; golden changes without explained contract; fact/custody corruption; false cake memory or question/answer mismatch; new malformed or missing-text output in candidate gates; repeated completed acts; failure of required reveals/exit; unrelated scenes regressing.
- **O1/O2:** preserve opening/earned-reunion separation and tolerate ordinary looking/approach. Recitation remains an explicit defect until the speech gate passes; a new THINGS line alone does not close it.
- **O3:** a cake keyword is insufficient. The question, narrator lead-up and appended answer must fit; no invented calendar/memory theory. Keep the handoff's actual authored answer.
- **O4:** radio world effect remains correct, but c9 repeat is open. No claim that the old-bio improvement survives; no new c9 story rewrite is bundled here.
- **O5/O6:** cosmetic keypad and isolated official caution remain accepted known items if they do not invent a capability, stop the action, or change who gives the signal.
- **O7/O9:** preserve the 1A deadbolt and stale-placement/provenance fixes. Raw self-custody proposals are recorded separately from validation/commit defects. Bench Ringer PASS is not the narrator experiment's win.
- **O8:** deep-turn size stays open in 3A/3B/3C. Report actual deltas, retain speaker limits, and never raise a ceiling. The older plan records Brandon's specific exception; verify its scope before merge rather than treating it as unlimited permission for further growth. Prefer the smallest candidate that passes safety/quality gates.
- **O10:** retain accepted R wording and the removed stale bio goal. Do not reopen an already rejected pressure rewrite as a new cure.

Brandon can review a draft with known O2/O4 defects, as the historical record already did. A PR claiming this plan's objective is solved must meet the new gates. Any decision to ship with remaining failures must state them explicitly; do not quietly redefine success. Full-script qualification and the still-unmeasured bio effects in 1C/2A/2B remain visible work, not implied passes.

## What not to do

- Do not apply Amendment 18 unchanged, change state guidance for every visible person, or update goldens mechanically.
- Do not delete the six speaker lines, hide reunion statements with a companion effect, trim away Michelle's organizing role, or move “Michelle was among them” into the opening again without a distinct, preregistered hypothesis.
- Do not equate participants, `together`, companions, group membership, visibility and immediate contact.
- Do not rewrite both biographies, facts, pressure, prompt rules and schema in one arm.
- Do not add “never say reunited,” parse narration with keywords to gate play, synthesize placement sentences, or hard-code this story in shared runtime.
- Do not spend a schema migration before testing its exact narrator-facing words.
- Do not fix the separate-study instruction conflicts across the whole project in this work.
- Do not call a frozen-prefix state a live history, a valid JSON object valid content, or a prior-day control a causal comparison.
