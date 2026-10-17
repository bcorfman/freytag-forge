"""Summarize the photo-eliciting bench: per arm x prompt, how often the narrator wrote a photo word and
how often a turn was rejected.
"""

import json
import re
import sys
from pathlib import Path

out, reps = Path(sys.argv[1]), int(sys.argv[2])
words = re.compile(r"\b(photo|photograph|picture|image)s?\b", re.I)
table, bad = {}, []
for arm in ("baseline", "current"):
    for script in ("photos", "picture", "photograph"):
        f = out / f"{arm}-{script}" / "all-turn-records.json"
        if not f.exists():
            bad.append(f"missing records for {arm}-{script}")
            continue
        runs = json.loads(f.read_text())["runs"]
        row = {
            "runs": len(runs),
            "statuses": sorted({str(r.get("status")) for r in runs}),
            "narrated": 0,
            "photo_word": 0,
            "rejected": 0,
            "photo_rejected": 0,
            "reasons": [],
        }
        for run in runs:
            for t in run.get("turns", []):
                row["narrated"] += 1
                if words.search(t.get("narration") or ""):
                    row["photo_word"] += 1
            for r in run.get("rejected_turns", []):
                row["rejected"] += 1
                text = json.dumps(r)
                row["reasons"].append(text[:240])
                if re.search(
                    r"photo|picture|photograph",
                    str(r.get("rejection_reason", "")) + str(r.get("guard_rejections", "")),
                    re.I,
                ):
                    row["photo_rejected"] += 1
        if row["runs"] != reps:
            bad.append(f"{arm}-{script}: {row['runs']} runs, expected {reps}")
        table[f"{arm}/{script}"] = row
(out / "summary.json").write_text(json.dumps(table, indent=2))
for k, v in table.items():
    print(k, {x: v[x] for x in ("runs", "statuses", "narrated", "photo_word", "rejected", "photo_rejected")})
if bad:
    print("PROBLEMS:", *bad, sep="\n  ")
    sys.exit(1)
