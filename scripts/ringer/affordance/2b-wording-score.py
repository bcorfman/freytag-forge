"""Score the 2B follow-up reveal groups in knowledge.yaml with the real matcher (requires ignored).

The a_* reveals fire on any Michelle search and need no chain, so only b_* and c_* are scored.
"""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_2b_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_2b_")
}
assert {"a_r1", "b_r1", "b_r2", "b_r3", "c_r1", "c_r2"} <= set(G), sorted(G)

# command -> the set of b/c reveals expected (empty = none may fire)
CASES = {
    "Read Brandon's record.": {"b_r1"},
    "Read Brandon's earlier messages.": {"b_r1"},
    "Read Brandon's earlier messages on the remote terminal.": {"b_r1"},
    "Examine the development records.": {"b_r1"},
    "Search the development records for Brandon.": {"b_r1"},
    "Read the JANUS development records.": {"b_r1"},
    "Check the original JANUS records for Brandon's name.": {"b_r1"},
    "Question Brandon about the development records.": {"b_r2"},
    "Ask Brandon why he helped write JANUS.": {"b_r2"},
    "Confront Brandon about his earlier messages.": {"b_r2"},
    "Check the security logs for Michelle's evidence.": {"b_r3"},
    "Examine the security logs for Charles.": {"b_r3"},
    "Search the medical terminal for Michelle's patient record.": {"c_r1"},
    "Read the warning message on the medical terminal.": {"c_r1"},
    "Examine the corrupted prisoner files.": {"c_r1"},
    "Open the corrupted files on the medical terminal.": {"c_r1"},
    "Inspect the medical terminal.": {"c_r1"},
    "Read the delayed transfer notices.": {"c_r1"},
    "Read the maintenance reports.": {"c_r2"},
    "Examine the maintenance reports.": {"c_r2"},
    "Inspect the maintenance messages.": {"c_r2"},
    "Enter the records archive.": set(),
    "Examine the facility detention layout.": set(),
    "Read Michelle's Eclipse-12 transfer record.": set(),
    "Search the archive terminals for Dr. Rachel Kim.": set(),
    "Search the medical terminal for Dr. Rachel Kim.": set(),
    "Read Dr. Rachel Kim's medical record.": set(),
    "Read the decrypted location code.": set(),
    "Search the selection files on the archive terminals.": set(),
    "Read Michelle's current location.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if not k.startswith("a_") and _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"2B scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
