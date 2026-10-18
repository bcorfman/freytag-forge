# ChatGPT prompt: a complete implementation plan for the 2A turn-7 door probe

Paste everything below the line into ChatGPT Desktop. It has the project files
open, so it reads them itself. Bring the answer back to Claude Code, which
turns it into Ringer tasks and runs them.

---

You are helping me test a fix for a defect in an interactive-fiction engine,
`freytag-forge`, and its story package `data/stories/continuity-initiative/`.
You can read the repository. Read these first, in order, and follow them:
`AGENTS.md`, `docs/testing-runbook.md`, `docs/scene-fixing-guide.md`,
`docs/contributor-guide.md`, `bench/README.md`, then `bench/core.py`,
`bench/cli.py`, `scripts/ringer/stage7/2b_cue_probe.py`,
`scripts/ringer/stage7/check_2b_probe.py` and
`scripts/ringer/stage7/2b-cue-n12.json`.

## Background

A hosted blind-player run got stuck in scene 2B because scene 2A's last turn
(turn 7) invented "a small, unmarked door with a keycard reader and a
ventilation grille". An earlier answer (kept at `/home/bcorfman/astra-solution.md`)
named three package edits to test, plus a player-wording arm and a bridge arm:

- `stage7-door-control`: no change.
- `stage7-door-review`: `pacing.yaml`, "A second credential check threatens
  their inspector cover." becomes "Their inspector cover faces a second review."
- `stage7-door-stale-scene`: two `knowledge.yaml` statements shortened.
- `stage7-door-wording`: the player command becomes "Search the service
  corridors for a route to the detention area."
- Bridge arm: in `plot.md`, drop "Beyond those corridors, the records archive
  waited behind another layer of security." from the 2A to 2B bridge.

The first four variations already exist in `bench/variations/stage7-door-*.json`.
The bridge arm does not.

## What already failed, and why

I tried to replay scene 2A with `python -m bench run --scene 2A --script
door-replay`, using the seven recorded commands (the script is inside each
variation). The result: the replay played 11 turns, turn 7's prompt did not
contain "credential check", and turn 7 was set in an "abandoned communications
center", not the service corridors. A scripted replay from bare entry does not
reproduce the hosted turn-7 situation (earned facts, placements, the pending
pacing event). The hosted run saved no world state, only prompts and transcripts.

What is saved: the exact narrator prompt (`system` and `user` text) for every
turn, in
`bench/results/stage7-blind-raw/attempt-1/e2e-blind-player-prompts.json`
(scene `2A`, turn 7), and the transcript in `e2e-blind-player.json`. All three
strings under test appear verbatim in the recorded turn-7 user prompt.

## The approach I chose

Replay the exact recorded turn-7 prompt. For each arm, apply the arm's text
edits to the recorded prompt, send the result to the same Cloudflare narrator
the bench uses, and judge the narration. This tests the wording, not pacing or
transition state. State that limit in your plan.

## Rules you must follow

- Billed runs: Cloudflare narration and the OpenAI raw player. Plan a free
  dry run, then a 1-per-arm smoke, then the full run. Put hard call caps inside
  the script.
- Unit tests and the dry run never need a live worker or network.
- One Ringer task per independent run unit. A Ringer check is killed after 60
  seconds unless the task sets `check_timeout_s`; set it for slow checks.
- Ringer workers cannot run `uv`; use the main `.venv` with `PYTHONPATH`.
- Never use keyword or regex scanning of narration as the acceptance gate.
  Narrations are judged by reading them. A keyword count may only be a
  disclosed triage aid.
- Reuse the bench's narrator call path so the model, temperature, output schema
  and validation match the hosted narrator. Do not invent a second client.
- Do not edit tracked story files. Arms are variation overrides or prompt text
  edits. Do not edit the recorded fixtures.
- Keep the harness under `scripts/ringer/stage7/`, results under
  `bench/results/stage7-door-*` (gitignored), and follow the repo's ruff format.

## What I need from you

A complete implementation plan, not a sketch. Cover each of these:

1. **Prompt source.** The exact way to load the turn-7 prompt from the JSON
   fixture, and a pre-flight assertion that each arm's old text occurs exactly
   once in it (fail loudly if not). Say how the wording arm's command is
   swapped inside the prompt, naming the exact place the command appears in the
   `user` text, and confirm by reading the fixture.
2. **Narrator call.** Which function in `bench/core.py` or the provider layer
   sends a prompt and parses the segments, and how to call it with a raw
   `system`/`user` pair while keeping validation and the spend ledger. If no
   such entry point exists, say the smallest safe wrapper and where it lives.
3. **Arms and trials.** The arms (including the bridge arm and how it works with
   a fixed recorded 2A output), 12 trials per arm, interleaved in rep-major
   order, with the call caps worked out.
4. **Scoring.** What a human or judge reads in each narration: does it create
   an undeclared access obstacle or credential requirement, does it respect the
   place and the attempted action, does it stay within the declared things. Say
   exactly how the reading is recorded (a per-row verdict file) so Claude Code
   can read every row. Say how the 2B continuation (compose the exit with the
   bridge and 2B entry text, let the raw player pick command 1, then command 2,
   score with the real matcher `_matches_all`) reuses
   `scripts/ringer/stage7/2b_cue_probe.py`.
5. **Ringer task breakdown.** The manifests, one task per run unit: names,
   `task_type`, files each task owns (disjoint), the exact commands, the check
   command that executes something and prints why it fails, `check_timeout_s`,
   and the order (dry run, smoke, full). Write each spec as a self-contained
   brief a worker can follow with no other context.
6. **Acceptance bar.** The screening bar from the earlier answer, restated, and
   what result means "adopt", "run live scene replicates", or "drop the arm".
7. **Risks.** Where the prompt-replay differs from the hosted run, and what
   would make the result misleading.
8. **Unverifiable items.** Anything you could not check from the files.

Do not write the code. Give the plan, file by file and step by step, with exact
commands, names and file paths.
