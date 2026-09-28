"""Capture the shipped narrator's payloads for chosen scenes, with the network stubbed.

Usage, from the repository root:
    uv run python .plans/world-model-scenes/capture_scenes.py OUT.json \
        1A:"Search the kitchen for signs of a struggle." 1B:"Look around the bench for anything Michelle left."

Each argument is SCENE:COMMAND. For each scene it bootstraps the package, enters the scene
(applying its placements), and records the opening and one turn. Capture before and after a
package change and diff the two files: any difference is a change the player would see.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
import storygame.runtime.cloudflare as cf  # noqa: E402
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.runtime.world_model import apply_scene_placements  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402

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
first_scene = package.scenes[0].metadata.scene_id
result = {}
for argument in sys.argv[2:]:
    scene_id, command = argument.split(":", 1)
    state = RuntimeState.bootstrap(package)
    if scene_id != first_scene:
        state.current_scene_id = scene_id
        apply_scene_placements(package, state.facts, scene_id)
    provider = cf.CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    captured.clear()
    provider.opening()
    provider(command)
    result[scene_id] = [{"system": p.get("system"), "user": p.get("user")} for p in captured]
Path(sys.argv[1]).write_text(json.dumps(result, indent=1, sort_keys=True))
print("captured", {k: len(v) for k, v in result.items()})
