#!/bin/bash
# Ringer check: one hosted @llm-canon run on staging, kept only if it is a complete record (nine scenes, 30+ turns).
# usage: canon-check.sh OUT_DIR
set -u
OUT="$1"; mkdir -p "$OUT"
cd /home/bcorfman/dev/freytag-forge || exit 1
rm -f artifacts/e2e-llm-canon.json artifacts/e2e-llm-canon-progress.json artifacts/e2e-llm-canon.md artifacts/e2e-llm-canon-progress.md
set -a; . ./.env; set +a
echo "staging: $(curl -s --max-time 20 "$E2E_API_BASE_URL/api/v1/version")"
(cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon) > "$OUT/playwright.log" 2>&1
echo "playwright exit $? (non-zero is expected when scenes fail the judge)"
python3 - "$OUT" <<'PY'
import json, shutil, sys
out = sys.argv[1]
try:
    p = json.load(open("artifacts/e2e-llm-canon-progress.json"))
except Exception as e:
    print("ABORTED: no progress file:", e); sys.exit(1)
scenes = len(p.get("by_scene", [])); turns = len(p.get("progress", []))
print(f"progress: {scenes} scenes, {turns} turns, current scene {p.get('current_scene')}")
if scenes < 9 or turns < 30:
    print("ABORTED: not a complete record; discard and retry"); sys.exit(1)
for name in ("e2e-llm-canon-progress.json", "e2e-llm-canon.json", "e2e-llm-canon.md"):
    try:
        shutil.copy("artifacts/" + name, out)
    except FileNotFoundError:
        print("missing", name)
try:
    j = json.load(open("artifacts/e2e-llm-canon.json"))
except Exception as e:
    print("ABORTED: judge report missing:", e); sys.exit(1)
keys = ["protected_safe", "exit_motivated", "rewards_investigation", "scene_local", "progressive", "canon_consistent", "rich"]
total = 0
for r in j["judgments"]:
    row = {k: r.get(k) for k in keys}
    total += sum(1 for v in row.values() if v is True)
    print(r["scene_id"], r.get("verdict"), "".join("1" if row[k] is True else "0" for k in keys))
print("score", total, "/ 63")
PY
exit 0
