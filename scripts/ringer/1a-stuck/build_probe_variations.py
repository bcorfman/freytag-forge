# ruff: noqa: E501  (probe commands and replacement strings are long literals)
"""Write the 1A stuck-turn probe variations (control and hold-on-foot arms, one file per script). No model call, nothing billed.

Usage: build_probe_variations.py   (writes bench/variations/probe-1a-{control,hold}-<script>.json, one per script and arm)
The arms follow the scene-fixing guide: replay the recorded stuck commands with one arm per likely cause. The hold arm
widens the existing departure-hold claim (k_sl_1a_k_r1) to the on-foot park-bench lead; no exit, transition or pacing
value changes.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PREFIX = [
    "Search the kitchen and the back door for concrete signs of what happened here - the overturned chair, the forced lock, her phone left on the floor.",
    "Search under the drawer in her workstation.",
    "Read the files on Michelle's memory card.",
]
SCRIPTS = {
    "bench-onfoot": PREFIX
    + [
        "Search the park bench.",
        "Feel beneath the park bench for a hidden compartment.",
        "Investigate the park bench.",
    ],
    "truck-drive": PREFIX + ["Go out to the truck.", "Drive my truck to the park bench."],
    "unoffered": [
        PREFIX[0],
        "Inspect the calendar.",
        "Read Michelle's text message.",
        "Go out to the truck.",
        "Ask Walt Pruitt about the commotion.",
    ],
    "laptop": PREFIX + ["Retrieve my laptop from my truck.", "Carry my laptop into the kitchen."],
    "officer": PREFIX
    + ["Look around.", "Look around.", "Look around.", "Look around.", "Question Officer Reyes about Michelle."],
}

BASE = {
    "story_package": "data/stories/continuity-initiative",
    "runtime": True,
    "item_facts": {"mode": "single_call", "seed_from_package": True},
    "fixed_refusal": True,
    "engine_refusal": True,
}

HOLD_OVERRIDES = {
    "source/scenes/1A.yaml": {
        "replacements": [
            {
                "old": "      entities:\n      - kristin\n      - kristin_truck\n      - park_bench\n      reach:\n      - kristin_truck\n      relevance:\n        entity_ids:\n        - kristin\n        - kristin_truck\n        - park_bench\n        priority: 0\n      audience:\n        kind: public\n        character_ids: []\n        player_visible: true\n      voiceable: false\n      repeatable: true\n      when:\n        michelle_lead_actionable: true\n      text: Kristin does not pull away yet.",
                "new": "      entities:\n      - kristin\n      - kristin_truck\n      - park_bench\n      reach: []\n      relevance:\n        entity_ids:\n        - kristin\n        - kristin_truck\n        - park_bench\n        priority: 0\n      audience:\n        kind: public\n        character_ids: []\n        player_visible: true\n      voiceable: false\n      repeatable: true\n      when:\n        michelle_lead_actionable: true\n      text: Kristin does not pull away yet.",
            },
            {
                "old": "text: Kristin does not pull away yet. If anyone is watching the street, driving to the park now would lead them straight to the bench. She waits to see what the street does.",
                "new": "text: Kristin does not go yet. If anyone is watching the street, going to the park now would lead them straight to the bench. She waits to see what the street does.",
            },
            {
                "old": "text: Kristin does not pull away yet. The patrol is still at the house, and the truck would be the first thing they follow. If she drives to the park now, she leads them straight to the bench. She waits to see what the patrol does.",
                "new": "text: Kristin does not go yet. The patrol is still at the house, and they would follow her to the park. If she goes to the bench now, she leads them straight to it. She waits to see what the patrol does.",
            },
            {
                "old": "text: Kristin does not pull away yet. The patrol has only just left, and it could be waiting around the corner. If she drives to the park now, she may lead it straight to the bench. She waits to see what the street does.",
                "new": "text: Kristin does not go yet. The patrol has only just left, and it could be waiting around the corner. If she goes to the park now, she may lead it straight to the bench. She waits to see what the street does.",
            },
            {
                "old": "earn_when: tries to drive or head to the park before the street is clear",
                "new": "earn_when: tries to drive, head or go to the park, or to search the park bench, before the street is clear",
            },
        ]
    },
    "source/scenes/1A.match.yaml": {
        "replacements": [
            {
                "old": "      - take the truck\n      - get to\n    - - park\n      - bench\n    must_convey:\n    - - pull away\n      - drive\n    - - park\n    - - bench\n    - - waits\n      - wait\n",
                "new": "      - take the truck\n      - get to\n      - search\n      - look\n      - investigate\n      - examine\n      - check\n      - feel\n      - visit\n    - - park\n      - bench\n    must_convey:\n    - - pull away\n      - drive\n      - go\n      - goes\n      - going\n    - - park\n    - - bench\n    - - waits\n      - wait\n",
            }
        ]
    },
}


def write(arm: str, script: str, overrides: dict | None) -> Path:
    """One variation per script and arm: the bench cycles a script when fixed_turns exceeds its length."""

    inputs = SCRIPTS[script]
    name = f"probe-1a-{arm}-{script}"
    data = {"name": name, **BASE, "fixed_turns": len(inputs)}
    if overrides:
        data["overrides"] = overrides
    data["scripts"] = {"1A": [{"name": script, "inputs": inputs}]}
    path = ROOT / "bench" / "variations" / f"{name}.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    for script in SCRIPTS:
        print(write("control", script, None))
        print(write("hold", script, HOLD_OVERRIDES))
