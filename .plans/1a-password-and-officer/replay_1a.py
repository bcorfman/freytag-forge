"""Network-free replay of the 1A transcript (Brandon, 2026-11-08). Each narrator reply is stubbed with the text he saw;
the script prints the full user prompt the narrator received each turn, the world state before/after, and the
composed result (stub reply plus any appended authored cue). No model is called.
Run: TMPDIR=/tmp .venv/bin/python .plans/1a-password-and-officer/replay_1a.py"""

import json
import sys
from pathlib import Path

import storygame.runtime.cloudflare as cf
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

SCRIPT = [
    ("turn on the phone", "She presses the power button, and the screen flickers to life."),
    ("unlock the phone", "The screen flickers to life, and a password prompt appears."),
    ("type in the password", "She types in the password, and the laptop screen flickers to life."),
    ("type the password into michelle's phone", "She types in the password, and the phone screen flickers to life."),
    ("turn off the phone and put it in my pocket", "She turns off Michelle's phone and puts it in her pocket."),
    ("officer, hello", "Hello, officer. I'm Kristin Schweitzer."),
    ("officer, do you know where Dr. McGehee is?", "No, I don't know where Dr. McGehee is, Mrs. Jenkins says."),
]
captured = []
CLOCK = [0]
replies = {}


class _Response:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_urlopen(request, timeout):
    payload = json.loads(request.data)
    captured.append(payload)
    text = "Fixture."
    for command, reply in replies.items():
        if command in (payload.get("user") or ""):
            text = reply
    return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": text}]})})


cf.urlopen = fake_urlopen
package = load_story_package(Path("data/stories/continuity-initiative"))
state = RuntimeState.bootstrap(package)
provider = cf.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
engine = RuntimeEngine(state, provider)
engine.opening()
from storygame.runtime.world_model import world_for


def diag(label):
    world = world_for(package, state.facts)
    asserted = sorted((f.predicate, f.subject, f.value) for f in state.facts.asserted if "patrol" in f.predicate or "officer" in f.predicate or "walt" in f.subject or "reyes" in f.subject)
    print(f"  [{label}] officer parent={world.parent('patrol_officer')!r} walt parent={world.parent('walt_pruitt')!r} kristin parent={world.parent('kristin')!r} together(kristin,officer)={world.together('kristin','patrol_officer')} present(officer)={provider._is_present('patrol_officer')}")
    print(f"  [{label}] patrol facts={asserted}")
    print(f"  [{label}] scene participants={[c for c in provider._current_scene().participant_ids]}")


for command, reply in SCRIPT:
    replies = {command: reply}
    print("#" * 100)
    diag("before " + command)
    captured.clear()
    result = engine.turn(command, clock_seconds=CLOCK[0])
    CLOCK[0] += 40
    print("=" * 100)
    print("COMMAND:", command, "->", type(result).__name__)
    print("reference:", engine.last_reference_resolution)
    for payload in captured:
        user = payload.get("user") or ""
        print("--- request (full user prompt) ---")
        print(user)
    diag("after " + command)
    print("scene:", state.current_scene_id, "turn_index:", state.turn_index)
    rec = state.turn_records[-1] if state.turn_records else None
    print("last record text:", getattr(rec, "narration", None) or getattr(rec, "text", None))
    print("patrol facts:", [(f.predicate, f.subject, f.value) for f in state.facts.facts() if "patrol" in f.predicate or "officer" in f.predicate] if hasattr(state.facts, "facts") else "n/a")
    print("result:", result)
sys.exit(0)
