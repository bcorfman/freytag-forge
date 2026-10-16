"""Ringer check: a recorded @llm-canon run counts only if it is complete and fresh (runbook section 7).

usage: check_llm_canon.py <repo> <out-dir> <report.md>
"""

import json
import sys
import time
from pathlib import Path

repo, out, report = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
problems = []
if not report.is_file() or not report.read_text().strip():
    problems.append(f"{report} missing or empty")
progress = out / "e2e-llm-canon-progress.json"
verdicts = out / "e2e-llm-canon.json"
for path in (progress, verdicts):
    if not path.is_file():
        problems.append(f"{path} missing (aborted run: the report must say so and no result may be recorded)")
if not problems:
    age = time.time() - progress.stat().st_mtime
    if age > 3 * 3600:
        problems.append(f"{progress} is {age / 3600:.1f} h old: stale artifact from an earlier run")
    data = json.loads(progress.read_text())
    scenes = data.get("by_scene") or {}
    turns = data.get("completed_turn", 0)
    if len(scenes) < 9 or turns < 30:
        problems.append(f"incomplete run: {len(scenes)} scenes, {turns} turns (need 9 scenes and 30+ turns)")
    text = report.read_text().lower()
    for needed in ("staging", "sha", "smoke"):
        if needed not in text:
            problems.append(f"report never mentions '{needed}'")
if problems:
    sys.exit("FAIL " + "; ".join(problems))
print("llm-canon run complete and fresh")
