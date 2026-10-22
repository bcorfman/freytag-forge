"""Check for the E-R2 delivery task: load the package and verify the new text."""

import sys
from pathlib import Path

from storygame.story_package.loader import load_story_package

NEW = (
    "A partially recovered JANUS file labels the disappearances Phase One. Phase Two was designed to provoke "
    "conflict among those who remained. From an unknown location, Charles watches the unrest, believing "
    "frightened people may yet ask him to restore order."
)
package = load_story_package(Path("data/stories/continuity-initiative"))
item = package.knowledge_indexes.by_id["k_sl_3c_e_r2"]
if item.delivery_text != NEW:
    sys.exit(f"FAIL: k_sl_3c_e_r2 delivery_text is {item.delivery_text!r}")
text = Path("data/stories/continuity-initiative/storylet-routes.yaml").read_text()
flat = " ".join(text.split())
if "Reveal the Phase One label and the Phase Two plan through the partially recovered JANUS file." not in flat:
    sys.exit("FAIL: SL-3C-E-R2 dramatic_intent not replaced")
if "Recognize the Phase Two statement against visible unrest" in flat:
    sys.exit("FAIL: old dramatic_intent still present")
print("ok")
