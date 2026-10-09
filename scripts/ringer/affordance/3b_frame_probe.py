"""Replay a recorded 3B narrator prompt under six arms (billed: narrator Worker).

usage: 3b_frame_probe.py <prompts-r1.json> <samples> OUT.json

Arms: A = as recorded; B = frame A (situation and pressure about the false alarms);
C = B and the entry statement removed; D = C and 'broadcast relay' dropped from the scene
details; E = D and the 'EARLIER IN THE STORY' recall removed; F = E with frame B wording.
Two player inputs: the recorded 'Seize the broadcast relay.' (does the narration redirect?)
and a neutral 'Search the security corridors.' (where does it point?). On the neutral input
the command-referred 'Broadcast relay. This is a place.' THINGS line is dropped in every arm.
A reply is scored: mentions the relay; mentions an alarm, warning, door or console.
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
SIT = (
    "- The fight runs through the security corridors and the executive office. JANUS is tracking the fight"
    " through cameras, doors, and alarms; the group needs an opening to reach the broadcast relay.\n"
)
PRESS = "- What presses on Kristin now: Overload JANUS and seize the broadcast\n"
ENTRY = "- The broadcast relay is the immediate contested objective.\n"
DETAIL = "- broadcast relay\n"
EARLIER = (
    "EARLIER IN THE STORY:\n- The uprising is active, and the group is moving toward"
    " the command and broadcast levels.\n\n"
)
THING = "- Broadcast relay. This is a place.\n"
RECORDED = "- Seize the broadcast relay."
NEUTRAL = "- Search the security corridors."


def swap(user, old, new):
    assert old in user, old
    return user.replace(old, new, 1)


def frame(user, sit, press):
    return swap(swap(user, SIT, f"- {sit}\n"), PRESS, f"- What presses on Kristin now: {press}\n")


def b(user):
    return frame(user, "JANUS is tracking Kristin's moves.", "Feed JANUS false water and air alarms.")


def c(user):
    return swap(b(user), ENTRY, "")


def d(user):
    return swap(c(user), DETAIL, "")


def e(user):
    return swap(d(user), EARLIER, "")


ARMS = {"A": lambda u: u, "B": b, "C": c, "D": d, "E": e}


def arm_f(user):
    user = swap(user, ENTRY, "")
    user = swap(user, DETAIL, "")
    user = swap(user, EARLIER, "")
    return frame(user, "JANUS uses each warning to guess Kristin's next move.", "Make JANUS follow fake alarms.")


ARMS["F"] = arm_f
report = json.loads(Path(PROMPTS).read_text())
scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "3B")
base = next(p["prompt"] for p in scene["prompts"] if p["turn"] == 2)
assert RECORDED in base["user"] and "Place: security corridors" in base["user"]
INPUTS = {"recorded": lambda u: u, "neutral": lambda u: swap(swap(u, RECORDED, NEUTRAL), THING, "")}
ALARM = re.compile(r"alarm|warning|door|console|false", re.I)
url, token = os.environ["CLOUDFLARE_WORKER_URL"], os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
rows = []
for inp, mk in INPUTS.items():
    for arm, edit in ARMS.items():
        user = edit(mk(base["user"]))
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
                row["relay"] = "relay" in text.casefold()
                row["alarm"] = bool(ALARM.search(text))
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
for inp in INPUTS:
    for arm in ARMS:
        cell = [r for r in rows if r["input"] == inp and r["arm"] == arm]
        print(
            f"input {inp} arm {arm}: relay {sum(1 for r in cell if r.get('relay'))}/{len(cell)},"
            f" alarm-words {sum(1 for r in cell if r.get('alarm'))}/{len(cell)},"
            f" {sum(1 for r in cell if 'error' in r)} errors"
        )
