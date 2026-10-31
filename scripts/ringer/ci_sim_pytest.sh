#!/usr/bin/env bash
# Run pytest the way CI sees the repo: only tracked and new non-ignored files, at a different path.
# Gitignored local artifacts (bench/results, .env) are absent, and the checkout path is not the dev path.
# Usage: ci_sim_pytest.sh [pytest args and test paths...]
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
SIM=$(mktemp -d /tmp/ff-ci-sim.XXXXXX)
trap 'rm -rf "$SIM"' EXIT
cd "$ROOT" || exit 2
git ls-files -z -co --exclude-standard | while IFS= read -r -d '' path; do
  [ -e "$path" ] && printf '%s\0' "$path"
done | tar --null -T - -cf - | tar -xf - -C "$SIM" || exit 2
cd "$SIM" || exit 2
ln -s "$ROOT/.venv" "$SIM/.venv" && git init -q && git add -A && git -c user.name=ci-sim -c user.email=ci-sim@localhost commit -q -m ci-sim || exit 2
env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN -u CLOUDFLARE_AI_TOKEN -u CLOUDFLARE_ACCOUNT_ID \
  PYTHONPATH="$SIM" TMPDIR=/tmp \
  "$ROOT/.venv/bin/python" -m pytest -q -p no:cacheprovider --no-cov "$@"
