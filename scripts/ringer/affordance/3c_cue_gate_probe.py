"""Read-only probe for the scene 3C cue chain.

No model calls. Walks the 3C chain fact by fact, and prints,
per stage, the cue source (`_bridge_delivery_fact_ids`), the ranked cue facts, the step
facts each 3C canonical event still lacks, and whether each lacking fact has a delivery.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from storygame.runtime.contracts import FactOperation
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENE = next(s for s in PACKAGE.scenes if s.metadata.scene_id == "3C")
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")
CHAIN = (
    ("A done", ("truth_no_longer_containable", "national_facility_locations_broadcast")),
    ("B done", ("rebecca_captured", "charles_at_large", "portable_archive_secured", "archive_copies_distributed")),
    ("C done", ("captives_reaching_surface", "los_angeles_facility_lost", "evacuation_route_open")),
    ("D1 only", ("national_network_fragmenting",)),
    ("D2 only (instead of D1)", ("community_rescue_efforts_begun",)),
)


def build(extra: tuple[str, ...], fired: set[str]) -> RuntimeEngine:
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase=SCENE.metadata.freytag_phase)
    state.turn_index = 0
    for fact_id in (*ENTRY_FACTS, *extra):
        state._apply_operation(
            state.facts,
            FactOperation(operation="assert", fact=Fact(predicate=fact_id, subject="story", value="true")),
        )
    state.fired_event_ids = set(fired)
    return RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Nothing."}]})


def main(out: str) -> None:
    routes = PACKAGE.storylet_routes
    deliveries = {d.fact_id: d for d in PACKAGE.deliveries}
    events = [e for e in (*routes.bridge_events, *routes.resolution_events) if e.scene_id == "3C"]
    report: dict[str, object] = {
        "3c_bridge_event_ids": [e.id for e in routes.bridge_events if e.scene_id == "3C"],
        "3c_resolution_event_ids": [e.id for e in routes.resolution_events if e.scene_id == "3C"],
        "3c_delivery_fact_ids": sorted(d.fact_id for d in PACKAGE.deliveries if d.scene_id == "3C"),
        "stages": [],
    }
    facts: tuple[str, ...] = ()
    stages = [("3C entry", ())] + [(label, add) for label, add in CHAIN]
    for label, add in stages:
        if label.startswith("D2 only"):
            facts = tuple(f for f in facts if f != "national_network_fragmenting") + add
        else:
            facts = facts + add
        engine = build(facts, set())
        true_facts = engine._true_facts(engine.state.facts)
        lacking = {}
        for event in events:
            if not event.activation.is_satisfied(true_facts):
                missing = event.activation.minimal_undelivered_facts(true_facts)
                lacking[event.id] = {f: (f in deliveries) for f in missing}
        report["stages"].append(
            {
                "stage": label,
                "facts_added": list(facts),
                "cue_source_fact_ids": list(engine._bridge_delivery_fact_ids()),
                "ranked_cue_fact_ids": list(engine._ranked_cue_fact_ids()),
                "events_lacking_facts_and_has_delivery": lacking,
            }
        )
    Path(out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
