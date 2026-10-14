#!/usr/bin/env bash
set -u
D=/home/bcorfman/dev/ringer-work/astra-guard-retry-diagnose-notes
R=/home/bcorfman/dev/freytag-forge
[ -z "$(git -C $R status --porcelain | grep -v -E 'scripts/ringer/astra/|\.plans/')" ] || { echo "FAIL main checkout modified"; exit 1; }
[ -s "$D/diagnosis.md" ] || { echo "FAIL no diagnosis.md"; exit 1; }
for h in "Answer" "Request trace" "Where the leak error is raised" "Proposed fix" "Confidence"; do
  grep -q -i "^## .*$h" "$D/diagnosis.md" || { echo "FAIL diagnosis.md lacks section '$h'"; exit 1; }
done
grep -q -E "[a-z_/]+\.py:[0-9]+" "$D/diagnosis.md" || { echo "FAIL diagnosis.md cites no file:line"; exit 1; }
[ -s "$D/repro.py" ] || { echo "FAIL no repro.py"; exit 1; }
out=$(cd $R && PYTHONPATH=$R TMPDIR=/tmp timeout 300 $R/.venv/bin/python "$D/repro.py" 2>&1)
echo "$out" | tail -15
echo "$out" | grep -q -E "^REPRO guard_retry_fired=(True|False) http_requests=[0-9]+ rejections=[0-9]+ error=" || { echo "FAIL repro did not print REPRO line"; exit 1; }
echo PASS
