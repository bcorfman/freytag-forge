# ruff: noqa: E501
"""Independent offline check of the round-2 1A passcode Stage A freeze and its replay. No network, no billing.

Prints "1A PASSCODE FREEZE VALIDATION OK" only if ACCESS differs from CTRL by exactly the planned statement.
Plan: .plans/1a-password-and-officer-plan.md (Round 2).
"""

import difflib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/1a-passcode-round2"
PKG = ROOT / "data/stories/continuity-initiative"
errors: list[str] = []


def need(condition, message):
    if not condition:
        errors.append(message)


ENDPOINTS = {
    "PW1": "Type in the password.",
    "PW2": "Type in the passcode.",
    "PW3": "Type the passcode into Michelle's phone.",
}
PREFIX = ["Pick up Michelle's phone.", "Turn on the phone."]
STATEMENT = "Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend."
RECORD = """- id: k_1a_michelle_phone_access
  statement: Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend.
  entity_ids: [michelle_phone]
  aliases: [Michelle's phone passcode]
  leak_terms: []
  voiceable: false
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1A]
  establishes: [{op: assert, fact_id: scene_1a_entry_known, value: true}]
  source: {kind: scene_entry}
"""


def load(arm, endpoint):
    path = OUT / f"frozen-{arm}-{endpoint}.json"
    need(path.exists(), f"missing {path.name}")
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    need(data.get("arm") == arm, f"{path.name}: wrong arm field")
    entry = data.get("endpoint", {})
    need(entry.get("n") == endpoint, f"{path.name}: wrong endpoint id")
    need(entry.get("command") == ENDPOINTS[endpoint], f"{path.name}: wrong command {entry.get('command')!r}")
    return entry


def line_diff(a, b):
    added, removed = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a.split("\n"), b=b.split("\n"), autojunk=False).get_opcodes():
        if tag != "equal":
            removed += a.split("\n")[i1:i2]
            added += b.split("\n")[j1:j2]
    return added, removed


# arm package: shipped knowledge.yaml plus exactly the planned record after k_scene_1a_entry; all else identical
base_path = PKG / "knowledge.yaml"
arm_path = OUT / "pkg/access/knowledge.yaml"
need(arm_path.exists(), "missing pkg/access/knowledge.yaml")
if arm_path.exists():
    lines = base_path.read_text(encoding="utf-8").split("\n")
    starts = [i for i, ln in enumerate(lines) if ln == "- id: k_scene_1a_entry"]
    need(len(starts) == 1, "shipped knowledge.yaml no longer has exactly one k_scene_1a_entry")
    if len(starts) == 1:
        end = next((i for i in range(starts[0] + 1, len(lines)) if lines[i].startswith("- id: ")), None)
        need(end is not None, "k_scene_1a_entry is the last record; cannot place the planned record")
        if end is not None:
            expected = "\n".join(lines[:end] + RECORD.rstrip("\n").split("\n") + lines[end:])
            actual = arm_path.read_text(encoding="utf-8")
            need(
                actual == expected,
                f"pkg/access/knowledge.yaml is not the shipped file plus exactly the planned record; diff {list(difflib.unified_diff(expected.split(chr(10)), actual.split(chr(10)), lineterm='', n=0))[:12]}",
            )
    for path in sorted(PKG.rglob("*")):
        if path.is_file() and path.relative_to(PKG).as_posix() != "knowledge.yaml":
            twin = OUT / "pkg/access" / path.relative_to(PKG)
            need(
                twin.exists() and twin.read_bytes() == path.read_bytes(),
                f"pkg/access/{path.relative_to(PKG)} differs from the shipped package",
            )
    extra = {p.relative_to(OUT / "pkg/access").as_posix() for p in (OUT / "pkg/access").rglob("*") if p.is_file()} - {
        p.relative_to(PKG).as_posix() for p in PKG.rglob("*") if p.is_file()
    }
    need(not extra, f"pkg/access has files not in the shipped package: {sorted(extra)}")

# payloads: ACCESS = CTRL plus only the statement line(s); envelope identical
for endpoint in ENDPOINTS:
    ctrl, access = load("CTRL", endpoint), load("ACCESS", endpoint)
    if ctrl is None or access is None:
        continue
    label = endpoint
    cp, ap = ctrl["wire_payload"], access["wire_payload"]
    for key in sorted(set(cp) | set(ap)):
        if key != "user":
            need(cp.get(key) == ap.get(key), f"{label}: wire field {key!r} differs from control")
    added, removed = line_diff(cp["user"], ap["user"])
    need(not removed, f"{label}: ACCESS removed or changed control lines: {removed[:4]}")
    need(
        bool(added) and all(STATEMENT in ln or STATEMENT.split(". ")[0] in ln for ln in added),
        f"{label}: ACCESS added lines other than the statement: {added[:4]}",
    )
    need(
        sum(STATEMENT in ln for ln in added) == 1, f"{label}: statement does not appear exactly once in the added lines"
    )
    cu = "\n".join(ln for ln in cp["user"].splitlines() if ln != f"- {ENDPOINTS[endpoint]}").lower()
    need("passcode" not in cu, f"{label}: control already mentions a passcode")
    need(ENDPOINTS[endpoint] in cp["user"], f"{label}: control payload does not contain the endpoint command")
    need(
        not any(c in cp["user"] for c in ("Unlock Michelle's phone", "Unlock the phone")),
        f"{label}: control carries an unlock command in its prefix",
    )
    # smoke: sha matches payload
    import hashlib

    need(ctrl["user_sha256"] == hashlib.sha256(cp["user"].encode()).hexdigest(), f"{label}: CTRL user_sha256 is stale")
    need(
        access["user_sha256"] == hashlib.sha256(ap["user"].encode()).hexdigest(),
        f"{label}: ACCESS user_sha256 is stale",
    )

