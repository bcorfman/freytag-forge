"""Ringer check helper: bench must plumb engine_refusal and have the required tests."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
core = Path("bench/core.py").read_text()
if core.count("engine_refusal") < 4:
    sys.exit("FAIL bench/core.py mentions engine_refusal fewer than 4 times (two WorldCapture builds, hash, record)")
text = Path("tests/test_bench_runtime_mode.py").read_text()
need = [
    "test_runtime_mode_passes_engine_refusal_to_capture",
    "test_bench_engine_refused_turn_has_no_prompt_and_no_stale_item_facts",
    "test_engine_refusal_variation_hash",
]
missing = [n for n in need if not re.search(rf"def {n}\b", text)]
if missing:
    sys.exit(f"FAIL required tests missing: {missing}")
print("bench engine refusal structure ok")
