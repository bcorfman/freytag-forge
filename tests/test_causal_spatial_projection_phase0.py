from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.authoring.candidate_review import ReviewedCausalStory
from storygame.authoring.compiler import _causal_story_as_compiled_story, load_compiled_story_fixture
from storygame.authoring.contracts import ItemDefinition, OpeningContact, OpeningMetadata
from storygame.authoring.spatial_audit import audit_runtime_projection
from storygame.runtime.state import bootstrap_runtime_state


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_cross_genre_suggested_actions_require_current_fact_backed_targets(genre: str) -> None:
    story = load_compiled_story_fixture(genre, Path("data/compiled_stories/v1"))
    location = str(story.initial_world_state["location"])
    contact = story.characters[0]
    item = ItemDefinition(
        id="opening_token",
        name="opening token",
        kind="story_object",
        description="A visible object that can ground an investigative suggestion.",
        initial_holder=f"location:{location}",
    )
    opening = OpeningMetadata(
        scene="A public opening scene.",
        protagonist_context="You have a reason to act.",
        arrival_context="You have just arrived.",
        public_briefing=("The immediate situation is public.",),
        scene_purpose="Offer one social and one investigative lead.",
        contacts=(
            OpeningContact(
                id=contact.id,
                name=contact.name,
                role=contact.role,
                relationship="opening contact",
                location=location,
            ),
        ),
        first_available_actions=(
            f"Speak with {contact.name}.",
            "Inspect the opening token.",
            "Question the gathered witnesses.",
        ),
    )
    projected = story.model_copy(update={"opening": opening, "item_definitions": (item,)})

    report = audit_runtime_projection(projected)

    assert [action.supported for action in report.suggested_actions] == [True, True, False]
    assert report.suggested_actions[0].target_kinds == ("present_npc",)
    assert report.suggested_actions[1].target_kinds == ("visible_item",)
    assert report.unsupported_suggested_actions == ("Question the gathered witnesses.",)


def test_vale_blueprint_locations_and_holders_are_lost_before_runtime_facts() -> None:
    fixture_root = Path("data/compiled_stories/v2")
    fixture_map = json.loads((fixture_root / "runtime-fixtures.json").read_text(encoding="utf-8"))
    reviewed_path = fixture_root / fixture_map["fixtures"]["mystery"]
    reviewed = ReviewedCausalStory.model_validate(json.loads(reviewed_path.read_text(encoding="utf-8")))
    compiled = _causal_story_as_compiled_story(reviewed.story)

    report = audit_runtime_projection(
        compiled,
        participant_ids=tuple(participant.id for participant in reviewed.story.participants),
        evidence_opportunity_ids=tuple(opportunity.id for opportunity in reviewed.story.evidence_opportunities),
    )
    state = bootstrap_runtime_state(compiled)

    assert len(reviewed.story.evidence_opportunities) == 23
    assert report.participant_placements.declared_count == 7
    assert report.participant_placements.fact_backed_count == 1
    assert report.evidence_realization.declared_count == 23
    assert report.evidence_realization.fact_backed_count == 0
    assert report.evidence_custody.missing_ids == report.evidence_realization.declared_ids
    assert report.scene_subjects.declared_count == 0
    assert report.group_encounters.declared_count == 0
    assert report.unsupported_suggested_actions == reviewed.story.opening.first_available_actions
    assert len(state.facts.matching("at")) == 1
    assert state.facts.has("at", "player", "grand_foyer")
    assert state.facts.matching("present") == ()
    assert state.facts.matching("custody") == ()
