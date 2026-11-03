"""Print every turn of a bench result for hand reading.

Usage (repository root): python .plans/richer-probe-report.py bench/results/richer-1b-probe/baseline > report.md
"""

import json
import sys

results = sys.argv[1]
with open(f"{results}/all-turn-records.json", encoding="utf-8") as handle:
    runs = json.load(handle)["runs"]
out = [f"# {results}: {len(runs)} replicates\n"]
for run in runs:
    out.append(
        f"\n## replicate {run.get('replicate')} status={run.get('status')} "
        f"turns={len(run.get('turns', []))} rejected={run.get('rejected_turn_count')}"
    )
    out.append("OPENING: " + (run.get("opening") or "").replace("\n", " ")[:900])
    for index, turn in enumerate(run.get("turns", []), 1):
        new = [name for name, kind in (turn.get("item_facts_resolutions") or {}).items() if kind == "new"]
        out.append(
            f"\n[{index}] {turn.get('typed_input')!r}  revealed={turn.get('selected_knowledge_ids')}  "
            f"NEW={new}  issues={turn.get('item_facts_issues')}"
        )
        out.append("   " + (turn.get("narration") or "").replace("\n", " ")[:700])
print("\n".join(out))
