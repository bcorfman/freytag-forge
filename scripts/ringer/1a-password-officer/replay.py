# ruff: noqa: E501
"""Replay frozen 1A narrator payloads with an explicit billing guard."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
ARMS = {
    "officer": ("CTRL", "BIO"),
    "raw": ("BIO", "ALIAS"),
    "walt": ("CTRL", "BIO"),
    "password": ("CTRL", "SUB", "ADD"),
    "voice": ("CTRL", "NOVOICE"),
    "recovery": ("REC",),
}
ENDPOINTS = {
    "officer": ("OFF6", "OFF7"),
    "raw": ("RAW7",),
    "walt": ("WALT",),
    "password": ("PW",),
    "voice": ("VOICE8", "VOICE9"),
    "recovery": ("REC8",),
}


def run(stage, out, first, last, send=None, only=None):
    assert 0 <= first <= last <= 12
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    root = ROOT / "bench/results/1a-password-officer"
    selected = ENDPOINTS[stage] if only is None else tuple(n for n in ENDPOINTS[stage] if n in only)
    frozen = {arm: json.loads((root / f"frozen-{stage}-{arm}.json").read_text(encoding="utf-8")) for arm in ARMS[stage]}
    endpoints = {
        (arm, n): next(item for item in frozen[arm]["endpoints"] if item["n"] == n)
        for n in selected
        for arm in ARMS[stage]
    }
    if send is None:
        import bench.frozen_prompts as fp
        from bench.core import load_dotenv

        fp.SCENE = "1A"
        load_dotenv()
        send = fp._default_transport({"variation": "1a-password-officer"})
    else:
        import bench.frozen_prompts as fp

    rows = []
    for sample in range(first, last + 1):
        for n in selected:
            for arm in ARMS[stage]:
                endpoint = endpoints[(arm, n)]
                row = {
                    "stage": stage,
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
    parser.add_argument("stage", choices=sorted(ARMS))
    parser.add_argument("out", type=Path)
    parser.add_argument("first", type=int)
    parser.add_argument("last", type=int)
    parser.add_argument("--only")
    parser.add_argument("--confirm", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    assert 0 <= args.first <= args.last <= 12
    if args.out.exists():
        raise FileExistsError(args.out)
    only = None if args.only is None else tuple(args.only.split(","))
    if only is not None:
        assert all(n in ENDPOINTS[args.stage] for n in only)
    count = (args.last - args.first + 1) * len(ENDPOINTS[args.stage] if only is None else only) * len(ARMS[args.stage])
    print(f"requests {count}")
    if not args.confirm:
        print("dry run: nothing sent")
        raise SystemExit(0)
    run(args.stage, args.out, args.first, args.last, only=only)
