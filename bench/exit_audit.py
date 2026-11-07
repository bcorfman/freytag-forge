"""Offline authoritative-world audit for the nine-command 3A exit script."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bench.core import load_variation
from bench.frozen_prompts import _handoff_id, _prefix_states, _script_inputs
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]
SCENE = "3A"
REQUIRED_ENTITY_IDS = ("kristin", "michelle", "brandon", "captives", "stolen_radio")
ACCESSOR_USED = "world.parent(entity_id) for place and world.holder(entity_id) for holder"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _radio_like_ids(package) -> tuple[str, ...]:
    """Include the required radio plus every package item whose authored name is radio-like."""

    ids = set(REQUIRED_ENTITY_IDS)
    for item in package.world.items:
        names = (item.id, item.name, *item.aliases, *item.scoped_aliases)
        if any("radio" in name.casefold() for name in names):
            ids.add(item.id)
    return tuple(sorted(ids))


def _placement(world, entity_id: str) -> dict[str, str | None]:
    """Read placement only through worldkeeper's parent and holder accessors."""

    place = world.parent(entity_id)
    holder = world.holder(entity_id)
    return {"place": place, "holder": holder}


def _placements(state, entity_ids: tuple[str, ...]) -> dict[str, dict[str, str | None]]:
    world = world_for(state.package, state.facts)
    return {entity_id: _placement(world, entity_id) for entity_id in entity_ids}


def _true_fact_ids(state) -> list[str]:
    return sorted(
        fact.predicate
        for fact in state.facts.asserted
        if fact.subject == "story" and str(fact.value).casefold() == "true"
    )


def _scripted_provider(state, package, engine_ref: list[RuntimeEngine]):
    def provider(command: str) -> dict[str, object]:
        engine = engine_ref[0]
        handoff_id = _handoff_id(engine, state, command)
        if handoff_id is None:
            return {"segments": [{"kind": "narration", "text": "Kristin looks."}], "selected_knowledge_ids": []}
        entry = package.knowledge_indexes.by_id[handoff_id]
        return {
            "segments": [{"kind": "narration", "text": entry.delivery_text, "grounding_ids": [handoff_id]}],
            "selected_knowledge_ids": [handoff_id],
        }

    return provider


def audit(variation_path: Path | str, out_path: Path | str | None = None) -> dict[str, Any]:
    """Play the complete 3A script with authored deliveries and audit live world state."""

    variation = load_variation(Path(variation_path))
    inputs = _script_inputs(variation)
    if len(inputs) != 9:
        raise ValueError(f"expected the nine-command 3A script, found {len(inputs)} commands")

    # _prefix_states uses the same seeded_state_for_scene path as frozen runs.
    prefix_states, seeded_inputs = _prefix_states(variation, [1])
    if seeded_inputs != inputs:
        raise ValueError("variation script changed while seeding the audit")
    state = prefix_states[0]
    entity_ids = _radio_like_ids(state.package)
    engine_ref: list[RuntimeEngine] = []
    provider = _scripted_provider(state, state.package, engine_ref)
    engine = RuntimeEngine(state, provider)
    engine_ref.append(engine)

    records: list[dict[str, Any]] = []
    custody: list[dict[str, str | None]] = []
    for command in inputs:
        scene_before = state.current_scene_id
        engine.turn(command)
        placements = _placements(state, entity_ids)
        radio = placements["stolen_radio"]
        records.append(
            {
                "command": command,
                "scene_id": state.current_scene_id,
                "left_scene": state.current_scene_id != scene_before,
                "true_fact_ids": _true_fact_ids(state),
                "placements": placements,
            }
        )
        custody.append({"command": command, "holder": radio["holder"], "place": radio["place"]})

    final_placements = _placements(state, entity_ids)
    final_radio = final_placements["stolen_radio"]
    if final_radio["holder"] is not None:
        radio_finding = f"the stolen radio is held by {final_radio['holder']} after c9."
    else:
        radio_finding = f"the stolen radio is at {final_radio['place'] or 'unplaced'} after c9."
    kristin_place = final_placements["kristin"]["place"] or "unplaced"
    scene_id = state.current_scene_id
    report: dict[str, Any] = {
        "variation": variation["name"],
        "package_hash": variation["_package_hash"],
        "accessor_used": ACCESSOR_USED,
        "commands": records,
        "radio_custody_by_command": custody,
        "exit": {
            "from_scene": SCENE,
            "scene_id": scene_id,
            "placements": final_placements,
            "radio_custody": {"holder": final_radio["holder"], "place": final_radio["place"]},
        },
        "findings": [
            f"Kristin place after c9 is {kristin_place} in scene {scene_id}.",
            radio_finding,
        ],
        "limits": [
            "The narrator is scripted (no model item_facts), so only authored effects change the world.",
            "Live narrator item_facts proposals are not exercised.",
        ],
    }
    if out_path is not None:
        _write_json(Path(out_path), report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bench.exit_audit")
    parser.add_argument("--variation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    audit(args.variation, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
