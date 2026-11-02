"""Product-wired, network-free replay of the 1A opening and a command route (plan step 1).

Usage: capture.py OUT.json [--boards yes|no] [--cmd "..."]...
WorldCapture is attached (the product wiring in web_demo.engine_for). The model questions (Jev) are
answered by a scripted ask, so state/prompt wiring is diagnosed; live writing quality is not.
--boards yes: boards_vehicle answers yes for any command naming the vehicle; no: answers no.
"""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("FREYTAG_SEMANTIC_REVEAL", "0")
os.environ.setdefault("FREYTAG_WORLD_CAPTURE", "1")
os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")

import storygame.runtime.cloudflare as cf
from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

RAW = (
    "open the drawer",
    "feel in the gap",
    "head out to the truck",
    "look for the laptop",
    "get in the truck",
    "plug the memory card into the laptop",
)
TRACKED = ("kristin", "kristin_laptop", "memory_card", "kristin_truck", "truck_driver_seat")
captured: list[dict] = []


class _Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(request, timeout=None, **_kw):
    captured.append(json.loads(request.data))
    return _Response(
        {"narration": '{"segments":[{"kind":"narration","text":"[narration]"}],"selected_knowledge_ids":[]}'}
    )


def make_ask(boards: bool, asked: list):
    def ask(state, questions):
        command = (state or {}).get("command", "") if isinstance(state, dict) else ""
        out = {}
        for key in questions:
            yes = False
            if key == "boards_vehicle":
                yes = boards and "truck" in command.lower()
            elif key == "only_boards_vehicle":
                yes = not any(w in command.lower() for w in ("drive", "look", "plug", "search"))
            elif key == "uses_thing":
                yes = any(w in command.lower() for w in ("plug", "read", "open the laptop"))
            out[key] = {"noul": 1.0 if yes else 0.0}
        asked.append({"command": command, "answers": {k: v["noul"] for k, v in out.items()}})
        return out

    return ask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--boards", choices=("yes", "no"), default="yes")
    ap.add_argument("--cmd", action="append")
    args = ap.parse_args()
    cf.urlopen = fake_urlopen
    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    provider = build_capture_provider(state)
    asked: list = []
    ask = make_ask(args.boards == "yes", asked)
    provider.semantic_ask = ask
    capture = WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True)
    engine = RuntimeEngine(state, provider, capture=capture)

    def places():
        world = world_for(state.package, state.facts)
        return {n: world.parent(n) for n in TRACKED}

    captured.clear()
    opening = engine.opening()
    record = {
        "opening": {
            "narration": opening.narration,
            "places": places(),
            "prompts": [{"system": p.get("system"), "user": p.get("user")} for p in captured],
        },
        "turns": [],
    }
    for command in args.cmd or RAW:
        captured.clear()
        asked.clear()
        before = places()
        result = engine.turn(command)
        record["turns"].append(
            {
                "input": command,
                "before": before,
                "after": places(),
                "scene": state.current_scene_id,
                "asked": list(asked),
                "narration": result.narration,
                "prompts": [{"system": p.get("system"), "user": p.get("user")} for p in captured],
            }
        )
    Path(args.out).write_text(json.dumps(record, indent=1, sort_keys=True, default=str))
    for t in record["turns"]:
        print(t["input"], "|", t["after"]["kristin"], "|", t["after"]["kristin_laptop"], "|", t["narration"][:100])


main()
