# ruff: noqa: E501
"""Blind scoring sheet for a shared-narrator comparison. Free. Usage:
PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/build_sheet.py COMPARISON ROWS_GLOB OUTDIR
Writes OUTDIR/sheet-COMPARISON.md (shuffled, no arm labels) and key-COMPARISON.json. Handoff endpoints show the lead-up, the exact appended
delivery and the composed turn; the mechanical JSON/segment check is recorded in the key, never shown to the reader."""

import glob
import json
import random
import sys
from pathlib import Path

from storygame.story_package.loader import load_story_package  # noqa: E402

comparison, pattern, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
rows = [r for f in sorted(glob.glob(pattern)) for r in json.loads(Path(f).read_text())]
package = load_story_package(Path("data/stories/continuity-initiative"))
DELIVERY = {"H1": "k_sl_3a_h_r1", "H2": "k_sl_1c_a_r1"}


def delivery(eid):
    k = DELIVERY.get(eid)
    return package.knowledge_indexes.by_id[k].delivery_text.strip() if k else None


def parse(row):
    """Return (lead_up_text, mechanical_ok, note)."""
    raw = row.get("raw")
    if row.get("error") or raw is None:
        return None, False, f"transport error: {row.get('error')}"
    try:
        wrapper = json.loads(raw)
        inner = wrapper["narration"] if isinstance(wrapper, dict) and "narration" in wrapper else raw
        body = json.loads(inner) if isinstance(inner, str) else inner
        segs = body["segments"]
        texts = [s["text"] for s in segs]
        ok = bool(texts) and all(isinstance(t, str) and t.strip() for t in texts)
        return "\n\n".join(t for t in texts if isinstance(t, str)), ok, "ok" if ok else "empty segment text"
    except Exception as error:
        return row.get("narration") or raw, False, f"not valid response JSON: {error}"


random.seed(f"shared-narrator-{comparison}")
order = list(range(len(rows)))
random.shuffle(order)
sheet, key = [f"# Blind sheet, comparison {comparison}\n"], []
for i, idx in enumerate(order, 1):
    row = rows[idx]
    text, ok, note = parse(row)
    d = delivery(row["id"])
    key.append(
        {
            "sheet": i,
            "arm": row["arm"],
            "id": row["id"],
            "sample": row["sample"],
            "mechanical_ok": ok,
            "note": note,
            "words": len((text or "").split()),
        }
    )
    sheet.append(f"## S{i} — endpoint {row['id']}: `{row['command'] or '(opening)'}`\n")
    sheet.append("**Model text:**\n\n" + (text if text is not None else f"(no text: {note})") + "\n")
    if d:
        sheet.append("**Game appends:**\n\n" + d + "\n")
outdir.mkdir(parents=True, exist_ok=True)
(outdir / f"sheet-{comparison}.md").write_text("\n".join(sheet))
(outdir / f"key-{comparison}.json").write_text(json.dumps(key, indent=1))
print("rows", len(rows), "mechanical failures", sum(not k["mechanical_ok"] for k in key))
