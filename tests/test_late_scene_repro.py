"""Offline characterization of late-scene vocabulary, records, and custody."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.reference_resolution import resolve_references
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LOCATIONS = {location.id: location for location in PACKAGE.world.locations}

EXPECTED_PLACE_FORMS_BY_SCENE = {
    "1A": (
        "Michelle's house",
        "Michelle's home",
        "the house",
        "kitchen",
        "outside the house",
        "outside",
        "the yard",
        "the driveway",
        "the street",
        "the curb",
        "the front of the house",
        "inside",
        "indoors",
        "the living room",
        "the front room",
        "the hallway",
    ),
    "1B": ("Los Angeles park",),
    "1C": ("freight terminal", "abandoned freight terminal", "processing line"),
    "2A": (
        "Facility perimeter",
        "Brandon's hideout",
        "hideout",
        "communications center",
        "infrastructure corridors",
        "restricted infrastructure corridors",
        "infrastructure corridor",
    ),
    "2B": (
        "records archive",
        "restricted records archive",
        "infrastructure corridors",
        "restricted infrastructure corridors",
        "infrastructure corridor",
    ),
    "2C": ("command levels", "command level", "upper command corridors"),
    "3A": ("detention level", "Los Angeles surface"),
    "3B": (
        "Broadcast relay",
        "security corridors",
        "executive office",
        "Los Angeles surface",
        "infrastructure corridors",
        "restricted infrastructure corridors",
        "infrastructure corridor",
    ),
    "3C": (
        "Broadcast relay",
        "executive office",
        "maintenance network",
        "maintenance route",
        "maintenance routes",
        "maintenance tunnel",
        "maintenance tunnels",
        "broadcast chamber",
        "Los Angeles surface",
    ),
}

EXPECTED_SCOPED_ALIASES_BY_SCENE = {
    "1A": {"chair": "workstation_chair", "front gate": "house_gate", "gate": "house_gate"},
    "1B": {
        "bench": "park_bench",
        "drain": "storm_drain",
        "tunnel": "storm_drain",
        "photograph": "michelle_photograph",
        "photo": "michelle_photograph",
    },
    "1C": {"captives": "captives", "captive": "captives", "prisoner": "captives", "prisoners": "captives"},
    "2A": {
        "servers": "hideout_servers",
        "gate": "facility_gate",
        "front gate": "facility_gate",
        "access panel": "cooling_service_archive_panel",
        "hidden panel": "cooling_service_archive_panel",
        "concealed panel": "cooling_service_archive_panel",
        "panel": "cooling_service_archive_panel",
        "grille": "cooling_service_archive_panel",
        "ventilation grille": "cooling_service_archive_panel",
        "seam": "cooling_service_archive_panel",
    },
    "2B": {
        "access panel": "cooling_service_archive_panel",
        "hidden panel": "cooling_service_archive_panel",
        "concealed panel": "cooling_service_archive_panel",
        "panel": "cooling_service_archive_panel",
        "grille": "cooling_service_archive_panel",
        "ventilation grille": "cooling_service_archive_panel",
        "seam": "cooling_service_archive_panel",
    },
    "2C": {
        "copied files": "copied_janus_files",
        "JANUS files": "copied_janus_files",
        "JANUS evidence": "copied_janus_files",
    },
    "3A": {
        "copied files": "copied_janus_files",
        "JANUS files": "copied_janus_files",
        "JANUS evidence": "copied_janus_files",
        "prisoners": "captives",
        "prisoner": "captives",
        "captives": "captives",
        "captive": "captives",
    },
    "3B": {
        "copied files": "copied_janus_files",
        "JANUS files": "copied_janus_files",
        "JANUS evidence": "copied_janus_files",
    },
    "3C": {
        "copied files": "copied_janus_files",
        "JANUS files": "copied_janus_files",
        "JANUS evidence": "copied_janus_files",
        "prisoners": "captives",
        "prisoner": "captives",
        "captives": "captives",
        "captive": "captives",
        "speakers": "emergency_speakers",
        "barrier": "watertight_barrier",
    },
}


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _scene_state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    apply_scene_placements(PACKAGE, state.facts, scene_id)
    return state


def _engine(
    monkeypatch: pytest.MonkeyPatch,
    state: RuntimeState,
    *,
    text: str = "The scene continues.",
    selected: tuple[str, ...] = (),
    grounding: tuple[str, ...] = (),
) -> RuntimeEngine:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    payload = {
        "narration": json.dumps(
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": text,
                        **({"grounding_ids": list(grounding)} if grounding else {}),
                    }
                ],
                "selected_knowledge_ids": list(selected),
            }
        )
    }
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda _request, **_kwargs: _Response(payload),
    )
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


def _declared_location_ids(scene: object) -> set[str]:
    metadata = scene.metadata  # type: ignore[union-attr]
    parents = {
        placement.parent
        for placement in (*metadata.item_placements.values(), *metadata.character_placements.values())
        if hasattr(placement, "parent")
    }
    return {entity_id for entity_id in (metadata.location_id, *parents) if entity_id in LOCATIONS}


def _place_forms(scene: object) -> tuple[str, ...]:
    return tuple(
        form
        for location_id in _declared_location_ids(scene)
        for form in (LOCATIONS[location_id].name, *LOCATIONS[location_id].aliases)
    )


def _scoped_aliases(scene: object) -> dict[str, str]:
    metadata = scene.metadata  # type: ignore[union-attr]
    in_scene = set(metadata.item_ids) | set(metadata.character_placements)
    return {
        alias: entity.id
        for entity in (*PACKAGE.world.groups, *PACKAGE.world.items)
        if entity.id in in_scene
        for alias in entity.scoped_aliases
    }


def test_late_scene_place_and_scoped_alias_declarations_are_characterized() -> None:
    for scene in PACKAGE.scenes:
        scene_id = scene.metadata.scene_id
        assert set(_place_forms(scene)) == set(EXPECTED_PLACE_FORMS_BY_SCENE[scene_id])
        assert _scoped_aliases(scene) == EXPECTED_SCOPED_ALIASES_BY_SCENE[scene_id]


@pytest.mark.parametrize("scene_id", tuple(EXPECTED_PLACE_FORMS_BY_SCENE))
def test_declared_place_forms_are_nameable_in_their_scene(scene_id: str) -> None:
    state = _scene_state(scene_id)
    validator = NarrationSafetyValidator()
    for form in EXPECTED_PLACE_FORMS_BY_SCENE[scene_id]:
        validator.validate(
            state,
            state,
            ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=f"{form} is quiet."),)),
            KnowledgeProjector(),
            "Look around.",
        )


def test_3c_captives_are_out_of_scope_where_the_story_places_them() -> None:
    """The captives wait in maintenance_network (under the command levels), not in the 3C scene or with Kristin."""

    result = resolve_references(_scene_state("3C"), "Inspect the captives.")
    assert result.question is None
    assert result.resolutions == ()


@pytest.mark.parametrize(
    ("scene_id", "text"),
    [
        ("2B", "A terminal hums beside the archive."),
        ("3A", "The gate opens beyond the corridor."),
        ("3B", "The archive evidence moves through the corridor."),
    ],
)
def test_ordinary_scene_words_are_not_rejected_as_place_leaks(
    monkeypatch: pytest.MonkeyPatch, scene_id: str, text: str
) -> None:
    result = _engine(monkeypatch, _scene_state(scene_id), text=text).turn("Look around.")
    assert result.segments[0].text == text


def test_future_facility_place_is_nameable_in_2C_by_design(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole regional-facility subtree is nameable, so 'broadcast chamber' is accepted before 3C."""

    text = "The broadcast chamber is quiet."
    result = _engine(monkeypatch, _scene_state("2C"), text=text).turn("Look around.")
    assert result.segments[0].text == text


