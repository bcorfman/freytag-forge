"""Score the 2A/1C misses from the PR 526 live run with the real matcher (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith(("k_sl_2a_", "k_sl_1c_")) and it.get("action_evidence")
}

CASES = {
    "Present my cooling-water warning to the supervisor.": {"2a_c_r1"},
    "Present my emergency inspection warning to the supervisor.": {"2a_c_r1"},
    "Explain my unscheduled inspection to the supervisor.": {"2a_c_r1"},
    "Show my inspector credentials at the facility checkpoint.": {"2a_b_r2", "2a_e_r1"},
    "Present my inspector credentials at the checkpoint.": {"2a_b_r2"},
    "Show my emergency inspection notice to the supervisor.": set(),
    "Tell the supervisor about the weather.": set(),
    "Show my laptop to the guard.": set(),
    "Record the identification numbers on my laptop.": {"1c_b_r1"},
    "Photograph the identification numbers on the uniforms.": {"1c_b_r1"},
    "Write down the identification numbers.": {"1c_b_r1"},
    "Search the processing line for evidence.": set(),
    "Read the facility schematic.": set(),
    "Examine Michelle's record.": set(),
    "Record the loading dock activity.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"2A/1C scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
