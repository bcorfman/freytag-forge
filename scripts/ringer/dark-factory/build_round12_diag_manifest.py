# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12 diagnosis: why the carry matrix finds more than 200 entry states for 2B.

One read-only Codex probe, no model call in the game. Usage: build_round12_diag_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-carry-matrix"
DIAG = f"{WORK}/diag-2b-states"

SPEC = f"""You are a read-only diagnosis probe worker. Your current directory is {DIAG}, a scratch directory you own. NEVER modify anything under {REPO} (read it only), never git commit, never run `uv`, never call a model or the network. Python is {REPO}/.venv/bin/python; run every script with `PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src TMPDIR=/tmp` and cwd {REPO} so relative story paths resolve, but write files only into {DIAG}.

BACKGROUND. A new free factory gate, the carry matrix, walks the game scene by scene with scripted offline players (no model) and collects the distinct states the player can be in on entering each scene. Two entry states are merged when their `state_key` is equal. The current draft is {WORK}/attempt2/carry_matrix.py (not in the repo; load it with `importlib.util.spec_from_file_location` under the module name `carry_matrix_draft`). Its key for scene T is: the sorted `Fact.key` tuples `(predicate, subject, object, value)` of the asserted facts whose predicate is in `forward_reads(package, T)` (facts read by conditions of T or a later scene), plus every asserted fact whose value (`fact.value`, else `fact.object`) is not "true" or "false". On the real story (`data/stories/continuity-initiative`, loaded with `storygame.story_package.loader.load_story_package`, then `_legacy_package` from `storygame.personas`), 1A has 1 entry state, 1B has 8, and 2B passes the cap of 200 entry states. At bootstrap there are 125 asserted facts and the 2B key holds 117 of them. We need to know WHICH facts differ between the 2B entry states, so we can decide what the key should leave out.

YOUR TASK.
1. Write {DIAG}/diagnose.py. It reuses the draft's own rollout code (read `carry_matrix` and its helpers; copy or call them, but do not change the rollout rules) to collect the distinct entry snapshots of every scene from 1A through 2B, with the cap lifted (pass a very large `max_states_per_scene`, or copy the walk so it stops after collecting 2B's entry states without running 2B's own rollouts). Keep the merge rule exactly the draft's. For each scene 1A..2B it records: the number of distinct entry states; and every Fact (as predicate, subject, object, value) that is present in some but not all of that scene's entry states, with: how many states hold it, whether its predicate is in `forward_reads(package, scene)`, and its kind (`flag` when the value is "true"/"false", else `relational`). Then, for each scene, group the varying facts by predicate: predicate, kind, number of distinct (subject, object, value) variants, number of states that hold any of them. Then count how many distinct entry states each scene would have under three alternative keys, computed from the same snapshots: (A) `flags_forward`: only the true flag fact ids in `forward_reads`; (B) `flags_plus_forward_relational`: A plus the relational facts whose predicate is in `forward_reads`; (C) `draft`: the draft key (must equal the recorded count). Write {DIAG}/diag.json: {{"scenes": {{"<scene>": {{"entry_states": n, "alt_counts": {{"flags_forward": a, "flags_plus_forward_relational": b, "draft": c}}, "varying_facts": [...], "by_predicate": [...]}}}}, "seconds": x}}. Sort every list deterministically (by predicate, subject, object, value). The script takes `--out PATH` (default {DIAG}/diag.json).
2. Run it and keep its stdout in {DIAG}/run.out.
3. For the top predicates in 2B's `by_predicate` (by variant count, at least the top 10), find in {REPO} (`grep -rn` under `storygame/` and `packages/worldkeeper/src`) where the engine or the story asserts them, and what they mean (custody, place, turn bookkeeping, delivery records, cue stages, counters, and so on). Look at the story source under `data/stories/continuity-initiative/source/` too.
4. Write {DIAG}/report.md with sections: ## Counts (per scene, the entry-state count and the three alternative counts); ## What varies in 2B (a table: predicate, kind, variants, states, read forward?, what it is, where it is asserted with file:line); ## Which of these change how 2B plays (for each top predicate: does any 2B-or-later condition, transition, storylet activation, pacing event or delivery depend on it, yes or no with the evidence; a relational fact can matter without being in forward_reads, e.g. custody checked by the engine, so look); ## Recommended key (the smallest key that keeps every fact that can change how 2B or a later scene plays, its predicted 2B count from your data, and what it would wrongly merge, if anything). Mark observed facts separately from your inferences.

HARD RULES. Do not edit {REPO} or {WORK}/attempt2. Do not change the merge rule or rollout rules when collecting states. Do not round or sample: every entry state counts. If the walk takes more than 25 minutes, stop it, say so in report.md with the partial counts you have, and still write diag.json for the scenes you finished.
"""

CHECK = f"""set -eo pipefail
cd {DIAG}
for f in diagnose.py diag.json run.out report.md; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
{REPO}/.venv/bin/python - <<'PY'
import json, re
d = json.load(open("diag.json"))
s = d["scenes"]
for scene in ["1A", "1B", "1C", "2A", "2B"]:
    assert scene in s, f"scene {{scene}} missing from diag.json"
    row = s[scene]
    alt = row["alt_counts"]
    assert alt["draft"] == row["entry_states"], (scene, alt, row["entry_states"])
    assert alt["flags_forward"] <= alt["flags_plus_forward_relational"] <= alt["draft"], (scene, alt)
assert s["1A"]["entry_states"] == 1, s["1A"]["entry_states"]
assert s["1B"]["entry_states"] == 8, s["1B"]["entry_states"]
assert s["2B"]["entry_states"] > 200, s["2B"]["entry_states"]
assert s["2B"]["varying_facts"] and s["2B"]["by_predicate"], "no varying facts recorded for 2B"
report = open("report.md").read()
for heading in ["counts", "what varies in 2b", "which of these change how 2b plays", "recommended key"]:
    assert re.search(r"^##\\s+" + re.escape(heading), report, re.I | re.M), f"report.md lacks section: {{heading}}"
top = sorted(s["2B"]["by_predicate"], key=lambda r: -int(r.get("variants", r.get("variant_count", 0))))[:5]
missing = [r["predicate"] for r in top if r["predicate"] not in report]
assert not missing, f"report.md does not discuss top varying predicates: {{missing}}"
assert re.search(r"(storygame|packages/worldkeeper)/[\\w/]+\\.py:\\d+", report), "report.md cites no file:line"
print("diag ok", {{k: v["alt_counts"] for k, v in s.items()}})
PY
"""


def build() -> dict:
    return {
        "run_name": "factory-carry-matrix",
        "workdir": WORK,
        "max_parallel": 1,
        "tasks": [
            {
                "key": "diag-2b-states",
                "task_type": "probe",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 120,
                "ownership": [f"{DIAG}/diagnose.py", f"{DIAG}/diag.json", f"{DIAG}/run.out", f"{DIAG}/report.md"],
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [f"{DIAG}/report.md", f"{DIAG}/diag.json"],
                "verified": "diag.json covers 1A to 2B with consistent alternative counts (draft equals the recorded count, 1A=1, 1B=8, 2B>200), varying facts recorded, and report.md has the four sections, discusses the top varying predicates and cites engine file:line.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-diag-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
