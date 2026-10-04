#!/bin/bash
# Ringer check for L0: run in the task worktree (cwd). Exports patch, runs tests, lint, CLI.
set -u
OUT=/home/bcorfman/dev/ringer-work/affordance-l0b
mkdir -p "$OUT"
[ -f notes.md ] || { echo 'FAIL: notes.md missing at the worktree root'; exit 1; }
cp notes.md "$OUT/notes.md"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e bench/affordance_map.py -e tests/test_affordance_map.py -e bench/affordance_known_gaps.json || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
for f in bench/affordance_map.py tests/test_affordance_map.py bench/affordance_known_gaps.json; do
  [ -f "$f" ] || { echo "FAIL: missing $f"; exit 1; }
done
git diff --cached > "$OUT/l0.patch"
TMPDIR=/tmp uv run ruff check bench/affordance_map.py tests/test_affordance_map.py || exit 1
TMPDIR=/tmp uv run ruff format --check bench/affordance_map.py tests/test_affordance_map.py || { echo "FAIL: run ruff format"; exit 1; }
TMPDIR=/tmp uv run pytest -q -p no:cacheprovider -n0 tests/test_affordance_map.py 2>&1 | tail -40
[ "${PIPESTATUS[0]}" -eq 0 ] || { echo "FAIL: tests"; exit 1; }
for pkg in data/stories/continuity-initiative tests/fixtures/stories/lighthouse-keeper; do
  TMPDIR=/tmp uv run python -m bench.affordance_map --package "$pkg" --out "$OUT/$(basename $pkg).json" || { echo "FAIL: CLI on $pkg"; exit 1; }
done
TMPDIR=/tmp uv run python - <<PY || exit 1
import json
d=json.load(open("$OUT/continuity-initiative.json"))
scenes={s["scene_id"] for s in d["scenes"]}
want={"1A","1B","1C","2A","2B","2C","3A","3B","3C"}
assert want<=scenes, f"missing scenes {want-scenes}"
a=[x for s in d["scenes"] if s["scene_id"]=="1A" for g in s.get("gates",[]) for x in g.get("affordances",[])]
names=json.dumps(a).lower()
assert "michelle_drawer" in names, "1A map lacks michelle_drawer"
assert "michelle_workstation" in names and "kristin_laptop" in names, "1A map lacks workstation/laptop"
assert "park_bench" not in names and "\"kristin\"" not in names.replace("kristin_laptop",""), "1A map still has protagonist/outcome noise"
assert "memory_card" in json.dumps([r for s in d["scenes"] if s["scene_id"]=="1A" for g in s["gates"] for src in g["sources"] for r in src.get("reveals",[])]), "memory_card not a reveal"
print("map ok;", len(a), "1A affordances")
PY
echo PASS
