"""Ringer check helper: 'transmit the evidence' is no longer guarded; C-R2 keeps its other phrases; nothing else in the three items changed."""

import os
import subprocess
import sys

import yaml

PATH = "data/stories/continuity-initiative/knowledge.yaml"
PHRASE = "transmit the evidence"
OWNERS = ("k_sl_2c_c_r2", "k_sl_2c_d_r1", "k_sl_2c_d_r2")


def items(text):
    data = yaml.safe_load(text)
    rows = data["knowledge"] if isinstance(data, dict) else data
    return {row["id"]: row for row in rows}


new = items(open(PATH).read())
old = items(subprocess.check_output(["git", "show", f"HEAD:{PATH}"], text=True))
for key in OWNERS:
    leak = new[key].get("leak_terms")
    if key == "k_sl_2c_c_r2":
        if not leak:
            sys.exit("FAIL k_sl_2c_c_r2 needs an explicit leak_terms list")
        expected = {
            t.casefold()
            for group in old[key]["must_convey"]
            for t in group
            if len(t.split()) > 1 and t.casefold() != PHRASE
        } | {a.casefold() for a in old[key].get("aliases", []) if len(a.split()) > 1}
        have = {t.casefold() for t in leak}
        if missing := expected - have:
            sys.exit(f"FAIL k_sl_2c_c_r2 leak_terms lost {sorted(missing)}")
    if leak and PHRASE in {t.casefold() for t in leak}:
        sys.exit(f"FAIL {key} still lists '{PHRASE}' in leak_terms")
    for field in ("statement", "delivery_text", "must_convey", "requires", "establishes", "action_evidence", "aliases", "earn_when"):
        if new[key].get(field) != old[key].get(field):
            sys.exit(f"FAIL {key}.{field} changed; only leak_terms may change")
for key, row in old.items():
    if key not in OWNERS and new.get(key) != row:
        sys.exit(f"FAIL unrelated knowledge item changed: {key}")
sys.path.insert(0, os.getcwd())
print("transmit guard data ok")
