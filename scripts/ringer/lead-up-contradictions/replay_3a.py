# ruff: noqa: E501
"""Replay frozen 3A reunion payloads, with an explicit billed-request guard."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
ARMS = ("CUR", "CAND")
ENDPOINTS = ("R1", "R2")


def run(out, first, last, send=None):
    assert 1 <= first <= last <= 12
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    root = ROOT / "bench/results/lead-up-contradictions"
    frozen = {arm: json.loads((root / f"frozen-3A-{arm}.json").read_text(encoding="utf-8")) for arm in ARMS}
    endpoints = {
        (arm, n): next(endpoint for endpoint in frozen[arm]["endpoints"] if endpoint["n"] == n)
        for n in ENDPOINTS
        for arm in ARMS
    }
    if send is None:
        import bench.frozen_prompts as fp
        from bench.core import load_dotenv

        fp.SCENE = "3A"
        load_dotenv()
        send = fp._default_transport({"variation": "richer-3a-live"})
    else:
        import bench.frozen_prompts as fp

    rows = []
    for sample in range(first, last + 1):
        for n in ENDPOINTS:
            for arm in ARMS:
                endpoint = endpoints[(arm, n)]
                row = {
                    "arm": arm,
                    "n": n,
                    "sample": sample,
                    "command": endpoint["command"],
                    "narration": None,
                    "error": None,
                    "raw": None,
                }
                try:
                    body = send(endpoint["wire_payload"])
                    row["raw"] = body.decode("utf-8", errors="replace")
                    row["narration"] = fp._decode_replay_body(body)
                except Exception as error:
                    row["error"] = str(error)
                rows.append(row)
                out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rows


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("first", type=int)
    parser.add_argument("last", type=int)
    parser.add_argument("--confirm", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    assert 1 <= args.first <= args.last <= 12
    if args.out.exists():
        raise FileExistsError(args.out)
    count = (args.last - args.first + 1) * 4
    print(f"requests {count}")
    if not args.confirm:
        print("dry run: nothing sent")
        raise SystemExit(0)
    run(args.out, args.first, args.last)
