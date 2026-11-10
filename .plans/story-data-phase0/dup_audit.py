import sys, yaml, json, collections
from pathlib import Path

root = Path(sys.argv[1]) / "data/stories/continuity-initiative"
L = lambda n: yaml.safe_load((root / n).read_text())
routes, know, world, pacing, inc, hand = (
    L(n)
    for n in ("storylet-routes.yaml", "knowledge.yaml", "world.yaml", "pacing.yaml", "incidents.yaml", "handoffs.yaml")
)
print("top keys routes:", list(routes), "know:", list(know), "world:", list(world))
# 1 fact definition copies
rf = {f["id"]: f for f in routes["new_fact_ids"]}
kf = {f["id"]: f for f in know.get("facts", [])}
wf = world.get("facts") or world.get("fact_ids") or []
print("route facts", len(rf), "knowledge facts", len(kf), "world fact entries", len(wf))
same = sum(1 for k in rf if k in kf and rf[k].get("definition") == kf[k].get("purpose"))
print("facts defined in both routes+knowledge:", len(set(rf) & set(kf)), "with identical text:", same)
# 2 route realization op lists duplicated
sl = routes["storylets"]
total_real = dup_real = 0
sig_all = collections.Counter()
for s in sl:
    sigs = collections.Counter()
    for r in s.get("realization_options", []):
        sig = json.dumps(r.get("operations", []), sort_keys=True)
        sigs[sig] += 1
        total_real += 1
    dup_real += sum(c for c in sigs.values() if c > 1)
print("storylets", len(sl), "realizations", total_real, "realizations whose op list equals a sibling's:", dup_real)
# 3 claim effects vs source ops
rl = {(s["id"], r["id"]): r for s in sl for r in s.get("realization_options", [])}
claims = know["knowledge"]
n_src = n_eq = n_sub = 0
for c in claims:
    src = c.get("source", {})
    if src.get("kind") != "storylet_realization":
        continue
    r = rl.get((src["storylet_id"], src["realization_id"]))
    if r is None:
        continue
    n_src += 1
    a = json.dumps(c.get("establishes", []), sort_keys=True)
    ops = r.get("operations", [])
    est = c.get("establishes", [])
    if est == ops:
        n_eq += 1
    elif all(e in ops for e in est):
        n_sub += 1
print("claims sourced from realizations:", n_src, "effects == route ops:", n_eq, "strict subset:", n_sub)
# 4 sibling claims with identical shared fields
fields = [
    "reach_entity_ids",
    "earn_when",
    "action_evidence",
    "entity_ids",
    "audience",
    "available_in_scenes",
    "relevance",
    "leak_terms",
    "must_convey",
]
bysrc = collections.defaultdict(list)
for c in claims:
    s = c.get("source", {})
    if s.get("kind") == "storylet_realization":
        bysrc[s["storylet_id"]].append(c)
pairs = same_fields = 0
for sid, cs in bysrc.items():
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            pairs += 1
            eq = [f for f in fields if cs[i].get(f) == cs[j].get(f) and f in cs[i]]
            same_fields += len(eq)
print(
    "sibling claim pairs:",
    pairs,
    "avg equal shared-fields per pair:",
    round(same_fields / max(pairs, 1), 2),
    "of",
    len(fields),
)
# 5 claims per source scene etc.
print(
    "claims",
    len(claims),
    "with delivery_text",
    sum(1 for c in claims if c.get("delivery_text")),
    "with statement",
    sum(1 for c in claims if c.get("statement")),
)
# 6 incident cross refs per incident
print("incident count", len(inc["incidents"]))
