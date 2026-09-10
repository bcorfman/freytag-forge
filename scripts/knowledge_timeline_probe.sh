#!/usr/bin/env bash

set -euo pipefail

for required in RAILWAY_TOKEN RAILWAY_PROJECT_ID RAILWAY_SERVICE_ID RAILWAY_STAGING_ENVIRONMENT_ID RAILWAY_PUBLIC_API_URL; do
  test -n "${!required-}" || {
    echo "Missing staging configuration: $required" >&2
    exit 1
  }
done

api_base_url="${RAILWAY_PUBLIC_API_URL%/}"
scripted_opening='Rain beads on the quiet house.'

version_response="$(curl -sf "$api_base_url/api/v1/version")"
channel="$(jq -r '.channel' <<<"$version_response")"
if test "$channel" != staging; then
  echo "Refusing to modify deployment: API channel is '$channel', not 'staging'." >&2
  exit 1
fi

test_status=1

revert_staging() {
  railway variable set "FREYTAG_SCRIPTED_TURNS=" \
    --project "$RAILWAY_PROJECT_ID" \
    --service "$RAILWAY_SERVICE_ID" \
    --environment "$RAILWAY_STAGING_ENVIRONMENT_ID" \
    --skip-deploys || true
  railway variable set "FREYTAG_EXPOSE_KNOWLEDGE_AUDIT=" \
    --project "$RAILWAY_PROJECT_ID" \
    --service "$RAILWAY_SERVICE_ID" \
    --environment "$RAILWAY_STAGING_ENVIRONMENT_ID" \
    --skip-deploys || true
  railway variable set "FREYTAG_TURN_PROVIDER=" \
    --project "$RAILWAY_PROJECT_ID" \
    --service "$RAILWAY_SERVICE_ID" \
    --environment "$RAILWAY_STAGING_ENVIRONMENT_ID" || true

  local live_opening_response=''
  local live_opening=''
  local live_restored=0
  for attempt in $(seq 1 30); do
    live_opening_response="$(curl -sf -X POST "$api_base_url/api/v1/session" \
      -H 'Content-Type: application/json' \
      -d '{"story_id":"continuity_initiative"}' || true)"
    live_opening="$(jq -r '.opening.text // empty' <<<"$live_opening_response" 2>/dev/null || true)"
    if test -n "$live_opening" && test "$live_opening" != "$scripted_opening"; then
      live_restored=1
      break
    fi
    sleep 2 || true
  done
  if test "$live_restored" -ne 1; then
    echo "Warning: staging did not show a live opening after the revert." >&2
  fi
}

trap revert_staging EXIT

railway variable set "FREYTAG_TURN_PROVIDER=scripted" \
  --project "$RAILWAY_PROJECT_ID" \
  --service "$RAILWAY_SERVICE_ID" \
  --environment "$RAILWAY_STAGING_ENVIRONMENT_ID" \
  --skip-deploys
railway variable set "FREYTAG_SCRIPTED_TURNS=deployment/knowledge-timeline-script.json" \
  --project "$RAILWAY_PROJECT_ID" \
  --service "$RAILWAY_SERVICE_ID" \
  --environment "$RAILWAY_STAGING_ENVIRONMENT_ID" \
  --skip-deploys
railway variable set "FREYTAG_EXPOSE_KNOWLEDGE_AUDIT=1" \
  --project "$RAILWAY_PROJECT_ID" \
  --service "$RAILWAY_SERVICE_ID" \
  --environment "$RAILWAY_STAGING_ENVIRONMENT_ID"

scripted_live=0
for attempt in $(seq 1 30); do
  opening_response="$(curl -sf -X POST "$api_base_url/api/v1/session" \
    -H 'Content-Type: application/json' \
    -d '{"story_id":"continuity_initiative"}' || true)"
  opening_text="$(jq -r '.opening.text // empty' <<<"$opening_response" 2>/dev/null || true)"
  if test "$opening_text" = "$scripted_opening"; then
    scripted_live=1
    break
  fi
  sleep 2
done
if test "$scripted_live" -ne 1; then
  echo "Scripted narration did not become live on staging within 30 attempts." >&2
  exit 1
fi

export E2E_KNOWLEDGE_TIMELINE=1
export E2E_TURN_TIMEOUT_MS=90000
export E2E_API_BASE_URL="$api_base_url"
test_status=0
(cd frontend && npm run test:e2e -- --grep @knowledge-timeline) || test_status=$?

exit "$test_status"
