# ruff: noqa: E501
"""Billed replay for experiments 1A, 1B, and 2A."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ENDPOINTS = {"1A": "c6", "1A2": "c6", "1B": "c4", "2A": "c4"}


def run(cmp, out, first, last, send=None):
    """Replay the selected comparison for samples FIRST through LAST."""
    assert cmp in ENDPOINTS
    assert 1 <= first <= last <= 12
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)

    root = ROOT / "bench/results/lead-up-contradictions"
    if cmp == "1A2":
        frozen = {
            "1A": json.loads((root / "frozen-1A.json").read_text(encoding="utf-8")),
            "1A2": json.loads((root / "frozen-1A2.json").read_text(encoding="utf-8")),
        }
        arms = ("1A", "1A2")
    else:
        frozen = {arm: json.loads((root / f"frozen-{arm}.json").read_text(encoding="utf-8")) for arm in ("C0", cmp)}
        arms = ("C0", cmp)
    n = ENDPOINTS[cmp]
    endpoints = {
        arm: next(endpoint for endpoint in data["endpoints"] if endpoint["n"] == n) for arm, data in frozen.items()
    }

    if send is None:
        import bench.frozen_prompts as fp
        from bench.core import load_dotenv

        fp.SCENE = "3A"
        load_dotenv()
        send = fp._default_transport({"variation": "richer-3a-live"})
        decode = fp._decode_replay_body
    else:
        import bench.frozen_prompts as fp

        decode = fp._decode_replay_body

    rows = []
    for sample in range(first, last + 1):
        for arm in arms:
            endpoint = endpoints[arm]
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
                row["narration"] = decode(body)
                print(arm, n, sample, "ok", flush=True)
            except Exception as error:
                row["error"] = str(error)
                print(arm, n, sample, "error", flush=True)
            rows.append(row)
            out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmp", choices=ENDPOINTS)
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
    count = (args.last - args.first + 1) * 2
    print(f"requests {count}")
    if not args.confirm:
        print("dry run: nothing sent")
        raise SystemExit(0)
    run(args.cmp, args.out, args.first, args.last)
