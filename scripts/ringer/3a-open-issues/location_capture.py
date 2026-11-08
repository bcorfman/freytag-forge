# ruff: noqa: E501
"""Amendment 19, free step: capture the C/P/L wire payloads for the 3A opening (n=0), c4 and c5.

C = shipped state (saved Amendment 13 stage B payloads for c4/c5; the opening is the current engine's payload with the
single automatic person line removed, asserted byte-equal to the saved Amendment 16 control opening).
P = presence line + P1 (placement text), frame sentence kept.
L = P with K1 (frame sentence removed), built from a private copy of the story package.
Zero model calls. Run from the repo root: TMPDIR=/tmp PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/ringer/3a-open-issues/location_capture.py
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/richer-3a-probe/loc"
PKG = ROOT / "data/stories/continuity-initiative"
COPY = Path("/home/bcorfman/dev/ringer-work/3a-loc/story-L")
SAVED = ROOT / "bench/results/richer-3a-probe"
FRAME = " Michelle is beside the captives."
MICHELLE = "- Michelle. Place: beside the captives."

from bench.core import load_variation, seeded_state_for_scene  # noqa: E402
from bench.frozen_prompts import (  # noqa: E402
    _CANNED_REPLY,
    _offline_capture_provider,
    _write_json,
    capture,
)
from storygame.runtime.engine import RuntimeEngine  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def variation_file(name: str, package: str, path: Path) -> Path:
    base = json.loads((ROOT / "bench/variations/richer-3a-people-candidate.json").read_text())
    base["name"] = name
    base["story_package"] = package
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(base, indent=2))
    return path


def opening_payload(variation_path: Path) -> dict:
    variation = load_variation(variation_path)
    _, state = seeded_state_for_scene(variation, "3A")
    provider = _offline_capture_provider(state)
    calls = []

    def send(payload):
        calls.append(copy.deepcopy(payload))
        return _CANNED_REPLY

    provider._send_http = send
    RuntimeEngine(state, provider, capture=None, refusal_mode="off").opening()
    narration = [c for c in calls if str(c.get("system", "")).startswith("You are the narrator of an interactive")]
    assert len(narration) == 1, len(narration)
    return narration[0]


def diff(a: str, b: str):
    lines = list(difflib.ndiff(a.splitlines(), b.splitlines()))
    return [x[2:] for x in lines if x.startswith("- ")], [x[2:] for x in lines if x.startswith("+ ")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # story copy for L (K1)
    if COPY.exists():
        shutil.rmtree(COPY)
    shutil.copytree(PKG, COPY)
    knowledge = COPY / "knowledge.yaml"
    text = knowledge.read_text()
    assert text.count(FRAME) == 1, "frame sentence must occur exactly once"
    knowledge.write_text(text.replace(FRAME, ""))
    vp = variation_file("richer-3a-loc-P", "data/stories/continuity-initiative", OUT / "var-P.json")
    vl = variation_file("richer-3a-loc-L", str(COPY), OUT / "var-L.json")

    # P and L: c4, c5 by the normal offline capture; opening by the opening path
    for arm, var in (("P", vp), ("L", vl)):
        capture(var, [4, 5], OUT / f"cmd-{arm}.json")
    ctl = {n: json.loads((SAVED / f"bio/frozen-candidate-c{n}.json").read_text())["endpoints"][0] for n in (4, 5)}
    assert sha(SAVED / "bio/frozen-candidate-c4.json") == "c3f98a8f9601"
    assert sha(SAVED / "bio/frozen-candidate-c5.json") == "8e8555fa004d"

    arms: dict[str, dict[int, dict]] = {"C": {}, "P": {}, "L": {}}
    opening = {"P": opening_payload(vp), "L": opening_payload(vl)}
    saved = json.loads((SAVED / "frame/control-open.json").read_text())
    saved_user = saved[0]["prompt"]["user"]
    saved_system = saved[0]["prompt"]["system"]
    # C opening: P minus the one automatic person line, must equal the saved control opening byte for byte
    p_lines = opening["P"]["user"].split("\n")
    assert p_lines.count(MICHELLE) == 1, "P opening must carry exactly one Michelle line"
    c_user = "\n".join(line for line in p_lines if line != MICHELLE)
    assert c_user == saved_user, "derived C opening differs from the saved control opening"
    assert opening["P"]["system"] == saved_system
    opening_c = copy.deepcopy(opening["P"])
    opening_c["user"] = c_user
    arms["C"][0] = {"n": 0, "command": "(opening)", "wire_payload": opening_c, "committed_after_prefix": None}
    for arm in ("P", "L"):
        arms[arm][0] = {"n": 0, "command": "(opening)", "wire_payload": opening[arm], "committed_after_prefix": None}
        for ep in json.loads((OUT / f"cmd-{arm}.json").read_text())["endpoints"]:
            arms[arm][ep["n"]] = ep
    for n in (4, 5):
        arms["C"][n] = ctl[n]

    report = []
    for n in (0, 4, 5):
        c, p, lo = (arms[a][n] for a in "CPL")
        for a, e in (("P", p), ("L", lo)):
            if n:
                assert e["command"] == c["command"], f"c{n} {a}: command differs"
                assert e["committed_after_prefix"] == c["committed_after_prefix"], f"c{n} {a}: committed facts differ"
        for a, e in (("P", p), ("L", lo)):
            assert e["wire_payload"]["system"] == c["wire_payload"]["system"], f"n{n} {a}: system differs"
            for key in ("max_tokens", "response_format"):
                assert e["wire_payload"].get(key) == c["wire_payload"].get(key), f"n{n} {a}: {key} differs"
        cp = diff(c["wire_payload"]["user"], p["wire_payload"]["user"])
        pl = diff(p["wire_payload"]["user"], lo["wire_payload"]["user"])
        report.append(
            {
                "n": n,
                "C->P minus": cp[0],
                "C->P plus": cp[1],
                "P->L minus": pl[0],
                "P->L plus": pl[1],
                "chars C/P/L": [len(x["wire_payload"]["user"]) for x in (c, p, lo)],
            }
        )
        # expectations
        if n == 5:
            assert (
                [x for x in cp[0] if "Michelle" not in x] == []
                and len(cp[0]) == 1
                and cp[0][0].startswith("- Michelle. Place: detention level.")
            ), cp
            assert cp[1] == [MICHELLE], cp
        else:
            assert cp[0] == [] and cp[1] == [MICHELLE], f"n{n}: C->P must add exactly the Michelle line, got {cp}"
        assert len(pl[0]) == 1 and len(pl[1]) == 1 and FRAME in pl[0][0] and pl[0][0].replace(FRAME, "") == pl[1][0], pl
    for a in "CPL":
        eps = [arms[a][n] for n in (0, 4, 5)]
        _write_json(
            OUT / f"frozen-{a}.json",
            {"variation": f"richer-3a-loc-{'P' if a != 'L' else 'L'}", "package_hash": "", "endpoints": eps},
        )
        print(a, sha(OUT / f"frozen-{a}.json"))
    _write_json(OUT / "diff-report.json", report)
    for r in report:
        print(json.dumps(r, ensure_ascii=False))


main()
