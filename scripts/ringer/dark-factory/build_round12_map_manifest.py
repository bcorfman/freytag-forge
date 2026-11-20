# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12 sizing: how big is each scene's state map (every distinct state played once)?

One read-only Codex probe, no model call in the game. Usage: build_round12_map_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-carry-matrix"
KEY = "map-size"
DIR = f"{WORK}/{KEY}"

SPEC = f"""You are a read-only sizing probe worker. Your current directory is {DIR}, a scratch directory you own. NEVER modify anything under {REPO} (read it only), never git commit, never run `uv`, never call a model or the network. Python is {REPO}/.venv/bin/python; run scripts with `PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp` and cwd {REPO}, and write files only into {DIR}.

BACKGROUND. We are designing a free factory gate that proves no scene of the game can leave the player stuck. The old design replayed the same turns many times (22 scripted runs of 1A that are identical until the one turn they differ). The new design plays each distinct state ONCE. A scene is a map: a POINT is a distinct game state inside the scene; a STEP is one thing the player can do on a turn, either pick one of the offered candidates or wait. From the scene's entry state, play each step from each point once; a step that lands on a point already seen joins it instead of being played again. A point is STUCK when no sequence of steps from it reaches an earned exit. Before building the gate we need the size of these maps.

How the game is played offline (copy these mechanics; see `tests/journey_prefix.py` and `storygame/personas.py`): load `data/stories/continuity-initiative` with `storygame.story_package.loader.load_story_package`, then `_legacy_package` from `storygame.personas`; `state = RuntimeState.bootstrap(played)`; `provider = _ScriptedProvider(played, state)`; `engine = RuntimeEngine(state, provider)`. One turn: `engine._activate_pacing()`; `offered = engine.projector.project(state, "player", "").candidates`; to PICK candidate c set `provider.selected = (c.id,)`, to WAIT set `provider.selected = ()`; then `engine.turn(PERSONAS["thorough"])`. A `ProposalValidationError` or `RuntimeContractError` means that pick was rejected: record the step as rejected and do not explore it (do not retry it as a wait; the wait is its own step). After the turn, `state.current_scene_id` tells whether the scene changed and `engine.last_attempt.transition_cause` is `"earned"`, `"forced"` or `"timer"`; `_resolution_complete(state)` ends the last scene. `state.snapshot()` / `state.restore_snapshot(snap)` save and restore; restoring into one engine and provider is what `tests/journey_prefix.py` does (restore `provider.handoff_ids` too, as it does). A turn costs roughly 250 ms; a profiling report that may help is at {WORK}/profile-rollout/report.md (read it if it exists).

POINT IDENTITY. Two states are the same point only if every later turn would behave the same. Read `RuntimeSnapshot` in `storygame/runtime/state.py` and the engine and pacing code to decide which fields affect later turns. Start from: the asserted facts (all of them, as sorted `Fact.key` tuples), the turns spent in the current scene (`turn_index - scene_entered_at_turn`), `active_event_ids`, `fired_event_ids`, `cue_stages` with turns made relative to the scene entry, `staged_cue_fact_id`, `staged_cue_stage`, `staged_handoff_fact_ids`, and `delivered_cue_ids`. Leave out the absolute `turn_index`, `turn_records` and `last_turn_delivery` ONLY if you confirm from the code that later turns do not read them; if they are read, find the part that is read and include just that. Also measure a SECOND, coarser identity: the first one minus facts that no scene at or after the current scene reads (`knowledge_narrated` records of earlier scenes, `story_elapsed_seconds`, flags read only by earlier scenes; a reads-by-scene walk is in {WORK}/attempt3/carry_matrix.py, `reads_by_scene` and `forward_reads`, load it with importlib if useful). Report both counts. Write down every field you included or excluded and why, with file:line.

YOUR TASK.
1. Write {DIR}/map_size.py that builds the map for a scene from one entry snapshot by breadth-first search with a visited set keyed by point identity, stopping a branch when the scene changes (an EXIT, recorded with its cause), the resolution completes, or `handoff_after_turns + 3` turns pass in the scene (a DEAD END). Caps: stop a scene at 20000 points or 15 minutes, whichever comes first, and say which. Record per scene: points, steps played, steps rejected, steps that joined an existing point, exits by cause (earned, forced, timer), distinct exit states (by the coarse identity, these become the next scene's entry points), dead ends, points per turn depth (a table: depth -> new points), the largest number of offered candidates at one point, the per-turn time, total wall time, and how many STUCK points there are (no path to an earned exit; compute by a backward search after the map is built) with the first five stuck points described by their turn depth and the scene's read facts that are true there. Also list which player-visible realizations of the scene appear on some step that reaches an earned exit, and which never do.
2. Run it for scene 1A from bootstrap, and for 2B from the default-path entry state (reach it by playing the default thorough policy as `tests/journey_prefix.py` `_default_walk` does, or by a map of each earlier scene taking the first earned exit). If 1A or 2B finishes quickly, also run 3A from its default-path entry. Run the fine identity first, then the coarse one. Single process is fine; if you use several, say how many.
3. Keep stdout in {DIR}/run.out and write {DIR}/map.json: {{"identity_fields": [...], "scenes": {{"<scene>": {{"fine": {{...}}, "coarse": {{...}}}}}}}} with the measures above.
4. Write {DIR}/report.md with sections: ## Point identity (fields kept and dropped, with file:line evidence); ## Sizes (a table per scene and identity: points, steps, joined, rejected, exits by cause, distinct exit states, dead ends, stuck, wall time); ## Growth (points per depth; does the map converge or keep growing, and why: which choices commute, which multiply); ## Realizations (reached versus never reached on an earned path); ## Estimate (whole-story time for the gate: sum over scenes of points times steps per point times per-turn cost, entry points per scene taken from the distinct exit states you measured; give it for one process and for 16; say what dominates); ## Risks (merges that could be wrong, anything the map misses that the old scripted runs covered). Mark measured numbers separately from estimates.

HARD RULES. Do not edit {REPO} or {WORK}/attempt3. Do not sample: a scene's map is complete or the cap is reported. Keep the whole probe under 45 minutes of run time.
"""

