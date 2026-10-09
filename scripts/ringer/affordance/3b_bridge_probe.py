"""Replay the blind player's first 3B command under three opening arms (billed: player model).

usage: 3b_bridge_probe.py <report-dir> <samples> OUT.json

Reads the recorded 3B opening of replicates r1-r3 from <report-dir>/e2e-blind-player-r<N>.json.
Arms: A = as recorded; B = the clause 'while Charles sealed the primary exits and sent armed teams
downward' cut from the bridge sentence; C = B and the recap sentences about the one-use surface-gate
authorization cut. The player prompt is the real one (frontend/e2e/blind-player.js), with the 3B
opening as the whole transcript (the live player also sees earlier scenes).
A command is scored: exit/gate/surface words (pull) versus alarm/warning/console/door words (cue).
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

REPORTS, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
SYSTEM = (
    "You are a player at a text adventure. You only know what you have read on the screen. "
    "Write one active command for the next turn. Use an imperative verb and a direct object. "
    "Name your own things with first-person possessive words such as my laptop. "
    "Do not write I, do not refuse or restrain an action, and do not wait or merely listen. "
    "End the command with a period. Reply with one command."
)
CLAUSE = ", while Charles sealed the primary exits and sent armed teams downward."
RECAP = re.compile(
    r"The senior official Charles framed gives Kristin one-use authorization"
    r".*?narrow escape window rather than a solution\. "
)
PULL = re.compile(r"exit|gate|surface|escape|leave|flee", re.I)
CUE = re.compile(r"alarm|warning|console|door|false|corridor", re.I)


def arm_b(text):
    assert CLAUSE in text
    return text.replace(CLAUSE, ".", 1)


def arm_c(text):
    return RECAP.sub("", arm_b(text), count=1)


ARMS = {"A": lambda t: t, "B": arm_b, "C": arm_c}
key = os.environ["OPENAI_API_KEY"]
model = os.environ.get("E2E_PLAYER_MODEL", "gpt-5.6-luna")
rows = []
for rep in (1, 2, 3):
    report = json.loads(Path(REPORTS, f"e2e-blind-player-r{rep}.json").read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "3B")
    opening = scene["opening_text"]
    for arm, edit in ARMS.items():
        user = f"Screen transcript:\n{edit(opening)}\n\nStatus line:\n"
        for sample in range(N):
            body = {
                "model": model,
                "store": False,
                "input": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "c",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {"command": {"type": "string"}},
                            "required": ["command"],
                            "additionalProperties": False,
                        },
                    }
                },
            }
            row = {"opening": rep, "arm": arm, "sample": sample}
            try:
                req = Request(
                    "https://api.openai.com/v1/responses",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                    method="POST",
                )
                with urlopen(req, timeout=60) as resp:  # noqa: S310
                    payload = json.loads(resp.read())
                text = ""
                for item in payload.get("output", []):
                    for c in item.get("content", []):
                        text += c.get("text", "") if c.get("type") == "output_text" else ""
                row["command"] = json.loads(text)["command"]
                row["pull"] = bool(PULL.search(row["command"]))
                row["cue"] = bool(CUE.search(row["command"]))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for arm in ARMS:
    cell = [r for r in rows if r["arm"] == arm]
    print(
        f"arm {arm}: pull {sum(1 for r in cell if r.get('pull'))}/{len(cell)},"
        f" cue {sum(1 for r in cell if r.get('cue'))}/{len(cell)},"
        f" {sum(1 for r in cell if 'error' in r)} errors"
    )
