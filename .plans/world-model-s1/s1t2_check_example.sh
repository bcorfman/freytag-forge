#!/usr/bin/env bash
# S1 task 2 check: runs inside the task worktree (cwd). Prints why it fails.
set -u
R=/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/37a04a00-4fcd-4fc2-a22c-70b9a8c03706/scratchpad/s1t2
PY=/home/bcorfman/dev/freytag-forge/.venv/bin/python
PKG=packages/worldkeeper
export TMPDIR=/tmp
export PYTHONPATH="$PKG/src:."
mkdir -p "$R/out"
status=0
fail() { echo "FAIL: $*"; status=1; }

# 1. Ownership: only the library, storygame, tests and pyproject.toml may change.
changed=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u | grep -v '^$' || true)
[ -z "$changed" ] && fail "no files changed"
outside=$(echo "$changed" | grep -vE "^($PKG/|storygame/|tests/|pyproject\.toml$|\.gitignore$)" | grep -v '^$' || true)
[ -n "$outside" ] && { fail "files outside the allowed set changed (uv.lock, data/, docs/, bench/ are off limits):"; echo "$outside"; }
[ -f tests/test_world_model.py ] || fail "tests/test_world_model.py does not exist"
git check-ignore -q packages/worldkeeper/src/worldkeeper.egg-info/PKG-INFO || fail ".gitignore does not ignore packages/worldkeeper/src/worldkeeper.egg-info/ (add *.egg-info/)"
echo "$changed" | grep -q 'egg-info' && fail "an egg-info build directory is in the change set"

# 2. pyproject.toml: worldkeeper is a workspace dependency of storygame.
"$PY" - <<'PY' || status=1
import tomllib
d = tomllib.load(open("pyproject.toml", "rb"))
errs = []
deps = d.get("project", {}).get("dependencies", [])
if not any(dep.split()[0].split(">")[0].split("=")[0] == "worldkeeper" for dep in deps):
    errs.append("project.dependencies must list 'worldkeeper'")
uv = d.get("tool", {}).get("uv", {})
if "packages/worldkeeper" not in uv.get("workspace", {}).get("members", []):
    errs.append("[tool.uv.workspace] members must include 'packages/worldkeeper'")
if uv.get("sources", {}).get("worldkeeper") != {"workspace": True}:
    errs.append("[tool.uv.sources] must set worldkeeper = { workspace = true }")
for e in errs: print("FAIL:", e)
raise SystemExit(1 if errs else 0)
PY

