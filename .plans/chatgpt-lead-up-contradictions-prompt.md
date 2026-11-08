# ChatGPT prompt: lead-up text that contradicts, repeats or pre-empts the authored delivery (scene 3A)

Paste everything below the line into ChatGPT Desktop. It has the project files open, so it reads them itself. Bring the plan back to Claude Code,
which applies approved changes through Ringer tasks (tests first) and probes them.

---

## Task

On turns where the game has already selected an authored handoff, the engine composes the player-visible turn from two parts: a model-written lead-up,
then the package's authored delivery text, appended verbatim. In the live scene 3A runs recorded below, the composed turn sometimes reads wrongly
because of how the lead-up relates to the appended delivery. Read the record, **establish the causes and the evidence yourself**, and write one plan
that proposes fixes at the source, in the order `docs/scene-fixing-guide.md` ranks them. Do not assume any single cause covers every case. State, for
each proposed change, what must be approved by Brandon, what is a story-text proposal for ChatGPT Desktop to author, and what is an engine change for
Claude Code to build through Ringer.

Write the plan to `.plans/lead-up-contradictions-plan.md`. Edit it in place on later rounds; do not regenerate it.

## What to read first

- `AGENTS.md`, `docs/scene-fixing-guide.md`, `docs/narrator-writing-guide.md`, `docs/world-model-grounding.md`, `docs/contributor-guide.md`, and the
  parts of `docs/PRD.md` that say what the narrator may be shown on a handoff turn
- `.plans/shared-narrator-instruction-conflicts-plan.md` and `.plans/shared-narrator-instruction-conflicts-prereg.md` (every experiment section, in
  particular G, GU, GU2, GUE1 and L, each with its question, arms, rubric, result and what was kept), and
  `.plans/astra-3a-things-and-speaker-lines-plan.md`
- The story package: `data/stories/continuity-initiative/` (`plot.md` scene 3A, `knowledge.yaml` entries `k_sl_3a_*`, `handoffs.yaml`, `world.yaml`)
- Code that builds and composes these turns: `storygame/runtime/cloudflare.py` (`_authored_handoff_rules`, `_turn_rules`, `_system_prompt`,
  `_section_user_prompt`, `_speaker_constraint_lines`, `_speaker_context`), `storygame/runtime/engine.py` (`_prepare_handoff` and the handoff
  composition), `storygame/runtime/candidate_matcher.py` (`uniquely_matched_authored_handoff`), `storygame/runtime/knowledge.py`
  (`_established_for`, `is_narrated`)

## The recorded evidence (local and gitignored; read the rows, not only the counts)

| Path | What it is |
| --- | --- |
| `bench/results/shared-narrator/live/control-r1/` and `final-r1/` | Experiment L smoke pair: the nine-command 3A script played live on the shipped commit (`control`) and on the current working tree (`final`). `all-turn-records.json` holds every turn's recorded prompt, model text and appended text; `summary.json` the run |
| `bench/results/shared-narrator/g/sheet-GUE1.md`, `key-GUE1.json`, `scores-gue1-blind.json`, `frozen-GUE1-{OLD,EMB}.json`, `gue1-*-rows.json` | Experiment GUE1: 48 frozen-payload replies on the two reunion turns, old versus new delivery text |
| `bench/results/shared-narrator/g/` `sheet-{G,GU,GU2}.md`, `key-*.json`, `scores-*.json`, `frozen-{C0,G,GF,GU,GU2}.json`, `*-rows.json` | Experiments G, GU and GU2: frozen-payload replies at 3A commands 4, 5 and 9 |
| `bench/results/shared-narrator/baseline/baseline.json` | Free captures of the production payloads (openings, ordinary and handoff turns, recovery) |

The final-state story text under test is uncommitted in the working tree (`git diff` for `knowledge.yaml`, `handoffs.yaml`, `storygame/`,
`packages/worldkeeper/`, `tests/`). `scripts/ringer/shared-narrator/` holds the capture, replay, scoring and manifest scripts for every experiment.

## What was observed

In the `final-r1` run of experiment L, read every turn and compare each lead-up with the delivery appended after it. Compare against `control-r1`.
Turns 1, 4 and 6 are where the composed text first read wrongly to Brandon; look at all nine and at the GUE1 rows.

## What I need back

1. For every composed turn in the two live runs, whether the lead-up and appended delivery agree, repeat each other, or conflict, with the quoted
   text and the turn's recorded prompt as evidence.
2. The cause of each kind of mismatch, established from the recorded prompts, the story text and the code, and checked against the earlier
   experiments' rows. Say what you could not establish.
3. A plan of fixes ranked as `docs/scene-fixing-guide.md` and Brandon's standing positions rank them (see the notes in `.plans/` and `AGENTS.md`):
   the exact allowed-line diffs or story text proposals, what each would be probed against, and the win rule you would preregister. Nothing in the
   plan is applied until Brandon approves it.
