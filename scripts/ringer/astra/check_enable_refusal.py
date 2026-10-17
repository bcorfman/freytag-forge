"""Ringer check helper: the web path must enable the refusal by default with a kill switch, and the
multi-turn API tests must exist.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
web = Path("storygame/web_demo.py").read_text()
if "FREYTAG_FIXED_REFUSAL" not in web or "engine_refusal=" not in web or "fixed_refusal=" not in web:
    sys.exit("FAIL web_demo.py does not pass fixed_refusal/engine_refusal behind FREYTAG_FIXED_REFUSAL")
eng = Path("storygame/runtime/engine.py").read_text()
cls = eng.split("class EngineRefusalTurn")[1].split("\nclass ")[0]
for attr in ("selected_knowledge_ids", "events"):
    if attr not in cls:
        sys.exit(f"FAIL EngineRefusalTurn lacks {attr}")
t = Path("tests/test_web_demo_fixed_refusal.py").read_text()
need = [
    "test_refusal_is_on_by_default_with_world_capture",
    "test_refusal_kill_switch_turns_it_off",
    "test_refused_turn_works_with_knowledge_audit_and_prompt_exposure",
    "test_multi_turn_refusal_sequence_through_the_api",
    "test_refused_mixed_turn_then_normal_turn_through_the_api",
]
missing = [n for n in need if not re.search(rf"def {n}\b", t)]
if missing:
    sys.exit(f"FAIL required tests missing: {missing}")
print("enable refusal structure ok")
