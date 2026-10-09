"""Replay a recorded 2C narrator prompt under four frame arms (billed: narrator Worker).

usage: 2c_detention_probe.py <prompts-r1.json> <samples> OUT.json

Arms: A = as recorded (old frame, no 'detention level'); B = the frame that names the
detention level (PR 545); C = old frame with 'valuable captives on the detention level' as a
scene detail; D = old frame with the detention-level mention cut to 'captives' only.
Three player inputs: the recorded pull 'Enter the detention levels through Michelle's
maintenance route.', the chain step 'Read the transfer orders.', and neutral 'Search the
command corridor.'. A reply is scored: names the detention level or holding block (mention);
sends Kristin down (descent words); names the chain (orders, files, message, drive).
Read every narration by hand as well.
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
OLD = "private executive channels, transfer orders, and a maintenance network."
NEW = "transfer orders for the captives on the detention level, and a maintenance network."
CUT = "transfer orders for the captives, and a maintenance network."
DETAIL_OLD = "- private executive channels\n"
RECORDED = "- Enter the detention levels through Michelle's maintenance route."
INPUTS = {
    "pull": RECORDED,
    "chain": "- Read the transfer orders.",
    "neutral": "- Search the command corridor.",
}


def swap(user, old, new):
    assert old in user, old
    return user.replace(old, new, 1)


ARMS = {
    "A": lambda u: u,
    "B": lambda u: swap(u, OLD, NEW),
    "C": lambda u: swap(u, DETAIL_OLD, DETAIL_OLD + "- valuable captives on the detention level\n"),
    "D": lambda u: swap(u, OLD, CUT),
}
MENTION = re.compile(r"detention|holding block|captive", re.I)
DESCENT = re.compile(r"\bdown\b|below|descend|lower level|stairs|elevator|enter the", re.I)
CHAIN = re.compile(r"order|file|message|drive|schedule|record|traffic|laptop", re.I)
report = json.loads(Path(PROMPTS).read_text())
scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "2C")
base = scene["prompts"][0]["prompt"]
assert RECORDED in base["user"] and OLD in base["user"] and DETAIL_OLD in base["user"]
url, token = os.environ["CLOUDFLARE_WORKER_URL"], os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
rows = []
for inp, line in INPUTS.items():
    for arm, edit in ARMS.items():
        user = edit(swap(base["user"], RECORDED, line))
        payload = {
            "system": base["system"],
            "user": user,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }
        for sample in range(N):
            headers = {"Content-Type": "application/json", "User-Agent": BROWSER_USER_AGENT}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            row = {"input": inp, "arm": arm, "sample": sample}
            try:
                with urlopen(
                    Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST"), timeout=60
                ) as response:  # noqa: S310
                    body = json.loads(response.read())
                segments = body.get("segments") if isinstance(body, dict) else None
                text = " ".join(str(seg.get("text", "")) for seg in segments) if segments else json.dumps(body)
                row["text"] = text
                row["mention"] = bool(MENTION.search(text))
                row["descent"] = bool(DESCENT.search(text))
                row["chain"] = bool(CHAIN.search(text))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for inp in INPUTS:
    for arm in ARMS:
        cell = [r for r in rows if r["input"] == inp and r["arm"] == arm]
        print(
            f"input {inp} arm {arm}: mention {sum(1 for r in cell if r.get('mention'))}/{len(cell)},"
            f" descent {sum(1 for r in cell if r.get('descent'))}/{len(cell)},"
            f" chain {sum(1 for r in cell if r.get('chain'))}/{len(cell)},"
            f" {sum(1 for r in cell if 'error' in r)} errors"
        )
