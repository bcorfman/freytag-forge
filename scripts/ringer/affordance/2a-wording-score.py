"""Score the 2A reveal groups in knowledge.yaml with the real matcher (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_2a_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_2a_")
}
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1", "c_r2", "e_r1"} <= set(G), sorted(G)

# command -> the set of 2A reveals expected (empty = none may fire)
CASES = {
    "Complete my inspector forms.": {"b_r2"},
    "Complete the blank inspector forms.": {"b_r2"},
    "Fill out the blank inspector forms.": {"b_r2"},
    "Prepare the inspector credentials with Brandon.": {"b_r2"},
    "Inspect the cooling system.": {"b_r1"},
    "Check the facility's cooling weakness.": {"b_r1"},
    "Examine Brandon's Continuity Initiative documents.": {"a_r1"},
    "Search Brandon's hideout.": {"a_r1"},
    "Question Brandon about his attempt to expose the program.": {"a_r2"},
    "Present my completed inspector forms to the guard.": {"b_r2", "e_r1"},
    "Show my completed inspector forms to the guard.": {"b_r2", "e_r1"},
    "Enter the secured facility.": {"e_r1"},
    "Enter the facility with Brandon.": {"e_r1"},
    "Follow Brandon into the facility.": {"e_r1"},
    "Follow Brandon's inspection route to the facility.": {"e_r1"},
    "Drive to the facility.": {"e_r1"},
    "Explain the emergency cooling-water inspection to the supervisor.": {"c_r1"},
    "Warn the supervisor about the cooling-water fault.": {"c_r1"},
    "Tell the supervisor about the ventilation fault.": {"c_r1"},
    "Enter the restricted infrastructure corridor.": {"c_r2"},
    "Show my emergency inspection notice to the supervisor.": set(),
    "Question Brandon about the facility inspection.": set(),
    "Question Brandon about my inspector forms.": set(),
    "Examine the communications center.": set(),
    "Help Brandon pick the lock.": set(),
    "Follow Brandon's inspection route.": set(),
    "Review Brandon's inspection route.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"2A scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
