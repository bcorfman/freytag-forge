"""Replay recorded Scene 2C narrator prompts with one small edit per arm."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

LINE_A = (
    "- Kristin and Brandon. Place: security corridors. This is a group of people. "
    "If the player talks to them, they say nothing."
)
LINE_B = "- Kristin and Brandon. Place: security corridors."

SAYS_SECURITY_CORRIDORS = re.compile(r"\bsecurity corridors?\b", re.IGNORECASE)
NAMES_DETENTION = re.compile(r"\bdetention\b", re.IGNORECASE)
ENTERS_DETENTION_LEVEL = re.compile(
    r"\b(reach(es|ed)?|enter(s|ed)?|arrive[sd]?|descend(s|ed)?)\b[^.]{0,60}\bdetention\b",
    re.IGNORECASE,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompts")
    parser.add_argument("samples", type=int)
    parser.add_argument("output")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be at least 1")
    if args.samples * 3 > 40:
        parser.error("refusing more than 40 calls")
    return args


def build_arms(prompts):
    cells = {"C3": prompts["C3"]}
    source = cells["C3"]["user"]

    variants = {
        "C3": {
            "control": (source, 0),
            "nogroup": (source.replace(LINE_A + "\n", "").replace(LINE_B + "\n", ""), 2),
            "commandlevels": (
                source.replace(LINE_A, LINE_A.replace("security corridors", "command levels")).replace(
                    LINE_B, LINE_B.replace("security corridors", "command levels")
                ),
                2,
            ),
        }
    }
    for arm in ("nogroup", "commandlevels"):
        assert source.splitlines().count(LINE_A) == 1, f"C3 arm {arm}: unexpected LINE_A count"
        assert source.splitlines().count(LINE_B) == 1, f"C3 arm {arm}: unexpected LINE_B count"
        replacement, expected_count = variants["C3"][arm]
        assert replacement != source, f"C3 arm {arm}: edit made no change"
        assert expected_count == 2, f"C3 arm {arm}: unexpected replacement count"
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

    for cell in ("C3",):
        for arm in variants[cell]:
            replacement_count = variants[cell][arm][1]
            state = "edited" if arm != "control" else "unchanged"
            print(f"{cell} arm {arm}: {state}, {replacement_count} replacements")
    calls = args.samples * 3
    if args.dry:
        print(f"calls: {calls}")
        return

    sys.path.insert(0, ".")
    from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: PLC0415

    url = os.environ["CLOUDFLARE_WORKER_URL"]
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    output = Path(args.output)
    rows = []
    for sample in range(args.samples):
        for cell in ("C3",):
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

    for cell in ("C3",):
        for arm in variants[cell]:
            cell_rows = [row for row in rows if row["cell"] == cell and row["arm"] == arm]
            says_security_corridors = sum(bool(SAYS_SECURITY_CORRIDORS.search(row["prose"] or "")) for row in cell_rows)
            names_detention = sum(bool(NAMES_DETENTION.search(row["prose"] or "")) for row in cell_rows)
            enters_detention_level = sum(bool(ENTERS_DETENTION_LEVEL.search(row["prose"] or "")) for row in cell_rows)
            errors = sum(row["error"] is not None for row in cell_rows)
            print(
                f"{cell} arm {arm}: {says_security_corridors}/{len(cell_rows)} says_security_corridors, "
                f"{names_detention}/{len(cell_rows)} names_detention, "
                f"{enters_detention_level}/{len(cell_rows)} enters_detention_level, {errors} errors"
            )


if __name__ == "__main__":
    main()
