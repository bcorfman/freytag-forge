import re, sys, yaml, collections
from pathlib import Path

repo = Path(sys.argv[1])
root = repo / "data/stories/continuity-initiative"
Y = lambda n: yaml.safe_load((root / n).read_text())
know, pac, hand = Y("knowledge.yaml"), Y("pacing.yaml"), Y("handoffs.yaml")
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()
passages = {}
for c in know["knowledge"]:
    for f in ("delivery_text", "statement"):
        if c.get(f):
            passages[f"claim {c['id']} {f}"] = c[f]
for e in pac["events"]:
    for i, r in enumerate(e.get("realizations", [])):
        passages[f"pacing {e['id']}[{i}]"] = r["text"]
sent = {}
for k, t in passages.items():
    for s in re.split(r"(?<=[.!?])\s+", norm(t)):
        if len(s) >= 45:
            sent.setdefault(s, k)
tests = {p.name: norm(p.read_text()) for p in (repo / "tests").glob("test_*.py")}
hits = collections.defaultdict(set)
files = collections.defaultdict(set)
for s, k in sent.items():
    for n, t in tests.items():
        if s in t:
            hits[n].add(s)
            files[k].add(n)
print("authored sentences >=45 chars:", len(sent), "passages:", len(passages))
print("tests copying >=1 sentence verbatim:", len(hits), "of", len(tests))
print("distinct sentences copied into tests:", len({s for v in hits.values() for s in v}))
print("passages with a sentence copied into a test:", len(files))
for n, v in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:8]:
    print(" ", n, len(v))
