"""Profile story package loading. Read-only; run with PYTHONPATH=<worktree>."""

import cProfile
import json
import pstats
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import storygame
from storygame.story_package import loader

root = Path(sys.argv[1]).resolve() / "data/stories/continuity-initiative"
assert str(Path(storygame.__file__).resolve()).startswith(str(Path(sys.argv[1]).resolve())), storygame.__file__


def cold():
    loader.load_story_package.cache_clear() if hasattr(loader.load_story_package, "cache_clear") else None
    for name in dir(loader):
        obj = getattr(loader, name)
        if hasattr(obj, "clear") and name.startswith("_") and isinstance(obj, dict) and name.isupper():
            obj.clear()


# Cold uncached loads (bypass cache)
times = []
for _ in range(7):
    t = time.perf_counter()
    loader._load_story_package_uncached(root)
    times.append(time.perf_counter() - t)
print("uncached load s:", [round(x, 3) for x in times], "median", round(statistics.median(times), 3))

# Warm cached load
loader.load_story_package(root)
w = []
for _ in range(50):
    t = time.perf_counter()
    loader.load_story_package(root)
    w.append(time.perf_counter() - t)
print("cached load ms: median", round(statistics.median(w) * 1000, 3), "max", round(max(w) * 1000, 3))

# Fingerprint cost (paid on every cached call)
f = []
for _ in range(50):
    t = time.perf_counter()
    loader._story_package_fingerprint(root)
    f.append(time.perf_counter() - t)
print("fingerprint ms: median", round(statistics.median(f) * 1000, 3))

# Memory of one package
tracemalloc.start()
pkg = loader._load_story_package_uncached(root)
cur, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print("tracemalloc current MiB", round(cur / 2**20, 1), "peak MiB", round(peak / 2**20, 1))

# Profile
pr = cProfile.Profile()
pr.enable()
loader._load_story_package_uncached(root)
pr.disable()
ps = pstats.Stats(pr)
ps.sort_stats("cumulative")
import io

buf = io.StringIO()
ps.stream = buf
ps.print_stats(28)
print(buf.getvalue()[:6000])
