"""Free replay: which first command earns the 1A door clue or the drawer cue.

Stub narrator, no network. Run from the repo root:
TMPDIR=/tmp uv run python .plans/1a-password-and-officer/replay_first_commands.py
"""

import json
from pathlib import Path

import storygame.runtime.cloudflare as cf
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package


class R:
    def __init__(s, b):
        s.b = json.dumps(b).encode()

    def read(s):
        return s.b

    def __enter__(s):
        return s

    def __exit__(s, *a):
        return False


cf.urlopen = lambda request, **kw: R({"narration": '{"segments":[{"kind":"narration","text":"[stub]"}]}'})
pkg = load_story_package(Path("data/stories/continuity-initiative"))
for cmd in [
    "Look around.",
    "Examine the room.",
    "Search the kitchen.",
    "Look in the kitchen.",
    "Inspect the back door.",
    "Search the house for Michelle.",
    "Call out for Michelle.",
    "Examine the workstation.",
]:
    state = RuntimeState.bootstrap(pkg)
    eng = RuntimeEngine(state, cf.CloudflareTurnProvider(worker_url="https://w/turn", token="", state=state))
    p = eng.turn(cmd)
    texts = [s.text for s in p.segments]
    door = any("splinter" in t for t in texts)
    cue = any("KMS" in t for t in texts)
    print(f"{cmd!r:40} door-clue={door!s:5} drawer-cue={cue!s:5} extra={len(texts) - 1}")
