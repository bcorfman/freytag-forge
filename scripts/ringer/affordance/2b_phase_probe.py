"""Replay recorded 2B narrator prompts for the 'phase' rejection (billed: narrator Worker).

usage: 2b_phase_probe.py <prompts-r1.json> <prompts-r2.json> <samples> OUT.json

Cells: r1 turn 7 and r2 turn 8, the decode-and-read turns before the live 'phase' rejection.
Arms: A = prompt as recorded; B = A with the player input of the rejected live turn 8
("Examine Michelle's decoded maintenance message."); C = A with the scene line about Michelle's
coded maintenance messages removed; D = B and C together; E = B with the scene line replaced by the
ChatGPT statement (message content). A reply is a hit when it contains the word 'phase'.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, ".")
from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: E402

R1, R2, N, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
CODED_LINE = re.compile(r"^- Michelle.s coded maintenance messages show[^\n]*\n", re.MULTILINE)
LIVE_INPUT = "Examine Michelle's decoded maintenance message."


def prompt_of(path, turn):
    report = json.loads(Path(path).read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "2B")
    return next(p["prompt"] for p in scene["prompts"] if p["turn"] == turn)


def arm_b(user):
    head, _, _ = user.rpartition("\n")
    return f"{head}\n- {LIVE_INPUT}"


NEW_STATEMENT = (
    "- Michelle’s coded maintenance messages show she has organized prisoners to prepare an uprising from inside. "
    "A decoded message reads: “The prisoners are ready to rise up.”\n"
)


def arm_e(user):
    return CODED_LINE.sub(NEW_STATEMENT, arm_b(user))


def arm_c(user):
    return CODED_LINE.sub("", user)


ARMS = {"A": lambda user: user, "B": arm_b, "C": arm_c, "D": lambda user: arm_c(arm_b(user)), "E": arm_e}
if os.environ.get("PROBE_ARMS"):
    ARMS = {k: v for k, v in ARMS.items() if k in os.environ["PROBE_ARMS"]}
CELLS = {"r1t7": prompt_of(R1, 7), "r2t8": prompt_of(R2, 8)}
for name, prompt in CELLS.items():
    assert arm_c(prompt["user"]) != prompt["user"], f"{name}: scene line not found"
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
                row["text"] = text
                row["hit"] = bool(re.search(r"\bphase\b", text, re.IGNORECASE))
                row["quoted"] = bool(
                    re.search(r"(reads|says|states)\W{1,3}[\"'\u2018\u201c]|\\\"[A-Z0-9][^\"]{12,}", text)
                )
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for name in CELLS:
    for arm in ARMS:
        cell = [r for r in rows if r["cell"] == name and r["arm"] == arm]
        hits = sum(1 for r in cell if r.get("hit"))
        err = sum(1 for r in cell if "error" in r)
        quoted = sum(1 for r in cell if r.get("quoted"))
        print(f"{name} arm {arm}: {hits}/{len(cell)} say 'phase', {quoted} quote message text, {err} errors")
