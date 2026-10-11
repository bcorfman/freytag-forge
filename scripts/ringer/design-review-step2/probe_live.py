"""Targeted live probes for the attempt bundle against the hosted staging API.

Probe forced: play scene 1A with moves that earn nothing until the staged handoff moves the scene.
Probe reject: ask about protected story terms in a fresh session until narration is rejected.
Usage: probe_live.py <base_url> <test_clock_token> <out.json>
"""

import json
import sys
import time
import urllib.error
import urllib.request

base, token, out = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3]
HEADERS = {"content-type": "application/json", "x-freytag-test-clock-token": token}


def call(path, body):
    request = urllib.request.Request(base + path, json.dumps(body).encode(), HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read() or b"{}"), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}"), dict(error.headers)


def session():
    status, body, _ = call("/api/v1/session", {"story_id": "continuity_initiative"})
    assert status == 200, (status, body)
    return body["session_id"]


def turn(session_id, text):
    for _ in range(3):
        status, body, headers = call("/api/v1/turn", {"session_id": session_id, "player_input": text})
        if status != 429:
            break
        time.sleep(65)
    headers = {key.lower(): value for key, value in headers.items()}
    return {"input": text, "status": status, "bundle": body.get("attempt_bundle"), "detail": body.get("detail"),
            "scene": (body.get("state") or {}).get("scene_id"), "code": headers.get("x-freytag-rejection-code")}


report = {"forced": [], "reject": []}
idle = ["Examine the ceiling.", "Look under the rug.", "Check the window latch.", "Inspect the light switch.",
        "Examine the floor.", "Look behind the door.", "Check the wall outlet.", "Inspect the baseboard."]
sid = session()
for index in range(20):
    row = turn(sid, idle[index % len(idle)])
    report["forced"].append(row)
    if row["status"] == 200 and row["scene"] not in (None, "1A"):
        break
    time.sleep(0.5)

asks = ["Ask about Phase Two.", "Say JANUS out loud.", "Ask about the cooling-water imbalance.", "Ask for Rebecca.",
        "Tell everyone about Phase Two.", "Read the Phase Two file."]
sid = session()  # rejected turns restore state, so one session serves every ask
for text in asks:
    row = turn(sid, text)
    report["reject"].append(row)
    if sum(1 for item in report["reject"] if item["status"] == 409) >= 2:
        break
json.dump(report, open(out, "w"), indent=1)

problems = []
for name in report:
    for row in report[name]:
        if row["status"] in (200, 409) and row["bundle"] is None:
            problems.append(f"{name}: no bundle for {row['input']!r} status {row['status']}")
forced = [r for r in report["forced"] if r["bundle"] and r["bundle"]["transition_cause"] == "forced"]
rejected = [r for r in report["reject"] if r["status"] == 409]
print("forced turns", len(report["forced"]), "scene end", report["forced"][-1]["scene"])
print("causes", [(r["status"], r["bundle"]["outcome"], r["bundle"]["transition_cause"]) for r in report["forced"] if r["bundle"]])
print("rejections", [(r["input"], r["code"], r["bundle"] and r["bundle"]["rejection"]) for r in rejected])
print("reject statuses", [r["status"] for r in report["reject"]])
if not forced:
    problems.append("no forced exit observed")
if not rejected:
    problems.append("no rejection observed")
for item in rejected:
    if item["bundle"]["outcome"] != "rejected" or item["bundle"]["rejection"]["code"] != item["code"]:
        problems.append(f"rejection bundle does not match header for {item['input']!r}")
print("PROBLEMS", problems or "none")
sys.exit(1 if problems else 0)