# the three endpoints' payloads differ from each other only where the command differs (same fixed state)
cu = [load("CTRL", e) for e in ENDPOINTS]
if all(cu):
    a, b = cu[0]["wire_payload"]["user"], cu[1]["wire_payload"]["user"]
    added, removed = line_diff(a, b)
    need(
        len(added) <= 6 and len(removed) <= 6,
        f"PW1 vs PW2 control payloads differ in too many lines: {added[:3]} {removed[:3]}",
    )

notes = OUT / "state-notes.txt"
need(notes.exists() and notes.read_text(encoding="utf-8").strip() != "", "missing or empty state-notes.txt")
prov_path = OUT / "provenance.json"
need(prov_path.exists(), "missing provenance.json")
if prov_path.exists():
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    for key in ("head", "dirty_files", "package_sha256", "frozen_sha256", "prefix_inputs", "endpoints"):
        need(key in prov, f"provenance.json missing {key!r}")
    need(prov.get("prefix_inputs") == PREFIX, f"provenance prefix_inputs wrong: {prov.get('prefix_inputs')}")

# replay: dry-run guard, caps, order, no network
replay = ROOT / "scripts/ringer/1a-password-officer/replay_passcode.py"
need(replay.exists(), "missing replay_passcode.py")
if replay.exists():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "rows.json"
        dry = subprocess.run(
            [sys.executable, str(replay), str(target), "0", "12"], capture_output=True, text=True, cwd=ROOT
        )
        need(
            dry.returncode == 0
            and "requests 78" in dry.stdout
            and "dry run: nothing sent" in dry.stdout
            and not target.exists(),
            f"replay dry run wrong (rc {dry.returncode}): {dry.stdout[-200:]} {dry.stderr[-200:]}",
        )
        smoke = subprocess.run(
            [sys.executable, str(replay), str(target), "0", "0"], capture_output=True, text=True, cwd=ROOT
        )
        need("requests 6" in smoke.stdout and smoke.returncode == 0, f"replay smoke count wrong: {smoke.stdout[-200:]}")
        over = subprocess.run(
            [sys.executable, str(replay), str(target), "1", "13"], capture_output=True, text=True, cwd=ROOT
        )
        need(over.returncode != 0, "replay accepted sample 13")
        spec = importlib.util.spec_from_file_location("replay_passcode", replay)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sent = []

        def stub(payload):
            sent.append(payload)
            return json.dumps({"narration": json.dumps({"segments": [{"kind": "narration", "text": "ok"}]})}).encode()

        rows_path = Path(tmp) / "stub-rows.json"
        rows = module.run(rows_path, 1, 2, send=stub)
        order = [(r["sample"], r["n"], r["arm"]) for r in rows]
        expected_order = [(s, e, a) for s in (1, 2) for e in ENDPOINTS for a in ("CTRL", "ACCESS")]
        need(order == expected_order, f"replay row order wrong: {order}")
        need(len(sent) == 12 and all(r["error"] is None for r in rows), "replay stub run wrong")
        # sent payloads are the frozen ones verbatim
        frozen_users = {load(a, e)["wire_payload"]["user"] for a in ("CTRL", "ACCESS") for e in ENDPOINTS if load(a, e)}
        need(all(p["user"] in frozen_users for p in sent), "replay sent a payload that is not a frozen payload")
        try:
            module.run(rows_path, 1, 1, send=stub)
            errors.append("replay overwrote an existing rows file")
        except FileExistsError:
            pass

        def boom(payload):
            raise RuntimeError("transport down")

        rows = module.run(Path(tmp) / "err-rows.json", 1, 1, send=boom)
        need(
            len(rows) == 6 and all(r["error"] and r["narration"] is None for r in rows),
            "replay did not keep transport errors as rows",
        )
        only = module.run(Path(tmp) / "only-rows.json", 1, 1, send=stub, only=["PW3"])
        need([(r["n"], r["arm"]) for r in only] == [("PW3", "CTRL"), ("PW3", "ACCESS")], "replay --only wrong")

if errors:
    print("1A PASSCODE FREEZE VALIDATION FAILED")
    for message in errors:
        print(" -", message)
    sys.exit(1)
print("1A PASSCODE FREEZE VALIDATION OK")
