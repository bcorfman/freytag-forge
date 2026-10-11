#!/bin/bash
# Ringer check for the Railway-state wait in scene-affordance-l2-all-live.sh. Runs in the task worktree.
set -u
OUT=/home/bcorfman/dev/ringer-work/l2-railway-wait
N=$OUT-notes/notes.md
[ -s "$N" ] || { echo "FAIL no notes at $N"; exit 1; }
F=scripts/ringer/affordance/scene-affordance-l2-all-live.sh
git add -A -- "$F"
bad=$(git status --porcelain | grep -v "$F" || true)
[ -z "$bad" ] || { echo "FAIL stray paths:"; echo "$bad"; exit 1; }
mkdir -p "$OUT-patches"
git diff --cached > "$OUT-patches/l2wait.patch"
[ -s "$OUT-patches/l2wait.patch" ] || { echo "FAIL empty patch"; exit 1; }
bash -n "$F" || exit 1
grep -q wait_for_new_deployment "$F" || { echo "FAIL no wait_for_new_deployment"; exit 1; }
grep -q "sleep 60" "$F" && { echo "FAIL sleep 60 still present"; exit 1; }

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
S=$T/state
mkdir -p "$S"
# Fake railway CLI: first call returns the old deployment; the next two show the new one DEPLOYING; then SUCCESS (FAILED when FAKE_FAIL=1).
cat > "$T/npx" <<EOF
#!/bin/bash
n=\$(cat "$S/n" 2>/dev/null || echo 0); echo \$((n+1)) > "$S/n"
old='{"id":"old","status":"SUCCESS","createdAt":"2026-10-11T18:00:00.000Z","meta":{}}'
if [ "\$n" -lt 1 ]; then echo "[\$old]"
elif [ "\$n" -lt 3 ]; then echo "[{\"id\":\"new\",\"status\":\"DEPLOYING\",\"createdAt\":\"2026-10-11T18:05:00.000Z\",\"meta\":{}},\$old]"
else st=SUCCESS; [ "\${FAKE_FAIL:-0}" = 1 ] && st=FAILED
  echo "[{\"id\":\"new\",\"status\":\"\$st\",\"createdAt\":\"2026-10-11T18:05:00.000Z\",\"meta\":{}},\$old]"; fi
EOF
cat > "$T/curl" <<'EOF'
#!/bin/bash
echo '{"api":"v1","runtime":"scene-v1","channel":"staging","sha":"abc"}'
EOF
chmod +x "$T/npx" "$T/curl"
run() {
  echo 0 > "$S/n"
  env PATH="$T:$PATH" E2E_API_BASE_URL=http://x WAIT_POLL_SECONDS=0 WAIT_GIVEUP_SECONDS=5 WAIT_FOR_RAILWAY_SELFTEST=1 "$@" bash "$F" 1 > "$T/out" 2>&1
}
run EXPECTED_SHA=abc; rc=$?
[ $rc -eq 0 ] || { echo "FAIL good case rc=$rc"; cat "$T/out"; exit 1; }
run EXPECTED_SHA=zzz; rc=$?
[ $rc -ne 0 ] || { echo "FAIL wrong sha accepted"; cat "$T/out"; exit 1; }
run FAKE_FAIL=1 EXPECTED_SHA=abc; rc=$?
[ $rc -ne 0 ] || { echo "FAIL failed deployment accepted"; cat "$T/out"; exit 1; }
grep -qi FAILED "$T/out" || { echo "FAIL no FAILED message"; cat "$T/out"; exit 1; }
echo PASS
