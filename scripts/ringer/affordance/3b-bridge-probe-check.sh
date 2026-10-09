#!/bin/bash
# Ringer check: replay the blind player's first 3B command under three opening arms (billed).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/3b-bridge-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/3b_bridge_probe.py \
  /home/bcorfman/dev/ringer-work/affordance-live-all "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^arm C" "$OUT/probe.out"
