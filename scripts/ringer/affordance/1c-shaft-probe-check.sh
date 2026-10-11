#!/bin/bash
# Ringer check: replay recorded 1C narrator prompts under line-addition arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/1c-shaft-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/1c_shaft_probe.py \
  "$OUT/prompts-a.json" "$OUT/prompts-c.json" "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^c3 arm C" "$OUT/probe.out" && ! grep -q "[1-9][0-9]* errors" "$OUT/probe.out"
