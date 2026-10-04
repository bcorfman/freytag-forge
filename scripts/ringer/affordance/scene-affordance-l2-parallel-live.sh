#!/bin/bash
# Ringer check: run L2 @blind-player on staging with a raised per-session turn cap, then restore it.
# usage: scene-affordance-l2-parallel-live.sh <replicates>
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
R="${1:-1}"
case "$R" in
  1|2|3) ;;
  *) echo "FAIL: replicates must be 1 to 3"; exit 1 ;;
esac
OUT=/home/bcorfman/dev/ringer-work/affordance-live
rw=(npx --yes @railway/cli@latest)
scope=(--project "$RAILWAY_PROJECT_ID" --service "$RAILWAY_SERVICE_ID" --environment "$RAILWAY_STAGING_ENVIRONMENT_ID")
restore() { "${rw[@]}" variable delete FREYTAG_RATE_LIMIT_PER_MINUTE "${scope[@]}" --skip-deploys >/dev/null 2>&1 || "${rw[@]}" variable delete FREYTAG_RATE_LIMIT_PER_MINUTE "${scope[@]}" 2>&1 | tail -2; echo "restored: staging turn cap variable deleted (default 10 applies after next deploy)"; }
trap restore EXIT
"${rw[@]}" variable set FREYTAG_RATE_LIMIT_PER_MINUTE=60 "${scope[@]}" || { echo "FAIL: could not raise the cap"; exit 1; }
# The redeploy swaps containers and drops sessions made on the old one, so wait until the new one has
# answered 5 times in a row, 10 s apart, after the variable change (at least 60 s).
sleep 60; ok=0
for i in $(seq 1 40); do
  if curl -sf "$E2E_API_BASE_URL/api/v1/health" >/dev/null; then ok=$((ok+1)); else ok=0; fi
  [ "$ok" -ge 5 ] && break; sleep 10
done
[ "$ok" -ge 5 ] || { echo "FAIL: staging did not settle after the redeploy"; exit 1; }
cd frontend
rm -f ../artifacts/e2e-blind-player-r*.json ../artifacts/e2e-blind-player.json ../artifacts/e2e-blind-player.md
tmp_root=$(mktemp -d)
pids=()
for n in $(seq 1 "$R"); do
  mkdir -p "$tmp_root/replicate-$n"
  E2E_TURN_TIMEOUT_MS=90000 E2E_BLIND_SCENE=1A E2E_BLIND_REPLICATE_INDEX="$n" npx playwright test --grep @blind-player --output "$tmp_root/replicate-$n" >"$tmp_root/replicate-$n.log" 2>&1 &
  pids[$n]=$!
done
failed=()
for n in $(seq 1 "$R"); do
  if wait "${pids[$n]}"; then
    status=0
  else
    status=$?
    failed+=("$n")
  fi
  echo "--- replicate $n log (last 15 lines; exit $status) ---"
  tail -15 "$tmp_root/replicate-$n.log"
done
if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAIL: replicate(s) failed: ${failed[*]}"
  exit 1
fi
node e2e/merge-blind-player.js ../artifacts "$R"
cp ../artifacts/e2e-blind-player*.json ../artifacts/e2e-blind-player*.md "$OUT/"
python3 ../scripts/ringer/affordance/digest.py ../artifacts/e2e-blind-player.json
