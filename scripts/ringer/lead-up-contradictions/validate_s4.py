# ruff: noqa: E501
"""Offline check for comparison S4 (current vs candidate lead-up boundary rule at c1, c2, c5, c6, c8 and the 1C discovery turn). No network, no billing."""

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/lead-up-contradictions"
LEAD = "- Right after your story, the game will add this: "
RULE_CUR = "- Write only what leads up to it. Do not have Kristin find anything else."
RULE_NEW = "- Write the lead-up to the text above. Stop before its first action or spoken words. Leave its discoveries for that text."
BIO = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."
ORDER = ["c1", "c2", "c5", "c6", "c8", "h2"]
FINAL_IDX = {"c1": 0, "c2": 1, "c5": 4, "c6": 5, "c8": 7}
errors = []


def need(c, m):
    if not c:
        errors.append(m)


def rename(text: str) -> str:
    text = re.sub(r'coded(\s*"\s*\n\s*")announcement', r"secret\1message", text)
    text = text.replace("Coded announcement", "Secret message").replace("coded announcement", "secret message")
    return text.replace("Coded words", "Code words").replace("coded words", "code words")


final = json.loads((ROOT / "bench/results/shared-narrator/live/final-r1/all-turn-records.json").read_text())["runs"][0][
    "turns"
]
know = yaml.safe_load((ROOT / "data/stories/continuity-initiative/knowledge.yaml").read_text())
variant = {}


def walk(o):
    if isinstance(o, dict):
        if o.get("id") == "k_sl_3a_f_r1":
            variant["text"] = [v for v in o["delivery_variants"] if "held_transfers_seen" in v["requires"]][0][
                "text"
            ].strip()
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(know)


def expected_user(n: str) -> str:
    lines = final[FINAL_IDX[n]]["prompt_user"].split("\n")
    out = []
    for line in lines:
        out.append(line)
        if line.startswith("- Brandon Corfman is"):
            out.append(BIO)
    if n == "c2":
        out = [LEAD + variant["text"] if x.startswith(LEAD) else x for x in out]
    return rename("\n".join(out))


frozen = {}
for arm in ("CUR", "CAND"):
    p = OUT / f"frozen-S4-{arm}.json"
    need(p.exists(), f"missing {p.name}")
    if p.exists():
        frozen[arm] = {e["n"]: e for e in json.loads(p.read_text())["endpoints"]}
for arm, eps in frozen.items():
    need(list(eps) == ORDER, f"{arm}: endpoints are {list(eps)}, expected {ORDER}")
if len(frozen) == 2 and all(list(v) == ORDER for v in frozen.values()):
    for n in ORDER:
        c, k = frozen["CUR"][n], frozen["CAND"][n]
        cu, ku = c["wire_payload"]["user"].split("\n"), k["wire_payload"]["user"].split("\n")
        need(c["wire_payload"]["system"] == k["wire_payload"]["system"], f"{n}: system differs between arms")
        for key in ("max_tokens", "response_format"):
            need(c["wire_payload"].get(key) == k["wire_payload"].get(key), f"{n}: {key} differs between arms")
        need(
            cu.count(RULE_CUR) == 1 and ku.count(RULE_NEW) == 1 and RULE_CUR not in ku,
            f"{n}: rule line present once in CUR and replaced in CAND",
        )
        need(
            len(cu) == len(ku) and [(x, y) for x, y in zip(cu, ku, strict=False) if x != y] == [(RULE_CUR, RULE_NEW)],
            f"{n}: arms must differ in exactly the rule line",
        )
        need(c["command"] == k["command"], f"{n}: command differs")
        if n in FINAL_IDX:
            need(c["command"] == final[FINAL_IDX[n]]["player_input"], f"{n}: command is not the FINAL command")
            need(
                c["wire_payload"]["system"] == final[FINAL_IDX[n]]["prompt_system"],
                f"{n}: system is not the FINAL system prompt",
            )
            need(
                c["wire_payload"]["user"] == expected_user(n),
                f"{n}: CUR user is not FINAL + trimmed bio + rename (+ new c2 delivery)",
            )
        else:
            need(
                c["command"] == "Check the loading docks for signs of activity.",
                f"{n}: wrong 1C command {c['command']!r}",
            )
            need("coded announcement" not in c["wire_payload"]["user"].lower(), f"{n}: old phrase present")
need((ROOT / "scripts/ringer/lead-up-contradictions/replay_s4.py").exists(), "replay_s4.py missing")
if (ROOT / "scripts/ringer/lead-up-contradictions/replay_s4.py").exists() and len(frozen) == 2:
    spec = importlib.util.spec_from_file_location(
        "replay_s4", ROOT / "scripts/ringer/lead-up-contradictions/replay_s4.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sent = []

    def fake(payload):
        sent.append(payload)
        return json.dumps({"narration": f"r{len(sent)}"}).encode()

    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "rows.json"
        rows = mod.run(out, 1, 2, send=fake)
        want = [(s, n, a) for s in (1, 2) for n in ORDER for a in ("CUR", "CAND")]
        need(
            [(r["sample"], r["n"], r["arm"]) for r in rows] == want,
            "row order wrong (sample-major, endpoint, then CUR before CAND)",
        )
        need(len(sent) == 24, f"expected 24 requests, got {len(sent)}")
        need(
            all(sent[i] == frozen[r["arm"]][r["n"]]["wire_payload"] for i, r in enumerate(rows)),
            "sent payloads are not the frozen payloads",
        )
        try:
            mod.run(out, 1, 1, send=fake)
            errors.append("existing rows file must be refused")
        except (FileExistsError, SystemExit, AssertionError):
            pass
    try:
        mod.run(Path(tempfile.mkdtemp()) / "x.json", 1, 13, send=fake)
        errors.append("cap of 12 samples (144 requests) not enforced")
    except (SystemExit, AssertionError, ValueError):
        pass
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ringer/lead-up-contradictions/replay_s4.py"),
            "/tmp/never-written-s4.json",
            "1",
            "12",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    need(
        r.returncode == 0 and "requests 144" in r.stdout and "dry run" in r.stdout,
        f"dry run must print 'requests 144' and 'dry run'; got rc={r.returncode} {r.stdout!r} {r.stderr[-200:]!r}",
    )
    need(not Path("/tmp/never-written-s4.json").exists(), "dry run wrote a file")
if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("S4 VALIDATION OK")
