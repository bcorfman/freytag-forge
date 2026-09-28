"""Read the leak-fix live replicates and say whether the three fixes held.

Usage, from the repository root, after the two bench runs:
    uv run python .plans/world-model-scenes/leak_fix_check.py \
        bench/results/world-leakfix-1b-1c bench/results/world-leakfix-2a

It never calls a model. It prints every turn (scene, typed input, handoff) and
every rejected turn, then fails if a replicate did not complete, if a turn was
rejected by a narration leak check, or if either target handoff did not
fire in its own scene.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LEAK_CODES = ("narration_known_term_leak", "uncited_knowledge", "protected_narration_leak")
# (typed input, handoff that must fire, scene it must fire in)
EXPECTED_HANDOFFS = (
    ("Search the logistics terminal for transfer records.", "k_sl_1c_c_r1", "1C"),
    ("Warn the supervisor about the cooling-water fault.", "k_sl_2a_c_r1", "2A"),
)


def main(run_dirs: list[str]) -> int:
    failures: list[str] = []
    seen_inputs: set[str] = set()
    for run_dir in map(Path, run_dirs):
        path = run_dir / "all-turn-records.json"
        if not path.is_file():
            failures.append(f"{path} is missing")
            continue
        for run in json.loads(path.read_text(encoding="utf-8"))["runs"]:
            label = f"{run_dir.name} r{run.get('replicate')}"
            print(f"== {label}: completed={run.get('completed')} failure={run.get('failure_reason')!r}")
            if not run.get("completed") or run.get("failure_reason"):
                failures.append(f"{label} did not complete: {run.get('failure_reason')!r}")
            for transition in run.get("scene_transitions") or ():
                print(f"   transition {transition}")
            for number, turn in enumerate(run.get("turns") or (), start=1):
                typed = turn.get("typed_input") or turn.get("player_input")
                handoff = turn.get("authored_handoff_candidate_id")
                print(f"   t{number} [{turn.get('scene_id')}] {typed} -> handoff={handoff}")
                for expected_input, expected_id, expected_scene in EXPECTED_HANDOFFS:
                    if typed != expected_input:
                        continue
                    seen_inputs.add(expected_input)
                    if handoff != expected_id or turn.get("scene_id") != expected_scene:
                        failures.append(
                            f"{label}: {expected_input!r} gave handoff {handoff} in {turn.get('scene_id')}, "
                            f"expected {expected_id} in {expected_scene}"
                        )
            for rejected in run.get("rejected_turns") or ():
                reason = rejected.get("rejection_reason", "")
                print(
                    f"   REJECTED t{rejected.get('turn_number')} {rejected.get('typed_input')!r}: "
                    f"{rejected.get('rejection_code')} {reason}"
                )
                is_target = rejected.get("typed_input") in {item[0] for item in EXPECTED_HANDOFFS}
                if is_target:
                    seen_inputs.add(rejected["typed_input"])
                if rejected.get("rejection_code") in LEAK_CODES:
                    failures.append(f"{label}: turn {rejected.get('turn_number')} leak rejection: {reason}")
                elif is_target:
                    failures.append(f"{label}: target turn {rejected['typed_input']!r} was rejected: {reason}")
    for expected_input, _expected_id, _scene in EXPECTED_HANDOFFS:
        if expected_input not in seen_inputs:
            failures.append(f"no run played {expected_input!r}")
    print()
    for failure in failures:
        print(f"FAIL: {failure}")
    print("PASS" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
