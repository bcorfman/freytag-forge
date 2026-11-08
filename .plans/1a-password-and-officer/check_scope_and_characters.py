import json
from pathlib import Path
import storygame.runtime.cloudflare as cf
from storygame.runtime.state import RuntimeState
from storygame.runtime.reference_resolution import _scene_things, resolve_references
from storygame.story_package.loader import load_story_package

package = load_story_package(Path("data/stories/continuity-initiative"))
state = RuntimeState.bootstrap(package)
provider = cf.CloudflareTurnProvider(worker_url="x", token="", state=state)
print("package.characters:", [c.id for c in package.characters])
print("in-scope things for 1A resolver:", [(t.entity_id, t.heads) for t in _scene_things(state)])
payload = provider.assemble_turn_prompt("officer, do you know where Dr. McGehee is?")
text = json.dumps(payload, default=str)
print("'Jenkins' anywhere in assembled turn prompt payload:", "Jenkins" in text)
sysp = provider._system_prompt() if hasattr(provider, "_system_prompt") else ""
print("'Jenkins' in system prompt:", "Jenkins" in str(sysp))
for cmd in ("type in the password", "type in the laptop password", "unlock the laptop"):
    r = resolve_references(state, cmd)
    print(cmd, "->", r.outcome, r.resolutions, r.question)
