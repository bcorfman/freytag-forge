"""Render the narrator prompt the engine would send for a 2C turn-1 command (offline, no network).

usage: 2c_files_render.py OUT.json
State: scene 2C entered, janus_evidence earned, the copy step not yet taken, purge clock not started. The commands are
the first or second commands typed by the two blind players that left 2C by timer on 80f5c64c.
"""

import json
import sys
from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

COMMANDS = {
    "search": "Search the command levels for Michelle.",
    "medical": "Retrieve Michelle's current location from the medical terminal.",
    "orders": "Read the transfer orders.",
}
PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def render(command: str) -> dict[str, str]:
    import storygame.runtime.cloudflare as cloudflare

    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2C"
    state.phase = next(s.metadata.freytag_phase for s in PACKAGE.scenes if s.metadata.scene_id == "2C")
    state._assert_scene_entry_fact("2C")
    state.facts.assert_fact(Fact(predicate="janus_evidence", subject="story", value="true"))
    narration = {"segments": [{"kind": "narration", "text": "Kristin looks around the command levels."}]}
    original = cloudflare.urlopen
    cloudflare.urlopen = lambda *_a, **_k: _Response({"narration": json.dumps(narration)})
    try:
        provider = cloudflare.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
        RuntimeEngine(state, provider).turn(command)
    finally:
        cloudflare.urlopen = original
    assert provider.last_prompt is not None
    return dict(provider.last_prompt)


if __name__ == "__main__":
    out = {name: render(command) | {"command": command} for name, command in COMMANDS.items()}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
    for name, prompt in out.items():
        print("=====", name)
        print(prompt["user"])
