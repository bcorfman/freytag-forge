#!/bin/bash
# Ringer check: replay a recorded 2C prompt under four frame arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/2c-detention-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/2c_detention_probe.py \
  /home/bcorfman/dev/ringer-work/affordance-live-all/e2e-blind-player-prompts-r1.json "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^input neutral arm D" "$OUT/probe.out"
