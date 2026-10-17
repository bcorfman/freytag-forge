"""Ringer check helper: mixed-command clarification must be wired and tested."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
need = [
    "test_mixed_refusal_appends_clarification",
    "test_simple_refusal_has_no_clarification",
    "test_unanswered_other_action_appends_clarification",
    "test_names_other_action_question_joins_refused_names",
    "test_refused_turn_survives_save_and_load",
]
text = Path("tests/test_fixed_refusal.py").read_text()
missing = [n for n in need if not re.search(rf"def {n}\b", text)]
if missing:
    sys.exit(f"FAIL required tests missing: {missing}")
if "def names_other_action" not in Path("storygame/runtime/jev_questions.py").read_text():
    sys.exit("FAIL names_other_action missing in jev_questions.py")
if "Nothing else in that command was done." not in Path("storygame/runtime/fixed_refusal.py").read_text():
    sys.exit("FAIL clarification sentence missing in fixed_refusal.py")
print("mixed refusal structure ok")
