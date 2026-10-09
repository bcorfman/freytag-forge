"""Re-score 3b_frame_probe replies offline: narration segments only. usage: 3b_frame_rescore.py replies.json"""

import json
import re
import sys
from pathlib import Path

ALARM = re.compile(r"alarm|warning|door|console|false", re.I)


def narration(row):
    try:
        outer = json.loads(row["text"])
        inner = json.loads(outer["narration"]) if isinstance(outer.get("narration"), str) else outer
        return " ".join(str(s.get("text", "")) for s in inner["segments"])
    except Exception:  # noqa: BLE001
        return row.get("text", "")


rows = json.loads(Path(sys.argv[1]).read_text())
for row in rows:
    row["prose"] = narration(row)
for inp in ("neutral", "recorded"):
    for arm in "ABCDEF":
        cell = [r for r in rows if r["input"] == inp and r["arm"] == arm]
        relay = sum("relay" in r["prose"].casefold() for r in cell)
        alarm = sum(bool(ALARM.search(r["prose"])) for r in cell)
        print(f"input {inp} arm {arm}: relay {relay}/{len(cell)}, alarm-words {alarm}/{len(cell)}")
if len(sys.argv) > 2:
    for r in rows:
        print(r["input"], r["arm"], "|", r["prose"].replace("\n", " "))
