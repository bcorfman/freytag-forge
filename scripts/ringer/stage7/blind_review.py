"""Blinded review helper for a Stage 7 door screen.

prep: write shuffled arm-free packets and a private key.
convert: map packet verdicts back to row verdicts, write review-summary.json.
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_door_probe import _canonical_row_hash, _row_text  # noqa: E402

FIELDS = (
    "upstream_invention",
    "downstream_new_invention",
    "inherited_invention",
    "player_pursuit",
    "premature_disclosure",
    "contradictory_delivery",
    "earned_by_command_2",
    "declared_panel_used",
    "invented_access_object",
    "reached_archive_without_new_credential",
)


def prep(out: Path, work: Path) -> None:
    rows = json.loads((out / "results.json").read_text())["rows"]
    order = list(range(len(rows)))
    random.Random(7).shuffle(order)
    (work / "packets").mkdir(parents=True, exist_ok=True)
    key = {}
    for i, idx in enumerate(order, 1):
        row = rows[idx]
        pid = f"p{i:02d}"
        key[pid] = row["row_id"]
        packet = {
            "packet_id": pid,
            "text_json": _row_text(row),
            "screen": row["screen"],
            "commands": row["commands"],
            "responses": row["responses"],
            "turns": row.get("continuation", {}).get("turns", [])[:2],
        }
        (work / "packets" / f"{pid}.json").write_text(json.dumps(packet, indent=1, ensure_ascii=False))
    (work / "key.json").write_text(json.dumps(key, indent=1))


def convert(out: Path, work: Path) -> None:
    rows = {r["row_id"]: r for r in json.loads((out / "results.json").read_text())["rows"]}
    key = json.loads((work / "key.json").read_text())
    (out / "verdicts").mkdir(exist_ok=True)
    for pid, row_id in key.items():
        v = json.loads((work / "verdicts" / f"{pid}.json").read_text())
        verdict = {"row_id": row_id, "row_hash": _canonical_row_hash(rows[row_id]), "reviewer": "blinded-codex-luna"}
        for f in FIELDS:
            verdict[f] = v[f]
        verdict["evidence"] = v.get("evidence", {})
        verdict["notes"] = v.get("notes", "")
        (out / "verdicts" / f"{row_id}.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False))
    arms: dict[str, dict] = {}
    for row_id, row in rows.items():
        v = json.loads((out / "verdicts" / f"{row_id}.json").read_text())
        c = arms.setdefault(
            row["arm"],
            dict.fromkeys(
                (
                    "earned",
                    "unsupported_access",
                    "premature_disclosure",
                    "contradictory_delivery",
                    "declared_panel_used",
                    "invented_access_object",
                    "reached_archive_without_new_credential",
                    "door_appears",
                ),
                0,
            ),
        )
        c["earned"] += v["earned_by_command_2"] is True
        c["unsupported_access"] += any(
            v[f] is True for f in ("upstream_invention", "downstream_new_invention", "player_pursuit")
        )
        for f in ("premature_disclosure", "contradictory_delivery"):
            c[f] += v[f] is True
        for f in ("declared_panel_used", "invented_access_object", "reached_archive_without_new_credential"):
            c[f] += v[f] is True
        c["door_appears"] += v["declared_panel_used"] is True or v["invented_access_object"] is True
    ctl = arms["control"]["earned"]
    for arm, c in arms.items():
        c["decision"] = (
            "wins"
            if arm == "grounded"
            and c["reached_archive_without_new_credential"] >= 10
            and c["earned"] >= 10
            and c["invented_access_object"] <= 2
            and c["premature_disclosure"] == 0
            and c["contradictory_delivery"] == 0
            and c["earned"] >= ctl + 3
            else "does_not_win"
        )
    (out / "review-summary.json").write_text(json.dumps({"arms": arms}, indent=1))
    print(json.dumps(arms, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("prep", "convert"))
    ap.add_argument("out", type=Path)
    ap.add_argument("work", type=Path)
    a = ap.parse_args()
    (prep if a.cmd == "prep" else convert)(a.out, a.work)
