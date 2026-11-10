import statistics, sys, time
from pathlib import Path
import storygame
from storygame.story_package import loader
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for

wt = Path(sys.argv[1]).resolve()
assert str(Path(storygame.__file__).resolve()).startswith(str(wt))
pkg = loader.load_story_package(wt / "data/stories/continuity-initiative")
proj = KnowledgeProjector()
inputs = ["", "Look around", "Search under the drawer", "Ask the officer about the card"]
rows = []
for scene in pkg.scenes:
    st = RuntimeState(package=pkg, current_scene_id=scene.metadata.scene_id, phase=scene.metadata.freytag_phase)
    st._assert_scene_entry_fact(scene.metadata.scene_id)
    per = {}
    for inp in inputs:
        ts = []
        for _ in range(15):
            t = time.perf_counter()
            proj.project(st, "player", inp)
            ts.append(time.perf_counter() - t)
        per[inp] = statistics.median(ts) * 1000
    ts = []
    for _ in range(15):
        t = time.perf_counter()
        world_for(pkg, st.facts)
        ts.append(time.perf_counter() - t)
    rows.append((scene.metadata.scene_id, per, statistics.median(ts) * 1000))
print("scene | project ms by input (empty, look, search, ask) | world_for ms")
for sid, per, w in rows:
    print(sid, [round(v, 2) for v in per.values()], round(w, 2))
allp = [v for _, per, _ in rows for v in per.values()]
print("project ms: median", round(statistics.median(allp), 2), "max", round(max(allp), 2))
print("scenes", len(pkg.scenes), "claims", len(pkg.knowledge.knowledge), "storylets", len(pkg.storylets))
