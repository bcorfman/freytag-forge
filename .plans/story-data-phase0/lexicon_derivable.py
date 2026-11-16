import re
from collections import Counter
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


def kind(entry):
    e = entry.casefold()
    if e in names:
        return "entity_name"
    if e in cls:
        return "class_word"
    # possessive of entity
    if e.endswith("'s") and e[:-2] in names:
        return "entity_name"
    if any(n in e for n in names if len(n) > 3):
        return "contains_entity"
    if e in tokens or e.rstrip("s") in tokens:
        return "name_token"
    return "bespoke"


ks = [k for k in p.knowledge.knowledge if "1A" in k.available_in_scenes]
for field in ("action_evidence", "must_convey", "leak_terms"):
    c = Counter()
    bespoke = []
    for k in ks:
        v = getattr(k, field)
        if not v:
            continue
        entries = [x for g in v for x in g] if field != "leak_terms" else list(v)
        for x in entries:
            kd = kind(x)
            c[kd] += 1
            if kd == "bespoke":
                bespoke.append(x)
    tot = sum(c.values())
    print(field, tot, dict(c))
    print("  bespoke sample:", sorted(set(bespoke))[:40])
# duplication: distinct lists reused across claims
for field in ("action_evidence", "must_convey"):
    seen = Counter(repr(getattr(k, field)) for k in ks if getattr(k, field))
    print(field, "claims with list", sum(seen.values()), "distinct", len(seen))
