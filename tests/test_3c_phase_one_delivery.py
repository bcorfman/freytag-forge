from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package


@pytest.mark.parametrize(
    ("knowledge_id", "required_text"),
    [
        ("k_sl_3c_e_r1", "conflict among survivors"),
        ("k_sl_3c_e_r2", "conflict among those who remained"),
    ],
)
def test_phase_one_and_phase_two_delivery(knowledge_id: str, required_text: str) -> None:
    package = load_story_package(Path("data/stories/continuity-initiative"))
    delivery_text = package.knowledge_indexes.by_id[knowledge_id].delivery_text

    assert "Phase One" in delivery_text
    assert required_text in delivery_text
    if knowledge_id == "k_sl_3c_e_r2":
        assert "unknown location" in delivery_text
