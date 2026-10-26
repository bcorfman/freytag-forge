"""Offline diagnosis: who may say what aloud in the drawer scene (no network, no model)."""
import os
os.environ["CLOUDFLARE_WORKER_URL"] = "https://w.example"
from pathlib import Path
from storygame.runtime.capture import build_capture_provider
from storygame.story_package.loader import load_story_package
from storygame.runtime.state import RuntimeState

pkg = load_story_package(Path("data/stories/continuity-initiative"))
state = RuntimeState.bootstrap(pkg)
prov = build_capture_provider(state)
scene = prov._current_scene()
print("scene", scene.scene_id, "participants", scene.participant_ids)
npcs = {n.id for n in pkg.world.npcs}
for sid in scene.participant_ids:
    if sid in npcs:
        print("npc", sid, "present?", prov._is_present(sid))
print("speaker contexts now:", {k: [i["id"] for i in v["sayable_knowledge"]] for k, v in prov._speaker_contexts("inspect the drawer").items()})
prose = " ".join(b.prose for b in prov._scene().beats.values())
print("beat prose:", prose[:900])
# mark the card knowledge as established by the real effect and re-ask
kd = pkg.knowledge_indexes.by_id["k_sl_1a_b_r0"]
print("k_sl_1a_b_r0 audience:", kd.audience, "establishes:", kd.establishes, "scenes:", kd.available_in_scenes, "source:", kd.source)

import re
from storygame.runtime import cloudflare as cf
ent = next(i for i in pkg.world.npcs if i.id == "michelle")
aliases = (ent.name, *ent.aliases)
print("aliases:", aliases)
for sentence in re.split(r"(?<=[.!?])\s+", prose):
    folded = sentence.casefold()
    if not any(re.search(rf"\b{re.escape(a.casefold())}\b", folded) for a in aliases):
        continue
    words = set(re.findall(r"[a-z]+", folded))
    if words & cf._ABSENCE_OR_EVIDENCE:
        print("SKIP (absence/evidence):", sentence[:110]); continue
    ap = "|".join(sorted(cf._PRESENCE_ACTIONS, key=len, reverse=True))
    hit = [a for a in aliases if re.search(rf"\b{re.escape(a.casefold())}(?!['’]s)\b(?:\s+\w+){{0,2}}\s+(?:{ap})\b", folded)]
    print("MATCH" if hit else "no match", hit, "|", sentence[:140])

from storygame.runtime.world_model import world_for
w = world_for(pkg, state.facts)
for who in ("kristin", "michelle", "patrol_officer"):
    print(who, "area:", w.area(who) if w.resolve(who) or True else None, "parent:", w.parent(who))
