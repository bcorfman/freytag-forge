# ruff: noqa: E501
"""Shared-narrator-instruction-conflicts plan, step 2 (free): freeze the endpoint payloads and derive the A/B/C arms.
Zero model calls. Control payloads are the production capture payloads; each arm is the control with exactly one
allowed-line edit, asserted below. Run from the repo root:
TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/prereg_capture.py OUTDIR [--probe]
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402
from storygame.runtime.capture import WorldCapture  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

OUT = Path(sys.argv[1])
PROBE = "--probe" in sys.argv
OUT.mkdir(parents=True, exist_ok=True)
BASE = json.loads((ROOT / "bench/variations/richer-3a-loc-P.json").read_text())
S3A = BASE["scripts"]["3A"][0]["inputs"]

SCENE_ONLY = "Use only what the SCENE section tells you.\n"
OPENING_OLD = "Show only the opening beat and what the SCENE section tells you."
OPENING_NEW = "Show only the opening beat."
COMPLETION = "Finish each action the player gives.\n"
LENGTH_OLD = "Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately."
LENGTH_NEW = "Write only as much as the lead-up needs. Then stop."

# id, scene, entry_facts, scripted prefix (engine plays these with a handoff-aware stub), command, expected kind
ENDPOINTS = [
    ("A1", "3A", BASE["entry_facts"], [], None, "opening"),
    ("A2", "3A", BASE["entry_facts"], S3A[:8], S3A[8], "ordinary"),
    ("A3", "3A", BASE["entry_facts"], S3A[:8], "Ask Michelle about the medical level.", "ordinary"),
    ("H1", "3A", BASE["entry_facts"], S3A[:4], S3A[4], "handoff"),
    ("H2", "1C", [], [], "Check the loading docks for signs of activity.", "handoff"),
]


def build_variation(eid, scene, entry_facts, prefix, command):
    v = copy.deepcopy(BASE)
    v["name"] = f"shared-narrator-{eid}"
    v["entry_facts"] = entry_facts
    v["scripts"] = {scene: [{"inputs": [*prefix, *([command] if command else ["unused"])]}]}
    path = OUT / f"variation-{eid}.json"
    path.write_text(json.dumps(v, indent=2) + "\n")
    return load_variation(path)


def capture_one(eid, scene, entry_facts, prefix, command):
    variation = build_variation(eid, scene, entry_facts, prefix, command)
    fp.SCENE = scene
    n = len(prefix) + 1
    states, _ = fp._prefix_states(variation, [n])
    state = copy.deepcopy(states[n - 1])
    provider = fp._offline_capture_provider(state)
    calls, seen = [], {}

    def send(wire):
        calls.append(copy.deepcopy(wire))
        if fp._is_narration_payload(wire) and "handoff" not in seen:
            h = provider.authored_handoff
            seen["handoff"] = h.candidate.id if h is not None else None
        return fp._CANNED_REPLY

    provider._send_http = send
    engine = RuntimeEngine(state, provider, capture=WorldCapture(provider, lambda _s, _q: None))
    engine.opening() if command is None else engine.turn(command)
    narr = [c for c in calls if fp._is_narration_payload(c)]
    assert len(narr) == 1, (eid, len(narr))
    return {
        "id": eid,
        "scene": scene,
        "command": command,
        "prefix": prefix,
        "selected_handoff": seen.get("handoff"),
        "committed_after_prefix": fp._true_fact_ids(states[n - 1]),
        "package_hash": variation["_package_hash"],
        "wire_payload": narr[0],
    }


def one_edit(payload, old, new):
    assert payload["system"].count(old) == 1, old
    p = copy.deepcopy(payload)
    p["system"] = p["system"].replace(old, new)
    return p


records = []
for eid, scene, ef, prefix, command, expected in ENDPOINTS:
    rec = capture_one(eid, scene, ef, prefix, command)
    kind = "opening" if command is None else ("handoff" if rec["selected_handoff"] else "ordinary")
    user = rec["wire_payload"]["user"]
    print(
        eid,
        scene,
        repr(command),
        kind,
        rec["selected_handoff"],
        "speaker lines",
        user.count(" may say this aloud: "),
        "chars",
        len(rec["wire_payload"]["system"]) + len(user),
    )
    assert kind == expected, f"{eid}: expected {expected}, got {kind}"
    records.append(rec)
if PROBE:
    sys.exit(0)

arms = {"C0": {}, "A": {}, "B": {}, "C": {}}
for rec in records:
    p, eid = rec["wire_payload"], rec["id"]
    arms["C0"][eid] = p
    if eid in ("A1", "A2", "A3"):
        arms["A"][eid] = one_edit(p, OPENING_OLD, OPENING_NEW) if eid == "A1" else one_edit(p, SCENE_ONLY, "")
    if eid in ("H1", "H2"):
        arms["B"][eid] = one_edit(p, COMPLETION, "")
        arms["C"][eid] = one_edit(p, LENGTH_OLD, LENGTH_NEW)
out = {"endpoints": {r["id"]: {k: v for k, v in r.items() if k != "wire_payload"} for r in records}, "arms": {}}
for arm, eps in arms.items():
    for eid, payload in eps.items():
        base = arms["C0"][eid]
        assert payload["user"] == base["user"]
        diff_lines = set(base["system"].split("\n")) ^ set(payload["system"].split("\n"))
        out["arms"].setdefault(arm, {})[eid] = {
            "payload": payload,
            "chars": {"system": len(payload["system"]), "user": len(payload["user"])},
            "changed_lines": sorted(diff_lines),
            "sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12],
        }
        print(
            arm,
            eid,
            "system chars",
            len(base["system"]),
            "->",
            len(payload["system"]),
            "| changed:",
            sorted(diff_lines) if arm != "C0" else "-",
        )
(OUT / "frozen.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print("wrote", OUT / "frozen.json")
