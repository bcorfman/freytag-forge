# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12 attempt 7: attempt 6 plus a per-scene step cache, so no turn is played twice.

Attempt 6 (stopped 2026-11-20) was correct but searched every undecided cell again from the
entry, replaying every turn: at --search-budget 3 the real story played 1972 turns (913 at the
default) and took 294 s, over the 240 s budget. Its first try then pruned "irrelevant" choices,
which dropped deviations (69 entry states to 19). Attempt 7 starts from attempt 6's files,
removes relevance pruning, and caches every applied step. Usage: build_round12_attempt7_manifest.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC6 = importlib.util.spec_from_file_location(
    "attempt6", Path(__file__).with_name("build_round12_attempt6_manifest.py")
)
attempt6 = importlib.util.module_from_spec(_SPEC6)
_SPEC6.loader.exec_module(attempt6)

REPO = attempt6.REPO
WORK = attempt6.WORK
PRIOR = f"{WORK}/attempt6"
OUT = attempt6.OUT
GATE_SECONDS = attempt6.GATE_SECONDS
QUICK_TEST_SECONDS = attempt6.QUICK_TEST_SECONDS
REPLAY_RATIO = 1.15

HEAD_START = f"""HEAD START. {PRIOR}/ holds the previous attempt of this exact brief: carry_matrix.py, free_gates.py, test_factory_carry_matrix.py, test_factory_stations.py and NOTES_12.txt. FIRST copy them into place: `cp {PRIOR}/carry_matrix.py factory/checks/`, `cp {PRIOR}/free_gates.py factory/stations/`, `cp {PRIOR}/test_factory_carry_matrix.py {PRIOR}/test_factory_stations.py tests/`, `cp {PRIOR}/NOTES_12.txt .`. That attempt already does changes 1 to 4 below (the static check, three outcomes, no early stop, station output) and has the five required tests. Its measured results: the real story at the default budget, 69 entry states, 913 turns, 0 stuck, 124 to 150 s; at `--search-budget 3`, 1972 turns, 92 undecided, 294 s, OVER the {GATE_SECONDS} s budget. The cause: `_SearchWorker.search(..., unbounded=True)` and `deviations(..., unbounded=True)` start again from the entry or deviation point, and `_apply` plays a real turn for every step it walks, so every turn of the budgeted pass is played a second time. An earlier try of that attempt then pruned "irrelevant" candidates to get under the budget; that dropped the deviations (the real story fell from 69 entry states to 19) and was rejected. Relevance pruning is now FORBIDDEN, see change 5. An early real-story run of that attempt also had the static check wrongly mark all 13 entry states of 3A stuck; it was fixed, but re-read `static_exit_possible` against NOTES_12.txt's list of fact-assertion paths and keep it sound.

"""

STEP_CACHE = f"""5. NO TURN PLAYED TWICE (replaces relevance pruning). DELETE relevance pruning completely: `relevant_facts_by_scene`, `_candidate_touches_relevant`, every `relevant_ids` parameter and the filtering in `_ordered_steps`. Every offered candidate and wait is a step again, as before. Instead give each `_SearchWorker` a STEP CACHE for its scene: a dict from (point identity key, step) to the `_Applied` result (outcome, turns and the child snapshot). `_apply` looks the pair up first and plays a turn only on a miss; `_ordered_steps` caches the offered steps per point identity too, so projecting a point twice costs nothing. A cache hit counts as no turn in `turns`. The cache is per worker process and per scene, shared by the budgeted pass, the unbounded re-search and the deviations of the same worker; the undecided re-search and the undecided deviations must run in the SAME worker that ran their budgeted pass (attempt 6 already does this; keep it). Prove the cache is correct: the identity key is what the search already uses to merge points, so a cached child is exactly what replaying would give; write in NOTES_12.txt why the snapshot stored for a key is a valid stand-in for any point with that key (or, if two points with the same key can produce different children, key the cache on something stricter and say what). Add `cache_hits: int` to `CarryReport`, the JSON and the TOTAL line (`cache_hits=<n>`). EXPECTED EFFECT, enforced by the check: at `--search-budget 3` the real story plays at most {REPLAY_RATIO} times the turns it plays at the default budget, and both runs finish under {GATE_SECONDS} s. Add a quick test `test_unbounded_research_replays_no_turns` on the fixture story: with `search_budget=1`, the total turns played are at most the turns played at the default budget plus 5% (or prove equality if the fixture is that small), and `cache_hits >= 1`. Do not monkeypatch the search in it. Remove "relevance pruning" as an option from NOTES_12.txt and instead write the step cache's design, the correctness argument and the turn counts of both real-story runs.

"""

