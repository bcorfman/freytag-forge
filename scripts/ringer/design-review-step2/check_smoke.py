"""Check the Step 2 live smoke: every turn of a blind-player 1A run carries a bundle."""

import json
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])
bundles = json.loads((root / "artifacts/e2e-blind-player-bundles.json").read_text())
main = json.loads((root / "artifacts/e2e-blind-player.json").read_text())
count = Counter()
total = 0
for replicate in bundles["replicates"]:
    for scene in replicate["scenes"]:
        for item in scene["bundles"]:
            bundle = item["attempt_bundle"]
            total += 1
            count[(bundle["outcome"], bundle["transition_cause"])] += 1
            assert bundle["schema_version"] == 1, bundle["schema_version"]
            assert any(stage["kind"] == "narration" for stage in bundle["stages"]), item["turn"]
turns = sum(len(run["turns"]) for run in main["replicates"])
print("turns", turns, "bundles", total)
for key, n in sorted(count.items()):
    print(key, n)
print("exits", [(run.get("exit_cause"), run.get("exit_transition_cause")) for run in main["replicates"]])
assert total == turns, f"{turns - total} turns have no bundle"
assert any(outcome == "committed" for outcome, _ in count), "no committed attempt"
print("SMOKE_OK")
