#!/usr/bin/env bash
set -u
N=/home/bcorfman/dev/ringer-work/stage5-notes/missed-reveals.md
test -s $N || { echo "missing $N"; exit 1; }
bad=$(git status --porcelain | grep -vE '^\?\? (scripts/|\.ringer)' | head)
[ -n "$bad" ] && { echo "REPO CHANGED (read-only task):"; echo "$bad"; exit 1; }
for id in k_sl_1a_b_r2 k_sl_1a_d_r1 k_sl_1b_a_r1 k_sl_1c_c_r2 k_sl_2b_a_r2 k_sl_2c_a_r1; do
  grep -q "$id" $N || { echo "note lacks section for $id"; exit 1; }
done
for id in k_sl_1a_b_r2 k_sl_1a_d_r1 k_sl_1b_a_r1 k_sl_1c_c_r2 k_sl_2b_a_r2 k_sl_2c_a_r1; do
  sec=$(awk -v id="$id" '$0 ~ "^#+ .*"id {f=1;next} /^#+ / {f=0} f' $N)
  echo "$sec" | grep -qiE 'verdict: *(displaced|ineligible|matcher-miss|not-prompted|selection-lost|other)' || { echo "$id section lacks 'Verdict: <displaced|ineligible|matcher-miss|not-prompted|selection-lost|other>'"; exit 1; }
  echo "$sec" | grep -qiE 'turn [0-9]+' || { echo "$id section cites no turn number"; exit 1; }
done
test -s /home/bcorfman/dev/ringer-work/stage5-notes/missed_reveals.py || { echo "missing probe script missed_reveals.py"; exit 1; }
/home/bcorfman/dev/freytag-forge/.venv/bin/python /home/bcorfman/dev/ringer-work/stage5-notes/missed_reveals.py >/dev/null || { echo "probe script does not run"; exit 1; }
