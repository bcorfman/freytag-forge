#!/bin/bash
# Ringer check: replay recorded 3A narrator prompts under line-addition arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/3a-records-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/3a_records_probe.py \
  "$OUT/prompts-r2.json" "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^t6 arm D" "$OUT/probe.out" && ! grep -q "[1-9][0-9]* errors" "$OUT/probe.out"
