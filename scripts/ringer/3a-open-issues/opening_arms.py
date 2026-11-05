"""Opening-only probe for one arm: one narration request per sample.

Usage: opening_arms.py VARIATION N OUT.json
Records each narration and the exact prompt sent, so the arms can be checked to differ as intended.
Sources .env itself (run it inside Ringer); one request per sample, no retries, failures kept.
"""

from bench.core import load_dotenv

load_dotenv()
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from bench.core import load_variation, seeded_state_for_scene  # noqa: E402
from storygame.runtime.capture import build_capture_provider  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

variation = load_variation(Path(sys.argv[1]))
count = int(sys.argv[2])
rows = []
for i in range(count):
    package, state = seeded_state_for_scene(variation, "3A")
    provider = build_capture_provider(state, mark_fixed=False)
    engine = RuntimeEngine(state, provider, capture=None, refusal_mode="off")
    row = {"i": i, "narration": None, "error": None, "prompt": None}
    try:
        row["narration"] = engine.opening().narration
    except Exception as exc:  # keep every failure; never replace a sample
        row["error"] = repr(exc)
    row["prompt"] = getattr(provider, "last_prompt", None)
    rows.append(row)
    print(i, "error" if row["error"] else "ok", flush=True)
    Path(sys.argv[3]).write_text(json.dumps(rows, indent=1))