CHECK = f"""set -eo pipefail
cd {DIR}
for f in map_size.py run.out map.json report.md; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
{REPO}/.venv/bin/python - <<'PY'
import json, re
d = json.load(open("map.json"))
assert d["identity_fields"], "no identity fields recorded"
s = d["scenes"]
for scene in ["1A", "2B"]:
    assert scene in s, f"scene {{scene}} missing"
    for ident in ["fine", "coarse"]:
        row = s[scene][ident]
        for key in ["points", "steps", "exits", "stuck", "seconds"]:
            assert key in row, f"{{scene}} {{ident}} lacks {{key}}: {{sorted(row)}}"
        assert row["points"] >= 1 and row["seconds"] > 0, (scene, ident, row["points"], row["seconds"])
    assert s[scene]["coarse"]["points"] <= s[scene]["fine"]["points"], (scene, "coarse identity has more points than fine")
report = open("report.md").read()
for heading in ["point identity", "sizes", "growth", "realizations", "estimate", "risks"]:
    assert re.search(r"^##\\s+" + re.escape(heading), report, re.I | re.M), f"report.md lacks section: {{heading}}"
assert re.search(r"storygame/[\\w/]+\\.py:\\d+", report), "report.md cites no file:line"
print("map ok", {{k: {{i: (v[i]["points"], round(v[i]["seconds"], 1)) for i in v}} for k, v in s.items()}})
PY
"""


def build() -> dict:
    return {
        "run_name": "factory-carry-matrix",
        "workdir": WORK,
        "max_parallel": 1,
        "tasks": [
            {
                "key": KEY,
                "task_type": "probe",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 4200,
                "check_timeout_s": 120,
                "ownership": [f"{DIR}/{name}" for name in ("map_size.py", "run.out", "map.json", "report.md")],
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [f"{DIR}/report.md", f"{DIR}/map.json"],
                "verified": "map.json has fine and coarse map sizes for 1A and 2B (points, steps, exits, stuck, seconds; coarse no larger than fine); report.md has point identity with file:line, sizes, growth, realizations, a whole-story estimate and risks.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-map-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
