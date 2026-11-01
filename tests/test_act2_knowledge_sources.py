from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

PACING_KNOWLEDGE_IDS = (
    "k_supervisor_escorting",
    "k_inspection_recovery_ready",
    "k_audit_recovery_ready",
    "k_purge_recovery_ready",
    "k_inspection_window_missed",
    "k_audit_window_missed",
    "k_purge_window_missed",
)
WORLD_ONLY_PACING_KNOWLEDGE_IDS = {
    "k_inspection_recovery_ready",
    "k_audit_recovery_ready",
    "k_purge_recovery_ready",
}


def _operation_key(operation) -> tuple[str, str, str]:
    return operation.op, operation.fact_id, str(operation.value).strip().lower()


def test_storylet_realization_knowledge_sources_cover_exact_operations() -> None:
    for storylet in PACKAGE.storylet_routes.storylets:
        for realization in storylet.realizations:
            source_key = f"storylet:{storylet.id}:{realization.id}"
            knowledge_ids = PACKAGE.knowledge_indexes.source_to_knowledge.get(source_key, ())
            if not knowledge_ids:
                continue

            established = sorted(
                _operation_key(operation)
                for knowledge_id in knowledge_ids
                for operation in PACKAGE.knowledge_indexes.by_id[knowledge_id].establishes
            )
            expected = sorted(_operation_key(operation) for operation in realization.operations)

            assert established == expected, source_key


def test_canonical_route_event_knowledge_is_not_player_matchable() -> None:
    for item in PACKAGE.knowledge.knowledge:
        if item.source.kind != "canonical_route_event":
            continue

        assert item.action_evidence == ()
        assert item.earn_when is None


@pytest.mark.parametrize("knowledge_id", PACING_KNOWLEDGE_IDS)
def test_pacing_knowledge_is_hidden_and_not_player_matchable(knowledge_id: str) -> None:
    item = PACKAGE.knowledge_indexes.by_id[knowledge_id]

    assert item.action_evidence == ()
    assert item.earn_when is None
    if knowledge_id in WORLD_ONLY_PACING_KNOWLEDGE_IDS:
        assert item.audience.kind == "world_only"
        assert not item.audience.player_visible


def test_2a_cooling_manifold_does_not_select_pacing_knowledge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")

    def fail_if_called(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("semantic reveal fallback must not run in this regression")

    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state.current_scene_id = "2A"
    state.phase = scene.metadata.freytag_phase
    state.turn_index = 2
    state._assert_scene_entry_fact("2A")
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, semantic_ask=fail_if_called)

    provider.assemble_turn_prompt("Examine the cooling manifold for a safe footing.")

    assert provider.last_reveal_selection["matched"] != "k_supervisor_escorting"
