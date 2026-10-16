"""Ringer check: the sentence-isolation rejudge must hold 30 valid verdicts in the planned design.

usage: check_isolation.py <results.json> <report.md>
"""

import json
import sys
from collections import Counter
from pathlib import Path

results_path, report_path = Path(sys.argv[1]), Path(sys.argv[2])
problems = []
if not results_path.is_file():
    problems.append(f"{results_path} missing")
if not report_path.is_file() or not report_path.read_text().strip():
    problems.append(f"{report_path} missing or empty")
if not problems:
    data = json.loads(results_path.read_text())
    rows = data["results"] if isinstance(data, dict) else data
    cells = Counter((row.get("scene"), row.get("arm")) for row in rows if isinstance(row.get("exit_motivated"), bool))
    scenes = {"1A", "1C", "2A", "3A", "3B"}
    arms = {"with_sentence", "without_sentence"}
    for scene in scenes:
        for arm in arms:
            if cells[(scene, arm)] != 3:
                problems.append(f"cell {scene}/{arm} has {cells[(scene, arm)]} valid verdicts, need 3")
    extra = [k for k in cells if k[0] not in scenes or k[1] not in arms]
    if extra:
        problems.append(f"unexpected cells {extra}")
    if len(rows) != 30:
        problems.append(f"{len(rows)} result rows, need exactly 30 (one billed call each)")
    text = report_path.read_text().lower()
    for needed in ("with_sentence", "without_sentence", "limits"):
        if needed not in text:
            problems.append(f"report never mentions '{needed}'")
if problems:
    sys.exit("FAIL " + "; ".join(problems))
print("sentence isolation complete: 30 verdicts in 10 cells of 3")
