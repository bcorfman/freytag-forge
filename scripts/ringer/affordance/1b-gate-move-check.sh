#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/1b-gate-move
mkdir -p "$OUT"
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/runtime/cloudflare.py -e tests/test_semantic_reveal_match.py -e data/stories/continuity-initiative/knowledge.yaml -e scripts/ringer/affordance/1b-wording-score.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached --name-only | grep -q storygame/runtime/cloudflare.py || { echo "FAIL: cloudflare.py not changed"; exit 1; }
git diff --cached --name-only | grep -q tests/test_semantic_reveal_match.py || { echo "FAIL: no new semantic test"; exit 1; }
if git diff --cached -U0 storygame/runtime/cloudflare.py | grep -n '^+.*\bany(' ; then echo "NOTE: new any( in cloudflare.py diff, check it by hand"; fi
TMPDIR=/tmp uv run python scripts/ringer/affordance/1b-wording-score.py || { echo "FAIL: 1B matcher scorer"; exit 1; }
TMPDIR=/tmp uv run python - <<'PY' || exit 1
from pathlib import Path
from storygame.runtime.candidate_matcher import _matches_all
import yaml
K = yaml.safe_load(Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8"))
items = K["knowledge"] if isinstance(K, dict) else K
g = {i["id"]: tuple(tuple(x) for x in i["action_evidence"]) for i in items if i.get("id", "").startswith("k_sl_1b_c_")}
for cmd in ("Open the secured maintenance gate.", "Pick the lock on the maintenance gate."):
    assert _matches_all(g["k_sl_1b_c_r1"], cmd), f"c_r1 does not match: {cmd}"
for cmd in ("Search the bench.", "Examine the man.", "Open the folder of documents."):
    assert not _matches_all(g["k_sl_1b_c_r1"], cmd), f"c_r1 wrongly matches: {cmd}"
print("gate-move matcher ok")
PY
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
