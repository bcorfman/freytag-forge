# ruff: noqa: E501
"""Blind sheet for experiment GUE1 (free). Usage: .venv/bin/python scripts/ringer/shared-narrator/build_sheet_u.py 'ROWS_GLOB' OUTDIR
Shuffled, no arm labels; shows the command, the model text (decoded segments) and, when the reply is malformed, the raw prefix.
The key records arm, endpoint, sample and the mechanical check."""

import glob
import json
import random
import sys
from pathlib import Path

pattern, outdir = sys.argv[1], Path(sys.argv[2])
rows = [r for f in sorted(glob.glob(pattern)) for r in json.loads(Path(f).read_text())]


def parse(row):
    raw = row.get("raw")
    if row.get("error") or raw is None:
        return None, False, f"transport error: {row.get('error')}"
    try:
        wrapper = json.loads(raw)
        inner = wrapper["narration"] if isinstance(wrapper, dict) and "narration" in wrapper else raw
        body = json.loads(inner) if isinstance(inner, str) else inner
        texts = [s["text"] for s in body["segments"]]
        ok = bool(texts) and all(isinstance(t, str) and t.strip() for t in texts)
        return "\n\n".join(t for t in texts if isinstance(t, str)), ok, "ok" if ok else "empty segment text"
    except Exception as error:
        return (row.get("narration") or raw)[:1500], False, f"not valid response JSON: {error}"


random.seed("shared-narrator-GUE1")
order = list(range(len(rows)))
random.shuffle(order)
sheet, key = ["# Blind sheet, experiment GUE1\n"], []
for i, idx in enumerate(order, 1):
    row = rows[idx]
    text, ok, note = parse(row)
    key.append(
        {"sheet": i, "arm": row["arm"], "n": row["n"], "sample": row["sample"], "mechanical_ok": ok, "note": note}
    )
    sheet.append(f"## S{i} — endpoint c{row['n']}: `{row['command']}`\n")
    sheet.append(("**Model text:**\n\n" + text if text is not None else f"(no text: {note})") + "\n")
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "sheet-GUE1.md").write_text("\n".join(sheet))
(outdir / "key-GUE1.json").write_text(json.dumps(key, indent=1))
print("rows", len(rows), "mechanical failures", sum(not k["mechanical_ok"] for k in key))
