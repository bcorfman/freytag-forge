"""Score the 3A reveal groups in knowledge.yaml with the real matcher (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_3a_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_3a_")
}
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1", "c_r2", "d_r1", "d_r2"} <= set(G), sorted(G)

# command -> the set of 3A reveals expected (empty = none may fire)
CASES = {
    "Find Michelle.": {"a_r1"},
    "Listen to the stolen radio.": {"a_r1"},
    "Free the captives in the holding block.": {"a_r1"},
    "Help Michelle organize the prisoner escape.": {"a_r1"},
    "Use the stolen radio.": {"a_r1"},
    "Follow the coded announcements.": {"a_r1"},
    "Ask Michelle about the other sites.": {"a_r2"},
    "Talk to Michelle.": {"a_r2"},
    "Read the experiment records.": {"b_r1"},
    "Examine the medical files.": {"b_r1"},
    "Check the survivor list.": {"b_r1"},
    "Go to the medical level.": {"b_r2"},
    "Question the senior official.": {"d_r1"},
    "Ask the imprisoned official about the gate codes.": {"c_r2", "d_r1"},
    "Talk to the prisoner with the official access seal.": {"d_r1"},
    "Check the gate-status panel.": {"d_r2"},
    "Read the access codes on the gate-status panel.": {"d_r2"},
    "Use the official access seal on the gate-status panel.": {"d_r2"},
    "Override the gate-status panel.": {"d_r2"},
    "Enter the displayed access code on the gate-status panel.": {"d_r2"},
    "Signal the uprising.": {"c_r1"},
    "Rally the prisoners for the revolt.": {"c_r1"},
    "Tell Michelle to start the uprising.": {"a_r2", "c_r1"},
    "Warn Michelle about the expiring codes.": {"c_r2"},
    "Lead the prisoners through the blind checkpoints.": {"c_r1"},
    "Escort the prisoners through the checkpoints.": {"c_r1"},
    "Guide the prisoners toward the surface gates.": {"c_r1"},
    "Advance the prisoners through the next blind checkpoint.": {"c_r1"},
    "Follow Michelle to the checkpoints.": {"a_r1", "b_r2", "c_r1"},
    "Lead the prisoners toward the surface gates.": {"c_r1"},
    "Enter Rebecca's secured office.": set(),
    "Follow the maintenance route to the exit.": set(),
    "Examine the maintenance mainframe.": set(),
    "Read the cryptic messages on the office console.": set(),
    "Lead the freed captives through the narrow corridor.": set(),
    "Open the detention cells.": set(),
    "Take the stolen radio.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"3A scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
