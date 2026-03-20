from __future__ import annotations

import textwrap
from random import Random

from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import _infer_binary_pronouns, build_default_state
from storygame.engine.world_builder import _extract_character_names, build_world_package, select_story_outline


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
    assert package["goals"]["setup"]
    assert package["beat_candidates"]
    assert package["item_graph"]["items"]
    assert package["trigger_seeds"]


def test_build_world_package_uses_generic_placeholder_goals_until_bootstrap(tmp_path) -> None:
    outlines = tmp_path / "story_outlines.yaml"
    outlines.write_text(
        textwrap.dedent(
            """
            stories:
              - id: mystery_custom_001
                genre: mystery
                outline: |
                  Premise: The mayor vanished after the lantern festival and the town square was sealed.
                  Scene: Old town square.
                  Characters: Inspector Vale, Archivist Rowan.
            """
        ).strip()
    )

    package = build_world_package(
        genre="mystery",
        session_length="medium",
        seed=7,
        tone="neutral",
        outlines_path=outlines,
    )

    primary = package["goals"]["primary"].lower()
    setup = package["goals"]["setup"].lower()
    assert primary == "uncover who is behind the case and why the truth was buried."
    assert setup == "review the case file, question your first contact, and identify the strongest lead."
    assert "mayor vanished" not in primary
    assert "lantern festival" not in setup


def test_active_goal_starts_with_setup_then_refines_to_primary() -> None:
    state = build_default_state(seed=91, genre="drama", tone="dark")
    setup_goal = state.world_package["goals"]["setup"]
    primary_goal = state.world_package["goals"]["primary"]
    assert state.active_goal == setup_goal

    rng = Random(91)
    for _ in range(6):
        state, _events, _beat, _template = advance_turn(state, parse_command("look"), rng)

    assert state.active_goal == primary_goal


def test_story_plan_seeds_only_hidden_threads_for_later_bootstrap(tmp_path) -> None:
    outlines = tmp_path / "story_outlines.yaml"
    outlines.write_text(
        textwrap.dedent(
            """
            stories:
              - id: mystery_detective_001
                genre: mystery
                outline: |
                  Situation: A detective, embittered by a past failure and now living the life of a recluse in a secluded mansion, is tasked with solving one last case that leads him to a confrontation with the ghosts of his past and a choice between justice and mercy.
            """
        ).strip()
    )

    package = build_world_package(
        genre="mystery",
        session_length="medium",
        seed=12,
        outlines_path=outlines,
    )

    plan = package["story_plan"]
    assert plan["protagonist_name"] == "Detective Elias Wren"
    assert len(plan["setup_paragraphs"]) == 3
    opening_text = "\n".join(plan["setup_paragraphs"]).lower()
    assert "choice between justice and mercy" not in opening_text
    assert "confrontation with the ghosts of his past" not in opening_text
    assert "you are detective elias wren" in opening_text
    assert "your first objective is clear" in opening_text

    hidden_text = "\n".join(plan["hidden_threads"]).lower()
    assert "choice between justice and mercy" in hidden_text
    assert "ghosts of his past" in hidden_text
    setup_goal = package["goals"]["setup"].lower()
    assert "tasked with." not in setup_goal
    assert "is tasked with" not in setup_goal
    assert "case file" in setup_goal


def test_extract_character_names_reads_outline_character_lines() -> None:
    outline = "Characters:\nAri Vale: Investigator.\nMina Cole: Archivist.\n"
    names = _extract_character_names(outline)
    assert names[:2] == ["Ari Vale", "Mina Cole"]


def test_extract_character_names_ignores_outline_section_labels() -> None:
    outline = "Premise: A detective returns.\nScene: Manor gate.\nCharacters:\nAri Vale: Investigator.\n"
    names = _extract_character_names(outline)
    assert "Premise" not in names
    assert "Scene" not in names
    assert names[0] == "Ari Vale"


def test_infer_binary_pronouns_uses_likely_name_gender() -> None:
    assert _infer_binary_pronouns("Daria Stone") == "she/her"
    assert _infer_binary_pronouns("Alexander Grey") == "he/him"


def test_generated_npcs_use_binary_pronouns() -> None:
    state = build_default_state(seed=101, genre="mystery")
    assert state.world.npcs
    assert all(npc.pronouns in {"he/him", "she/her"} for npc in state.world.npcs.values())


def test_mystery_world_package_pins_daria_stone_as_first_contact() -> None:
    package = build_world_package(genre="mystery", session_length="short", seed=103, tone="dark")

    assert package["entities"]["npcs"][0] == "Daria Stone"


def test_mystery_start_room_places_daria_stone_beside_player() -> None:
    state = build_default_state(seed=104, genre="mystery", tone="dark")
    start_npc_id = state.world.rooms[state.player.location].npc_ids[0]

    assert start_npc_id == "daria_stone"
    assert state.world.npcs[start_npc_id].name == "Daria Stone"


def test_mystery_start_room_north_exit_leads_into_foyer() -> None:
    state = build_default_state(seed=102, genre="mystery")

    assert state.player.location == "front_steps"
    assert state.world.rooms["front_steps"].exits["north"] == "foyer"

    next_state, _events, _beat, _template = advance_turn(state, parse_command("go north"), Random(102))
    assert next_state.player.location == "foyer"
