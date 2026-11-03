import json, sys, textwrap
"""Print every turn of a bench result for hand reading.

Usage (repository root): python .plans/richer-probe-report.py bench/results/richer-1b-probe/baseline > report.md
"""
results = sys.argv[1]
d = json.load(open(f"{results}/all-turn-records.json"))
runs = d["runs"]
out = [f"# {results}: {len(runs)} replicates\n"]
for r in runs:
    out.append(f"\n## replicate {r.get('replicate')} status={r.get('status')} turns={len(r.get('turns', []))} rejected={r.get('rejected_turn_count')}")
    out.append("OPENING: " + (r.get("opening") or "").replace("\n", " ")[:900])
    for i, t in enumerate(r.get("turns", []), 1):
        new = [k for k, v in (t.get("item_facts_resolutions") or {}).items() if v == "new"]
        out.append(f"\n[{i}] {t.get('typed_input')!r}  revealed={t.get('selected_knowledge_ids')}  NEW={new}  issues={t.get('item_facts_issues')}")
        out.append("   " + (t.get("narration") or "").replace("\n", " ")[:700])
print("\n".join(out))
