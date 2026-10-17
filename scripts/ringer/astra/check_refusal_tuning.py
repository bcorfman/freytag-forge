"""Ringer check helper: both classifier questions must carry the tuned wording, and the fresh commands
must not leak into source.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
src = Path("storygame/runtime/jev_questions.py").read_text()
reloc = src.split("def relocates_thing")[1].split("def names_other_action")[0].lower()
other = src.split("def names_other_action")[1].split("\ndef ")[0].lower()
for verb in ("tilt", "rotate", "roll", "nudge", "reposition"):
    if verb not in reloc:
        sys.exit(f"FAIL relocates_thing wording lacks '{verb}'")
if "swung" not in reloc and "swing" not in reloc:
    sys.exit("FAIL relocates_thing lacks the hinged-part use note")
if "slid" not in reloc and "slide" not in reloc:
    sys.exit("FAIL relocates_thing lacks the sliding-part use note")
if "and" not in other or "one verb" not in other:
    sys.exit("FAIL names_other_action lacks the shared-verb note")
frozen = [
    "Drag the workstation and my laptop",
    "Lift the passenger seat and the back door",
    "Push the driver's seat and my laptop",
    "Rotate the workstation, then",
    "Turn the workstation around",
    "Reposition the passenger seat.",
    "Roll the workstation toward",
    "Nudge the back door",
    "Swing the back door open",
    "Press on the drawer to check",
    "Tilt my laptop screen back",
    "Slide the drawer open, then close",
]
tests = Path("tests/test_fixed_refusal.py").read_text()
leaks = [c for c in frozen if c in src or c in tests]
if leaks:
    sys.exit(f"FAIL fresh measurement commands leaked into source or tests: {leaks}")
print("tuning wording ok")
