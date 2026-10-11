#!/bin/bash
# Ringer check: replay rendered 2C narrator prompts under file-sentence arms (billed: narrator Worker).
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/2c-files-probe
mkdir -p "$OUT"
uv run python scripts/ringer/affordance/2c_files_render.py "$OUT/prompts.json" >/dev/null || exit 1
uv run python scripts/ringer/affordance/2c_files_probe.py "$OUT/prompts.json" "${PROBE_N:-1}" "$OUT/replies.json" | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^medical arm C" "$OUT/probe.out" && ! grep -q "[1-9][0-9]* errors" "$OUT/probe.out"
