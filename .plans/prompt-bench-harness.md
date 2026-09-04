# Build prompt — narration prompt bench for freytag-forge

Paste the section below to an agent working in `~/dev/freytag-forge`. Everything
it references has been verified to exist at the paths given.

---

## What to build

Build a local **narration prompt bench** for this repository: a two-mode tool that lets
one person try many prompt and story variations against the Llama-3.1-8B narrator and
find out, with defensible numbers, whether a variation actually improved anything.

**Mode 1 — `chat`.** An interactive session against the real engine and the real hosted
narrator, so a human can play turns, type unexpected things, and read the narration that
comes back with the exact prompt that produced it displayed alongside.

**Mode 2 — `bench`.** A non-interactive runner that plays scripted turns, grades the
result with the project's existing LLM judge, and reports whether a variation differs
from a baseline by more than measurement noise.

Both modes share one code path to the model. A number the bench reports must come from
the same machinery the chat mode exercises.

## Why this is worth building

Today, measuring a single prompt variation costs roughly twenty minutes: the change has
to be merged to `main`, clear CI, deploy to Railway staging, be confirmed live via
`GET /api/v1/health`, and then be measured by a nine-scene Playwright run — of which
about one in three dies on infrastructure. Twelve measured runs took about four hours of
wall clock.

None of that is necessary for prompt iteration. `CloudflareTurnProvider` reads its
configuration straight from the environment and posts to a Cloudflare Worker, so the
whole narration path is reachable in-process from Python with no deploy, no merge to
`main`, and no HTTP server. The deploy loop exists because the *browser* E2E must run
against hosted staging — it is not a property of the narration path.

## Ground truth you must reuse, not reimplement

Reimplementing any of these silently produces numbers that cannot be compared to anything
already measured. Import them.

| What | Where | Note |
|---|---|---|
| The judge | `frontend/e2e/roleplay-judge.js` → `judgeSceneNarration({sceneId, opening, turns})` | JavaScript. Call it; never port it. |
| Scene canon assembly | same file → `sceneCanon(sceneId)` | Slices `plot.md`, `storylets.md`, `storylet-routes.yaml` to the scene; passes `pacing.yaml` and `world.yaml` whole. |
| The narrator provider | `storygame/runtime/cloudflare.py` → `CloudflareTurnProvider.from_environment(state)` | Needs `CLOUDFLARE_WORKER_URL` and the worker token from `.env`. |
| The turn loop | `storygame/runtime/engine.py` → `RuntimeEngine(state, provider).turn(input_text, clock_seconds=None)` | Same call `web_demo.py:236` makes. |
| Session bootstrap | `RuntimeState.bootstrap(package)` | See `storygame/web_demo.py` for the canonical wiring. |
| The prompt itself | `CloudflareTurnProvider._turn_instruction()` and `_tagged_user_prompt()` | This is what variations vary. |
| The model | `@cf/meta/llama-3.1-8b-instruct-fast`, selected in `.plans/cloudflare.js:53` | Overridable on the Worker via `CF_AI_MODEL`. Do not change the default. |

The judge is JavaScript and the engine is Python. Resolve that by having the Python side
write turn records to JSON and a thin Node CLI read them and call `judgeSceneNarration`
unmodified. Do not translate the judge into Python.

The turn record the judge expects is built at `frontend/e2e/scene-runtime.spec.js:220-226`:
`player_input`, `narration`, `left_scene`, and `beats_projected` (from the proposal's
`delivery.beats_projected`). Match that shape exactly.

## Where it lives

**In this repository**, under a new top-level `bench/` directory, as a development-only
tool. It must import the engine, the judge, and the story packages, all of which live
here; a separate project would have to vendor or path-hack into three moving targets and
would drift from them within a week.

Constraints on that placement:

- `bench/` is excluded from the shipped package and from coverage gates. Check
  `pyproject.toml` for how packaging and coverage are configured and follow the existing
  conventions.
- It must not modify anything under `storygame/runtime/`. If a variation needs a seam
  that does not exist, add the seam as a parameter with a default that preserves current
  behavior, and say so explicitly in your report.
- It takes a story package path as an argument and must work on any package, not just
  `continuity-initiative`.

## Variations are data, not code edits

The core workflow requirement: **trying a variation must not require editing engine code
or switching git branches.** A variation is a small declarative file naming:

- a story package path,
- a system-prompt template (rules block, and whether the `<output_example>` is included),
- a user-prompt template (how beats are delivered — authored prose, `<beat_detail>` noun
  phrases, or something new),
- optionally, a player-input script to drive.

The bench loads a variation file, runs it, and reports. Two variations must be runnable
back to back in one command without touching the working tree.

Read `storygame/runtime/cloudflare.py` before designing this. The prompt is currently
assembled in code; find the smallest change that makes the two blocks substitutable from
a variation file without altering default behavior.

## What the bench must report, and what it must refuse to say

This is the part that determines whether the tool is useful or actively misleading.

**Single runs are noise.** Measured across twelve verified nine-scene runs, within-arm
standard deviation is **2.24 points on a 63-point scale**. Three prompt configurations
that differed materially scored 13.75, 13.00 and 12.25 — all statistically
indistinguishable. At four runs per arm the smallest resolvable difference is about
**3.87 points**.

Therefore:

- Default to **n replicates** of a variation, never one. Make `n` explicit in output.
- Report **mean, standard deviation, and a confidence interval**, not a bare score.
- When comparing a variation to a baseline, run a two-sided Welch t-test and **state
  plainly when the difference is inside the noise.** The tool must be willing to say
  "this changed nothing detectable." A tool that reports `+1.5 points` without that
  qualification will send its user chasing noise for days.
