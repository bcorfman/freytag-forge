import re
from collections import Counter, defaultdict
from pathlib import Path

from storygame.runtime.candidate_matcher import _SYNONYM_CLASSES
from storygame.story_package.loader import load_story_package

p = load_story_package(Path("data/stories/continuity-initiative"))
w = p.world
names = set()
for coll in (w.locations, w.npcs, w.items, w.groups):
    for e in coll:
        for n in (e.name, *e.aliases, *e.scoped_aliases):
            names.add(n.casefold())
for c in p.characters:
    names.add(c.name.casefold())
tokens = {t for n in names for t in re.findall(r"[a-z0-9]+", n) if len(t) >= 3} - {
    "the",
    "and",
    "his",
    "her",
    "kristin",
    "michelle",
}
cls = set().union(*_SYNONYM_CLASSES)


def kind(x):
    e = x.casefold()
    if e in names or (e.endswith("'s") and e[:-2] in names):
        return "entity"
    if e in cls:
        return "class_word"
    if any(n in e for n in names if len(n) > 3):
        return "entity"
    if e in tokens or e.rstrip("s") in tokens:
        return "name_token"
    return "bespoke"


scenes = sorted({s for k in p.knowledge.knowledge for s in k.available_in_scenes})


def stats(ks):
    occ = defaultdict(list)
    for k in ks:
        for f in ("action_evidence", "must_convey", "leak_terms"):
            v = getattr(k, f)
            if not v:
                continue
            es = list(v) if f == "leak_terms" else [x for g in v for x in g]
            for x in es:
                occ[x.casefold()].append((k.id, f))
        for a in k.aliases:
            occ[a.casefold()].append((k.id, "aliases"))
    total = sum(map(len, occ.values()))
    rep = {x: v for x, v in occ.items() if len({c for c, _ in v}) >= 2 or len({f for _, f in v}) >= 2}
    cov = sum(map(len, rep.values()))
    kinds = Counter()
    bespoke_rep = 0
    for x, v in occ.items():
        for _ in v:
            kinds[kind(x)] += 1
        if kind(x) == "bespoke" and x in rep:
            bespoke_rep += len(v)
    return total, len(occ), len(rep), cov, kinds, bespoke_rep


print(
    f"{'scene':6}{'claims':>7}{'occ':>6}{'dist':>6}{'rep_phr':>8}{'rep_occ%':>9}{'bespoke%':>9}{'bespoke_in_rep%':>16}"
)
rows = []
for s in scenes:
    ks = [k for k in p.knowledge.knowledge if s in k.available_in_scenes and len(k.available_in_scenes) == 1]
    if not ks:
        continue
    t, d, r, c, kd, br = stats(ks)
    if t == 0:
        continue
    rep_pct = 100 * c / t
    bespoke_pct = 100 * kd["bespoke"] / t
    bespoke_rep_pct = 100 * br / max(kd["bespoke"], 1)
    print(f"{s:6}{len(ks):>7}{t:>6}{d:>6}{r:>8}{rep_pct:>8.0f}%{bespoke_pct:>8.0f}%{bespoke_rep_pct:>15.0f}%")
t, d, r, c, kd, br = stats(p.knowledge.knowledge)
print(
    "ALL",
    len(p.knowledge.knowledge),
    t,
    d,
    r,
    f"{100 * c / t:.0f}%",
    {k: f"{100 * v / t:.0f}%" for k, v in kd.items()},
    f"bespoke_in_rep {100 * br / max(kd['bespoke'], 1):.0f}%",
)
multi = sum(1 for k in p.knowledge.knowledge if len(k.available_in_scenes) > 1)
print("claims spanning >1 scene (excluded from per-scene rows):", multi)