@pytest.mark.parametrize("scene_id", ("2A", "3B"))
def test_corridor_place_names_are_accepted_before_the_access_reveal(scene_id: str) -> None:
    """The corridor is public vocabulary; naming it does not satisfy the access action evidence."""

    state = _scene_state(scene_id)

    def validate(text: str) -> None:
        NarrationSafetyValidator().validate(
            state,
            state,
            ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=text),)),
            KnowledgeProjector(),
            "Look around.",
        )

    validate("The infrastructure corridors are quiet.")
    validate("The infrastructure corridor is quiet.")


def test_3a_medical_record_reveal_places_the_entity_and_accepts_its_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _scene_state("3A")
    state.facts.assert_fact(Fact(predicate="michelle_reached", subject="story", value="true"))
    state.active_event_ids.add("SL-3A-B")
    assert world_for(PACKAGE, state.facts).parent("detention_medical_records") is None

    result = _engine(
        monkeypatch,
        state,
        text="Michelle shows Kristin experiment records.",
        selected=("k_sl_3a_b_r1",),
        grounding=("k_sl_3a_b_r1",),
    ).turn("Read the medical records.")

    assert result.selected_knowledge_ids == ("k_sl_3a_b_r1",)
    world = world_for(PACKAGE, state.facts)
    assert (world.parent("detention_medical_records"), world.relation("detention_medical_records")) == (
        "medical_level",
        "in",
    )


