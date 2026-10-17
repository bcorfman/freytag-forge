"""Ringer check helper: engine-owned fixed refusal must exist, be opt-in, and be tested for the required behaviours."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
need_tests = [
    "test_engine_refusal_makes_no_provider_call",
    "test_engine_refusal_consumes_no_turn",
    "test_engine_refusal_unanswered_classifier_narrates_normally",
    "test_engine_refusal_off_by_default",
    "test_relocates_thing_criteria_cover_lift_then_lower_and_source",
]
text = Path("tests/test_fixed_refusal.py").read_text()
missing = [n for n in need_tests if not re.search(rf"def {n}\b", text)]
if missing:
    sys.exit(f"FAIL required tests missing in tests/test_fixed_refusal.py: {missing}")
cap = Path("storygame/runtime/capture.py").read_text()
if "engine_refusal" not in cap:
    sys.exit("FAIL capture.py has no engine_refusal option")
eng = Path("storygame/runtime/engine.py").read_text()
if "engine_refusal" not in eng:
    sys.exit("FAIL engine.py never reads engine_refusal")
jq = Path("storygame/runtime/jev_questions.py").read_text()
for needle in ("lower", "from"):
    if needle not in jq.split("def relocates_thing")[1].split("def reaches_reveals")[0].lower():
        sys.exit(f"FAIL relocates_thing criteria do not mention '{needle}'")
print("engine refusal structure ok")
