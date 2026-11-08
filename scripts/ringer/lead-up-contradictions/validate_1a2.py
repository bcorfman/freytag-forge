# ruff: noqa: E501
"""Offline check for comparison 1A2 (full bio vs trimmed bio at c6): frozen payload differs by exactly one line; replay.py drives it with control arm '1A'."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/lead-up-contradictions"
FULL = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
TRIM = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."
errors = []


def need(c, m):
    if not c:
        errors.append(m)


a = json.loads((OUT / "frozen-1A.json").read_text())["endpoints"][0]
path = OUT / "frozen-1A2.json"
need(path.exists(), "frozen-1A2.json missing")
if path.exists():
    d = json.loads(path.read_text())
    need(d.get("control") == "1A", f"control field is {d.get('control')!r}, expected '1A'")
    es = d["endpoints"]
    need([e["n"] for e in es] == ["c6"], "1A2 must have exactly one endpoint c6")
    w = es[0]["wire_payload"]
    need(w["system"] == a["wire_payload"]["system"], "system changed")
    need(
        w["max_tokens"] == a["wire_payload"]["max_tokens"]
        and w["response_format"] == a["wire_payload"]["response_format"],
        "settings changed",
    )
    x, y = a["wire_payload"]["user"].split("\n"), w["user"].split("\n")
    need(len(x) == len(y), "line count changed")
    diff = [(p, q) for p, q in zip(x, y, strict=False) if p != q]
    need(diff == [(FULL, TRIM)], f"expected exactly one changed line FULL->TRIM, got {len(diff)} changed")
    need(es[0].get("control_user_sha256") and es[0].get("arm_user_sha256"), "hash fields missing")
spec = importlib.util.spec_from_file_location("replay", Path(__file__).with_name("replay.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sent = []


def fake(p):
    sent.append(p)
    return json.dumps({"narration": f"r{len(sent)}"}).encode()


with tempfile.TemporaryDirectory() as t:
    rows = mod.run("1A2", Path(t) / "r.json", 1, 2, send=fake)
need(
    [(r["sample"], r["arm"]) for r in rows] == [(1, "1A"), (1, "1A2"), (2, "1A"), (2, "1A2")],
    f"1A2 order wrong: {[(r['sample'], r['arm']) for r in rows]}",
)
if path.exists() and len(sent) == 4:
    need(
        sent[0] == a["wire_payload"] and sent[1] == es[0]["wire_payload"],
        "1A2 must send the frozen 1A payload as control and the 1A2 payload as arm",
    )
if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("1A2 VALIDATION OK")
