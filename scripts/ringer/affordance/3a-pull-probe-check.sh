#!/bin/bash
# Ringer check: replay recorded 3A narrator prompts under line-removal arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/3a-pull-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/3a_pull_probe.py \
  /home/bcorfman/dev/ringer-work/3a-pull-probe/prompts-r2.json "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^t5 arm ${PROBE_LAST:-D}" "$OUT/probe.out"
