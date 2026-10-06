"""Offline check: would resolving a bare head word against the player's CURRENT scene help?

usage: bare_name_sim.py <e2e-blind-player.json>

For each recorded, non-rejected command: find bare head words (last word of a thing's name or alias, when the
full form is not in the command) that match things placed in that scene. One match = resolved; several = ambiguous.
A resolved command is rewritten with the full name and re-run through the real matcher against the scene's
reveals (requires ignored). Also prints the head words shared by several things across the whole story
versus inside one scene.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all
from storygame.story_package.loader import _parse_scenes

D = Path("data/stories/continuity-initiative")
world = yaml.safe_load((D / "world.yaml").read_text())
know = yaml.safe_load((D / "knowledge.yaml").read_text())["knowledge"]
scenes = {s.metadata.scene_id: s.metadata for s in _parse_scenes((D / "plot.md").read_text())}
ents = {}
for kind in ("locations", "npcs", "groups", "items"):
    for e in world.get(kind) or []:
        ents[e["id"]] = e


def forms(e):
    return sorted({" ".join(re.findall(r"[\w']+", f.casefold())) for f in [e["name"], *(e.get("aliases") or [])]})


def in_scene(sid):
    m = scenes[sid]
    ids = {m.location_id, *m.item_ids, *m.participant_ids, *m.companions, *m.character_placements}
    return {i for i in ids if i in ents}


def heads(eid):
    return {f.split()[-1] for f in forms(ents[eid]) if f}


STOP = {"the", "a", "of", "to", "my", "her", "his"}
# census
story = defaultdict(set)
for eid in ents:
    for h in heads(eid):
        story[h].add(eid)
print("HEAD WORDS SHARED BY SEVERAL THINGS (whole story -> worst scene)")
for h, ids in sorted(story.items()):
    if len(ids) < 2:
        continue
    per = {sid: sorted(ids & in_scene(sid)) for sid in scenes}
    worst = max(per.items(), key=lambda kv: len(kv[1]))
    print(f"  {h!r}: {sorted(ids)} | most in one scene: {worst[0]} {worst[1]}")

reveals = defaultdict(dict)
for k in know:
    if not k.get("action_evidence"):
        continue
    for sid in k.get("available_in_scenes") or []:
        reveals[sid][k["id"]] = tuple(tuple(g) for g in k["action_evidence"])

run = json.loads(Path(sys.argv[1]).read_text())
tot = res = amb = gain = 0
for rep in run["replicates"]:
    for s in rep["scenes"]:
        sid = s["scene"]
        if sid not in scenes:
            continue
        here = in_scene(sid)
        for t in s["turns"]:
            if t["rejected"]:
                continue
            cmd = t["input"]
            low = " ".join(re.findall(r"[\w']+", cmd.casefold()))
            matched_full = {e for e in here for f in forms(ents[e]) if re.search(rf"(?<!\w){re.escape(f)}(?!\w)", low)}
            rest = low
            for e in ents:  # words already used by a full name, in any scene, are not bare
                for f in forms(ents[e]):
                    rest = re.sub(rf"(?<!\w){re.escape(f)}(?!\w)", " ", rest)
            words = set(rest.split()) - STOP
            cand = defaultdict(set)
            for e in here - matched_full:
                for h in heads(e):
                    if h in words and len(h) > 2:
                        cand[h].add(e)
            if not cand:
                continue
            tot += 1
            before = sorted(k for k, g in reveals[sid].items() if _matches_all(g, cmd))
            note = []
            new_cmd = cmd
            for h, es in cand.items():
                if len(es) == 1:
                    e = next(iter(es))
                    new_cmd = re.sub(rf"\b{re.escape(h)}\b", ents[e]["name"], new_cmd, flags=re.I)
                    note.append(f"{h}->{e}")
                else:
                    note.append(f"{h}=AMBIG{sorted(es)}")
            resolved_all = all(len(es) == 1 for es in cand.values())
            if resolved_all:
                res += 1
            else:
                amb += 1
            after = sorted(k for k, g in reveals[sid].items() if _matches_all(g, new_cmd))
            flag = ""
            if resolved_all and after != before:
                gain += 1
                flag = f"  <-- CHANGE {before} -> {after}"
            print(f"[{sid}] {cmd!r} {' '.join(note)}{flag}")
print(f"commands with a bare head word: {tot}; resolved {res}; ambiguous {amb}; reveal result changed {gain}")
