import json

from scripts.generate_spine_expected_reveals import (
    FRONTEND_ROOT,
    simulate_expected_reveals,
)
from scripts.generate_spine_expected_reveals import (
    knowledge_items as _knowledge,
)

SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def test_committed_expectation_matches_the_engine_simulation() -> None:
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    assert tuple(expected) == SCENES
    assert expected == simulate_expected_reveals()


def test_expected_reveal_ids_are_current_and_scene_specific() -> None:
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    knowledge = _knowledge()

    assert all(ids == sorted(ids) for ids in expected.values())
    assert all(item_id in knowledge for ids in expected.values() for item_id in ids)
    assert "k_sl_2c_c_r2" in expected["2C"]
    assert all("k_sl_2c_a_r1" not in ids for ids in expected.values())
    assert expected["1C"] == ["k_sl_1c_a_r1", "k_sl_1c_b_r1", "k_sl_1c_c_copy_numbers"]
    assert "k_sl_1a_d_r1" not in expected["1A"]
    assert "k_sl_1b_a_r1" not in expected["1B"]
