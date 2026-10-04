#!/bin/bash
# Ringer check: run L2 @blind-player on staging with a raised per-session turn cap, then restore it.
# usage: scene-affordance-l2-live.sh <replicates>
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
R="${1:-1}"
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
E2E_TURN_TIMEOUT_MS=90000 E2E_BLIND_SCENE=1A E2E_BLIND_REPLICATES="$R" npx playwright test --grep @blind-player 2>&1 | tail -15
rc=${PIPESTATUS[0]}
cp ../artifacts/e2e-blind-player.json ../artifacts/e2e-blind-player.md "$OUT/" 2>/dev/null
[ $rc -eq 0 ] && test -s ../artifacts/e2e-blind-player.json && python3 ../scripts/ringer/affordance/digest.py ../artifacts/e2e-blind-player.json
