"""Score the 2C reveal groups in knowledge.yaml with the real matcher."""

import sys
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
items = K["knowledge"] if isinstance(K, dict) else K
G = {
    it["id"].removeprefix("k_sl_2c_"): tuple(tuple(group) for group in it.get("action_evidence", []))
    for it in items
    if str(it.get("id", "")).startswith("k_sl_2c_") and it.get("action_evidence")
}
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1", "c_r2", "d_r1", "d_r2"} <= set(G), sorted(G)

CASES = {
    "Secure the copied JANUS files.": {"c_r1"},
    "Finish copying the JANUS files to my portable drive.": {"c_r1"},
    "Copy the JANUS evidence to my laptop.": {"c_r1"},
    "Verify my portable drive.": {"c_r1"},
    "Check the copied files.": {"c_r1"},
    "Open Charles's Project Purge files.": {"b_r1"},
    "Read Charles's Project Purge files.": {"b_r1"},
    "Read Charles's command record.": {"b_r1"},
    "Search the command records for Charles.": {"b_r1"},
    "Find Michelle's transfer schedule on the archive terminals.": {"b_r1"},
    "Read the transfer orders.": {"b_r1"},
    "Open Michelle's message on my laptop.": {"d_r1"},
    "Read Michelle's decrypted message.": {"d_r1"},
    "Broadcast my JANUS evidence.": {"c_r2"},
    "Broadcast my JANUS evidence publicly.": {"c_r2"},
    "Send the JANUS evidence now.": {"c_r2"},
    "Read Michelle's safe-house message on my portable drive.": {"c_r1", "d_r1"},
    "Argue with Brandon about sending the proof.": {"c_r2"},
    "Follow the service corridor.": set(),
    "Search Michelle's holding block.": set(),
    "Follow Michelle's maintenance access route into her holding block.": set(),
    "Enter Michelle's holding block.": set(),
}

bad = 0
for command, expected in CASES.items():
    matched = {suffix for suffix, groups in G.items() if _matches_all(groups, command)}
    if matched != expected:
        bad += 1
        print(f"FAIL: {command!r} expected {sorted(expected)}, matched {sorted(matched)}")

print(f"{len(CASES) - bad}/{len(CASES)} correct")
sys.exit(1 if bad else 0)
