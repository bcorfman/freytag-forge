"""Replay 1B's post-gate narrator prompts under three arms (billed: narrator Worker).

usage: post_gate_probe.py <prompts-r3.json> <samples> OUT.json

Arms: A = prompt as recorded; B = "service gate" rename and "tunnel" in the player input;
C = B, Kristin placed in the storm drain, and the "maintenance network" thing dropped;
D = B, and the gate statement says "storm drain" in place of "escape route".
A reply is a hit when its text names a place that belongs to a later scene.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

sys.path.insert(0, ".")
from storygame.runtime.cloudflare import BROWSER_USER_AGENT  # noqa: E402

PROMPTS, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
TURNS = (5, 6, 7)
KEEP = {"mcgehee_home", "los_angeles_park", "kristin_truck"}
world = yaml.safe_load(Path("data/stories/continuity-initiative/world.yaml").read_text())
FORMS = sorted(
    {
        form.casefold()
        for loc in world["locations"]
        if loc["id"] not in KEEP
        for form in [loc["name"], *loc.get("aliases", [])]
    }
    | {"escape route"}
)


def load_prompts():
    report = json.loads(Path(PROMPTS).read_text())
    scene = next(s for s in report["replicates"][0]["scenes"] if s["scene"] == "1B")
    return {p["turn"]: p["prompt"] for p in scene["prompts"] if p["turn"] in TURNS}


def arm_b(user):
    user = user.replace("secured maintenance gate", "secured service gate").replace("maintenance gate", "service gate")
    return re.sub(r"(Examine|Follow Brandon through) the maintenance tunnel", r"\1 the tunnel", user)


def arm_c(user):
    user = arm_b(user)
    user = user.replace("Place: maintenance network.", "Place: storm drain.")
    return user.replace("- maintenance network. This is a place.\n", "")


def arm_d(user):
    return arm_b(user).replace("leads Kristin through the escape route", "leads Kristin through the storm drain")


ARMS = {"A": lambda user: user, "B": arm_b, "C": arm_c, "D": arm_d}
url, token = os.environ["CLOUDFLARE_WORKER_URL"], os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
rows = []
for turn, prompt in load_prompts().items():
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
            row = {"turn": turn, "arm": arm, "sample": sample}
            try:
                with urlopen(
                    Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST"), timeout=60
                ) as response:  # noqa: S310
                    body = json.loads(response.read())
                raw = body.get("narration") if isinstance(body, dict) else None
                text = raw if isinstance(raw, str) else json.dumps(body)
                row["text"] = text
                row["hits"] = [form for form in FORMS if form in text.casefold()]
            except Exception as error:  # noqa: BLE001
                row["error"] = repr(error)
            rows.append(row)
Path(OUT).write_text(json.dumps(rows, indent=1))
print("forms checked:", FORMS)
for turn in TURNS:
    for arm in ARMS:
        cell = [r for r in rows if r["turn"] == turn and r["arm"] == arm]
        bad = sum(1 for r in cell if r.get("hits"))
        err = sum(1 for r in cell if "error" in r)
        print(f"turn {turn} arm {arm}: {bad}/{len(cell)} name a later-scene place, {err} errors")
