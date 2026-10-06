#!/bin/bash
# Ringer check: replay 1B post-gate prompts under three arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/post-gate-probe
uv run python scripts/ringer/affordance/post_gate_probe.py \
  /home/bcorfman/dev/ringer-work/affordance-live-all/e2e-blind-player-prompts-r3.json "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^turn 7 arm D" "$OUT/probe.out"
