from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_world_effects
from storygame.story_package import StoryPackageError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import KnowledgeDefinition

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def _generic_item(*, voiceable: bool | None = None) -> KnowledgeDefinition:
    source = next(item for item in PACKAGE.knowledge.knowledge if item.id == "k_sl_1a_a_r1")
    data = source.model_dump(mode="json")
    data.update(
        {
            "id": "k_generic_claim",
            "statement": "The survey marker is established.",
            "aliases": ["survey marker established"],
            "entity_ids": [],
            "reach_entity_ids": [],
        }
    )
    if voiceable is not None:
        data["voiceable"] = voiceable
    return KnowledgeDefinition.model_validate(data)


def _generic_package(item: KnowledgeDefinition):
    catalog = PACKAGE.knowledge.model_copy(update={"knowledge": (item,)})
    indexes = PACKAGE.knowledge_indexes.model_copy(
        update={
            "by_id": {item.id: item},
            "scene_to_candidates": {"1A": (item.id,)},
        }
    )
    return PACKAGE.model_copy(update={"knowledge": catalog, "knowledge_indexes": indexes})


def _generic_state(item: KnowledgeDefinition) -> RuntimeState:
    state = RuntimeState.bootstrap(_generic_package(item))
    for effect in item.establishes:
        state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value="true"))
    return state


def _real_recovery_state(*, witnessed: bool) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    if witnessed:
        state.facts.assert_fact(Fact(predicate="card_challenged", subject="story", value="true"))
        state.facts.assert_fact(Fact(predicate="kristin_marked_by_patrol", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    return state


def _real_gap_and_patrol_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    state.facts.assert_fact(Fact(predicate="drawer_gap_pointed_out", subject="story", value="true"))
    state.fired_event_ids.add("SL-1A-F")
    state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    return state


def test_default_voiceable_claim_is_sayable_for_a_present_speaker() -> None:
    item = _generic_item()
    projection = KnowledgeProjector().project(_generic_state(item), "brandon", "Inspect the survey marker.")

    assert {claim.id for claim in projection.sayable_knowledge} == {item.id}


def test_non_voiceable_claim_is_committed_but_never_sayable_for_any_audience() -> None:
    item = _generic_item(voiceable=False)
    state = _generic_state(item)
    projector = KnowledgeProjector()

    for audience in ("player", "brandon", "another_npc"):
        projection = projector.project(state, audience, "Inspect the survey marker.")
        assert item.id in {claim.id for claim in projection.committed_knowledge}
        assert item.id not in {claim.id for claim in projection.sayable_knowledge}


def test_real_recovery_prompt_omits_non_voiceable_player_action_but_keeps_officer_line() -> None:
    state = _real_recovery_state(witnessed=True)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    prompt = provider.assemble_turn_prompt("Search the kitchen for signs of a struggle.")["context"]
    user_prompt = provider._section_user_prompt(prompt)

    assert "may say this aloud: Kristin finds Michelle" not in user_prompt
    assert "may say this aloud: An officer saw Kristin take Michelle's memory card" in user_prompt


def test_real_gap_prompt_omits_non_voiceable_player_actions_but_keeps_committed_knowledge() -> None:
    state = _real_gap_and_patrol_state()
    command = "Search the kitchen for signs of a struggle."
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    prompt = provider.assemble_turn_prompt(command)["context"]
    user_prompt = provider._section_user_prompt(prompt)
    committed_ids = {item.id for item in KnowledgeProjector().project(state, "player", command).committed_knowledge}

    assert "may say this aloud: Kristin looks over the drawer" not in user_prompt
    assert "may say this aloud: Kristin opens the drawer" not in user_prompt
    assert {"k_sl_1a_f_r1", "k_sl_1a_f_r2"} <= committed_ids


@pytest.mark.parametrize(
    ("knowledge_id", "witnessed", "expected_error"),
    [
        ("k_sl_1a_b_r0", False, True),
        ("k_sl_1a_b_r0w", True, False),
    ],
)
def test_dialogue_grounding_uses_voiceable_projection(knowledge_id: str, witnessed: bool, expected_error: bool) -> None:
    state = _real_recovery_state(witnessed=witnessed)
    statement = PACKAGE.knowledge_indexes.by_id[knowledge_id].statement
    payload = {
        "segments": [
            {
                "kind": "dialogue",
                "speaker_id": "patrol_officer",
                "text": statement,
                "grounding_ids": [knowledge_id],
            }
        ],
        "selected_knowledge_ids": [],
    }

    if expected_error:
        with pytest.raises(ProposalValidationError) as caught:
            RuntimeEngine(state, lambda _: payload).turn("Ask the patrol officer about the memory card.")
        assert caught.value.code == "dialogue_grounding_not_sayable"
    else:
        result = RuntimeEngine(state, lambda _: payload).turn("Ask the patrol officer about the memory card.")
        assert result.segments[0].text == statement


@pytest.mark.parametrize("knowledge_id", ["k_sl_1a_f_r1", "k_sl_1a_f_r2"])
def test_dialogue_grounding_rejects_quoted_gap_statement(knowledge_id: str) -> None:
    state = _real_gap_and_patrol_state()
    statement = PACKAGE.knowledge_indexes.by_id[knowledge_id].statement
    payload = {
        "segments": [
            {
                "kind": "dialogue",
                "speaker_id": "patrol_officer",
                "text": statement,
                "grounding_ids": [knowledge_id],
            }
        ],
        "selected_knowledge_ids": [],
    }

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, lambda _: payload).turn("Ask the patrol officer about the drawer.")

    assert caught.value.code == "dialogue_grounding_not_sayable"


def test_loader_rejects_non_boolean_voiceable(tmp_path: Path) -> None:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE_ROOT, destination)
    source = destination / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    item = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_1a_b_r0")
    item["voiceable"] = "false"
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    with pytest.raises(StoryPackageError) as caught:
        load_story_package(destination)
    assert "voiceable" in str(caught.value)


def test_real_package_has_exactly_the_non_voiceable_knowledge_items() -> None:
    non_voiceable = [item for item in PACKAGE.knowledge.knowledge if item.voiceable is False]

    assert [item.id for item in non_voiceable] == ["k_sl_1a_b_r0", "k_sl_1a_f_r1", "k_sl_1a_f_r2"]


def test_default_serialization_omits_voiceable_but_false_round_trips() -> None:
    default_item = _generic_item()
    non_voiceable = _generic_item(voiceable=False)

    assert "voiceable" not in default_item.model_dump(mode="json")
    assert non_voiceable.model_dump(mode="json")["voiceable"] is False
