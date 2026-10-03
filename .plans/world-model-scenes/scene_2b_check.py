"""Read the 2B live replicate and report how the grounding held.

Usage, from the repository root, after the bench run:
    uv run python .plans/world-model-scenes/scene_2b_check.py bench/results/world-2b

It never calls a model. It prints every turn (scene, typed input, handoff,
place and thing resolutions, unplaced reply changes) and every rejected turn.
It fails if the replicate did not complete, or if a name resolved to a
terminal or console that belongs to another scene. Leak rejections are
printed and counted but do not fail it: 2B has no reveal handoffs yet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OTHER_SCENE_THINGS = {"logistics_terminal", "hideout_servers", "logistics terminal", "servers"}


def main(run_dir: str) -> int:
    failures: list[str] = []
    leaks = 0
    path = Path(run_dir) / "all-turn-records.json"
    if not path.is_file():
        print(f"FAIL: {path} is missing")
        return 1
    for run in json.loads(path.read_text(encoding="utf-8"))["runs"]:
        label = f"r{run.get('replicate')}"
        print(f"== {label}: completed={run.get('completed')} failure={run.get('failure_reason')!r}")
        if not run.get("completed") or run.get("failure_reason"):
            failures.append(f"{label} did not complete: {run.get('failure_reason')!r}")
        for transition in run.get("scene_transitions") or ():
            print(f"   transition {transition}")
        for number, turn in enumerate(run.get("turns") or (), start=1):
            typed = turn.get("typed_input") or turn.get("player_input")
            print(
                f"   t{number} [{turn.get('scene_id')}] {typed} -> handoff={turn.get('authored_handoff_candidate_id')}"
            )
            for key in ("item_facts_place_resolutions", "item_facts_resolutions", "item_facts_unplaced"):
                value = turn.get(key)
                if value:
                    print(f"      {key}: {json.dumps(value)}")
                if key != "item_facts_unplaced" and isinstance(value, dict):
                    for name, target in value.items():
                        if str(target) in OTHER_SCENE_THINGS:
                            failures.append(f"{label} t{number}: {name!r} resolved to another scene's {target!r}")
        for rejected in run.get("rejected_turns") or ():
            code = rejected.get("rejection_code")
            print(
                f"   REJECTED t{rejected.get('turn_number')} {rejected.get('typed_input')!r}: "
                f"{code} {rejected.get('rejection_reason', '')}"
            )
            if code in ("narration_known_term_leak", "uncited_knowledge", "protected_narration_leak"):
                leaks += 1
    print()
    print(f"leak rejections: {leaks}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
