# ruff: noqa: E501
"""Shared-narrator-instruction-conflicts plan, step 1: free baseline captures. Zero model calls (network stubbed).

For each endpoint records the complete wire payload, whether an authored handoff was selected, the recovery
payload (first narration reply is deliberately malformed so the normal recovery path fires), size, and the presence of the
three disputed lines. Run from the repo root:
TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/shared-narrator/baseline_capture.py OUTDIR
"""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402
from storygame.runtime.capture import WorldCapture  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bench/results/shared-narrator/baseline"
OUT.mkdir(parents=True, exist_ok=True)

LINES = {
    "scene_only": "Use only what the SCENE section tells you.",
    "opening_scene": "Show only the opening beat and what the SCENE section tells you.",
    "completion": "Finish each action the player gives.",
    "length": "Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately.",
    "talks_answers": "When the player talks to someone, that person answers.",
    "may_say_aloud": " may say this aloud: ",
    "handoff_leadup": "Write only what leads up to it.",
}
BASE_VARIATION = json.loads((ROOT / "bench/variations/richer-3a-loc-P.json").read_text())
SCENES = {
    "3A": {
        "entry_facts": BASE_VARIATION["entry_facts"],
        "inputs": json.loads((ROOT / "bench/variations/richer-3a-loc-P.json").read_text())["scripts"]["3A"][0][
            "inputs"
        ],
    },
    "1C": {
        "entry_facts": [],
        "inputs": [
            "Look around the loading docks.",
            "Check the loading docks for signs of activity.",
            "Ask Brandon about the facility.",
        ],
    },
}


def variation_for(scene: str) -> Path:
    v = copy.deepcopy(BASE_VARIATION)
    v["name"] = f"shared-narrator-{scene}"
    v["entry_facts"] = SCENES[scene]["entry_facts"]
    v["scripts"] = {scene: [{"inputs": SCENES[scene]["inputs"]}]}
    path = OUT / f"variation-{scene}.json"
    path.write_text(json.dumps(v, indent=2) + "\n")
    return path


def flags(payload: dict) -> dict:
    both = payload["system"] + "\n" + payload["user"]
    return {name: both.count(text) for name, text in LINES.items()}


def run(provider_state, action) -> dict:
    """Run one action with a stub; first narration reply malformed -> recovery. Returns first and recovery payloads."""
    provider = fp._offline_capture_provider(provider_state)
    calls: list[dict] = []
    seen: dict = {"handoff": None, "handoff_at_recovery": None}

    def send(wire):
        calls.append(copy.deepcopy(wire))
        if fp._is_narration_payload(wire):
            n = sum(1 for c in calls if fp._is_narration_payload(c))
            if n == 1:
                seen["handoff"] = (
                    getattr(provider.authored_handoff, "candidate", None) and provider.authored_handoff.candidate.id
                )
                return json.dumps({"narration": "not valid json"}).encode()
            seen["handoff_at_recovery"] = (
                getattr(provider.authored_handoff, "candidate", None) and provider.authored_handoff.candidate.id
            )
        return fp._CANNED_REPLY

    provider._send_http = send
    capture = WorldCapture(provider, lambda _s, _q: None)
    engine = RuntimeEngine(provider_state, provider, capture=capture)
    action(engine)
    narr = [c for c in calls if fp._is_narration_payload(c)]
    return {"narration_calls": narr, "other_calls": [c for c in calls if not fp._is_narration_payload(c)], **seen}


records = []
for scene, spec in SCENES.items():
    vpath = variation_for(scene)
    variation = load_variation(vpath)
    fp.SCENE = scene
    n_inputs = len(spec["inputs"])
    states, inputs = fp._prefix_states(variation, list(range(1, n_inputs + 1)))
    # opening: the state before the first command
    pkg_hash = variation["_package_hash"]
    jobs = [("opening", None, copy.deepcopy(states[0]), lambda e: e.opening())]
    for i, cmd in enumerate(inputs, start=1):
        jobs.append((f"c{i}", cmd, copy.deepcopy(states[i - 1]), (lambda c: lambda e: e.turn(c))(cmd)))
    for label, cmd, state, action in jobs:
        res = run(state, action)
        narr = res["narration_calls"]
        if not narr:
            records.append({"scene": scene, "label": label, "command": cmd, "error": "no narration payload"})
            continue
        first, recov = narr[0], (narr[1] if len(narr) > 1 else None)
        rec = {
            "scene": scene,
            "label": label,
            "command": cmd,
            "kind": "opening" if label == "opening" else ("handoff" if res["handoff"] else "ordinary"),
            "selected_handoff": res["handoff"],
            "package_hash": pkg_hash,
            "chars": {
                "system": len(first["system"]),
                "user": len(first["user"]),
                "total": len(first["system"]) + len(first["user"]),
            },
            "flags": flags(first),
            "wire_payload": first,
            "recovery_payload": recov,
            "recovery_flags": flags(recov) if recov else None,
            "recovery_extra_system": recov["system"][len(first["system"]) :] if recov else None,
            "other_call_count": len(res["other_calls"]),
        }
        records.append(rec)
        print(
            f"{scene} {label:8} {rec['kind']:8} handoff={res['handoff']} chars={rec['chars']['total']} flags={ {k: v for k, v in rec['flags'].items() if v} } recovery={'yes' if recov else 'NO'}"
        )

diff = subprocess.run(["git", "diff", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout
meta = {
    "sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
    "dirty_diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
    "lines": LINES,
    "records": records,
}
(OUT / "baseline.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
print("wrote", OUT / "baseline.json", "sha", meta["sha"][:8], "dirty", meta["dirty_diff_sha256"][:12])
