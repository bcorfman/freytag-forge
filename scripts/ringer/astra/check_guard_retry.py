"""Ringer check helper: the engine retries once when narration safety rejects, passing the rejection to the provider."""

import re
import sys
from pathlib import Path

engine = Path("storygame/runtime/engine.py").read_text()
cloud = Path("storygame/runtime/cloudflare.py").read_text()
tests = Path("tests/test_narration_retry.py").read_text()
if not re.search(r"^TURN_NARRATION_ATTEMPTS\s*=\s*2\b", engine, re.M):
    sys.exit("FAIL engine.py needs TURN_NARRATION_ATTEMPTS = 2")
if "note_rejection" not in engine:
    sys.exit("FAIL engine.py never calls provider.note_rejection")
if not re.search(r"def note_rejection\(", cloud):
    sys.exit("FAIL cloudflare.py has no note_rejection method")
need = [
    "test_narration_leak_is_retried_once_and_the_turn_commits",
    "test_retry_passes_the_rejection_to_the_provider_once",
    "test_two_rejections_still_fail_the_turn_and_restore_state",
    "test_clean_reply_is_not_retried",
    "test_effect_validation_errors_are_not_retried",
    "test_cloudflare_note_reaches_only_the_next_prompt",
]
if missing := [n for n in need if not re.search(rf"def {n}\b", tests)]:
    sys.exit(f"FAIL required tests missing: {missing}")
print("guard retry structure ok")
