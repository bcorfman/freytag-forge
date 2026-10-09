"""Score the 3B reveal groups in knowledge.yaml with the real matcher (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_3b_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_3b_")
}
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1", "c_r2", "d_r1", "d_r2", "e_r1"} <= set(G), sorted(G)

# command -> the set of 3B reveals expected (empty = none may fire)
CASES = {
    "Trace the water-pressure warnings.": {"a_r1"},
    "Trigger a false alarm.": {"a_r1"},
    "Exploit the water-pressure warnings to overload JANUS.": {"a_r1"},
    "Overload JANUS with false alarms.": {"a_r1"},
    "Trigger the cooling-water overload.": set(),
    "Feed JANUS a false water-pressure alarm.": {"a_r1"},
    "Trigger a false water and air alarm.": {"a_r1"},
    "Feed JANUS false water and air alarms.": {"a_r1"},
    "Set off the water and air alarms.": {"a_r1"},
    "Sound the air alarms.": {"a_r1"},
    "Inspect the water and air alarm system.": set(),
    "Examine the inspection console.": set(),
    "Inspect the water-pressure warnings.": set(),
    "Change the door cycles.": {"a_r2"},
    "Use the empty service corridors.": {"a_r1"},
    "Enter Rebecca's executive office.": {"e_r1"},
    "Reach Rebecca's executive office.": {"e_r1"},
    "Go to Rebecca's office.": {"e_r1"},
    "Confront Rebecca about the experiment approvals.": {"b_r1"},
    "Show Rebecca the approval forms.": {"b_r1"},
    "Examine Rebecca's marked site list.": {"b_r2"},
    "Read the marked site list.": {"b_r2"},
    "Copy the site list.": {"b_r2"},
    "Access the remote channel marked Charles.": {"d_r1"},
    "Examine the executive screen.": {"d_r1"},
    "Access Rebecca's remote Charles channel.": {"d_r1"},
    "Confront Charles through Rebecca's remote channel.": {"d_r1"},
    "Open the Charles channel.": {"d_r1"},
    "Transmit my copied JANUS evidence through Rebecca's remote channel.": set(),
    "Demand Rebecca's surrender.": set(),
    "Read Charles's flood order.": {"d_r2"},
    "Open the Brandon voice channel.": {"c_r1"},
    "Access the Brandon voice channel.": {"c_r1"},
    "Tell Brandon to cut the relay.": {"c_r1"},
    "Activate the external broadcast relay.": {"c_r2"},
    "Transmit the JANUS evidence through the external broadcast relay.": {"c_r2"},
    "Begin the public broadcast.": {"c_r2"},
    "Inspect the relay chamber access panel.": set(),
    "Inspect Rebecca's national network controls.": set(),
    "Seize Rebecca's national network controls.": set(),
    "Open the sealed detention cells.": set(),
    "Free Michelle from her restraints.": set(),
    "Lead Michelle and the prisoners through the emergency exit.": set(),
    "Examine the facility layout.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"3B scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
