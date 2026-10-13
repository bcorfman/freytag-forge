"""Ringer check helper: the refusal sentence must say 'the driver's seat' but leave owner-named things alone."""

import os
import sys

sys.path.insert(0, os.getcwd())
from storygame.runtime import fixed_refusal  # noqa: E402

text = open("storygame/runtime/fixed_refusal.py").read()
if "def _fixed_article_name" not in text:
    sys.exit("FAIL helper _fixed_article_name missing in fixed_refusal.py")
helper = fixed_refusal._fixed_article_name
cases = {
    "driver's seat": "the driver's seat",
    "workstation": "the workstation",
    "Michelle's phone": "Michelle's phone",
    "back door": "the back door",
}
bad = {k: helper(k) for k, v in cases.items() if helper(k) != v}
if bad:
    sys.exit(f"FAIL article helper wrong: {bad}")
print("article ok")
