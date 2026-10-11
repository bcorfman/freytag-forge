"""Does a file sentence in the 2C SCENE bring the copied files into the narration? (billed)

usage: 2c_files_probe.py <prompts.json from 2c_files_render.py> <samples> OUT.json

Cells: 'search' ('Search the command levels for Michelle.') and 'medical' ('Retrieve Michelle's current location
from the medical terminal.'): the first commands of the two blind players that left 2C by timer on 80f5c64c. The
prompt is the one the engine renders offline for that command: no candidate, no copied-files material in it.
Arms: A = as rendered; B = ' Kristin can check the copied files.' added to the first SCENE line (ChatGPT's
sentence); C = ' The copied files lie close at hand.' added to the first SCENE line (existing approved 2C
delivery text, unchanged).
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
LINE_B = " Kristin can check the copied files."
LINE_C = " The copied files lie close at hand."
FILES = re.compile(r"\b(copied|copies|copy|files?|drive|usb|evidence|JANUS)\b", re.IGNORECASE)
INVENTED = re.compile(
    r"\b(console|monitor|screen|terminal|keyboard|desk|chair|panel|display|hatch|vault|safe|envelope|folder|badge)\b",
    re.IGNORECASE,
)


def add(user, line):
    anchor = "SCENE:\n- "
    assert anchor in user, "SCENE section missing from the rendered prompt"
    head, rest = user.split(anchor, 1)
    first, tail = rest.split("\n", 1)
    return f"{head}{anchor}{first}{line}\n{tail}"


ARMS = {"A": lambda user: user, "B": lambda user: add(user, LINE_B), "C": lambda user: add(user, LINE_C)}
if os.environ.get("PROBE_ARMS"):
    ARMS = {k: v for k, v in ARMS.items() if k in os.environ["PROBE_ARMS"]}
CELLS = {k: v for k, v in json.loads(Path(PROMPTS).read_text()).items() if k in ("search", "medical")}
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
                row["files"] = bool(FILES.search(prose))
                row["invented"] = bool(INVENTED.search(prose))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for name in CELLS:
    for arm in ARMS:
        cell = [r for r in rows if r["cell"] == name and r["arm"] == arm]
        print(
            f"{name} arm {arm}: {sum(1 for r in cell if r.get('files'))}/{len(cell)} mention files or evidence, "
            f"{sum(1 for r in cell if r.get('invented'))}/{len(cell)} name an invented object, "
            f"{sum(1 for r in cell if 'error' in r)} errors"
        )
