from __future__ import annotations

import json
from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import FactOperation, NarrationSegment, ResolvedTurnProposal, StoryEventProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    Audience,
    CharacterPlacement,
    FactDefinition,
    KnowledgeCatalog,
    KnowledgeDefinition,
    KnowledgeIndexes,
    Location,
    Npc,
    PacingSource,
    RevealSource,
    RouteOperation,
    RouteRealization,
    Scene,
    SceneBeat,
    SceneFrame,
    SceneMetadata,
    ScenePacing,
    Storylet,
    StoryletRoute,
    StoryletRoutesSource,
    StoryPackage,
    WorldSource,
)

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _normal_response(_request: object, **_kwargs: object) -> _Response:
    return _Response(
        {
            "narration": json.dumps(
                {
                    "segments": [{"kind": "narration", "text": "Kristin looks."}],
                    "selected_knowledge_ids": [],
                }
            )
        }
    )


def _fixture_knowledge(
    item_id: str,
    realization_id: str,
    *,
    requires: tuple[tuple[str, bool], ...] = (),
    fact_id: str,
    repeatable: bool = False,
) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id=item_id,
        statement=f"The story establishes {fact_id}.",
        aliases=(item_id,),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        requires=tuple({"fact_id": fact_id, "equals": equals} for fact_id, equals in requires),
        establishes=(RouteOperation(op="assert", fact_id=fact_id, value=True),),
        source=RevealSource(kind="storylet_realization", storylet_id="SL-1A-X", realization_id=realization_id),
        repeatable=repeatable,
    )


def _fixture_package() -> StoryPackage:
    base = _fixture_knowledge("k_base", "SL-1A-X-R1", fact_id="base_fact")
    follow_up = _fixture_knowledge(
        "k_follow_up", "SL-1A-X-R2", requires=(("base_fact", True),), fact_id="follow_up_fact"
    )
    repeatable = _fixture_knowledge(
        "k_repeatable", "SL-1A-X-R3", requires=(("base_fact", True),), fact_id="repeatable_fact", repeatable=True
    )
    alternative = _fixture_knowledge("k_alternative", "SL-1A-X-R4", fact_id="alternative_fact")
    knowledge = (base, follow_up, repeatable, alternative)
    scene_beat = SceneBeat(
        id="1A.1", anchor="opening", title="Opening", prose="A room.", details=("One.", "Two.", "Three.")
    )
    scene = Scene(
        metadata=SceneMetadata(
            scene_id="1A",
            location_id="room",
            freytag_phase="exposition",
            objective="Inspect the room",
            entry_text="A room waits.",
            character_placements={"hero": CharacterPlacement(parent="room")},
        ),
        prose="A room.",
        beats={"opening": scene_beat},
        opening_beat=scene_beat,
    )
    storylet_id = "SL-1A-X"
    realization_facts = ("base_fact", "follow_up_fact", "repeatable_fact", "alternative_fact")
    realizations = tuple(
        RouteRealization(
            id=f"{storylet_id}-R{number}",
            dramatic_intent="A fixture turn.",
            operations=(RouteOperation(op="assert", fact_id=fact_id, value=True),),
        )
        for number, fact_id in enumerate(realization_facts, start=1)
    )
    route = StoryletRoute(
        id=storylet_id,
        scene_id="1A",
        title="Fixture storylet",
        earliest_turn=0,
        target_turn=1,
        latest_turn=3,
        pressure_role="Test follow-ups",
        realizations=realizations,
    )
    catalog = KnowledgeCatalog(
        schema_version="2.0",
        facts=tuple(
            FactDefinition(id=fact_id, purpose="fixture")
            for fact_id in (
                "base_fact",
                "follow_up_fact",
                "repeatable_fact",
                "alternative_fact",
            )
        ),
        scene_frames=(SceneFrame(scene_id="1A", situation="A room.", pressure="Inspect the room"),),
        knowledge=knowledge,
    )
    indexes = KnowledgeIndexes(
        by_id={item.id: item for item in knowledge},
        facts_to_knowledge={},
        source_to_knowledge={},
        scene_to_candidates={"1A": tuple(item.id for item in knowledge)},
        alias_to_knowledge={},
        audience_to_known_terms={},
        prerequisite_dependents={},
    )
    return StoryPackage(
        story_id="fixture_story",
        protagonist_id="hero",
        scenes=(scene,),
        world=WorldSource(
            story_id="fixture_story",
            protagonist_id="hero",
            locations=(Location(id="room", name="the room"),),
            npcs=(Npc(id="hero", name="Ari"),),
            items=(),
            facts=("base_fact", "follow_up_fact", "repeatable_fact", "alternative_fact"),
        ),
        pacing=PacingSource(
            budget_seconds=10,
            scenes=(ScenePacing(scene_id="1A", min_turns=0, nudge_after_turns=1, handoff_after_turns=2),),
            transitions=(),
        ),
        storylets=(
            Storylet(
                id=storylet_id,
                scene_id="1A",
                title="Fixture storylet",
                source_links=("fixture",),
                sections={},
                earliest_turn=0,
                target_turn=1,
                latest_turn=3,
            ),
        ),
        storylet_routes=StoryletRoutesSource(
            story_id="fixture_story", canonical_scene_chain=("1A",), sole_ending_scene_id="1A", storylets=(route,)
        ),
        knowledge=catalog,
        knowledge_indexes=indexes,
        deliveries=(),
    )