# 3. Library boundary still holds: stdlib only, never storygame; no story names in the library.
"$PY" - "$PKG" <<'PY' || status=1
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1])
allowed = set(sys.stdlib_module_names) | {"worldkeeper", "__future__"}
bad = []
for path in root.rglob("*.py"):
    extra = ({"pytest"} if "tests" in path.parts else set()) | {p.stem for p in path.parent.glob("*.py")}
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
            [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
        bad += [f"{path}: imports {n}" for n in names if n.split(".")[0] not in allowed | extra]
for b in bad: print("FAIL:", b)
raise SystemExit(1 if bad else 0)
PY
hits=$(grep -rniE --exclude=pyproject.toml "kristin|michelle|brandon|rebecca|continuity|memory.?card|freytag|storygame" "$PKG" 2>/dev/null || true)
[ -n "$hits" ] && { fail "story or host names found in $PKG:"; echo "$hits" | head -10; }

# 4. The library's own tests, >= 90% branch coverage.
"$PY" -m pytest "$PKG/tests" -q -p no:cacheprovider -o addopts="" --cov=worldkeeper --cov-branch \
  --cov-report=term --cov-fail-under=90 > "$R/out/lib-tests.txt" 2>&1 \
  || { fail "worldkeeper's own tests failed or coverage < 90%:"; tail -25 "$R/out/lib-tests.txt"; }
grep -E "^TOTAL|passed|failed" "$R/out/lib-tests.txt" | tail -2

# 5. Acceptance tests (the contract for this task).
"$PY" -m pytest "$R/acceptance/test_acceptance.py" -q -p no:cacheprovider -o addopts="" \
  --rootdir=. > "$R/out/acceptance.txt" 2>&1 \
  || { fail "acceptance tests failed:"; grep -E "^(FAILED|ERROR)|Error|assert " "$R/out/acceptance.txt" | head -40; }
tail -1 "$R/out/acceptance.txt"

# 6. The full storygame suite with its coverage gate.
"$PY" -m pytest -q -p no:cacheprovider -n auto > "$R/out/full-suite.txt" 2>&1 \
  || { fail "full test suite failed:"; grep -E "^(FAILED|ERROR)|Required test coverage|FAIL Required" "$R/out/full-suite.txt" | head -40; tail -3 "$R/out/full-suite.txt"; }
tail -1 "$R/out/full-suite.txt"


# 6b. The new storygame tests alone cover world_model.py (>= 95%).
"$PY" -m pytest tests/test_world_model.py -q -p no:cacheprovider -o addopts="" --cov=storygame.runtime.world_model \
  --cov-branch --cov-report=term-missing --cov-fail-under=95 > "$R/out/world-model-tests.txt" 2>&1 \
  || { fail "tests/test_world_model.py failed or covers world_model.py below 95%:"; tail -15 "$R/out/world-model-tests.txt"; }

# 6c. Mutation checks: removing each wiring point must make a test fail.
mutate() {  # file, python-regex-of-line-to-delete (first match inside def NAME), def NAME, test target, label
  local file=$1 pattern=$2 func=$3 target=$4 label=$5 backup="$R/out/mutant.bak"
  cp "$file" "$backup"
  "$PY" - "$file" "$pattern" "$func" <<'PYM' || { cp "$backup" "$file"; fail "mutation setup failed for: $label"; return; }
import re, sys
path, pattern, func = sys.argv[1:4]
lines = open(path).read().split("\n")
start = next((i for i, l in enumerate(lines) if re.match(rf"\s*def {func}\b", l)), None)
if start is None: sys.exit(f"no def {func} in {path}")
indent = len(lines[start]) - len(lines[start].lstrip())
for i in range(start + 1, len(lines)):
    l = lines[i]
    if l.strip() and (len(l) - len(l.lstrip())) <= indent and not l.lstrip().startswith((")", "]")): break
    if re.search(pattern, l):
        lines[i] = l[: len(l) - len(l.lstrip())] + "pass"
        open(path, "w").write("\n".join(lines)); sys.exit(0)
sys.exit(f"no line matching {pattern} inside {func}")
PYM
  if "$PY" -m pytest $target -q -x -p no:cacheprovider -o addopts="" > "$R/out/mutant.txt" 2>&1; then
    fail "mutation survived (no test noticed): $label"
  fi
  cp "$backup" "$file"
}
mutate "$PKG/src/worldkeeper/model.py" "_move_companions\(" "_effect_move" "$PKG/tests" "story-effect move no longer carries companions"
mutate storygame/runtime/engine.py "apply_world_effects\(" "_activate_pacing" tests/test_world_model.py "_activate_pacing no longer sweeps world effects"
mutate storygame/runtime/state.py "apply_world_effects\(" "apply_proposal" tests/test_world_model.py "apply_proposal no longer sweeps world effects"
mutate storygame/runtime/state.py "\.seed\(\)" "bootstrap" tests/test_world_model.py "bootstrap no longer seeds the world"
git diff --quiet HEAD -- "$PKG/src/worldkeeper/model.py" storygame/runtime/engine.py storygame/runtime/state.py 2>/dev/null; true

# 7. Lint and format, repository-wide.
"$PY" -m ruff check . || fail "ruff check ."
"$PY" -m ruff format --check . || fail "ruff format --check . (run: ruff format .)"

# 8. Export the patch outside the worktree.
git add -A && git diff --cached > "$R/out/s1t2-r2.patch"
[ -s "$R/out/s1t2-r2.patch" ] || fail "empty patch"

[ $status -eq 0 ] && echo "PASS: worldkeeper wired into storygame (round 2)"
exit $status
