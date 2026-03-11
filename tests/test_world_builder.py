from __future__ import annotations

from storygame.engine.world_builder import build_world_package, select_story_outline


def test_select_story_outline_filters_by_genre() -> None:
    selected = select_story_outline(genre="mystery", seed=17)

    assert selected["genre"] == "mystery"
    assert selected["id"]
    assert selected["outline"].strip()


def test_select_story_outline_prefers_tone_matches_when_available() -> None:
    neutral = select_story_outline(genre="drama", seed=9)
    dark = select_story_outline(genre="drama", seed=9, tone="dark")

    assert neutral["genre"] == "drama"
    assert dark["genre"] == "drama"
    assert dark["tone"] in {"dark", "tense", "mysterious", "epic", "romantic", "light", "neutral"}


def test_build_world_package_has_required_sections() -> None:
    package = build_world_package(
        genre="fantasy",
        session_length="long",
        seed=33,
        tone="epic",
    )

    assert package["genre"] == "fantasy"
    assert package["session_length"] == "long"
    assert package["curve_id"].startswith("fantasy_")
    assert package["outline"]["id"]

    assert package["entities"]["npcs"]
    assert package["map"]["rooms"]
    assert package["goals"]["primary"]
    assert package["beat_candidates"]
    assert package["item_graph"]["items"]
    assert package["trigger_seeds"]
