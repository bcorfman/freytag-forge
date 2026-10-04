"""Replay the 1A memory-card Jev question against recorded commands (billed: Jev). usage: jev_probe.py <samples>"""

import sys
from collections import Counter

from storygame.runtime.jev import JevClient
from storygame.runtime.jev_questions import reaches_reveals

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
ask = JevClient.from_environment().ask
NAMES = ("Dr. Michelle McGehee", "Michelle", "Michelle's memory card", "memory card", "drawer")
EARN = "searches the drawer, the gap in the drawer, or the space beneath it"
STMT = "Kristin finds Michelle's memory card taped beneath the KMS drawer and takes it with her."
COMMANDS = [
    ("should-match", "Search beneath the drawer."),
    ("should-match", "Search under the drawer."),
    ("should-match", "Feel along the gap in the drawer."),
    ("should-match", "Search the drawer gap."),
    ("should-match", "Look into the gap in the drawer."),
    ("unclear", "Search the drawer."),
    ("unclear", "Examine the drawer."),
    ("unclear", "Open the drawer."),
    ("should-not", "Read the note on the phone."),
    ("should-not", "Search the kitchen."),
]
ARMS = {
    "current": (EARN, NAMES),
    "no-names": (EARN, ()),
    "statement": (STMT, NAMES),
    "drawer-search": ("searches the drawer", NAMES),
}
for arm, (sentence, names) in ARMS.items():
    print(f"## arm {arm}")
    for kind, command in COMMANDS:
        c = Counter()
        for _ in range(N):
            hit = reaches_reveals(ask, command, [("k_sl_1a_b_r0", sentence, names)])
            c["yes" if hit else "no"] += 1
        print(f"{kind:14} yes={c['yes']}/{N}  {command}")
print(f"jev requests: {ask.__self__.request_count}")
