# ruff: noqa: E501
"""Offline check for replay.py (no network, no billing): imports it, drives run() with a fake sender, asserts ordering, payloads and guards."""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/lead-up-contradictions"
spec = importlib.util.spec_from_file_location("replay", Path(__file__).with_name("replay.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
errors = []


def need(c, m):
    if not c:
        errors.append(m)


c0 = {e["n"]: e for e in json.loads((OUT / "frozen-C0.json").read_text())["endpoints"]}
for cmp, n in (("1A", "c6"), ("1B", "c4"), ("2A", "c4")):
    arm = json.loads((OUT / f"frozen-{cmp}.json").read_text())["endpoints"][0]
    sent = []

    def fake(payload, sent=sent):
        sent.append(payload)
        if len(sent) == 3:
            raise RuntimeError("boom")
        return json.dumps({"narration": f"reply {len(sent)}"}).encode()

    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "rows.json"
        rows = mod.run(cmp, out, 1, 2, send=fake)
        need(len(rows) == 4 and len(sent) == 4, f"{cmp}: expected 4 rows/requests, got {len(rows)}/{len(sent)}")
        need(
            [(r["sample"], r["arm"]) for r in rows] == [(1, "C0"), (1, cmp), (2, "C0"), (2, cmp)],
            f"{cmp}: order wrong {[(r['sample'], r['arm']) for r in rows]}",
        )
        need(
            sent[0] == c0[n]["wire_payload"] and sent[1] == arm["wire_payload"],
            f"{cmp}: payloads are not the frozen control/arm payloads",
        )
        need(
            rows[2]["error"] == "boom" and rows[2]["narration"] is None,
            f"{cmp}: an error must be kept as a row, not retried or replaced",
        )
        need(len(sent) == 4, f"{cmp}: a retry/replacement was sent")
        need(
            rows[0]["narration"] == "reply 1" and rows[0]["command"] == c0[n]["command"] and rows[0]["n"] == n,
            f"{cmp}: row fields wrong",
        )
        need(json.loads(out.read_text()) == rows, f"{cmp}: rows file not written")
        try:
            mod.run(cmp, out, 1, 1, send=fake)
            errors.append(f"{cmp}: overwriting an existing rows file must be refused")
        except (FileExistsError, SystemExit, AssertionError):
            pass
try:
    mod.run("1A", Path(tempfile.mkdtemp()) / "x.json", 1, 13, send=lambda p: b"{}")
    errors.append("cap of 12 samples (24 requests) not enforced")
except (SystemExit, AssertionError, ValueError):
    pass
r = subprocess.run(
    [sys.executable, str(Path(__file__).with_name("replay.py")), "1A", "/tmp/never-written-rows.json", "1", "12"],
    capture_output=True,
    text=True,
    cwd=ROOT,
)
need(
    r.returncode == 0 and "requests 24" in r.stdout and "dry run" in r.stdout,
    f"no-confirm run must print 'requests 24' and 'dry run' and send nothing; rc={r.returncode} out={r.stdout!r} err={r.stderr[-300:]!r}",
)
need(not Path("/tmp/never-written-rows.json").exists(), "dry run wrote a rows file")
if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("REPLAY VALIDATION OK")
