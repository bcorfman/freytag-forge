"""Ringer check helper: fail if the fixed-thing marker gate still depends on the match call's referred names."""

import sys
from pathlib import Path

src = Path("storygame/runtime/item_facts.py").read_text()
i = src.find("It is fixed in place.")
if i < 0:
    sys.exit("FAIL marker sentence missing")
block = src[src.rfind("if (", 0, i) : i]
if "_referred_names" in block:
    sys.exit("FAIL marker gate still mentions _referred_names")
print("gate ok")
