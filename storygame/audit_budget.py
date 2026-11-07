"""Offline deep-turn narrator prompt budgets for any story package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import KnowledgeDefinition, StoryPackage

_PLAYER_INPUT = "Look around."
_BUDGET = 6500
_DEFAULT_PACKAGE = Path("data/stories/continuity-initiative")
_DEFAULT_FIXTURE = Path("tests/fixtures/deep_turn_budget.json")


def _package(value: StoryPackage | Path | str) -> StoryPackage:
    return load_story_package(Path(value)) if isinstance(value, (Path, str)) else value


def _scene(package: StoryPackage, scene_id: str):
    try:
        return next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    except StopIteration as error:
        raise ValueError(f"scene {scene_id!r} is not in package {package.story_id!r}") from error


def _story_fact(state: RuntimeState, fact_id: str, value: object) -> None:
    """Assert one knowledge effect, making the latest value authoritative."""

    state.facts.asserted = {
        fact for fact in state.facts.asserted if not (fact.subject == "story" and fact.predicate == fact_id)
    }
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value=str(value).lower()))


def _selected_entries(
    package: StoryPackage, scene_id: str, *, one_per_storylet: bool
) -> tuple[KnowledgeDefinition, ...]:
    selected: list[KnowledgeDefinition] = []
    seen_storylets: set[str] = set()
    for entry in package.knowledge.knowledge:
        if scene_id not in entry.available_in_scenes:
            continue
        storylet_id = entry.source.storylet_id
        if one_per_storylet and storylet_id is not None and storylet_id in seen_storylets:
            continue
        selected.append(entry)
        if storylet_id is not None:
            seen_storylets.add(storylet_id)
    return tuple(selected)


def _state_for(
    package: StoryPackage, scene_id: str, *, one_per_storylet: bool, establish: bool = True
) -> tuple[RuntimeState, tuple[KnowledgeDefinition, ...]]:
    scene = _scene(package, scene_id)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    apply_scene_placements(package, state.facts, scene_id)
    entries = _selected_entries(package, scene_id, one_per_storylet=one_per_storylet)
    for entry in entries if establish else ():
        for effect in entry.establishes:
            if effect.op == "assert":
                _story_fact(state, effect.fact_id, effect.value)
    return state, entries


def _narration_measurement(state: RuntimeState) -> tuple[int, int]:
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    # prepare_turn is part of the production measurement path, but its matcher
    # request is deliberately replaced with a deterministic empty answer here.
    with patch.object(
        CloudflareTurnProvider,
        "_request_item_facts",
        return_value={"refers": [], "same_as": {}, "kind": {}},
    ):
        provider.prepare_turn(_PLAYER_INPUT)
    prompt = provider.assemble_turn_prompt(_PLAYER_INPUT)
    narration_chars = len(prompt["system"]) + len(provider._section_user_prompt(prompt["context"]))
    projection = provider.last_projection
    if projection is None:
        raise RuntimeError("prompt assembly did not produce a knowledge projection")
    return narration_chars, len(projection.committed_knowledge)


def _established_alternate_pairs(state: RuntimeState, entries: tuple[KnowledgeDefinition, ...]) -> list[str]:
    realizations_by_storylet: dict[str, set[str]] = {}
    for entry in entries:
        storylet_id = entry.source.storylet_id
        realization_id = entry.source.realization_id
        if storylet_id is not None and realization_id is not None and KnowledgeProjector._established(entry, state):
            realizations_by_storylet.setdefault(storylet_id, set()).add(realization_id)
    return sorted(
        storylet_id for storylet_id, realizations in realizations_by_storylet.items() if len(realizations) >= 2
    )


def deep_turn_budget(package: StoryPackage | Path | str, scene_id: str) -> dict[str, Any]:
    """Measure one scene after establishing its declared knowledge entries."""

    loaded = _package(package)
    state, entries = _state_for(loaded, scene_id, one_per_storylet=True)
    narration_chars, established_entries = _narration_measurement(state)

    all_state, all_entries = _state_for(loaded, scene_id, one_per_storylet=False)
    all_narration_chars, _ = _narration_measurement(all_state)
    return {
        "narration_chars": narration_chars,
        "established_entries": established_entries,
        "alternate_pairs": _established_alternate_pairs(all_state, all_entries),
        "narration_chars_all_alternates": all_narration_chars,
    }


def report(package: StoryPackage | Path | str) -> list[dict[str, Any]]:
    """Return deterministic deep-turn budget rows in package scene order."""

    loaded = _package(package)
    rows = []
    for scene in loaded.scenes:
        scene_id = scene.metadata.scene_id
        entry_state, _ = _state_for(loaded, scene_id, one_per_storylet=True, establish=False)
        entry_narration_chars, _ = _narration_measurement(entry_state)
        row = deep_turn_budget(loaded, scene_id)
        rows.append({"scene_id": scene_id, "entry_narration_chars": entry_narration_chars, **row})
    return rows


def _write_fixture(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scenes = {
        row["scene_id"]: {
            "narration_chars": row["narration_chars"],
            "narration_chars_all_alternates": row["narration_chars_all_alternates"],
        }
        for row in rows
    }
    path.write_text(json.dumps({"schema": 1, "scenes": scenes}, indent=2) + "\n", encoding="utf-8")


def _print_table(rows: list[dict[str, Any]]) -> None:
    print("scene  entry chars  deep chars  all-alternates chars  over 6500")
    for row in rows:
        mark = "*" if row["narration_chars"] > _BUDGET else ""
        print(
            f"{row['scene_id']:>5}  {row['entry_narration_chars']:>11}  "
            f"{row['narration_chars']:>10}  {row['narration_chars_all_alternates']:>20}  {mark}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=_DEFAULT_PACKAGE)
    parser.add_argument("--write", action="store_true", help="write the pinned fixture")
    parser.add_argument("--fixture", type=Path, default=_DEFAULT_FIXTURE)
    args = parser.parse_args(argv)
    rows = report(args.package)
    if args.write:
        _write_fixture(args.fixture, rows)
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