SPEC = (
    attempt6.SPEC.replace("YOU OWN exactly", HEAD_START + "YOU OWN exactly", 1)
    .replace(
        attempt6.SPEC[
            attempt6.SPEC.index("5. RELEVANCE PRUNING, ONLY IF NEEDED.") : attempt6.SPEC.index(
                "TESTS, on the two-scene"
            )
        ],
        STEP_CACHE,
    )
    .replace(
        "Required tests, with exactly these names:",
        "Required tests, with exactly these names (attempt 6 already wrote them; keep them passing, plus `test_unbounded_research_replays_no_turns` from change 5):",
    )
    .replace(
        "If a budget is missed, find where the time goes and fix that; do not raise a budget, do not drop deviations, and do not reintroduce budget-as-stuck or an early stop.",
        "If a budget is missed, find where the turns go and fix that with caching, never by skipping steps; do not raise a budget, do not drop deviations, do not prune candidates, and do not reintroduce budget-as-stuck or an early stop.",
    )
)
assert "RELEVANCE PRUNING" not in SPEC and "HEAD START" in SPEC and "STEP CACHE" in SPEC

REQUIRED_TESTS = [*attempt6.REQUIRED_TESTS, "test_unbounded_research_replays_no_turns"]

_EXTRA_SOURCE_RULES = """for banned in ("relevant_facts_by_scene", "_candidate_touches_relevant", "relevant_ids"):
    assert banned not in code, f"relevance pruning is still in carry_matrix.py ({banned})"
assert "cache_hits" in code, "no cache_hits in carry_matrix.py"
print("source rules ok")"""

_TURN_RATIO = f"""# probe 1+2 cross-check: the undecided re-search replays no turns
.venv/bin/python - "$OUT/probe-default.json" "$OUT/probe-budget3.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
assert d["entry_states"] == b["entry_states"], ("budget changed the entry states", d["entry_states"], b["entry_states"])
assert "cache_hits" in d and "cache_hits" in b, "JSON lacks cache_hits"
assert b["cache_hits"] >= 1, b["cache_hits"]
assert b["turns"] <= {REPLAY_RATIO} * d["turns"], ("budget 3 replays turns", b["turns"], d["turns"])
print("replay ok: default turns", d["turns"], "budget3 turns", b["turns"], "cache_hits", b["cache_hits"])
PY
# probe 3: a seeded broken 3A through station 5"""

CHECK = (
    attempt6.CHECK.replace(
        f"for t in {' '.join(attempt6.REQUIRED_TESTS)}; do", f"for t in {' '.join(REQUIRED_TESTS)}; do", 1
    )
    .replace(f"for name in {attempt6.REQUIRED_TESTS!r}:", f"for name in {REQUIRED_TESTS!r}:", 1)
    .replace('print("source rules ok")', _EXTRA_SOURCE_RULES, 1)
    .replace(
        'grep -qi "relevance pruning" NOTES_12.txt || { echo "NOTES_12.txt does not say whether relevance pruning was needed"; exit 1; }',
        'grep -qi "step cache" NOTES_12.txt || { echo "NOTES_12.txt does not describe the step cache"; exit 1; }',
        1,
    )
    .replace(
        "# probe 3: a seeded broken 3A through station 5: caught statically, fast, 3B and 3C unreachable",
        _TURN_RATIO + ": caught statically, fast, 3B and 3C unreachable",
        1,
    )
    .replace('for key in ("undecided",', 'for key in ("cache_hits", "undecided",', 1)
    .replace("carry-matrix-attempt6.patch", "carry-matrix-attempt7.patch")
)
for needle in (
    "test_unbounded_research_replays_no_turns",
    "relevant_facts_by_scene",
    "step cache",
    "replay ok",
    "attempt7.patch",
):
    assert needle in CHECK, needle


def build() -> dict:
    manifest = attempt6.build()
    task = manifest["tasks"][0]
    task.update(
        key="carry-matrix-attempt7",
        spec=SPEC,
        check=CHECK,
        verified=task["verified"]
        + f" Relevance pruning removed; a step cache keeps the budget-3 run within {REPLAY_RATIO}x the default run's turns.",
    )
    return manifest


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-attempt7-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
