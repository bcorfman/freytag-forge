"""Read-only prototype: render one storylet as an author-readable block from the
CURRENT sources. Nothing here is a source of truth; it shows what a reading view
could derive. Usage: render_reveal.py <repo> <storylet-id>..."""

import re
import subprocess
import sys
from pathlib import Path

import yaml

repo = Path(sys.argv[1])
root = repo / "data/stories/continuity-initiative"
Y = lambda n: yaml.safe_load((root / n).read_text())
routes, know, pac, inc, world = (
    Y("storylet-routes.yaml"),
    Y("knowledge.yaml"),
    Y("pacing.yaml"),
    Y("incidents.yaml"),
    Y("world.yaml"),
)
facts = {f["id"]: f["purpose"] for f in know["facts"]}
claims = know["knowledge"]
tests = sorted((repo / "tests").glob("test_*.py"))
test_text = {t.name: t.read_text() for t in tests}


def cond(cs):
    return " and ".join(f"{c['fact_id']} is {str(c['equals']).lower()}" for c in cs) or "always"


def ops(os_):
    return ", ".join(f"{o['fact_id']}={str(o['value']).lower()}" for o in os_)


def consumers(fact_id):
    out = []
    for e in pac["events"]:
        if any(c.get("fact_id") == fact_id for c in e.get("when", [])):
            out.append(f"pacing event {e['id']} (scene {e['scene_id']}) waits on it")
        for r in e.get("realizations", []):
            if any(c.get("fact_id") == fact_id for c in r.get("when", [])):
                out.append(f"pacing event {e['id']} (scene {e['scene_id']}) picks a passage by it")
        if any(x.get("fact_id") == fact_id for x in e.get("effects", [])):
            out.append(f"pacing event {e['id']} produces it")
    for t in pac["transitions"]:
        if any(c.get("fact_id") == fact_id for c in t["triggers"]):
            out.append(f"transition {t['id']} requires it")
    for s in routes["storylets"]:
        if any(c.get("fact_id") == fact_id for c in s["activation"].get("conditions", [])):
            out.append(f"storylet {s['id']} activation depends on it")
    for c in claims:
        if any(r.get("fact_id") == fact_id for r in c.get("requires", [])):
            out.append(f"claim {c['id']} requires it")
    return out


def tests_for(*needles):
    return sorted(n for n, t in test_text.items() if any(x in t for x in needles))


def render(sid):
    s = next(x for x in routes["storylets"] if x["id"] == sid)
    a = s["activation"]["pacing"]
    lines = [f"### Scene {s['scene_id']} / {s['title']} [{sid}]", ""]
    lines += [
        f"- Purpose: {s['pressure_role']}",
        f"- Available: {cond(s['activation'].get('conditions', []))}",
        f"- Window: earliest {a['earliest_turn']}, target {a['target_turn']}, latest {a['latest_turn']}",
        f"- Completes when: {cond(s['completion_or_abort']['complete_when'])}; abandoned if the scene is left",
        "",
    ]
    produced = set()
    for r in s["realization_options"]:
        cs = [c for c in claims if c.get("source", {}).get("realization_id") == r["id"]]
        lines += [f"#### Variant {r['id']}: {r['dramatic_intent']}", f"- Commits: {ops(r['operations'])}"]
        produced |= {o["fact_id"] for o in r["operations"]}
        for c in cs:
            when = cond(c.get("requires", []))
            same = (
                "all of the route's commits"
                if c.get("establishes") == r["operations"]
                else "SOME of the route's commits: " + ops(c["establishes"])
            )
            lines += [
                f"- Claim {c['id']}: when {when}; establishes {same}; voiceable={c.get('voiceable', True)}",
                f"  - Statement: {c['statement']}",
            ]
            if c.get("earn_when"):
                lines.append(f"  - Earned by: {c['earn_when']} (reach: {', '.join(c.get('reach_entity_ids', []))})")
            if c.get("delivery_text"):
                lines.append(f"  - Delivery: {c['delivery_text']}")
        lines.append("")
    lines += ["#### Facts and who uses them"]
    for f in sorted(produced):
        lines.append(f"- {f}: {facts.get(f, '(no purpose recorded)')}")
        for c in consumers(f):
            lines.append(f"  - {c}")
        t = tests_for(f)
        lines.append(
            f"  - tests naming it: {len(t)} files"
            + (f" ({', '.join(t[:6])}{'...' if len(t) > 6 else ''})" if t else "")
        )
    for i in inc["incidents"]:
        if i["scene_id"] == s["scene_id"] and (
            i["recovery_storylet_id"] == sid or any(o["storylet_id"] == sid for o in i["outcomes"])
        ):
            lines += [
                "",
                "#### Incident",
                f"- {i['id']}: outcomes "
                + "; ".join(
                    f"{o['id']} (+{', '.join(o['advantages'])}"
                    + (f" / cost {', '.join(o['costs'])}" if o["costs"] else "")
                    + ")"
                    for o in i["outcomes"]
                ),
                f"- Recovery storylet: {i['recovery_storylet_id']}; missed-window event: {i['missed_window_event_id']}; next scene transition: {i.get('successor_transition_id')}",
            ]
    return "\n".join(lines)


for sid in sys.argv[2:]:
    print(render(sid))
    print()
