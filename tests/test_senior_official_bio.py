from __future__ import annotations

from storygame.story_package.loader import load_story_package
from tests import test_prompt_presence, test_richer_2c, test_richer_3a

ROOT = test_richer_3a.ROOT
PACKAGE = load_story_package(ROOT)
OFFICIAL_NPC = next(item for item in PACKAGE.world.npcs if item.id == "senior_official")
OFFICIAL_LINE = f"- Imprisoned senior official is {OFFICIAL_NPC.narrator_bio[0].lower()}{OFFICIAL_NPC.narrator_bio[1:]}"


def test_package_character_uses_the_official_narrator_bio() -> None:
    character = next(item for item in PACKAGE.characters if item.id == "senior_official")
    npc = next(item for item in PACKAGE.world.npcs if item.id == "senior_official")

    assert character.bio == npc.narrator_bio


def test_senior_official_narrator_bio_is_lasting_only() -> None:
    assert OFFICIAL_NPC.narrator_bio == (
        "A senior government official whom Charles has publicly blamed for the catastrophe. "
        "He is exhausted and observant."
    )
    assert "authority" not in OFFICIAL_NPC.narrator_bio


def test_senior_official_is_a_participant_only_in_3a() -> None:
    scenes = [
        scene.metadata.scene_id for scene in PACKAGE.scenes if "senior_official" in scene.metadata.participant_ids
    ]

    assert scenes == ["3A"]


def test_official_line_is_scene_scoped_in_characters_prompt() -> None:
    state, _engine = test_richer_3a._engine()
    assert OFFICIAL_LINE in test_prompt_presence._characters(state, "Look at the captives.")

    state, _engine = test_richer_2c._engine()
    assert OFFICIAL_LINE not in test_prompt_presence._characters(state, "Look around.")
