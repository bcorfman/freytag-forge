import json

import pytest

from factory.contract_scene import build_contract_scene
from factory.outcome_contract import classify_run
from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import load_story_package


@pytest.fixture(scope="module")
def package():
    return load_story_package(default_package_root())


def _scene_id(scene):
    return scene.metadata.scene_id


def _scene(package, suffix):
    return next(scene for scene in package.scenes if _scene_id(scene).endswith(suffix))


def test_scene_2c_excludes_earlier_knowledge_from_reveals(package):
    result = build_contract_scene(package, _scene(package, "2C").metadata.scene_id)

    assert "k_sl_2b_b_r4" in result["delivered_before"]
    assert "k_sl_2b_b_r4" not in result["reveal_ids"]


def test_scene_2a_entry_is_delivered_before(package):
    result = build_contract_scene(package, _scene(package, "2A").metadata.scene_id)

    assert "k_scene_2a_entry" in result["delivered_before"]


def test_scene_1b_repeated_knowledge_is_delivered_before(package):
    result = build_contract_scene(package, _scene(package, "1B").metadata.scene_id)

    assert "k_sl_1a_b_r1" in result["delivered_before"]


def test_first_scene_has_no_earlier_deliveries(package):
    first_scene_id = _scene_id(package.scenes[0])
    result = build_contract_scene(package, first_scene_id)

    assert result["delivered_before"] == sorted(
        item.id
        for item in package.knowledge.knowledge
        if item.source.kind == "scene_entry" and first_scene_id in item.available_in_scenes
    )


def test_unknown_scene_raises_value_error(package):
    with pytest.raises(ValueError, match="unknown scene"):
        build_contract_scene(package, "9Z")


def test_result_is_json_serialisable_and_deterministic(package):
    scene_id = _scene(package, "2C").metadata.scene_id

    first = build_contract_scene(package, scene_id)
    second = build_contract_scene(package, scene_id)

    assert first == second
    json.dumps(first)


def test_build_does_not_mutate_package(package):
    before = package.model_dump(mode="python")

    build_contract_scene(package, _scene(package, "2C").metadata.scene_id)

    assert package.model_dump(mode="python") == before


def test_re_grounded_prior_knowledge_is_not_progress(package):
    scene_id = _scene(package, "2C").metadata.scene_id
    scene = build_contract_scene(package, scene_id)
    run = {
        "replicate": 1,
        "entry_facts": [],
        "turns": [
            {
                "turn": 1,
                "input": "Wait.",
                "text": "",
                "outcome": "committed",
                "rejected": False,
                "game_break": None,
                "story_complete": False,
                "grounding_ids": ["k_sl_2b_b_r4"],
                "null_grounding_ids": [],
                "committed_facts": [],
                "candidates_offered": [],
                "matched_candidate": None,
                "transition_cause": "none",
                "pressure_event": False,
                "npc_move": False,
                "ending_latched": False,
            }
        ],
    }

    assert classify_run(run, scene)["turns"][0]["knowledge_progress"] is False
