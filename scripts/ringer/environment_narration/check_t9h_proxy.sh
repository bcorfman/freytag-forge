#!/usr/bin/env bash
# Check for the local proxy concurrency task. Free: no network, no model call.
set -uo pipefail
ROOT=/home/bcorfman/dev/freytag-forge
cd "$ROOT" || exit 2
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN CLOUDFLARE_AI_TOKEN CLOUDFLARE_ACCOUNT_ID
node --test scripts/ringer/environment_narration/local_worker.test.mjs 2>&1 | tail -30
rc=${PIPESTATUS[0]}
[ $rc -eq 0 ] || { echo "FAIL: local_worker tests failed" >&2; exit $rc; }
grep -qi "concurren" scripts/ringer/environment_narration/local_worker.test.mjs || { echo "FAIL: no concurrency test" >&2; exit 1; }
if grep -n "await previous" scripts/ringer/environment_narration/local_worker.mjs | grep -q .; then
  grep -n -B4 "await previous" scripts/ringer/environment_narration/local_worker.mjs | grep -q "fetchImpl" || { echo "FAIL: the unconditional request queue still exists" >&2; exit 1; }
fi
echo "proxy checks ok"
