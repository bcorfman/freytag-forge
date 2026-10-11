#!/bin/bash
# Ringer check: run one continuous blind-player session through all selected scenes.
# usage: scene-affordance-l2-all-live.sh <replicates> <scenes>
# Optional: WAIT_POLL_SECONDS sets the Railway poll interval; 0 disables sleeps.
# Optional: WAIT_GIVEUP_SECONDS sets the deployment wait timeout; EXPECTED_SHA checks /version.
# Optional: WAIT_FOR_RAILWAY_SELFTEST=1 runs only the Railway wait self-test hook.
set -u
R="${1:-1}"
SCENES="${2:-}"
rw=(npx --yes @railway/cli@latest)
scope=(--project p --service s --environment e)

latest_deployment_id() {
  local deployments
  deployments=$("${rw[@]}" deployment list "${scope[@]}" --limit 1 --json 2>/dev/null) || return 0
  python3 -c 'import json, sys
try:
    deployments = json.load(sys.stdin)
    deployments.sort(key=lambda deployment: deployment.get("createdAt", ""), reverse=True)
    if deployments:
        print(deployments[0].get("id", ""))
except (json.JSONDecodeError, TypeError, AttributeError):
    pass' <<<"$deployments"
}

wait_for_new_deployment() {
  local previous_id="$1"
  local timeout="${2:-${WAIT_GIVEUP_SECONDS:-600}}"
  local poll_seconds="${WAIT_POLL_SECONDS:-10}"
  local deployments snapshot deployment_id status
  local confirmation attempt
  SECONDS=0
  while (( SECONDS <= timeout )); do
    deployments=$("${rw[@]}" deployment list "${scope[@]}" --limit 1 --json 2>/dev/null) || deployments=""
    snapshot=$(python3 -c 'import json, sys
try:
    deployments = json.load(sys.stdin)
    deployments.sort(key=lambda deployment: deployment.get("createdAt", ""), reverse=True)
    if deployments:
        deployment = deployments[0]
        print(deployment.get("id", "") + "\t" + deployment.get("status", ""))
except (json.JSONDecodeError, TypeError, AttributeError):
    pass' <<<"$deployments")
    deployment_id="${snapshot%%$'\t'*}"
    status="${snapshot#*$'\t'}"
    [ "$snapshot" = "$deployment_id" ] && status=""
    echo "poll: deployment id=${deployment_id:-none} status=${status:-unknown}"

    if [ -n "$deployment_id" ] && [ "$deployment_id" != "$previous_id" ]; then
      case "$status" in
        FAILED|CRASHED)
          echo "FAIL: deployment $deployment_id status $status"
          return 1
          ;;
        SUCCESS|SLEEPING)  # an idle service reports SLEEPING; the version check below wakes it
          for attempt in $(seq 1 6); do
            confirmation=$(curl -sf --max-time 15 "${E2E_API_BASE_URL:-}/api/v1/version" 2>/dev/null) || confirmation=""
            if [ -n "$confirmation" ] && python3 -c 'import json, os, sys
try:
    version = json.load(sys.stdin)
    ok = version.get("channel") == "staging" and version.get("runtime") == "scene-v1"
    if os.environ.get("EXPECTED_SHA"):
        ok = ok and version.get("sha") == os.environ["EXPECTED_SHA"]
    raise SystemExit(0 if ok else 1)
except (json.JSONDecodeError, TypeError, AttributeError):
    raise SystemExit(1)' <<<"$confirmation"; then
              echo "deployment ready: $deployment_id"
              return 0
            fi
            [ "$attempt" -ge 6 ] && break
            [ "$poll_seconds" -eq 0 ] || sleep 5
          done
          echo "FAIL: deployment $deployment_id passed Railway healthcheck but /version confirmation failed"
          return 1
          ;;
      esac
    fi
    [ "$poll_seconds" -eq 0 ] || sleep "$poll_seconds"
  done
  echo "FAIL: deployment wait timed out with id=${deployment_id:-none} status=${status:-unknown}"
  return 1
}

