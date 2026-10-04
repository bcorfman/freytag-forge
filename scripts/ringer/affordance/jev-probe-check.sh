#!/bin/bash
# Ringer check: run the Jev probe (billed) and keep its output.
set -u
cd /home/bcorfman/dev/freytag-forge && set -a && . ./.env && set +a
OUT=/home/bcorfman/dev/ringer-work/jev-probe
uv run python scripts/ringer/affordance/jev_probe.py 5 | tee "$OUT/probe.out"
[ "${PIPESTATUS[0]}" -eq 0 ] && grep -q "^## arm drawer-search" "$OUT/probe.out" && grep -q "jev requests" "$OUT/probe.out"
