#!/bin/bash
# Ringer check: replay recorded 2B narrator prompts for the 'phase' rejection (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/2b-phase-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/2b_phase_probe.py \
  artifacts/e2e-blind-player-prompts-r1.json artifacts/e2e-blind-player-prompts-r2.json "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^r2t8 arm ${PROBE_LAST:-D}" "$OUT/probe.out"