def _fixture_event(realization_id: str, fact_id: str) -> StoryEventProposal:
    return StoryEventProposal(
        event_id="SL-1A-X",
        realization_id=realization_id,
        operations=(
            FactOperation(operation="assert", fact={"predicate": fact_id, "subject": "story", "value": "true"}),
        ),
    )


def _fixture_commit(state: RuntimeState, realization_id: str, fact_id: str) -> None:
    proposal = ResolvedTurnProposal(
        segments=(NarrationSegment(kind="narration", text="A fixture turn."),),
        events=(_fixture_event(realization_id, fact_id),),
    )
    ProgressionValidator(state.package).validate_effects(state, proposal)
    state.apply_proposal(proposal)


def test_follow_up_realizations_rearm_only_sibling_dependent_routes() -> None:
    package = _fixture_package()
    state = RuntimeState(package=package, current_scene_id="1A", phase="exposition", active_event_ids={"SL-1A-X"})
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "A turn."}]})
    projector = KnowledgeProjector()

    assert package.follow_up_realization_ids == {"SL-1A-X-R2", "SL-1A-X-R3"}
    before = {candidate.id for candidate in projector._candidates(state, "player", ())}
    assert "k_follow_up" not in before
    assert "k_repeatable" not in before
    assert "k_alternative" in before

    _fixture_commit(state, "SL-1A-X-R1", "base_fact")
    assert state.fired_event_ids == {"SL-1A-X"}
    engine._activate_pacing()
    after_base = {candidate.id for candidate in projector._candidates(state, "player", ())}
    assert {"k_follow_up", "k_repeatable"} <= after_base
    assert "k_alternative" not in after_base

    _fixture_commit(state, "SL-1A-X-R2", "follow_up_fact")
    engine._activate_pacing()
    after_follow_up = {candidate.id for candidate in projector._candidates(state, "player", ())}
    assert "k_follow_up" not in after_follow_up
    assert "k_repeatable" in after_follow_up
    assert state.fired_event_ids == {"SL-1A-X"}

    _fixture_commit(state, "SL-1A-X-R3", "repeatable_fact")
    assert state.fired_event_ids == {"SL-1A-X"}


def _real_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    return state


def _real_engine(monkeypatch, state: RuntimeState) -> RuntimeEngine:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


def test_drawer_follow_ups_work_through_real_turns_without_rearming(monkeypatch) -> None:
    state = _real_state()
    engine = _real_engine(monkeypatch, state)

    engine.turn("Open the drawer.")
    result = engine.turn("Close the drawer.")

    assert result.selected_knowledge_ids == ("k_sl_1a_f_r3",)
    assert any(fact.predicate == "drawer_gap_pointed_out" and fact.value == "true" for fact in state.facts.asserted)
    assert "SL-1A-F" in state.fired_event_ids

    result = engine.turn("Check the drawer.")
    assert result.selected_knowledge_ids == ("k_sl_1a_f_r2",)


def test_phone_follow_up_works_through_real_turns(monkeypatch) -> None:
    state = _real_state()
    engine = _real_engine(monkeypatch, state)

    engine.turn("Unlock the phone.")
    engine.turn("Read Michelle's text.")
    result = engine.turn("Check the call log.")

    assert result.selected_knowledge_ids == ("k_sl_1a_j_r3",)
    assert "SL-1A-J" in state.fired_event_ids
