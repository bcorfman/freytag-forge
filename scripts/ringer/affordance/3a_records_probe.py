"""Replay recorded 3A prompts for 'read the experiment records' after the medical-level reveal (billed).

usage: 3a_records_probe.py <prompts-r2.json> <samples> OUT.json

Cells: r2 turn 4 ("Examine the experiment records.") and r2 turn 6 ("Read the experiment records."), the recorded 3A
prompts where the player tried to read the records after k_sl_3a_b_r2 had fired. b_r1 (the records reveal) is no longer
a candidate then, so the SCENE block carries no records material and no senior official.
Arms: A = as recorded; B = the k_sl_3a_b_r1 statement line added to SCENE, copied unchanged from knowledge.yaml;
C = the plot sentence "The senior official waits among the government prisoners." added to SCENE, copied unchanged from
the k_sl_3a_b_r2 delivery text; D = both lines.
The counts are a reading aid only; read every reply by hand.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, ".")
from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: E402

PROMPTS, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ANCHOR = "- Reaching Michelle and supporting the uprising are immediate priorities.\n"
LINE_B = (
    'Michelle shows Kristin experiment records proving planned "survivors" '
    "were conditioned to support Charles's story."
)
LINE_C = "The senior official waits among the government prisoners."
OFFICIAL = re.compile(r"\b(official|government prisoners?)\b", re.IGNORECASE)
RECORDS = re.compile(r"\b(survivors?|conditioned|conditioning)\b", re.IGNORECASE)
INVENTED = re.compile(r"\b(terminal|computer|screen|filing cabinet|folder|file cabinet|monitor|database)\b", re.I)


def prompt_of(turn):
    report = json.loads(Path(PROMPTS).read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "3A")
    return next(p["prompt"] for p in scene["prompts"] if p["turn"] == turn)


def add(user, *lines):
    assert ANCHOR in user, "anchor line missing from the recorded prompt"
    return user.replace(ANCHOR, "".join(f"- {line}\n" for line in lines) + ANCHOR, 1)


ARMS = {
    "A": lambda user: user,
    "B": lambda user: add(user, LINE_B),
    "C": lambda user: add(user, LINE_C),
    "D": lambda user: add(user, LINE_B, LINE_C),
}
if os.environ.get("PROBE_ARMS"):
    ARMS = {k: v for k, v in ARMS.items() if k in os.environ["PROBE_ARMS"]}
CELLS = {"t4": prompt_of(4), "t6": prompt_of(6)}
url, token = os.environ["CLOUDFLARE_WORKER_URL"], os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
rows = []
for name, prompt in CELLS.items():
    for arm, edit in ARMS.items():
        payload = {
            "system": prompt["system"],
            "user": edit(prompt["user"]),
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }
        for sample in range(N):
            headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            row = {"cell": name, "arm": arm, "sample": sample}
            try:
                with urlopen(
                    Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST"), timeout=60
                ) as response:  # noqa: S310
                    body = json.loads(response.read())
                raw = body.get("narration") if isinstance(body, dict) else None
                text = raw if isinstance(raw, str) else json.dumps(body)
                try:
                    prose = " ".join(s["text"] for s in json.loads(text)["segments"])
                except Exception:  # noqa: BLE001
                    prose = text
                row["text"] = text
                row["official"] = bool(OFFICIAL.search(prose))
                row["records"] = bool(RECORDS.search(prose))
                row["invented"] = bool(INVENTED.search(prose))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for name in CELLS:
    for arm in ARMS:
        cell = [r for r in rows if r["cell"] == name and r["arm"] == arm]
        print(
            f"{name} arm {arm}: {sum(1 for r in cell if r.get('official'))}/{len(cell)} name the official, "
            f"{sum(1 for r in cell if r.get('records'))}/{len(cell)} name the records' content, "
            f"{sum(1 for r in cell if r.get('invented'))}/{len(cell)} name a terminal or screen, "
            f"{sum(1 for r in cell if 'error' in r)} errors"
        )
