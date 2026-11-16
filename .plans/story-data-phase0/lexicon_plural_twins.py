from collections import defaultdict
from pathlib import Path

from storygame.story_package.loader import load_story_package

p = load_story_package(Path("data/stories/continuity-initiative"))


def partner(e, group):
    # entry is redundant if the group also holds its singular/plural twin (last word s / no s)
    w = e.split(" ")
    last = w[-1]
    for alt in ((last[:-1],) if last.endswith("s") and len(last) > 3 else ()) + ((last + "s",)):
        if " ".join(w[:-1] + [alt]) in group:
            return True
    return False


tot = defaultdict(int)
red = defaultdict(int)
for k in p.knowledge.knowledge:
    sc = k.available_in_scenes[0]
    for g in k.action_evidence:
        gs = {x.casefold() for x in g}
        for e in gs:
            tot[sc] += 1
            # count only one of each pair: the plural form
            if e.endswith("s") and len(e.split()[-1]) > 3 and partner(e, gs):
                red[sc] += 1
T = sum(tot.values())
R = sum(red.values())
for s in sorted(tot):
    print(s, tot[s], red[s], f"{100 * red[s] / tot[s]:.0f}%")
print("ALL", T, R, f"{100 * R / T:.0f}%")
