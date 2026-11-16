#!/usr/bin/env bash
# Ringer check for compiling the delivery token pattern once. Runs in the task worktree.
set -euo pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
PY="$PWD/.venv/bin/python"
export PYTHONPATH="$PWD:$PWD/packages/worldkeeper/src" TMPDIR=/tmp

echo "== 1. equivalence with a reference copy of the old logic, and speed =="
"$PY" -W ignore - <<'PYEOF'
import re, time
from pathlib import Path
from storygame.story_package import loader
from storygame.story_package.loader import _HANDOFF_BOOKKEEPING_LABELS, load_story_package

package = load_story_package(Path("data/stories/continuity-initiative"))

def reference(package, text):
    ids = {
        *(known.id for known in package.knowledge.knowledge),
        *package.fact_ids,
        *(transition.id for transition in package.pacing.transitions),
        *(route.id for route in package.storylet_routes.storylets),
        *(realization.id for route in package.storylet_routes.storylets for realization in route.realizations),
        *(event.id for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events)),
    }
    folded = text.casefold()
    for token in (*ids, *_HANDOFF_BOOKKEEPING_LABELS):
        if token and re.search(rf"(?<![\w-]){re.escape(token.casefold())}(?![\w-])", folded):
            return token
    match = re.search(r"(?<!\w)[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?!\w)", folded)
    return match.group(0) if match else None

assert hasattr(loader, "_delivery_token_matcher"), "_delivery_token_matcher is missing"
matcher = loader._delivery_token_matcher(package)
tokens = sorted({
    *(k.id for k in package.knowledge.knowledge), *package.fact_ids,
    *(t.id for t in package.pacing.transitions), *(r.id for r in package.storylet_routes.storylets),
    *(x.id for r in package.storylet_routes.storylets for x in r.realizations),
    *(e.id for e in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events)),
    *_HANDOFF_BOOKKEEPING_LABELS,
})
tokens = [t for t in tokens if t]
texts = []
for t in tokens:
    texts += [f"She read {t} aloud.", f"See {t}.", f"x{t}", f"{t}x", f"{t}-y", f"y-{t}", f"({t})", t.upper(), f"{t}_more", f"pre_{t}"]
for k in package.knowledge.knowledge:
    if k.delivery_text:
        texts.append(k.delivery_text)
    texts += [v.text for v in k.delivery_variants]
texts += ["Plain prose with no tokens at all.", "snake_case_word here", "Mixed Case_Word", ""]
mismatch = []
for text in texts:
    old = reference(package, text)
    new = loader._delivery_internal_token(matcher, text)
    if (old is None) != (new is None):
        mismatch.append((text[:60], old, new))
print(f"{len(texts)} texts compared, {len(mismatch)} found/not-found mismatches")
assert not mismatch, mismatch[:5]
# the real package's own delivery texts must be clean under both
assert all(reference(package, k.delivery_text) is None for k in package.knowledge.knowledge if k.delivery_text)

best = min((lambda: (lambda t0: (loader._validate_authored_handoffs(package), time.perf_counter() - t0)[1])(time.perf_counter()))() for _ in range(3))
print(f"_validate_authored_handoffs best of 3: {best:.3f}s (was about 0.21s before the fix)")
assert best < 0.08, f"handoff validation still slow: {best:.3f}s"
print("ok")
PYEOF

echo "== 2. only expected files changed =="
changed=$(git status --porcelain --untracked-files=all | sed -E 's/^.{3}//' | grep -vE '^\.venv$' | sort || true)
echo "$changed"
bad=$(echo "$changed" | grep -vE '^(storygame/story_package/loader\.py|tests/test_delivery_token_matcher\.py)$' | grep -v '^$' || true)
if [ -n "$bad" ]; then echo "FAIL: unexpected files changed:"; echo "$bad"; exit 1; fi
test -f tests/test_delivery_token_matcher.py || { echo "FAIL: tests/test_delivery_token_matcher.py missing"; exit 1; }

echo "== 3. focused tests =="
set -o pipefail
"$PY" -m pytest -q -p no:cacheprovider -x tests/test_delivery_token_matcher.py tests/test_markdown_story_package.py tests/test_story_package_cache.py tests/test_loader_pacing_producers.py tests/test_required_storylet_closure.py

echo "== 4. ruff =="
"$PY" -m ruff check storygame tests
"$PY" -m ruff format --check storygame tests

echo "== 5. export patch outside the worktree =="
PATCH=/home/bcorfman/dev/ringer-work/compile-delivery-token-pattern.patch
git add storygame/story_package/loader.py tests/test_delivery_token_matcher.py
git diff --cached HEAD > "$PATCH"
test -s "$PATCH" || { echo "FAIL: exported patch is empty"; exit 1; }
git diff --cached HEAD --stat
echo "patch written to $PATCH"
echo "ALL CHECKS PASSED"
