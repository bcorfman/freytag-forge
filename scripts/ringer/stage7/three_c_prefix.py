"""Build the deterministic carried-state prefix for the Stage 7 3C probe."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import _story_package_fingerprint
from tests._legacy_package import legacy_package
from tests.test_canon_journey import PACKAGE, UNCLOCKED_JOURNEY, _ScriptedProvider

SESSION_ID = "stage7-3c-prefix"
PACKAGE_ROOT = Path(__file__).resolve().parents[3] / "data/stories/continuity-initiative"


def _git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"cannot determine git SHA: {error}") from error


def _run(package, count: int) -> tuple[RuntimeState, list[str]]:
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    transcript: list[str] = []
    for selection, expected_scene in UNCLOCKED_JOURNEY[:count]:
        result = _turn(engine, provider, selection)
        transcript.append(result.narration)
        if state.current_scene_id != expected_scene:
            raise RuntimeError(
                f"canon journey turn {state.turn_index} selecting {selection!r} ended in "
                f"{state.current_scene_id}, expected {expected_scene}"
            )
        if state.has_pending_break:
            raise RuntimeError(f"canon journey turn {state.turn_index} left a pending game break")
    return state, transcript


def _turn(engine: RuntimeEngine, provider: _ScriptedProvider, selection: str | None):
    provider.selected = [selection] if selection else []
    return engine.turn("Act on the strongest available lead.")


def _prefix_count(package) -> int:
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    for index, (selection, expected_scene) in enumerate(UNCLOCKED_JOURNEY, start=1):
        _turn(engine, provider, selection)
        if state.current_scene_id != expected_scene:
            raise RuntimeError(
                f"canon journey turn {index} selecting {selection!r} ended in {state.current_scene_id}, "
                f"expected {expected_scene}"
            )
        if state.current_scene_id == "3C":
            if index < 2 or state.turn_records[-1].transition_id != "t_3b_3c":
                raise RuntimeError("canon journey reached 3C without the authored 3B->3C transition")
            return index - 1
    raise RuntimeError("canon journey never reached 3C")


def _fact_dump(state: RuntimeState) -> list[dict[str, str | None]]:
    return [fact.model_dump(mode="json") for fact in sorted(state.facts.asserted, key=lambda item: item.key)]


def _canonical_dump(state: RuntimeState) -> str:
    """Compare snapshots without letting set-backed JSON list order leak in."""

    def normalize(value):
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            normalized = [normalize(item) for item in value]
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
        return value

    return json.dumps(normalize(state.model_dump(mode="json", exclude={"package"})), sort_keys=True)


def _committed_reveals(state: RuntimeState) -> list[str]:
    return sorted(item.id for item in state.package.knowledge.knowledge if KnowledgeProjector._established(item, state))


def _knowledge_status(state: RuntimeState, name: str) -> dict[str, Any]:
    matching = [
        item
        for item in state.package.knowledge.knowledge
        if item.id == name or any(effect.fact_id == name for effect in item.establishes)
    ]
    committed_ids = set(_committed_reveals(state))
    projection = KnowledgeProjector().project(state, "player", "")
    projected_ids = {
        item.id for item in (*projection.committed_knowledge, *projection.sayable_knowledge, *projection.candidates)
    }
    matching_ids = sorted(item.id for item in matching)
    committed = bool(committed_ids.intersection(matching_ids)) or any(
        fact.predicate == name and str(fact.value).lower() == "true" for fact in state.facts.asserted
    )
    available = bool(projected_ids.intersection(matching_ids)) or any(
        fact.predicate == name and str(fact.value).lower() == "true" for fact in state.facts.asserted
    )
    return {
        "committed": committed,
        "available": available,
        "matching_entry_ids": matching_ids,
    }


def _world_parents(state: RuntimeState) -> dict[str, str | None]:
    world = world_for(state.package, state.facts)
    return {entity_id: world.parent(entity_id) for entity_id in sorted(world.entity_ids())}


def _transition_texts(state: RuntimeState, result) -> tuple[str, str]:
    scene_3c = next(scene for scene in state.package.scenes if scene.metadata.scene_id == "3C")
    entry_text = scene_3c.metadata.entry_text
    bridge_text = next(
        scene.metadata.bridge_text[transition.id]
        for scene in state.package.scenes
        for transition in state.package.pacing.transitions
        if transition.id == "t_3b_3c" and scene.metadata.scene_id == transition.source_scene_id
    )
    texts = {segment.text for segment in result.segments}
    if entry_text not in texts or bridge_text not in texts:
        raise RuntimeError("3B->3C transition did not render both authored bridge and entry text")
    return entry_text, bridge_text


def build(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    prefix_count = _prefix_count(package)
    state, transcript = _run(package, prefix_count)
    if state.current_scene_id != "3B":
        raise RuntimeError(f"prefix is in {state.current_scene_id}, expected 3B")
    if not any(record.transition_id == "t_3a_3b" for record in state.turn_records):
        raise RuntimeError("prefix did not commit the authored 3A->3B transition")
    if not state.facts.matching("scene_3b_entry_known"):
        raise RuntimeError("prefix did not commit the 3B scene-entry fact")

    checkpoint = out_dir / "checkpoint.sqlite"
    store = RuntimeStateSqliteStore(checkpoint)
    store.save(SESSION_ID, state)
    loaded = store.load(SESSION_ID, package)
    if _canonical_dump(loaded) != _canonical_dump(state):
        raise RuntimeError("save/load round trip changed the runtime state")

    crossing_provider = _ScriptedProvider(package)
    crossing_engine = RuntimeEngine(loaded, crossing_provider)
    selection, _ = UNCLOCKED_JOURNEY[prefix_count]
    transition_result = _turn(crossing_engine, crossing_provider, selection)
    if loaded.current_scene_id != "3C":
        raise RuntimeError(f"one loaded scripted turn ended in {loaded.current_scene_id}, expected 3C")
    entry_text, bridge_text = _transition_texts(loaded, transition_result)

    root = Path(__file__).resolve().parents[3]
    payload = {
        "package_id": package.story_id,
        "package_content_hash": _story_package_fingerprint(PACKAGE_ROOT),
        "git_sha": _git_sha(root),
        "turn_index": state.turn_index,
        "scene": state.current_scene_id,
        "committed_reveal_ids": _committed_reveals(state),
        "facts": _fact_dump(state),
        "world_parents": _world_parents(state),
        "knowledge_status": {
            "relay_open": _knowledge_status(state, "relay_open"),
            "janus_selection": _knowledge_status(state, "janus_selection"),
        },
        "transcript_lines": transcript,
        "entry_text": entry_text,
        "bridge_text": bridge_text,
    }
    (out_dir / "prefix.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.out)
    except Exception as error:  # pragma: no cover - CLI boundary
        print(f"three_c_prefix: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
