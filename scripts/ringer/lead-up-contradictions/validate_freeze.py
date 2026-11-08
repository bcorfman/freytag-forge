# ruff: noqa: E501
"""Independent validator for the lead-up-contradictions Stage 0 freeze. Prints WHY it fails. Exit 0 only if every invariant holds.
Run (repo root): .venv/bin/python scripts/ringer/lead-up-contradictions/validate_freeze.py"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "bench/results/lead-up-contradictions"
FINAL = ROOT / "bench/results/shared-narrator/live/final-r1/all-turn-records.json"
CONTROL = ROOT / "bench/results/shared-narrator/live/control-r1/all-turn-records.json"
LEAD = "- Right after your story, the game will add this: "
BIO = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
NEW_FIRST = "Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments."
OLD_FIRST = "Michelle shows Kristin the medical level."
ORG = [
    "- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.",
    "- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.",
    "- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.",
]
errors: list[str] = []


def need(cond, msg):
    if not cond:
        errors.append(msg)


def load(name):
    path = OUT / name
    need(path.exists(), f"missing output {path}")
    return json.loads(path.read_text()) if path.exists() else {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


turns = json.loads(FINAL.read_text())["runs"][0]["turns"]
need(len(turns) == 9, f"FINAL records have {len(turns)} turns, expected 9")
need(sha(CONTROL).startswith("cd396b259e68"), "CONTROL records hash differs from the plan's cd396b259e68...")

prov = load("provenance.json")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
need(prov.get("head") == head, f"provenance head {prov.get('head')!r} != {head!r}")
for key in (
    "dirty_diff_sha256",
    "status_porcelain_sha256",
    "package_files_sha256",
    "final_records_sha256",
    "control_records_sha256",
    "gu2_envelope_sha256",
):
    v = prov.get(key)
    need(
        isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v),
        f"provenance {key} not a sha256: {v!r}",
    )
need(prov.get("final_records_sha256") == sha(FINAL), "provenance final_records_sha256 does not match the file")
need(prov.get("control_records_sha256") == sha(CONTROL), "provenance control_records_sha256 does not match the file")
need(
    "package_hash" not in prov or prov.get("package_hash_note"),
    "GU2's stale package_hash must not be reused as proof of identity",
)

c0 = load("frozen-C0.json")
eps = c0.get("endpoints", [])
need([e.get("n") for e in eps] == [f"c{i}" for i in range(1, 10)], f"C0 endpoints are {[e.get('n') for e in eps]}")
gu2 = json.loads((ROOT / "bench/results/shared-narrator/g/frozen-GU2.json").read_text())["endpoints"][0]["wire_payload"]
for e, t in zip(eps, turns, strict=False):
    w = e.get("wire_payload", {})
    need(w.get("system") == t["prompt_system"], f"{e.get('n')}: system differs from recorded prompt_system")
    need(w.get("user") == t["prompt_user"], f"{e.get('n')}: user differs from recorded prompt_user")
    need(
        w.get("max_tokens") == gu2["max_tokens"] and w.get("response_format") == gu2["response_format"],
        f"{e.get('n')}: settings differ from the GU2 envelope",
    )
    need(e.get("command") == t["player_input"], f"{e.get('n')}: command differs")
    need(e.get("selected_id") == t.get("authored_handoff_candidate_id"), f"{e.get('n')}: selected_id differs")
    if e.get("n") != "c9":
        seg = t["authored_segments"][0]["text"]
        need(
            t["narration"].endswith(seg),
            f"{e.get('n')}: recorded narration does not end with its delivery (split once, never append twice)",
        )
        need(
            e.get("generated_portion") == t["narration"][: -len(seg)].rstrip(), f"{e.get('n')}: generated_portion wrong"
        )
        need(e.get("delivery_text") == seg, f"{e.get('n')}: delivery_text wrong")
        need(LEAD + seg in t["prompt_user"], f"{e.get('n')}: delivery line not found verbatim in prompt")
    else:
        need(
            [s["kind"] for s in e.get("authored_segments", [])] == ["bridge", "entry", "entry"],
            "c9: authored_segments kinds must be bridge, entry, entry",
        )
need(
    len({e["wire_payload"]["system"] for e in eps if "wire_payload" in e}) == 1,
    "FINAL system prompt not identical across turns",
)


def lines(s):
    return s.split("\n")


def arm(name, n, idx):
    data = load(f"frozen-{name}.json")
    es = data.get("endpoints", [])
    need([e.get("n") for e in es] == [n], f"{name}: endpoints {[e.get('n') for e in es]}, expected [{n!r}]")
    if not es:
        return None, None
    e = es[0]
    base = turns[idx]["prompt_user"]
    need(e["wire_payload"]["system"] == turns[idx]["prompt_system"], f"{name}: system prompt changed")
    for k in ("max_tokens", "response_format"):
        need(e["wire_payload"].get(k) == gu2[k], f"{name}: {k} changed")
    need(
        e.get("control_user_sha256") == hashlib.sha256(base.encode()).hexdigest(), f"{name}: control_user_sha256 wrong"
    )
    need(
        e.get("arm_user_sha256") == hashlib.sha256(e["wire_payload"]["user"].encode()).hexdigest(),
        f"{name}: arm_user_sha256 wrong",
    )
    return lines(base), lines(e["wire_payload"]["user"])


a, b = arm("1A", "c6", 5)
if a is not None:
    need(len(b) == len(a) + 1, f"1A: expected exactly +1 line, got {len(b) - len(a):+d}")
    need(BIO in b, "1A: bio line missing")
    need([x for x in b if x != BIO] == a, "1A: anything besides the single inserted bio line changed")
    i = b.index(BIO) if BIO in b else -1
    need(
        i > 0 and b[i - 1].startswith("- Brandon Corfman is") and b[i + 1] == "" and b[i + 2] == "SCENE:",
        "1A: bio must be the last CHARACTERS line",
    )
a, b = arm("1B", "c4", 3)
if a is not None:
    old = LEAD + turns[3]["authored_segments"][0]["text"]
    need(old.startswith(LEAD + OLD_FIRST), "1B: control delivery does not start with the expected first sentence")
    new = LEAD + NEW_FIRST + old[len(LEAD + OLD_FIRST) :]
    need(len(a) == len(b), "1B: line count changed")
    diff = [(x, y) for x, y in zip(a, b, strict=False) if x != y]
    need(
        len(diff) == 1 and diff[0] == (old, new),
        f"1B: expected exactly one changed line old->new; got {len(diff)} changed",
    )
a, b = arm("2A", "c4", 3)
if a is not None:
    need(all(x in a for x in ORG), "2A: control lacks one of the three organizing lines (check exact text)")
    need(len(b) == len(a) - 3, f"2A: expected exactly -3 lines, got {len(b) - len(a):+d}")
    need([x for x in a if x not in ORG] == b, "2A: anything besides the three organizing lines changed")
need(
    (OUT / "diff-report.txt").exists() and "system/user/total" in (OUT / "diff-report.txt").read_text(),
    "diff-report.txt missing or lacks the system/user/total character counts",
)

if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("VALIDATION OK: C0 c1..c9, arms 1A/1B/2A, provenance")
