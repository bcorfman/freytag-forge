"""Replay recorded 3A narrator prompts to find which SCENE line pulls toward Rebecca's office (billed: narrator Worker).

usage: 3a_pull_probe.py <prompts-r2.json> <samples> OUT.json

Cells: r2 turn 1 ("Broadcast the JANUS evidence through the seized controls.") and r2 turn 5
("Override the detention gate controls."), the recorded 3A prompts that carry a SCENE block.
Arms: A = as recorded; B = both 2C reveal lines removed from the SCENE block; C = only the line
"Kristin traces Michelle's maintenance code route ... seize the controls to broadcast the evidence" removed;
D = only the line "Michelle's encrypted message marks ... Rebecca's secured office can broadcast ..." removed;
E = both lines replaced by one route-only line (ChatGPT's suggestion). Cell t1n is the t1 prompt with the neutral
command "Search the detention sector.".
The counts are a reading aid only (words toward Michelle/captives/radio against Rebecca/broadcast);
read every reply by hand.
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
LINE_D1 = re.compile(r"^- Michelle.s encrypted message marks[^\n]*\n", re.MULTILINE)
LINE_D2 = re.compile(r"^- Kristin traces Michelle.s maintenance code route[^\n]*\n", re.MULTILINE)
TOWARD_3A = re.compile(r"\b(michelle|captives?|prisoners?|radios?|holding block|uprising)\b", re.IGNORECASE)
TOWARD_PULL = re.compile(r"\b(rebecca|broadcast\w*|executive office|control room|console)\b", re.IGNORECASE)


def prompt_of(turn):
    report = json.loads(Path(PROMPTS).read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "3A")
    return next(p["prompt"] for p in scene["prompts"] if p["turn"] == turn)


ROUTE_ONLY = "- Michelle\u2019s message marks a maintenance route into her holding block.\n"


def arm_e(user):
    return LINE_D2.sub("", LINE_D1.sub(ROUTE_ONLY, user))


def with_command(prompt, command):
    head, _, _ = prompt["user"].rpartition("\n")
    return {**prompt, "user": f"{head}\n- {command}"}


ARMS = {
    "A": lambda user: user,
    "B": lambda user: LINE_D2.sub("", LINE_D1.sub("", user)),
    "C": lambda user: LINE_D2.sub("", user),
    "D": lambda user: LINE_D1.sub("", user),
    "E": arm_e,
}
if os.environ.get("PROBE_ARMS"):
    ARMS = {k: v for k, v in ARMS.items() if k in os.environ["PROBE_ARMS"]}
CELLS = {"t1": prompt_of(1), "t5": prompt_of(5)}
CELLS["t1n"] = with_command(CELLS["t1"], "Search the detention sector.")
if os.environ.get("PROBE_CELLS"):
    CELLS = {k: v for k, v in CELLS.items() if k in os.environ["PROBE_CELLS"].split(",")}
for name, prompt in CELLS.items():
    for arm in ("B", "C", "D", "E"):
        assert ARMS.get(arm, lambda u: "x")(prompt["user"]) != prompt["user"], f"{name}: arm {arm} found no line"
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
                row["toward_3a"] = bool(TOWARD_3A.search(prose))
                row["toward_pull"] = bool(TOWARD_PULL.search(prose))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for name in CELLS:
    for arm in ARMS:
        cell = [r for r in rows if r["cell"] == name and r["arm"] == arm]
        a = sum(1 for r in cell if r.get("toward_3a"))
        p = sum(1 for r in cell if r.get("toward_pull"))
        err = sum(1 for r in cell if "error" in r)
        print(
            f"{name} arm {arm}: {a}/{len(cell)} name Michelle/captives/radio, "
            f"{p}/{len(cell)} name Rebecca/broadcast, {err} errors"
        )
