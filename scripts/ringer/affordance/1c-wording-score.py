"""Score the 1C reveal groups in knowledge.yaml with the real matcher (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_1c_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_1c_")
}
assert {"a_r1", "a_r2", "b_r1", "b_r2", "c_r1"} <= set(G), sorted(G)

# command -> the one reveal expected (None = no 1C reveal may fire)
CASES = {
    "Inspect the loading docks.": "a_r1",
    "Search the loading docks.": "a_r1",
    "Examine the identification numbers on the uniforms below.": "b_r1",
    "Read the identification numbers on the uniforms.": "b_r1",
    "Read the identification numbers on the workers' uniforms.": "b_r1",
    "Inspect the identification numbers on the uniforms.": "b_r1",
    "Compare the prisoners with the missing-person records.": "b_r1",
    "Search the processing line for Michelle.": "b_r2",
    "Look for Michelle in the processing area.": "b_r2",
    "Read the logistics computer.": "c_r1",
    "Access the logistics computer.": "c_r1",
    "Use the logistics computer.": "c_r1",
    "Examine the logistics computer.": "c_r1",
    "Inspect the logistics computer.": "c_r1",
    "Examine the processing line.": None,
    "Inspect the observation shaft.": None,
    "Examine the uniforms.": None,
    "Examine the crates on the processing line.": None,
    "Examine the Eclipse Corporation logo.": None,
    "Descend the concealed stairs.": None,
    "Climb the ladder to the observation shaft.": None,
    "Open the observation shaft grate.": None,
    "Enter the observation shaft.": None,
    "Inspect the humming air vents.": "a_r1",
}
bad = 0
for cmd, want in CASES.items():
    hits = sorted(k for k, g in G.items() if _matches_all(g, cmd))
    ok = hits == [want] if want else not hits
    if not ok:
        bad += 1
        print(f"FAIL: {cmd!r} expected {want}, matched {hits}")
print(f"1C scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