if [ "${WAIT_FOR_RAILWAY_SELFTEST:-}" = 1 ]; then
  prev=$(latest_deployment_id)
  wait_for_new_deployment "$prev"
  exit $?
fi

cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
case "$R" in
  1|2|3) ;;
  *) echo "FAIL: replicates must be 1 to 3"; exit 1 ;;
esac
OUT=/home/bcorfman/dev/ringer-work/affordance-live-all
scope=(--project "$RAILWAY_PROJECT_ID" --service "$RAILWAY_SERVICE_ID" --environment "$RAILWAY_STAGING_ENVIRONMENT_ID")
restore() {
  local restore_prev restore_current
  restore_prev=$(latest_deployment_id)
  "${rw[@]}" variable delete FREYTAG_RATE_LIMIT_PER_MINUTE "${scope[@]}" --skip-deploys >/dev/null 2>&1 || "${rw[@]}" variable delete FREYTAG_RATE_LIMIT_PER_MINUTE "${scope[@]}" 2>&1 | tail -2
  SECONDS=0
  while (( SECONDS <= 30 )); do
    restore_current=$(latest_deployment_id)
    if [ -n "$restore_current" ] && [ "$restore_current" != "$restore_prev" ]; then
      if ! wait_for_new_deployment "$restore_prev"; then
        echo "WARNING: restore redeploy did not settle"
      fi
      break
    fi
    [ "${WAIT_POLL_SECONDS:-10}" -eq 0 ] || sleep "${WAIT_POLL_SECONDS:-10}"
  done
  if [ "$restore_current" = "$restore_prev" ] || [ -z "$restore_current" ]; then
    echo "no redeploy was triggered by restore; continuing"
  fi
  echo "restored: staging turn cap variable deleted (default 10 applies after next deploy)"
}
trap restore EXIT
prev=$(latest_deployment_id)
"${rw[@]}" variable set FREYTAG_RATE_LIMIT_PER_MINUTE=60 "${scope[@]}" || { echo "FAIL: could not raise the cap"; exit 1; }
wait_for_new_deployment "$prev" || exit 1
cd frontend
rm -f ../artifacts/e2e-blind-player-r*.json ../artifacts/e2e-blind-player.json ../artifacts/e2e-blind-player.md ../artifacts/e2e-blind-player-prompts*.json ../artifacts/e2e-blind-player-prompts*.md
tmp_root=$(mktemp -d)
pids=()
for n in $(seq 1 "$R"); do
  mkdir -p "$tmp_root/replicate-$n"
  if [ -z "$SCENES" ] || [ "$SCENES" = "all" ]; then
    E2E_TURN_TIMEOUT_MS=90000 E2E_BLIND_SCENE=all E2E_BLIND_REPLICATE_INDEX="$n" npx playwright test --timeout=3600000 --grep @blind-player --output "$tmp_root/replicate-$n" >"$tmp_root/replicate-$n.log" 2>&1 &
  else
    E2E_TURN_TIMEOUT_MS=90000 E2E_BLIND_SCENE=all E2E_BLIND_SCENES="$SCENES" E2E_BLIND_REPLICATE_INDEX="$n" npx playwright test --timeout=3600000 --grep @blind-player --output "$tmp_root/replicate-$n" >"$tmp_root/replicate-$n.log" 2>&1 &
  fi
  pids[$n]=$!
done
failed=()
for n in $(seq 1 "$R"); do
  if wait "${pids[$n]}"; then status=0; else status=$?; failed+=("$n"); fi
  echo "--- replicate $n log (last 15 lines; exit $status) ---"
  tail -15 "$tmp_root/replicate-$n.log"
done
if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAIL: replicate(s) failed: ${failed[*]}"
  exit 1
fi
node e2e/merge-blind-player.js ../artifacts "$R"
mkdir -p "$OUT"
cp ../artifacts/e2e-blind-player*.json ../artifacts/e2e-blind-player*.md "$OUT/"
uv run python ../scripts/ringer/affordance/digest.py ../artifacts/e2e-blind-player.json
