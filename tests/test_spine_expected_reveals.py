import json

from scripts.generate_spine_expected_reveals import (
    FRONTEND_ROOT,
    expected_reveals,
)
from scripts.generate_spine_expected_reveals import (
    knowledge_items as _knowledge,
)
from scripts.generate_spine_expected_reveals import (
    scene_prompts as _scene_prompts,
)


def test_expected_reveal_mapping_has_current_scene_ids_and_matches_prompts() -> None:
    prompts = _scene_prompts()
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    knowledge = _knowledge()

    assert set(expected) == set(prompts)
    recomputed = expected_reveals(prompts, knowledge)
    assert expected == recomputed


def test_expected_reveal_ids_exist_and_include_2c_c_r2() -> None:
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    knowledge = _knowledge()

    assert all(item_id in knowledge for ids in expected.values() for item_id in ids)
    assert "k_sl_2c_c_r2" in expected["2C"]


def test_expected_reveals_spend_sibling_storylets_once() -> None:
    expected = expected_reveals(_scene_prompts(), _knowledge())
    ids = {item_id for scene in expected.values() for item_id in scene}
    assert not ids & {"k_sl_1a_b_r2", "k_sl_1b_a_r1", "k_sl_1c_c_r2", "k_sl_2b_a_r2"}
    knowledge = _knowledge()
    sources = [knowledge[item_id]["source"]["storylet_id"] for item_id in ids]
    assert len(sources) == len(set(sources))


def test_world_only_matches_are_not_expected() -> None:
    assert "k_sl_2c_a_r1" not in expected_reveals(_scene_prompts(), _knowledge())["2C"]


def test_prompt_three_tie_needs_a_separate_prompt() -> None:
    prompts = _scene_prompts()["1A"]
    expected = expected_reveals({"1A": [*prompts[:2], prompts[3]]}, _knowledge())["1A"]
    assert "k_sl_1a_b_r1" in expected
    assert "k_sl_1a_d_r1" not in expected
    assert "k_sl_1a_d_r1" in expected_reveals({"1A": prompts}, _knowledge())["1A"]