- Print the minimum detectable effect for the `n` actually used, so the user knows what
  the run could and could not have found.

**Two criteria are on the floor and need a finer signal.** Across 108 graded scenes,
`canon_consistent` passed **0 times** and `progressive` **3 times**. A boolean stuck at
zero has no gradient — it cannot show partial improvement, so a real advance would be
invisible until it crosses all the way to true.

So alongside the seven booleans, compute and report a **graded secondary metric** from
what the judge already emits: the count of `missing_or_wrong` entries per scene (fewer is
better), reported per criterion where attributable and in total. This gives a continuous
signal that can move while every boolean is still false. Present it as a *leading
indicator*, clearly distinguished from the 63-point score, which remains the metric of
record.

Note in your output that all seven booleans are weighted equally in the 63-point score
even though they differ enormously in difficulty, and that `canon_consistent` is 7 of
those 63 points currently unavailable to any configuration.

## Budget is a hard constraint, not a footnote

Two independent budgets are spent per run, and the first one to run out is not the
obvious one.

- **Cloudflare Workers AI neurons.** The free allocation is 10,000 per day and resets at
  **00:00 UTC**. A well-behaved 30-turn playthrough costs roughly 330 neurons. So one
  four-replicate nine-scene comparison costs about 1,320 — meaning **fewer than eight
  such comparisons per day.** That does not support "try a lot of variations" unless the
  tool is deliberate about spend.
- **OpenAI judge calls**, one per scene, nine per full traversal.

Requirements that follow:

- Support a **single-scene mode** (`--scene 1A`) costing roughly one ninth of the
  narration budget and exactly one judge call. This is the iteration loop; full
  nine-scene runs are for confirming a result, not for exploring.
- **Estimate and print projected spend before starting**, and require confirmation past a
  configurable threshold.
- **Track and report actual spend** per run.
- Detect quota exhaustion precisely: the turn endpoint answers **HTTP 429** with header
  `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`. The app's own rate limiter returns a
  *different* body, `{"detail": "rate limit exceeded"}`, which is worth retrying, whereas
  quota exhaustion cannot succeed until 00:00 UTC. Distinguish them by the header and
  stop cleanly on quota, reporting how much of the batch completed.

## Player input must vary

Narration is generated live specifically because the player types free text and the story
has to adapt. A bench that only ever replays one fixed input script will overfit prompts
to that single path and report improvements that do not survive contact with a real
player.

Support **multiple input scripts per scene** and report results per script as well as
pooled. Ship at least three for scene 1A: the existing E2E script, one that investigates
obliquely, and one that does something the scene does not anticipate. The engine's job is
to accommodate anything that is not game-breaking, so a script that wanders is a valid
test, not a broken one.

## How to prove the bench is trustworthy

A bench that measures something subtly different from the hosted judge is worse than no
bench, because its numbers will look authoritative. Validate it against measurements
already taken, archived at `~/bakeoff-data/`:

| Config | Branch | Fresh hosted result (n=4, nine scenes) |
|---|---|---|
| Arm A — beat prose + 3 prohibitions | `travel_and_clues` (6319757) | 15, 13, 12, 15 → mean **13.75**, sd 1.50 |
| Arm B — `<beat_detail>`, no prohibitions | `bakeoff-arm-b` (9d194a7) | 12, 12, 11, 17 → mean **13.00**, sd 2.71 |
| Arm C — `<beat_detail>` + prohibitions | `bakeoff-arm-c` (6a45574) | 12, 15, 13, 9 → mean **12.25**, sd 2.50 |

`canon_consistent` was false in all 108 scenes and `progressive` true in only 3.

**Acceptance criterion:** express Arm C as a variation file, run it at n=4, and confirm
the mean lands within the measured spread and that `canon_consistent` is 0/9 in every
replicate. If it does not, the bench is not measuring the same thing as the hosted judge —
investigate and report the discrepancy rather than adjusting the bench until the number
looks right.

Each archived run directory under `~/bakeoff-data/arm-*/run*/` holds
`e2e-llm-canon.json` (judgments), `e2e-llm-canon-progress.json` (every turn, including
the verbatim prompt under `by_scene[i][1].turns[j].prompt.{system,user}`), and
`run-meta.json`. Use them as fixtures so the scoring path can be tested without spending
either budget.

## Known trap: the package clock

The hosted E2E drives pacing through `frontend/e2e/package-clock-controller.js` with
`E2E_PACKAGE_CLOCK=1`. That controller is now **turn-based** — it validates milestones on
`target_turn` and explicitly rejects `target_seconds` — and the engine tracks
`turns_since_scene_entry` in its own state. `RuntimeEngine.turn()` takes an optional
`clock_seconds` and falls back to `proposal.narrative_seconds` when it is `None`.

It is therefore *plausible* that calling `.turn(input)` in-process reproduces hosted
pacing without injecting a clock at all — but **do not assume it.** Determine it
empirically against the archived baseline above, and state in your report which you found
and what evidence settled it. If pacing does diverge, reproduce the controller's schedule
rather than inventing one.

## Out of scope

Do not build: a hosted deployment of the bench, a replacement for the Playwright E2E
suite, a new judge or new criteria, changes to the story package content, or any change
to `main`. Do not run the browser E2E suite against a locally started API — that suite is
run only against hosted staging.

## Report back

State what you built and how to run it, the acceptance-criterion result with actual
numbers, what you found about the package clock, what the bench costs per run in both
budgets, and anything you could not verify. If the acceptance criterion failed, say so
plainly — a bench that disagrees with the hosted judge is an important finding, not a
failure to hide.
