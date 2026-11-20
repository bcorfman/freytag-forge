# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12 profile: where the carry matrix spends its time (about 3.5 s per scene run).

One read-only Codex probe, no model call in the game. Usage: build_round12_profile_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-carry-matrix"
KEY = "profile-rollout"
DIR = f"{WORK}/{KEY}"

SPEC = f"""You are a read-only profiling probe worker. Your current directory is {DIR}, a scratch directory you own. NEVER modify anything under {REPO} (read it only), never git commit, never run `uv`, never call a model or the network. Python is {REPO}/.venv/bin/python; run scripts with `PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp` and cwd {REPO}, and write files only into {DIR}.

BACKGROUND. A new free factory gate, the carry matrix, plays the game offline with scripted players (no model) many times: from each scene entry state it runs a default player, one run per choosable realization, and a few stall runs, each from a restored snapshot. The latest draft is {WORK}/attempt3/carry_matrix.py (not in the repo; load it with `importlib.util.spec_from_file_location` as `carry_matrix_draft`). It is far too slow: one scene run takes about 3.5 seconds, 1A's 22 runs took 46 seconds of wall time, and a test walking 1A to 2B took 172 seconds. The owner wants the per-change gate and its tests to be fast. We need to know exactly where the time goes before deciding what to change.

YOUR TASK.
1. Write {DIR}/profile.py that measures, on the real story (`data/stories/continuity-initiative`, `load_story_package`, then `_legacy_package` from `storygame.personas`):
   a. Time to load the package, to run `_legacy_package`, to `RuntimeState.bootstrap`, to build a `RuntimeEngine`, to take `state.snapshot()`, and to `restore_snapshot()` (median of 20 where repeatable).
   b. One `default` 1A rollout through the draft's own rollout code: total time, turn count, and per-turn time.
   c. The same rollout under `cProfile`: save the stats to {DIR}/rollout.prof and the top 40 functions by cumulative time and the top 40 by total (self) time to {DIR}/profile.txt.
   d. A breakdown of each turn's time into the engine's phases: candidate projection (`engine.projector.project` as called by the rollout loop), `engine._activate_pacing`, and `engine.turn`; and inside `engine.turn`, the largest sub-steps you can attribute from the profile (validation, commit, world-model application, item facts, delivery text, prompt or payload building, pydantic validation or copying, deep copies). Name each with file:line.
   e. Whether the draft's process pool helps: how it starts workers (fork or spawn), what each worker loads at start, and the wall time for 1A's 22 runs with the pool versus run one after another in one process. Explain the 46 seconds for 22 runs.
   f. Repeated work across runs: how much of a scene run repeats an identical earlier run (for example every one-choice path replaying the same default turns of later scenes), and how many of 1A's runs share an identical prefix of turns before they diverge.
2. Run it; keep stdout in {DIR}/run.out.
3. Write {DIR}/report.md with sections: ## Fixed costs (table from 1a); ## One rollout (1b and 1d: per phase, ms per turn and share of the turn, file:line); ## Hot spots (the top functions from profile.txt that matter, what each does, and whether an offline scripted run needs it at all: the narrator prompt, payloads for a model and similar output are never read offline); ## Pool (1e); ## Repeated work (1f); ## Speedups (a ranked list; for each: what to change, in which file, whether it is factory code or engine code, the measured or estimated saving with how you estimated it, and the risk to the gate's correctness. Include at least: skipping work an offline run never reads, sharing turn prefixes or memoizing identical runs, pool start-up, and whether the gate's unit tests should run on a small fixture story instead of the real one (look at `tests/fixtures/story_source/` and `tests/story_source/helpers.py`). Mark measured numbers separately from estimates.

HARD RULES. Do not edit {REPO} or {WORK}/attempt3. Do not round away measurements; report ms. Keep the whole probe under 20 minutes of run time.
"""

CHECK = f"""set -eo pipefail
cd {DIR}
for f in profile.py run.out profile.txt rollout.prof report.md; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
{REPO}/.venv/bin/python - <<'PY'
import pstats, re
stats = pstats.Stats("rollout.prof")
assert stats.total_tt > 0.5, f"profile too short to be a real rollout: {{stats.total_tt}}"
names = " ".join(f"{{k[0]}}:{{k[2]}}" for k in stats.stats)
assert "engine.py" in names and "turn" in names, "profile does not include engine.turn"
report = open("report.md").read()
for heading in ["fixed costs", "one rollout", "hot spots", "pool", "repeated work", "speedups"]:
    assert re.search(r"^##\\s+" + re.escape(heading), report, re.I | re.M), f"report.md lacks section: {{heading}}"
assert re.search(r"(storygame|packages/worldkeeper|factory)/[\\w/]+\\.py:\\d+", report), "report.md cites no file:line"
assert re.search(r"\\d+(\\.\\d+)?\\s*ms", report), "report.md has no ms measurements"
print("profile ok, total", round(stats.total_tt, 2), "s")
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
                "timeout_s": 2400,
                "check_timeout_s": 120,
                "ownership": [
                    f"{DIR}/{name}" for name in ("profile.py", "run.out", "profile.txt", "rollout.prof", "report.md")
                ],
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [f"{DIR}/report.md", f"{DIR}/profile.txt"],
                "verified": "A real cProfile of a 1A rollout that includes engine.turn; report.md has fixed costs, per-phase ms per turn, hot spots with file:line, pool and repeated-work analysis, and ranked speedups.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-profile-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
