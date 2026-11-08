# ruff: noqa: E501
"""Offline check for comparison 3A (current reunion delivery vs candidate rewrite) at R1 and R2. No network, no billing."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/lead-up-contradictions"
LEAD = "- Right after your story, the game will add this: "
BIO = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."
HEAD = 'Michelle pulls Kristin close and holds her there. "You\'re here," she says, her voice breaking. "You\'re really here." Kristin holds on just as hard. For one unhurried moment nobody asks anything of either of them.'
CAND = {
    "R1": HEAD
    + " When they let go, Michelle wipes her eyes and turns back to the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. She returns to sending her coded messages, and she points toward the medical level where the experiment records await.",
    "R2": HEAD
    + " When they let go, Michelle wipes her eyes and explains that freeing this block means little without exposing the other sites. She points toward the medical level, where the experiment records wait.",
}
IDS = {"R1": "k_sl_3a_a_r1", "R2": "k_sl_3a_a_r2"}
COMMANDS = {"R1": "Free the captives.", "R2": "Ask Michelle about the other sites."}
errors = []


def need(c, m):
    if not c:
        errors.append(m)


know = yaml.safe_load((ROOT / "data/stories/continuity-initiative/knowledge.yaml").read_text())
current = {}


def walk(o):
    if isinstance(o, dict):
        if str(o.get("id", "")).startswith("k_sl_3a_a_r") and "delivery_text" in o:
            current[o["id"]] = o["delivery_text"].strip()
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(know)
frozen = {}
for arm in ("CUR", "CAND"):
    p = OUT / f"frozen-3A-{arm}.json"
    need(p.exists(), f"missing {p.name}")
    if p.exists():
        frozen[arm] = {e["n"]: e for e in json.loads(p.read_text())["endpoints"]}
for arm in frozen:
    need(sorted(frozen[arm]) == ["R1", "R2"], f"{arm}: endpoints are {sorted(frozen[arm])}")
if len(frozen) == 2 and all(sorted(v) == ["R1", "R2"] for v in frozen.values()):
    for n in ("R1", "R2"):
        c, k = frozen["CUR"][n], frozen["CAND"][n]
        need(c["command"] == COMMANDS[n] == k["command"], f"{n}: command wrong")
        cu, ku = c["wire_payload"]["user"].split("\n"), k["wire_payload"]["user"].split("\n")
        need(c["wire_payload"]["system"] == k["wire_payload"]["system"], f"{n}: system differs between arms")
        for key in ("max_tokens", "response_format"):
            need(c["wire_payload"].get(key) == k["wire_payload"].get(key), f"{n}: {key} differs between arms")
        need(BIO in cu, f"{n}: CUR must be the CURRENT tree (trimmed official bio line present in CHARACTERS)")
        d_cur = [x for x in cu if x.startswith(LEAD)]
        d_new = [x for x in ku if x.startswith(LEAD)]
        need(len(d_cur) == 1 and len(d_new) == 1, f"{n}: delivery line count")
        if len(d_cur) == 1 and len(d_new) == 1:
            need(d_cur[0] == LEAD + current[IDS[n]], f"{n}: CUR delivery differs from knowledge.yaml {IDS[n]}")
            need(d_new[0] == LEAD + CAND[n], f"{n}: CAND delivery is not the approved candidate text")
        need(
            len(cu) == len(ku) and sum(x != y for x, y in zip(cu, ku, strict=False)) == 1,
            f"{n}: arms must differ in exactly one line",
        )
        for text in (CAND[n],):
            need(text.count("pulls Kristin close") == 1, f"{n}: candidate holds exactly one embrace")
            need("medical level" in text, f"{n}: candidate lost the medical-level pointer")
need(Path(ROOT / "scripts/ringer/lead-up-contradictions/replay_3a.py").exists(), "replay_3a.py missing")
if Path(ROOT / "scripts/ringer/lead-up-contradictions/replay_3a.py").exists() and len(frozen) == 2:
    spec = importlib.util.spec_from_file_location(
        "replay_3a", ROOT / "scripts/ringer/lead-up-contradictions/replay_3a.py"
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
        want = [(s, n, a) for s in (1, 2) for n in ("R1", "R2") for a in ("CUR", "CAND")]
        need(
            [(r["sample"], r["n"], r["arm"]) for r in rows] == want,
            f"order wrong: {[(r['sample'], r['n'], r['arm']) for r in rows]}",
        )
        need(len(sent) == 8, f"expected 8 requests, got {len(sent)}")
        need(
            all(sent[i] == frozen[r["arm"]][r["n"]]["wire_payload"] for i, r in enumerate(rows)),
            "sent payloads are not the frozen payloads",
        )
        need(json.loads(out.read_text()) == rows, "rows file not written")
        try:
            mod.run(out, 1, 1, send=fake)
            errors.append("existing rows file must be refused")
        except (FileExistsError, SystemExit, AssertionError):
            pass
    try:
        mod.run(Path(tempfile.mkdtemp()) / "x.json", 1, 13, send=fake)
        errors.append("cap of 12 samples (48 requests) not enforced")
    except (SystemExit, AssertionError, ValueError):
        pass
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ringer/lead-up-contradictions/replay_3a.py"),
            "/tmp/never-written-3a.json",
            "1",
            "12",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    need(
        r.returncode == 0 and "requests 48" in r.stdout and "dry run" in r.stdout,
        f"dry run must print 'requests 48' and 'dry run'; got rc={r.returncode} {r.stdout!r} {r.stderr[-200:]!r}",
    )
    need(not Path("/tmp/never-written-3a.json").exists(), "dry run wrote a file")
if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("3A VALIDATION OK")
