# ruff: noqa: E501
"""Network-free trace of the 1A patrol timeline at the narrator request boundary (2026-11-08).
Prints, for each command, turn_index/turns_since_entry, the patrol facts and the officer's parent at the moment the
narrator request is built (inside the provider), plus fired pacing events and the composed delivery text.
Two scripts: canonical (frozen-arm commands) and the transcript's raw seven turns.
Run: TMPDIR=/tmp PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python .plans/1a-password-and-officer/trace_timing.py"""

import json
from pathlib import Path

import storygame.runtime.cloudflare as cf
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

SCRIPTS = {
    "canonical": [
        "Turn on the phone.",
        "Unlock the phone.",
        "Type in the password.",
        "Type the password into Michelle's phone.",
        "Turn off the phone.",
        "Greet the officer.",
        "Ask the officer where Dr. McGehee is.",
        "Look at the wall calendar.",
        "Look at the photograph.",
    ],
    "raw": [
        "turn on the phone",
        "unlock the phone",
        "type in the password",
        "type the password into michelle's phone",
        "turn off the phone and put it in my pocket",
        "officer, hello",
        "officer, do you know where Dr. McGehee is?",
    ],
}


class _Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def run(label, commands):
    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    seen = {}

    def urlopen(request, timeout):
        payload = json.loads(request.data)
        world = world_for(package, state.facts)
        facts = {
            f.predicate: f.value
            for f in state.facts.asserted
            if f.subject == "story" and ("patrol" in f.predicate or f.predicate == "officer_demanded_card")
        }
        seen.update(
            turn_index=state.turn_index,
            since_entry=state.turn_index - state.scene_entered_at_turn,
            officer_parent=world.parent("patrol_officer"),
            facts=facts,
            fired=sorted(i for i in state.fired_event_ids if "patrol" in i or "officer" in i),
            officer_lines=[
                ln for ln in (payload.get("user") or "").split("\n") if "patrol officer" in ln.lower() and "Place" in ln
            ],
            place_text=world.place_text("patrol_officer"),
            place_label=world.place_label("patrol_officer"),
        )
        return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": "Kristin looks."}]})})

    cf.urlopen = urlopen
    provider = cf.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    engine = RuntimeEngine(state, provider)
    engine.opening()
    print(f"##### {label}: scene {state.current_scene_id}, entered_at_turn={state.scene_entered_at_turn}")
    clock = 0
    for number, command in enumerate(commands, start=1):
        seen.clear()
        result = engine.turn(command, clock_seconds=clock)
        clock += 40
        text = " ".join(getattr(s, "text", "") for s in getattr(result, "segments", ()))
        print(f"{number}. {command!r} -> {type(result).__name__}")
        print(f"   AT REQUEST: {dict(seen)}")
        print(
            f"   AFTER: turn_index={state.turn_index} officer_parent={world_for(package, state.facts).parent('patrol_officer')!r}"
        )
        print(f"   composed: {text[:230]!r}")


for name, commands in SCRIPTS.items():
    run(name, commands)
