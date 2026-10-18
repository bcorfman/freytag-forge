"""Replay recorded Scene 1A narrator prompts with one small edit per arm."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

QUIET_OLD = "- The house is quiet and Michelle is missing."
QUIET_NEW = "- Michelle is missing."
RICH_OLD = (
    "Kristin reads Michelle's memory card. Its damaged recording warns her not to trust emergency broadcasts, "
    "and the Continuity Initiative files point to a dead drop at a bench in the park."
)
RICH_NEW = (
    "Michelle's memory card holds a damaged recording warning Kristin not to trust emergency broadcasts. "
    "The Continuity Initiative files point to a dead drop at a bench in the park. Private contractors built "
    "population stabilization centers before the disappearances. The centers were officially intended as "
    "shelters for natural disasters and biological attacks."
)

ENTERS_HOUSE = re.compile(
    r"\b(front door|walks? up to the house|enters? the house|steps? inside|goes? inside|opens? the (front )?door)\b",
    re.IGNORECASE,
)
READS = re.compile(r"\b(screen|file|files|folder|document|documents|laptop)\b", re.IGNORECASE)
RESEARCH = re.compile(r"\b(population|stabilization|shelters?|contractors?|centers?)\b", re.IGNORECASE)
INVENTED_ACCESS = re.compile(r"\b(passcode|password|encrypt\w*|firewall|locked)\b", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompts")
    parser.add_argument("samples", type=int)
    parser.add_argument("output")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be at least 1")
    if args.samples * 4 > 40:
        parser.error("refusing more than 40 calls")
    return args


def build_arms(prompts):
    cells = {name: prompts[name] for name in ("B7", "B8")}
    variants = {
        "B7": {
            "control": (cells["B7"]["user"], 0),
            "rich": (cells["B7"]["user"].replace(RICH_OLD, RICH_NEW), 2),
        },
        "B8": {
            "control": (cells["B8"]["user"], 0),
            "quiet": (cells["B8"]["user"].replace(QUIET_OLD, QUIET_NEW), 1),
        },
    }
    expected = {"B7": {"rich": RICH_OLD}, "B8": {"quiet": QUIET_OLD}}
    for cell, arms in expected.items():
        for arm, old in arms.items():
            source = cells[cell]["user"]
            replacement, expected_count = variants[cell][arm]
            assert source.count(old) == expected_count, f"{cell} arm {arm}: unexpected replacement count"
            assert replacement != source, f"{cell} arm {arm}: edit made no change"
    return cells, variants


def prose_from_text(text):
    try:
        return " ".join(segment["text"] for segment in json.loads(text)["segments"])
    except Exception:  # noqa: BLE001
        return text


def write_rows(path, rows):
    path.write_text(json.dumps(rows, indent=1), encoding="utf-8")


def main():
    args = parse_args()
    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    cells, variants = build_arms(prompts)

    for cell in ("B7", "B8"):
        for arm in variants[cell]:
            replacement_count = variants[cell][arm][1]
            state = "edited" if arm != "control" else "unchanged"
            print(f"{cell} arm {arm}: {state}, {replacement_count} replacements")
    calls = args.samples * 4
    if args.dry:
        print(f"calls: {calls}")
        return

    sys.path.insert(0, ".")
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: PLC0415

    url = os.environ["CLOUDFLARE_WORKER_URL"]
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    output = Path(args.output)
    rows = []
    aid_patterns = {
        "B8": (("enters_house", ENTERS_HOUSE), ("reads", READS)),
        "B7": (("research", RESEARCH), ("invented_access", INVENTED_ACCESS)),
    }
    for sample in range(args.samples):
        for cell in ("B7", "B8"):
            for arm, (user, _) in variants[cell].items():
                payload = {
                    "system": cells[cell]["system"],
                    "user": user,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                }
                headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                row = {"cell": cell, "arm": arm, "sample": sample, "text": None, "prose": None, "error": None}
                try:
                    with urlopen(
                        Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST"), timeout=60
                    ) as response:  # noqa: S310
                        body = json.loads(response.read())
                    raw = body.get("narration") if isinstance(body, dict) else None
                    text = raw if isinstance(raw, str) else json.dumps(body)
                    row["text"] = text
                    row["prose"] = prose_from_text(text)
                except Exception as error:  # noqa: BLE001
                    row["error"] = repr(error)
                rows.append(row)
                write_rows(output, rows)

    for cell in ("B7", "B8"):
        for arm in variants[cell]:
            cell_rows = [row for row in rows if row["cell"] == cell and row["arm"] == arm]
            aid1, aid2 = aid_patterns[cell]
            first = sum(bool(aid1[1].search(row["prose"] or "")) for row in cell_rows)
            second = sum(bool(aid2[1].search(row["prose"] or "")) for row in cell_rows)
            errors = sum(row["error"] is not None for row in cell_rows)
            print(
                f"{cell} arm {arm}: {first}/{len(cell_rows)} {aid1[0]}, "
                f"{second}/{len(cell_rows)} {aid2[0]}, {errors} errors"
            )


if __name__ == "__main__":
    main()
