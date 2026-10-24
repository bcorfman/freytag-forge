"""Replay the reported 1A transcript with the network stubbed. Usage: baseline_replay.py OUT.json

Records, per turn: pre/post parents, custody, fired events, reference match, engine steps, prompts and the
composed narration. The stub narrator always answers "The scene continues.", so the prose here is the
engine's own output; model behavior needs a billed Ringer run.
"""

import json
import os
import sys
from pathlib import Path

os.environ["FREYTAG_SEMANTIC_REVEAL"] = "0"

import storygame.runtime.cloudflare as cf
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

INPUTS = (
    "go in the house",
    "feel in the gap",
    "look at the fabric",
    "pull out the drawer",
    "feel under the drawer",
    "go out to the truck",
    "get in",
    "look around",
)
TRACKED = ("kristin", "kristin_laptop", "memory_card", "michelle_drawer", "kristin_truck")


class _Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


captured: list[dict] = []


def fake_urlopen(request, timeout=None, **_kwargs):
    captured.append(json.loads(request.data))
    text = '{"segments":[{"kind":"narration","text":"The scene continues."}],"selected_knowledge_ids":[]}'
    return _Response({"narration": text})


def places(state):
    world = world_for(state.package, state.facts)
    return {name: world.parent(name) for name in TRACKED}


def main(out: str) -> None:
    cf.urlopen = fake_urlopen
    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    provider = cf.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    engine = RuntimeEngine(state, provider)
    record = {"package": str(package.root) if hasattr(package, "root") else "", "turns": []}
    captured.clear()
    opening = engine.opening()
    record["opening"] = {
        "narration": opening.narration,
        "places": places(state),
        "prompts": [{"system": p.get("system"), "user": p.get("user")} for p in captured],
    }
    for command in INPUTS:
        captured.clear()
        before = places(state)
        fired_before = set(state.fired_event_ids)
        result = engine.turn(command)
        reference = engine.last_reference_resolution
        record["turns"].append(
            {
                "input": command,
                "before": before,
                "after": places(state),
                "scene": state.current_scene_id,
                "turn_index": state.turn_index,
                "fired": sorted(set(state.fired_event_ids) - fired_before),
                "selected_knowledge_ids": list(result.selected_knowledge_ids),
                "reference": repr(reference) if reference is not None else None,
                "narration": result.narration,
                "prompts": [{"system": p.get("system"), "user": p.get("user")} for p in captured],
            }
        )
    Path(out).write_text(json.dumps(record, indent=1, sort_keys=True, default=str))
    for turn in record["turns"]:
        print(turn["input"], "|", turn["after"]["kristin"], "|", turn["after"]["memory_card"], "|", turn["narration"][:140])


if __name__ == "__main__":
    main(sys.argv[1])
