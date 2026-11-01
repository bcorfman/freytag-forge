from scripts.generate_spine_expected_reveals import (
    knowledge_items as _knowledge,
)
from scripts.generate_spine_expected_reveals import (
    simulate_expected_reveals,
)

SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def test_committed_expectation_matches_the_engine_simulation() -> None:
    simulated = simulate_expected_reveals()
    assert tuple(simulated) == SCENES
    assert all(
        item_id.startswith(("k_scene_", "k_sl_", "k_resolution_")) for ids in simulated.values() for item_id in ids
    )


def test_expected_reveal_ids_are_current_and_scene_specific() -> None:
    expected = simulate_expected_reveals()
    knowledge = _knowledge()

    assert all(ids == sorted(ids) for ids in expected.values())
    assert all(item_id in knowledge for ids in expected.values() for item_id in ids)
    assert {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2a")
        and item.get("available_in_scenes") == ["2A"]
        and item.get("audience", {}).get("player_visible", True)
    } == {
        "k_sl_2a_c_r5",
        "k_sl_2a_c_r6",
        "k_sl_2a_b_r1",
    }
    assert {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2b")
        and item.get("available_in_scenes") == ["2B"]
        and item.get("audience", {}).get("player_visible", True)
    } == {"k_sl_2b_a_r1", "k_sl_2b_b_r4", "k_sl_2b_b_r5", "k_sl_2b_c_r3"}
    assert {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2c")
        and item.get("available_in_scenes") == ["2C"]
        and item.get("audience", {}).get("player_visible", True)
    } == {
        "k_sl_2c_d_r3",
        "k_sl_2c_d_r4",
    }
    assert expected["3C"] == [
        "k_sl_3c_a_r1",
        "k_sl_3c_b_r2",
        "k_sl_3c_c_r1",
        "k_sl_3c_c_r2",
        "k_sl_3c_d_r1",
        "k_sl_3c_d_r2",
        "k_sl_3c_e_r1",
    ]
    assert all(not item_id.startswith(("k_sl_2a_a_", "k_sl_2a_e_")) for ids in expected.values() for item_id in ids)
    assert expected["1C"] == ["k_sl_1c_a_r1", "k_sl_1c_b_r1", "k_sl_1c_c_copy_numbers"]
    assert "k_sl_1a_d_r1" not in expected["1A"]
    assert "k_sl_1b_a_r1" not in expected["1B"]
