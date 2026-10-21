You are helping with Freytag Forge, an interactive-fiction engine where a small LLM narrator
writes each turn from a prompt built out of authored story material, and the engine, not the
narrator, owns world facts. Your job is to write an implementation PLAN (not code, not story
prose) that fixes one open problem in Scene 2B, using only techniques already proven in this
project unless none covers the case.

## Reference these files 
- .plans/implementation_plan.md  (read "Resume here", Stage 5, Stage 7, and the
  "Offline consistency fixes" section)
- docs/scene-fixing-guide.md  (the required diagnosis order)
- docs/world-model-grounding.md
- docs/narrator-writing-guide.md
- docs/player-input-guide.md
- the story package: plot.md (scenes 2A and 2B), knowledge.yaml, handoffs.yaml
- bench/results/stage7-door-n12/review-summary.json and
  bench/results/stage7-door-source-n12/ (summaries only)

## The problem
In a raw free-text blind-player run (84 turns, all 9 scenes, staging 8aba3ba3), Scene 2B was
the only scene that failed to play. 14 of its 15 turns were stuck, and the scene ended on a
forced handoff with no earned reveal.

Observed chain:
1. The 2A exit narration (turn 7) invents "a small, unmarked door with a keycard reader and a
   ventilation grille". No authored text declares it.
2. The player takes it up. In 2B it asks for "inspector credentials" and searches "financial
   data" for an ID and password.
3. The first 2B reveal, k_sl_2b_a_r1, needs the player to name Michelle's file or the
   selection files. Nothing in the 2B entry text or the 2A handoff points there. The 2B
   Details lines ("government data; financial data") and the janus_evidence cue in
   handoffs.yaml ("Government and financial records sit open beside them") make "open
   records" the visible object instead.
4. Secondary: the narrator repeats the same "sits down at one of the archive terminals"
   paragraph on every 2B turn. The 1A exit was a silent transition.

## What has been tried (do NOT re-propose the negative ones)
In Scene 2B / 2A, all negative or inconclusive:
- Rewording the 2B cue (N=12 per arm): control 0/12 hits, B ("Michelle's file is one of
  them") 0/12, C ("One file carries Michelle's name, and another carries Kristin's") 2/12.
  Not distinguishable. Cue wording is a weak lever. Shipped cue unchanged.
- 2A turn-7 prompt wording screen (6 arms x 12): control 7/12 reveals earned; review 3/12;
  stale-scene 3/12; wording 4/12; fixed-control 5/12; bridge-deletion 4/12. The invented
  access detail appeared in 12/12 rows of every generated arm. Bar was at least 10/12 reveals
  and at most 2/12 invention. No arm met it. All four edits dropped.
- 2A source screen (3 arms x 12): control 7/12; removing the stale perimeter sentence 5/12;
  restoring the 2A.3 console-limits statement 6/12. Both dropped.
- Reading so far: the pull toward an invented door is in the framing of the 2A turn-7
  material (for example "concealed route or access panel"), not in the lines tested.
- Still untested lead: a story-neutral ablation of the "Finish each action the player gives"
  instruction against search-to-discovery. The other option is to guard the invented route
  on the 2B side.

Proven techniques from other scenes (prefer these; the guide says to check them first):
- Scene-fixing guide step 1: find the SCENE line, talk line or stale recall that pulls the
  narration the wrong way. Past successes: 3B's missing 3B.2 office-entry line, 3A's captives
  talk line, 2C's silent stance, 2C's stale 1A recall.
- Reveal handoffs (handoffs.yaml) to put missing story material where the player sees it.
- Statements written in ChatGPT Desktop and scored with the real matcher (_matches_all).
- Scoped aliases: the photo/photograph alias fix cut narration-leak rejections from 6/36 to
  0/36 (p = 0.012).
- Recent-cue referent projection and evidence-append for bare nouns (Stage 4). It fixed the
  1A "Search the gap." miss and the 3A "Lead the captives through the emergency gate." miss.
- Negation-scoped command handling (Stage 5), which fixed the restraint-clause cases.
- The one narrator rule that won: "When the player talks to someone, that person answers."
- Rules that LOST and must not be retried: the go-into-a-place rule (1/15 vs 4/15), the
  plain-corridor rule, the copy-refers rule.
- Other-scene invention precedents: 1A invented an "old warehouse" meeting; 1C a "biohazard
  containment zone"; 3C a hidden panel and corridor. All three are narrator invention that
  pulls the player off the scene. Check how, or whether, each was handled in the plan before
  proposing anything.

## Constraints (hard)
- Facts are the sole mutable world truth. Shared runtime stays story-agnostic. Story-specific
  fixes go in story material, not runtime code.
- Fix the material at the source; add narrator rules last, and only story-neutral ones whose
  probe arm wins. Never use regex to patch narration.
- Prefer subtractive fixes (remove a pulling line) over adding constraints.
- Any new rule is written at a 12th-grade reading level, plain words, one idea per sentence.
- Read the grounding guide before declaring or placing any story thing or writing any prompt
  line about places. Anything the narration invents must be a declared world entity.
- Every probe is billed. Each needs a stopping rule fixed first, a smoke run (n=1) before
  n=10-15 per arm, one Ringer task per run unit, every attempt recorded, and guards on every
  model endpoint call. Score the narration plus appended delivery text, not item_facts.
- Player commands in any probe are first-person imperatives, per the player-input guide.
- Do not propose changes to the judge, a pipeline migration, or production promotion.

## What I want back
A plan with these parts, in order:
1. Diagnosis check. Which scene-fixing-guide step is still unfinished? Read the recorded 2A
   turn-7 prompt beside plot.md 2A and name the specific line or framing that pulls "keycard
   reader / concealed route" in, quoting it. If you can't see the prompts, say what you need
   instead of guessing.
2. Ranked candidate fixes, at most 4. For each: the technique and which earlier success it
   copies, the file it edits, and why it differs from the already-negative arms above. Include
   the "Finish each action" ablation and a 2B-side guard (for example, declaring the door as
   a real 2A entity and giving it a defined outcome so the player is not sent on a dead-end
   chase) as candidates, and say which you would run first and why.
3. For each candidate, a probe design: arms, n per arm, the exact success bar (earned-reveal
   count by command 2 and unsupported-invention count, as in the earlier screens), the
   stopping rule, the smoke step, and the spend cap.
4. What would count as done, in the form used by Stage 7: a replicate run of 2A to 2B showing
   a reveal earned by free-text play, plus a check that no earlier-scene behavior regressed.
5. Risks and what the plan does NOT establish (one story, temperature zero, a single recorded
   2A sample, and so on).

Keep it short enough that an engineer can execute it. No story prose. Name every file you
checked. If a claim isn't supported by the attached material, label it a guess.