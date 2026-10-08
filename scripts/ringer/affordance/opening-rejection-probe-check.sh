#!/bin/bash
# Ringer check: create 20 staging sessions and count rejected openings (billed).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/opening-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/opening_rejection_probe.py "${1:-20}" | tee "$OUT/probe-$(date +%s).out"
[ "${PIPESTATUS[0]}" -eq 0 ]
