# ruff: noqa: E501
"""Independent offline check of live_greeting.py (the billed fused-repair greeting check). No network, no billing.

Prints "LIVE HARNESS VALIDATION OK" only if the harness keeps arms interleaved, counts every real request,
enforces its hard cap, keeps errors as rows, refuses without --confirm, and toggles the repair per arm.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HARNESS = ROOT / "scripts/ringer/1a-password-officer/live_greeting.py"
errors: list[str] = []


def need(condition, message):
    if not condition:
        errors.append(message)


FUSED = json.dumps(
    {
        "segments": [
            {
                "kind": "narration",
                "text": '"Officer Reyes, what are you doing here?"',
                "},{": "kind",
                "narration": '"I am investigating a report of a break-in, ma\'am."',
            }
        ],
        "selected_knowledge_ids": [],
    }
)
CLEAN = json.dumps(
    {
        "segments": [
            {"kind": "narration", "text": "She greets him."},
            {"kind": "narration", "text": '"Hello," he says.'},
        ],
        "selected_knowledge_ids": [],
    }
)


def body(narration):
    return json.dumps({"narration": narration}).encode()


need(HARNESS.exists(), "missing live_greeting.py")
if HARNESS.exists():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "rows.json"
        # CLI dry run: no --confirm sends nothing and writes nothing
        dry = subprocess.run([sys.executable, str(HARNESS), str(out), "12"], capture_output=True, text=True, cwd=ROOT)
        need(
            dry.returncode == 0 and "dry run: nothing sent" in dry.stdout and not out.exists(),
            f"dry run wrong (rc {dry.returncode}): {dry.stdout[-300:]} {dry.stderr[-300:]}",
        )
        need(
            "turns 24" in dry.stdout and "cap 36" in dry.stdout,
            f"dry run must print 'turns 24' and 'cap 36': {dry.stdout[-300:]}",
        )
        over = subprocess.run(
            [sys.executable, str(HARNESS), str(out), "13", "--confirm"], capture_output=True, text=True, cwd=ROOT
        )
        need(over.returncode != 0 and not out.exists(), "harness accepted more than 12 samples")

        spec = importlib.util.spec_from_file_location("live_greeting", HARNESS)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # stub: first narration request of every turn is fused, any later one is clean
        seen = []

        def send(payload):
            seen.append(payload)
            is_recovery = "Your last answer was not valid" in payload["system"]
            return body(CLEAN if is_recovery else FUSED)

        rows = module.run(out, 2, send=send, cap=36)
        need(
            [(r["sample"], r["arm"]) for r in rows] == [(1, "ON"), (1, "OFF"), (2, "ON"), (2, "OFF")],
            f"row order must be sample-major, ON then OFF: {[(r['sample'], r['arm']) for r in rows]}",
        )
        by = {(r["sample"], r["arm"]): r for r in rows}
        for sample in (1, 2):
            on, off = by[(sample, "ON")], by[(sample, "OFF")]
            need(
                on["requests"] == 1 and on["recovery_used"] is False,
                f"ON with a repairable fused reply must use one request, got {on['requests']}",
            )
            need(
                off["requests"] == 2 and off["recovery_used"] is True,
                f"OFF must spend a recovery request, got {off['requests']}",
            )
            need(
                on["first_reply_parses"] is False and off["first_reply_parses"] is False,
                "first_reply_parses must be false for the fused reply",
            )
            need(
                any("I am investigating" in text for text in (on["segments"] or [])),
                "ON final segments must contain the officer's repaired line",
            )
            need(
                not any("I am investigating" in text for text in (off["segments"] or [])),
                "OFF final segments come from the recovery reply",
            )
            need(on["error"] is None and off["error"] is None, "no errors expected in the stub run")
            need(
                any("repair" in line.casefold() for line in on["logs"])
                and not any("repair" in line.casefold() for line in off["logs"]),
                "the repair warning must appear only in the ON arm",
            )
        need(len(seen) == 2 * (1 + 2), f"stub should have seen 6 narration requests, saw {len(seen)}")
        need(
            all(r["requests"] == len(r["request_systems"]) for r in rows),
            "rows must record one request_systems entry per real request",
        )
        try:
            module.run(out, 1, send=send, cap=36)
            errors.append("harness overwrote an existing rows file")
        except FileExistsError:
            pass

        # hard cap: refuse to start a turn that could exceed the cap, keep the rows so far, say so
        out2 = Path(tmp) / "rows-cap.json"
        seen.clear()
        rows2 = module.run(out2, 12, send=send, cap=5)
        need(len(seen) <= 5, f"cap 5 exceeded: {len(seen)} real requests")
        need(0 < len(rows2) < 24, f"cap should stop the run early with partial rows, got {len(rows2)}")
        need(
            json.loads(out2.read_text()) == rows2 or json.loads(out2.read_text())["rows"] == rows2,
            "rows file must hold the partial rows",
        )

        # transport failure becomes a row
        out3 = Path(tmp) / "rows-err.json"

        def boom(payload):
            raise OSError("transport down")

        rows3 = module.run(out3, 1, send=boom, cap=36)
        need(len(rows3) == 2 and all(r["error"] for r in rows3), "transport errors must be kept as rows")

if errors:
    print("LIVE HARNESS VALIDATION FAILED")
    for message in errors:
        print(" -", message)
    sys.exit(1)
print("LIVE HARNESS VALIDATION OK")
