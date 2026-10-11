#!/bin/bash
# Ringer check: two back-to-back 3-replicate all-scene hosted L2 runs (six replicates), kept in separate folders.
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
SHA=$(curl -sf "$E2E_API_BASE_URL/api/v1/version" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"][:8])')
[ -n "$SHA" ] || { echo "FAIL: could not read the staging version"; exit 1; }
echo "staging sha: $SHA"
OUT=/home/bcorfman/dev/ringer-work/affordance-live-all
for part in a b; do
  bash scripts/ringer/affordance/scene-affordance-l2-all-live.sh 3 all || { echo "FAIL: run $part failed"; exit 1; }
  DEST=/home/bcorfman/dev/ringer-work/l2x6-$SHA-$part
  rm -rf "$DEST" && mkdir -p "$DEST" && cp "$OUT"/e2e-blind-player* "$DEST/"
  echo "copied run $part to $DEST"
done
uv run python scripts/ringer/affordance/l2_summary.py /home/bcorfman/dev/ringer-work/l2x6-$SHA-a /home/bcorfman/dev/ringer-work/l2x6-$SHA-b | tee /home/bcorfman/dev/ringer-work/l2x6-$SHA-summary.txt
