#!/bin/bash
# Ringer check: replay a recorded 3B prompt under six arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/3b-frame-probe
uv run python scripts/ringer/affordance/3b_frame_probe.py \
  /home/bcorfman/dev/ringer-work/affordance-live-all/e2e-blind-player-prompts-r1.json "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^input neutral arm F" "$OUT/probe.out"
