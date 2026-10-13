"""Ringer check helper: the refuse-fixed-move step must exist, be wired behind a flag, and be off by default."""

import re
import sys
from pathlib import Path

root = Path(".")


def read(path):
    return (root / path).read_text()


problems = []
fr = root / "storygame/runtime/fixed_refusal.py"
if not fr.exists():
    problems.append("storygame/runtime/fixed_refusal.py missing")
elif "def refuse_fixed_move" not in fr.read_text():
    problems.append("refuse_fixed_move not defined")
if "def relocates_thing" not in read("storygame/runtime/jev_questions.py"):
    problems.append("relocates_thing question missing")
cap = read("storygame/runtime/capture.py")
if "fixed_refusal" not in cap:
    problems.append("capture.py does not mention fixed_refusal")
if not re.search(r"fixed_refusal\s*(:\s*bool\s*)?=\s*False", cap):
    problems.append("WorldCapture fixed_refusal does not default to False")
if "fixed_refusal" not in read("bench/core.py"):
    problems.append("bench/core.py does not pass fixed_refusal")
web = read("storygame/web_demo.py")
if "fixed_refusal" in web:
    problems.append("web_demo.py must not be changed (production stays off)")
if problems:
    sys.exit("FAIL " + "; ".join(problems))
print("fixed-refusal wiring ok")
