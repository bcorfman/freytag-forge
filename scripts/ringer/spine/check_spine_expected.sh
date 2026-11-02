#!/usr/bin/env bash
# Ringer check for the spine-expected-from-engine task. Prints why it fails.
set -euo pipefail
REPO=/home/bcorfman/dev/freytag-forge
cd "$REPO"
export TMPDIR=/tmp

echo "== 1. 1C journey commands"
uv run python - <<'EOF'
from scripts.generate_spine_expected_reveals import scene_prompts
want = [
    "Inspect the electrical load and fresh ventilation at the loading docks.",
    "Study the prisoners on the processing line through the observation shaft.",
    "Copy the prisoner numbers from the processing line.",
]
got = scene_prompts()["1C"]
assert got == want, f"1C prompts are {got!r}, expected {want!r}"
print("1C prompts ok")
EOF

echo "== 2. generator output: engine-simulated, committed file in sync, consistent with the live run"
uv run python - <<'EOF'
import json
from pathlib import Path
import scripts.generate_spine_expected_reveals as gen

assert hasattr(gen, "simulate_expected_reveals"), "generator must expose simulate_expected_reveals()"
sim = gen.simulate_expected_reveals()
committed = json.loads(Path("frontend/e2e/spine-expected-reveals.json").read_text())
assert sim == committed, f"spine-expected-reveals.json is stale.\n simulated={json.dumps(sim)}\n file={json.dumps(committed)}"
scenes = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")
assert tuple(sim) == scenes, f"scene keys/order {list(sim)}"
assert all(sim[s] for s in scenes), f"a scene expects nothing: {sim}"
assert sim["1C"] == ["k_sl_1c_a_r1", "k_sl_1c_b_r1", "k_sl_1c_c_copy_numbers"], f"1C expected {sim['1C']}"
assert "k_sl_2c_c_r1" in sim["2C"], "2C must expect k_sl_2c_c_r1"
assert "k_sl_1a_d_r1" not in sim["1A"], "k_sl_1a_d_r1 is not eligible on the scripted 1A walk"
assert "k_sl_1b_a_r1" not in sim["1B"], "k_sl_1b_a_r1 cannot commit after its sibling k_sl_1b_a_r2"
live = json.loads(Path("scripts/ringer/spine/live-spine-committed-d65fb99d.json").read_text())["committed_by_scene"]
problems = {s: sorted(set(sim[s]) - set(live.get(s, []))) for s in scenes if s != "1C"}
problems = {s: v for s, v in problems.items() if v}
assert not problems, f"simulation expects reveals the live run on the same prompts never committed: {problems}"
print("generator ok:", json.dumps(sim))
EOF

echo "== 3. focused pytest"
uv run pytest -q --no-cov -p no:cacheprovider tests/test_spine_expected_reveals.py tests/test_canon_journey.py

echo "== 4. frontend node tests"
(cd frontend && node --test e2e/*.test.js src/*.test.js 2>&1 | tail -15; exit "${PIPESTATUS[0]}")

echo "== 5. quick suite"
uv run python scripts/quick_suite.py --also tests/test_spine_expected_reveals.py -- -q -n 4 -p no:cacheprovider

echo "== 6. ruff"
uv run ruff check . && uv run ruff format --check .
echo "ALL CHECKS PASSED"
