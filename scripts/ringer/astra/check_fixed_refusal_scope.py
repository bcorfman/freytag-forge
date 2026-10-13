"""Ringer check helper: refuse_fixed_move must accept an in_scope callable and capture must pass the provider scope."""
import sys
from pathlib import Path

fr = Path("storygame/runtime/fixed_refusal.py").read_text()
cap = Path("storygame/runtime/capture.py").read_text()
problems = []
if "in_scope" not in fr:
    problems.append("fixed_refusal.py has no in_scope parameter")
if "_name_in_scene_scope" not in cap:
    problems.append("capture.py does not use the provider's _name_in_scene_scope")
if problems:
    sys.exit("FAIL " + "; ".join(problems))
print("scope wiring ok")
