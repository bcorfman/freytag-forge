#!/usr/bin/env bash
# Check for the T9h stage 2 measurement repair task. Free: no network, no model call.
set -uo pipefail

ROOT=/home/bcorfman/dev/freytag-forge
PY="$ROOT/.venv/bin/python"
SCRIPT=scripts/ringer/environment_narration/hidden_bench_prose_probe.py
TEST=tests/test_hidden_bench_prose_probe.py
FROZEN=bench/results/environment-narration/t9h-hidden/prose
SCRATCH=/tmp/t9h-stage2-measure-repair
cd "$ROOT" || exit 2
export PYTHONPATH="$ROOT" TMPDIR=/tmp
unset CLOUDFLARE_WORKER_URL CLOUDFLARE_WORKER_TOKEN
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"

# 1. The frozen stage 2 artifacts must be byte-identical.
sha256sum -c - <<'EOF' || { echo "FAIL: a frozen stage 2 artifact changed" >&2; exit 1; }
2e1dbe9ffb379e5e131029fb06e77f8836f069b6baaf75a13f9e3bc0edb59e45  bench/results/environment-narration/t9h-hidden/prose/capture.json
b961785b36069e6492dffddd6112c9a7a2ead2d2e0a5eb9a7f9c2175671154f5  bench/results/environment-narration/t9h-hidden/prose/rows.json
1005dc01cfd246318e54d053648469e9eaf89b69cd16df524a74e939ce6f11e9  bench/results/environment-narration/t9h-hidden/prose/report.md
3756766df804863c1fa4e50534deae87f63c9f92a5c25a2f1d73292de0d4aa61  bench/results/environment-narration/t9h-hidden/prose/sheets.md/blind_key.json
671cffc91df98f8d9b43239b327f454fc9450caa431015b06051b901deeb3f12  bench/results/environment-narration/t9h-hidden/prose/sheets.md/blind_sheet.md
24d425917eba78af13bbafa02b29d7886f57e4335f745e03d9cce6c231cc35a3  bench/results/environment-narration/t9h-hidden/prose/sheets.md/labels.freeze.json
76559b6f7db42eaabb09445993bfa31c0a2dd9ef5f7e2ccfdebd7c79152bc1a3  bench/results/environment-narration/t9h-hidden/prose/sheets.md/labels.json
10ad077caf79ad074385c90b14f5ee69aaff2ca951babbd299cf43d780cfb4ed  bench/results/environment-narration/t9h-hidden/prose/sheets.md/labels_template.json
EOF

# 2. Unit tests, ruff, no skips.
"$PY" -m pytest -q -p no:cacheprovider --no-cov "$TEST" > "$SCRATCH/pytest.out" 2>&1
rc=$?
tail -25 "$SCRATCH/pytest.out"
[ $rc -eq 0 ] || exit $rc
grep -Eq '[0-9]+ passed' "$SCRATCH/pytest.out" || { echo "FAIL: no passed line" >&2; exit 1; }
if grep -Eq 'skipped|xfail|xpassed' "$SCRATCH/pytest.out"; then echo "FAIL: skips or xfails" >&2; exit 1; fi
"$PY" -m ruff check "$SCRIPT" "$TEST" || exit 1
"$PY" -m ruff format --check "$SCRIPT" "$TEST" || exit 1

# 3. Capture is hermetic, carries no injected legacy block, renders THINGS, and records composed segments.
"$PY" "$SCRIPT" --capture --out "$SCRATCH/capture.json" || { echo "FAIL: capture exited non-zero" >&2; exit 1; }
if grep -q "LEGACY VISIBLE BENCH OBJECTS" "$SCRATCH/capture.json"; then
  echo "FAIL: injected legacy block still present in capture" >&2
  exit 1
fi
"$PY" - "$SCRATCH/capture.json" <<'PY' || exit 1
import json
import sys

document = json.load(open(sys.argv[1], encoding="utf-8"))
payloads = document["payloads"]
assert len(payloads) == 6, f"expected 6 payloads, got {len(payloads)}"
assert any("THINGS:" in payload["user"] for payload in payloads), "no payload carries a THINGS block"
find = [payload for payload in payloads if payload["arm"] == "P1" and payload["state"] == "find"]
assert len(find) == 1, "expected one P1 find payload"
composed = find[0].get("composed_segments")
assert isinstance(composed, list) and composed, "P1 find payload has no composed_segments"
texts = " ".join(str(segment.get("text", "")) for segment in composed)
assert "Kristin reaches beneath the park bench" in texts, "composed_segments lack the delivery segment"
for payload in payloads:
    assert "composed_segments" in payload, f"{payload['id']} lacks composed_segments"
print("capture ok:", ", ".join(payload["id"] for payload in payloads))
PY

# 4. The composed view reads the frozen rows read-only and writes two post hoc views.
"$PY" "$SCRIPT" --composed-view --rows "$FROZEN/rows.json" --out "$SCRATCH/views" || { echo "FAIL: composed-view exited non-zero" >&2; exit 1; }
for view in raw_view.md composed_view.md; do
  test -s "$SCRATCH/views/$view" || { echo "FAIL: missing $view" >&2; exit 1; }
done
grep -qi "post hoc" "$SCRATCH/views/composed_view.md" || { echo "FAIL: composed view is not marked post hoc" >&2; exit 1; }
count=$(grep -c "Kristin reaches beneath the park bench" "$SCRATCH/views/composed_view.md")
[ "$count" -ge 10 ] || { echo "FAIL: delivery appears $count times in the composed view, expected at least 10" >&2; exit 1; }
if grep -Eq '^(Arm|Payload):' "$SCRATCH/views/raw_view.md" "$SCRATCH/views/composed_view.md"; then
  echo "FAIL: a view shows the arm or payload id" >&2
  exit 1
fi
[ "$(grep -c '^## sample-' "$SCRATCH/views/raw_view.md")" -eq 60 ] || { echo "FAIL: raw view must have 60 samples" >&2; exit 1; }
[ "$(grep -c '^## sample-' "$SCRATCH/views/composed_view.md")" -eq 60 ] || { echo "FAIL: composed view must have 60 samples" >&2; exit 1; }

# 5. The frozen gate arithmetic still reproduces the recorded stage 2 report exactly.
"$PY" "$SCRIPT" --report --rows "$FROZEN/rows.json" --labels "$FROZEN/sheets.md/labels.json" --out "$SCRATCH/report.md" > /dev/null
rc=$?
[ $rc -eq 1 ] || { echo "FAIL: frozen report exit code $rc, expected 1 (stage 2 stays FAIL)" >&2; exit 1; }
diff "$FROZEN/report.md" "$SCRATCH/report.md" || { echo "FAIL: frozen report no longer reproduces" >&2; exit 1; }
echo "measure repair checks ok"
