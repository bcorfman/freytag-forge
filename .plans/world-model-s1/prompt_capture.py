"""Capture the shipped narrator's 1A payloads (no network). Usage: prompt_capture.py OUT.json [custody_fact]

After setting the custody fact it applies world effects, as every runtime commit point does.
"""

import json
import sys
from pathlib import Path

import storygame.runtime.cloudflare as cf
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects
from storygame.story_package.loader import load_story_package

out, custody = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "memory_card_recovered")
captured = []


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
    captured.append(json.loads(request.data))
    return _Response({"narration": '{"segments":[{"kind":"narration","text":"Fixture."}]}'})


cf.urlopen = fake_urlopen
package = load_story_package(Path("data/stories/continuity-initiative"))
result = {}
for label, set_custody in (("plain", False), ("custody", True)):
    state = RuntimeState.bootstrap(package)
    if set_custody:
        state.facts.assert_fact(Fact(predicate=custody, subject="story", value="true"))
        apply_world_effects(package, state.facts)
    provider = cf.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    captured.clear()
    provider.opening()
    provider("Search the kitchen for signs of a struggle.")
    result[label] = [{"system": p.get("system"), "user": p.get("user")} for p in captured]
Path(out).write_text(json.dumps(result, indent=1, sort_keys=True))
print("captured", {k: len(v) for k, v in result.items()})