@pytest.mark.parametrize("scene_id", ("2C", "3A"))
def test_medical_file_bare_head_resolves_to_existing_copied_files(
    scene_id: str,
) -> None:
    result = resolve_references(_scene_state(scene_id), "Read the medical file.")
    assert result.resolutions == (("file", "copied_janus_files"),)


def test_2b_medical_terminal_does_not_collide_with_medical_records() -> None:
    state = _scene_state("2B")
    specific = resolve_references(state, "Read the medical terminal.")
    ambiguous = resolve_references(state, "Read the terminal.")

    assert specific.question is None
    assert specific.resolutions == ()
    assert ambiguous.question is not None
    assert ambiguous.question.options == (
        ("archive_terminals", "archive terminals"),
        ("medical_terminal", "medical terminal"),
    )
    assert ambiguous.question.noun == "terminal"
    assert (
        f"Do you mean {ambiguous.question.options[0][1]} or {ambiguous.question.options[1][1]}?"
        == "Do you mean archive terminals or medical terminal?"
    )


EXPECTED_HANDOFF_PLACEMENTS = {
    "2B": {
        "archive_terminals": ("janus_archive", "in"),
        "medical_terminal": ("janus_archive", "in"),
    },
    "2C": {"copied_janus_files": ("kristin", "carried_by")},
    "3A": {
        "copied_janus_files": ("kristin", "carried_by"),
        "override_codes": ("senior_official", "carried_by"),
        "stolen_radio": ("detention_level", "in"),
        "gate_status_panel": ("detention_level", "in"),
        "emergency_surface_gates": ("facility_escape", "in"),
        "captives": ("detention_level", "in"),
        "senior_official": ("captives", "in"),
        "michelle": ("detention_level", "in"),
        "brandon": ("detention_level", "in"),
    },
    "3B": {
        "copied_janus_files": ("kristin", "carried_by"),
        "rebecca_desk": ("executive_office", "in"),
        "inspection_console": ("infrastructure_corridors", "in"),
        "emergency_surface_gates": ("facility_escape", "in"),
        "brandon": ("security_corridors", "in"),
        "michelle": ("security_corridors", "in"),
    },
    "3C": {
        "copied_janus_files": ("kristin", "carried_by"),
        "portable_archive": ("rebecca", "carried_by"),
        "drainage_pump_controls": ("maintenance_network", "in"),
        "emergency_surface_gates": ("facility_escape", "in"),
        "captives": ("maintenance_network", "in"),
        "brandon": ("broadcast_relay", "in"),
        "michelle": ("broadcast_chamber", "in"),
        "kristin": ("broadcast_chamber", "in"),
    },
}


def test_nonmatching_filler_preserves_authored_custody_across_2a_to_3c(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, "2A")
    engine = _engine(monkeypatch, state)

    for target_scene, expected in EXPECTED_HANDOFF_PLACEMENTS.items():
        source_scene = state.current_scene_id
        while state.current_scene_id == source_scene:
            engine.turn("Look around.")
        assert state.current_scene_id == target_scene
        assert engine.last_attempt is not None
        assert engine.last_attempt.transition_cause == "forced"
        world = world_for(PACKAGE, state.facts)
        assert {entity_id: (world.parent(entity_id), world.relation(entity_id)) for entity_id in expected} == expected

    world = world_for(PACKAGE, state.facts)
    assert (world.parent("transit_card"), world.relation("transit_card")) == ("park_bench", "under")
