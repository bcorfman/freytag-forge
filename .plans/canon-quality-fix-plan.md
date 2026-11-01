# Canon quality fix plan

Status: plan only; nothing applied, nothing billed. Step A approved by Brandon 2026-11-01; waiting on ChatGPT Desktop's `.plans/canon-quality-diagnosis-plan.md`. Written 2026-11-01 after the first complete hosted canon sample (`bench/results/staged-1abb54b0/canon/`, SHA `1abb54b0`, 25 of 63). Harness work is finished (see `.plans/chatgpt-canon-stall-diagnosis-plan.md`); everything below is about the judged quality of the story, not the test.

## Resume here

1. Run workstream A (ChatGPT establishes the evidence). Do not diagnose scenes myself first.
2. While it runs, do workstream B (judge-input faults) for whatever A confirms; judge faults are fixed before any comparison ([[fix-known-judge-faults-before-comparisons]]).
3. Then C (3C `protected_safe`, the one safety result), then D (cross-scene quality). Only after that, one measured canon batch (E), each run separately authorized.

## Status log

- 2026-11-01: Workstream A done (`.plans/canon-quality-diagnosis-plan.md`); its code and artifact claims were checked against `engine.py`, `scene-runtime.spec.js`, `roleplay-judge.js`, `authored-spans.js` and the saved run: they hold.
- 2026-11-01: Brandon approved F1-F3 (offline), then "the others": F4 (journey rewrite, after an offline eligibility check), F5 (delete the Brandon-beside-controls sentence, `knowledge.yaml:2560`), the story-data arm of F6 (`pacing.yaml:233`), F7 (exit rubric). Not approved: any billed probe, re-judge of the saved sample, or hosted run.
- Ringer run `canon-quality-fixes` (manifest `/home/bcorfman/dev/ringer-work/canon-quality/manifest-round1.json`): round 1 = F2 partition fix + F3 read-only scout. Next: round 2 = F1 (judge evidence, owns `roleplay-judge.js`), F5 + F6b (data edits), F4 eligibility scout; then F7 after F1 (same file).
- 2026-11-01: Applied on branch `canon-judge-evidence` (all offline, nothing billed, nothing merged): F2 `ec62a5d1` (all entry segments are the next scene's opening); F3 `e4826509` (engine keeps action prose and bridge on verbatim-event exits; 1C stall test rewritten, resume-path test added); F1a `38ba4fbf` (ending and verbatim pacing lines attributed as authored); F1b `997cbff2` and `99f3753a` (judge gets cross-scene knowledge, runtime deliveries, protected-fact inventory incl. world-only); F5/F6 data `4fc9dd77` and 3B r2 `dc975ebb`; F4 `390b790f`, 1A prompt `7f224e0a`; F7 `8f4f153b` (exit rubric reads departure + arrival + earlier turns); 3C seven-action script `d84a92b5` (ChatGPT plan `.plans/canon-3c-resolution-spread-plan.md`; offline replay earns A1..E1 on 3C turns 1-7, completes turn 7, no deadline fallback).
- Journey changed (1A, 2B, 2C, 3C): canon results from `390b790f` on are NOT comparable with the staged-1abb54b0 sample (25/63). 2B now earns the bait reveal (k_sl_2b_b_r3), not Brandon's confession branch (k_sl_2b_b_r1).
- Open: plot.md:798 still carries "Brandon waits beside the broadcast controls" (authored plot, left alone). F7 check (no sheet; the first one was deleted as unusable): Brandon replies with the numbers where he disagrees with Claude's pass/weak/fail read of the 8 saved departures (fails: 1A->1B, 2B->2C; weak: 1C->2A, 2C->3A, 3A->3B); his answer decides whether the exit rubric stays or must require a named destination. Saved sample not re-judged (billed). Next measured step needs a merged and staged SHA and Brandon's per-run authorization with a cost estimate.

## What the one sample shows (facts from the artifacts, not conclusions)

- Complete run: 75 turns, nine scenes, `story_complete_seen` true, nine judgments. Scores by scene: 1A 2, 1B 4, 1C 3, 2A 5, 2B 3, 2C 2, 3A 1, 3B 4, 3C 1.
- `protected_safe`: true in 8 of 9 scenes; false in 3C. The judge cites unrevealed Phase Two material and Charles's deluge framing in narrator prose (3C turns 3–4 and 14 in `e2e-llm-canon-progress.json` `by_scene` → `3C`). Whether those facts were in `revealed_knowledge` at that turn is not yet established.
- `exit_motivated` false in 7 of 9 scenes. 1A's departure turn narrates only "The patrol is coming back to the house." (turn 9, no authored span). 2C's departure turn carries a `bridge` authored span.
- Authored pacing-event lines (1A turns 5 and 9: officer enters, patrol returning) carry no `authored_spans`, and the judge called them invented ("federal patrol, officers entering the house, and a detective").
- Each scene runs the scripted prompts in a cycle after its reveals; 3C's "Read the recovered fragment describing what was meant to follow" returned nothing on turns 5 and 10. The judge's `rewards_investigation`, `progressive` and `rich` fail mostly on these repeated turns.
- No turn drew a clarification, so #740's path was not exercised live.
- One sample. Within-arm variance is as large as between-arm gaps ([[hosted-canon-judge-run-procedure]]); no number here is a baseline.

## Ground rules for every step (all from the record)

- Fix order: read the recorded prompt beside `plot.md`; probe one arm per candidate cause (10–15 samples, Ringer, read every narration); fix the source: missing material to ChatGPT Desktop, a pulling line scoped or removed, a story-neutral rule only if its probe arm wins ([[narration-fix-strategy-ranking]]; `docs/scene-fixing-guide.md`). Remove before adding. Never regex or keyword gate narration.
- Recommend only techniques already proven; name what was checked ([[recommend-only-proven-techniques]]). Checked so far: scene-fixing guide steps 1–4, and its record of what won (reveal handoffs, scoping a stale or hijacking line, restoring a missing plot sentence) and lost (go-into-place, plain-corridor, copy-refers rules).
- Brandon cares about inventions only when they break the story, and judges scenes by earned transitions at 80% or more over multi-turn runs, not by short windows or invention counts ([[invented-details-matter-only-if-story-breaking]], [[scene-bar-is-earned-transition-80-percent]]).
- Not scene 1 again: this plan starts from the whole-game pattern ([[step-back-to-whole-game-trends]]).
- Any plot, pacing or story-data change is marked as such and waits for Brandon's approval; story judgement goes to ChatGPT Desktop with a short pointer prompt that carries none of my conclusions ([[chatgpt-establishes-the-evidence]]).

## A. ChatGPT establishes the evidence (first, free)

Hand `.plans/canon-quality-fix-prompt.md` to ChatGPT Desktop. Its output replaces the "What the one sample shows" reading above wherever they differ. Required result per failed boolean per scene: cause class (judge input, scripted-prompt artifact, missing material, pulling line, or noise), the artifact lines proving it, and the proven technique that fits.

Done when: `.plans/canon-quality-diagnosis-plan.md` exists and I have checked its claims against the code and artifacts before acting ([[verify-plan-questions-against-code-first]]).

## B. Judge-input faults (only those A confirms)

Candidates to verify, not assumed: pacing-event text not marked as runtime-authored for the judge; the exit judged on departure prose that excludes the authored arrival or handoff; cycling filler prompts counted against `rewards_investigation` and `progressive`. Fix through a Ringer task in `frontend/e2e/roleplay-judge.js` and the canon spec, with offline fixture tests; no billed call. Free check: re-judging saved turns costs OpenAI calls, so ask Brandon before any re-judge of the saved sample.

## C. 3C protected-safe

First read the 3C recorded prompts and the revealed set at turns 3–4 against `plot.md` and `knowledge.yaml` (free). Then, by A's cause: judge fault goes to B; material or a pulling line goes to the scene-fixing workflow with a three-replicate bench script on 3C and the earned-transition bar. Success: `protected_safe` true in 3C on the next measured canon batch, with the safety verdict never traded for prose quality.

## D. Cross-scene quality

Only what A shows is real after B: for example, one shared cause behind `exit_motivated` across seven scenes is a whole-game win; per-scene prose richness is not worth a scene-by-scene campaign. Choose the single shared lever first and measure it on every scene.

## E. Measurement

A canon batch needs several complete runs and a plain statement of whether the arms are distinguishable at that sample size. Each billed attempt needs Brandon's explicit authorization and a cost estimate (about 460 s and 75 turns last time). Runs happen only against a merged and staged SHA, one Ringer task each, never during a deploy.

## Open decisions for Brandon

- Approve workstream A as the first step.
- Whether `exit_motivated` and `rich` are bars he wants enforced as judged, or tuned (a judge-rubric change is a measurement change).
- Whether any plot or pacing change is on the table; none is proposed here.
