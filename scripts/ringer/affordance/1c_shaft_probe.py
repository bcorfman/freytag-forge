"""Replay recorded 1C narrator prompts for 'climb the observation shaft' (billed).

usage: 1c_shaft_probe.py <prompts-a.json> <prompts-c.json> <samples> OUT.json

Cells: a3 ('Climb the observation shaft ladder.') and c3 ('Climb the observation shaft.'), turn 3 of two recorded runs
that timed out. In both the SCENE block says nothing about what the shaft overlooks, and the narrator went on to
invent a console or monitor.
Arms: A = as recorded; B = the plot 1C.2 sentence added to SCENE, copied unchanged from plot.md; C = the 1C cue sentence
added to SCENE, copied unchanged from handoffs.yaml.
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

PA, PC, N, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
ANCHOR = "- The regional facility is the immediate, dangerous destination.\n"
LINE_B = "From an observation shaft, Kristin sees rows of sedated prisoners being moved through a processing area."
LINE_C = "The observation shaft overlooks a processing line. Identification numbers are visible on the uniforms below."
SEES = re.compile(r"\b(processing|uniforms?|identification|prisoners?|captives?)\b", re.IGNORECASE)
INVENTED = re.compile(
    r"\b(console|computer|monitor|screen|terminal|keyboard|desk|chair|tab|logs?|panel|display)\b", re.IGNORECASE
)


def prompt_of(path, turn):
    report = json.loads(Path(path).read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "1C")
    return next(p["prompt"] for p in scene["prompts"] if p["turn"] == turn)


def add(user, line):
    assert ANCHOR in user, "anchor line missing from the recorded prompt"
    return user.replace(ANCHOR, f"- {line}\n" + ANCHOR, 1)


ARMS = {"A": lambda user: user, "B": lambda user: add(user, LINE_B), "C": lambda user: add(user, LINE_C)}
if os.environ.get("PROBE_ARMS"):
    ARMS = {k: v for k, v in ARMS.items() if k in os.environ["PROBE_ARMS"]}
CELLS = {"a3": prompt_of(PA, 3), "c3": prompt_of(PC, 3)}
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
                row["sees"] = bool(SEES.search(prose))
                row["invented"] = bool(INVENTED.search(prose))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for name in CELLS:
    for arm in ARMS:
        cell = [r for r in rows if r["cell"] == name and r["arm"] == arm]
        print(
            f"{name} arm {arm}: {sum(1 for r in cell if r.get('sees'))}/{len(cell)} name the processing line or "
            f"prisoners, {sum(1 for r in cell if r.get('invented'))}/{len(cell)} name a console or screen, "
            f"{sum(1 for r in cell if 'error' in r)} errors"
        )
