"""Score the 2A e_r1 'present my inspector credentials' gap from the PR 527 live run (requires ignored)."""

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
G = {
    it["id"].removeprefix("k_sl_"): tuple(tuple(g) for g in it.get("action_evidence", []))
    for it in K["knowledge"]
    if str(it.get("id", "")).startswith("k_sl_2a_e_r1") and it.get("action_evidence")
}

CASES = {
    "Present my inspector credentials at the facility checkpoint.": {"2a_e_r1"},
    "Present my inspector credentials at the checkpoint.": {"2a_e_r1"},
    "Present my inspector credentials to the guard.": {"2a_e_r1"},
    "Present our inspector credentials at the checkpoint.": {"2a_e_r1"},
    "Present our inspector credentials to the checkpoint guard.": {"2a_e_r1"},
    "Present my credentials at the checkpoint.": {"2a_e_r1"},
    "Show my inspector credentials at the checkpoint.": {"2a_e_r1"},
    "Present my laptop to the guard.": set(),
    "Present my inspector credentials.": set(),
    "Read the facility schematic.": set(),
}
bad = 0
for cmd, want in CASES.items():
    hits = {k for k, g in G.items() if _matches_all(g, cmd)}
    if hits != want:
        bad += 1
        print(f"FAIL: {cmd!r} expected {sorted(want)}, matched {sorted(hits)}")
print(f"2A e_r1 scorer: {len(CASES) - bad}/{len(CASES)} correct")
raise SystemExit(1 if bad else 0)
