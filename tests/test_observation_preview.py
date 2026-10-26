from __future__ import annotations

import copy

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_preview import CallMemo
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.models import (
    Audience,
    Character,
    CharacterPlacement,
    FactDefinition,
    Item,
    ItemPlacement,
    KnowledgeCatalog,
    KnowledgeDefinition,
    KnowledgeIndexes,
    Location,
    Npc,
    PacingSource,
    RevealSource,
    RouteOperation,
    Scene,
    SceneBeat,
    SceneFrame,
    SceneMetadata,
    ScenePacing,
    StoryletRoutesSource,
    StoryPackage,
    WorldSource,
)
from tests.test_observation_mode import _state_at


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _provider():
    state = _state_at("outside_house", already_aboard=True)
    provider = build_capture_provider(state)
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    provider._pending_item_facts_present = True
    return state, provider


def _ask(score: float | None, calls: list[tuple[object, object]]):
    def ask(state, questions):
        calls.append((state, questions))
        if score is None:
            return None
        return {key: {"noul": score} for key in questions}

    return ask


def _capture(provider, ask, score=1.0):
    calls = []
    capture = WorldCapture(provider, ask or _ask(score, calls))
    capture.enforcing_verifier = ObservationVerifier(capture.ask)
    return capture, calls


def _set_raw(provider, raw):
    provider._pending_item_facts = copy.deepcopy(raw)
    provider._pending_item_facts_present = True


def _provider_snapshot(provider):
    excluded = {"_turn_request_count", "_turn_item_facts_request_count", "request_count"}

    def plain(value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return copy.deepcopy(value)
        if isinstance(value, list):
            return [plain(item) for item in value]
        if isinstance(value, tuple):
            return tuple(plain(item) for item in value)
        if isinstance(value, set):
            return {plain(item) for item in value}
        if isinstance(value, dict):
            return {plain(key): plain(item) for key, item in value.items()}
        return None

    snapshot = {}
    for key, value in vars(provider).items():
        if key in excluded or callable(value):
            continue
        snapshot[key] = plain(value)
    return snapshot


def test_preview_is_off_by_default_and_does_not_touch_provider():
    state, provider = _provider()
    before = _provider_snapshot(provider)
    calls = []
    capture = WorldCapture(provider, _ask(1.0, calls))
    result = capture.preview_commit(
        "Inspect the truck.", "The truck is quiet.", copy.deepcopy(state), entered_scene=False
    )

    assert result.required is False
    assert result.accepted is True
    assert result.outcome == "not_required"
    assert calls == []
    assert _provider_snapshot(provider) == before
    assert provider.state is state


def test_preview_restores_every_provider_field_after_accept_and_reject():
    for score in (1.0, 0.0):
        state, provider = _provider()
        _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
        before_facts = state.facts.clone()
        before = _provider_snapshot(provider)
        capture, _calls = _capture(provider, None, score)

        result = capture.preview_commit(
            "Inspect the truck.", "A quiet narration.", copy.deepcopy(state), entered_scene=False
        )

        assert result.accepted is (score == 1.0)
        assert state.facts == before_facts
        assert provider.state is state
        assert _provider_snapshot(provider) == before


def test_preview_restores_every_provider_field_when_item_facts_raises(monkeypatch: pytest.MonkeyPatch):
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    before_facts = state.facts.clone()
    before = _provider_snapshot(provider)
    capture, _calls = _capture(provider, None, 1.0)

    def explode(*_args, **_kwargs):
        raise NarrationProviderError("candidate failure", 503, "candidate_failure")

    monkeypatch.setattr(provider, "apply_item_facts", explode)
    with pytest.raises(NarrationProviderError):
        capture.preview_commit("Inspect the truck.", "A quiet narration.", copy.deepcopy(state), entered_scene=False)

    assert state.facts == before_facts
    assert provider.state is state
    assert _provider_snapshot(provider) == before


def test_preview_applies_facts_to_candidate_only():
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    candidate = copy.deepcopy(state)
    capture, _calls = _capture(provider, None, 1.0)

    result = capture.preview_commit("Inspect the truck.", "The laptop is visible.", candidate, entered_scene=False)

    assert "Kristin's laptop" in result.changed
    assert result.facts_after
    assert state.facts == _state_at("outside_house", already_aboard=True).facts
    assert world_for(candidate.package, candidate.facts).parent("kristin_laptop") == "truck_driver_seat"


@pytest.mark.parametrize(
    ("score", "expected_accepted", "expected_outcome"),
    ((1.0, True, "ok"), (0.0, False, "ok"), (None, False, "unavailable"), (0.5, False, "ok")),
)
def test_preview_verdict_is_fail_closed_and_generic(score, expected_accepted, expected_outcome):
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    calls = []
    capture = WorldCapture(provider, _ask(score, calls))
    capture.enforcing_verifier = ObservationVerifier(capture.ask)
    narration = "Narration text must not become a failure code."

    result = capture.preview_commit("Inspect the truck.", narration, copy.deepcopy(state), entered_scene=False)

    assert result.accepted is expected_accepted
    assert result.outcome == expected_outcome
    assert narration not in str(result.failure)
    assert all(set(verdict) == {"thing", "verdict", "score"} for verdict in result.verdicts)


def test_unrelated_move_rejects_but_focus_move_is_allowed():
    state, provider = _provider()
    _set_raw(provider, {"Michelle's phone": {"place": "Michelle's house"}})
    capture, _calls = _capture(provider, None, 1.0)

    result = capture.preview_commit(
        "Inspect the truck.", "The truck is quiet.", copy.deepcopy(state), entered_scene=False
    )

    assert result.accepted is False
    assert result.outcome == "unrelated_move"
    assert result.moved_unrelated == ("Michelle's phone",)

    provider.observation_request = ObservationRequest("Inspect the laptop.", "look", "kristin_laptop")
    _set_raw(provider, {"Kristin's laptop": {"place": "kitchen"}, "Kristin": {"place": "kitchen"}})
    result = capture.preview_commit(
        "Inspect the truck.", "The truck is quiet.", copy.deepcopy(state), entered_scene=False
    )
    assert result.accepted is True


def test_preview_baseline_includes_proposal_move_before_item_facts():
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    candidate = copy.deepcopy(state)
    assert world_for(candidate.package, candidate.facts).move("michelle_phone", "mcgehee_home").ok
    capture, _calls = _capture(provider, None, 1.0)

    result = capture.preview_commit("Inspect the truck.", "The truck is quiet.", candidate, entered_scene=False)

    assert result.accepted is True
    assert result.moved_unrelated == ()


def test_preview_flags_only_item_facts_move_after_proposal_move():
    state, provider = _provider()
    _set_raw(provider, {"workstation chair": {"place": "Michelle's house"}})
    candidate = copy.deepcopy(state)
    assert world_for(candidate.package, candidate.facts).move("michelle_phone", "mcgehee_home").ok
    capture, _calls = _capture(provider, None, 1.0)

    result = capture.preview_commit("Inspect the truck.", "The truck is quiet.", candidate, entered_scene=False)

    assert result.accepted is False
    assert result.outcome == "unrelated_move"
    assert result.moved_unrelated == ("workstation chair",)


def test_preview_no_relations_rejects_unrelated_move_without_asking():
    state, provider = _provider()
    provider.observation_request = ObservationRequest("Look at the house.", "look", "mcgehee_home")
    _set_raw(provider, {"workstation chair": {"place": "Michelle's house"}})
    capture, calls = _capture(provider, None, 1.0)

    result = capture.preview_commit(
        "Look at the house.", "The house is quiet.", copy.deepcopy(state), entered_scene=False
    )

    assert result.accepted is False
    assert result.outcome == "unrelated_move"
    assert result.failure == "unrelated_move"
    assert result.moved_unrelated == ("workstation chair",)
    assert calls == []


def test_preview_no_relations_without_move_is_not_required():
    state, provider = _provider()
    provider.observation_request = ObservationRequest("Look at the house.", "look", "mcgehee_home")
    _set_raw(provider, {})
    capture, calls = _capture(provider, None, 1.0)

    result = capture.preview_commit(
        "Look at the house.", "The house is quiet.", copy.deepcopy(state), entered_scene=False
    )

    assert result.accepted is True
    assert result.outcome == "not_required"
    assert result.failure is None
    assert result.moved_unrelated == ()
    assert calls == []


def _synthetic_package() -> StoryPackage:
    scene = Scene(
        metadata=SceneMetadata(
            scene_id="1A",
            location_id="room",
            freytag_phase="exposition",
            objective="inspect the tray",
            item_ids=("tray", "lens", "remote_marker"),
            entry_text="A room waits.",
            item_placements={
                "tray": ItemPlacement(parent="room"),
                "lens": ItemPlacement(parent="tray"),
                "remote_marker": ItemPlacement(parent="yard"),
            },
            character_placements={"hero": CharacterPlacement(parent="room")},
        ),
        prose="A room.",
        beats={
            "opening": SceneBeat(
                id="1A.1", anchor="opening", title="Opening", prose="A room.", details=("One.", "Two.", "Three.")
            )
        },
        opening_beat=SceneBeat(
            id="1A.1", anchor="opening", title="Opening", prose="A room.", details=("One.", "Two.", "Three.")
        ),
    )
    world = WorldSource(
        story_id="second_story",
        protagonist_id="hero",
        locations=(
            Location(id="room", name="the room"),
            Location(id="yard", name="the yard"),
            Location(id="field", name="the far field"),
        ),
        npcs=(Npc(id="hero", name="Ari"),),
        items=(
            Item(id="tray", name="survey tray", kind="supporter"),
            Item(id="lens", name="calibrated lens"),
            Item(id="remote_marker", name="remote marker"),
        ),
        facts=("scene_1a_entry_known",),
    )
    catalog = KnowledgeCatalog(
        schema_version="2.0",
        facts=(FactDefinition(id="scene_1a_entry_known", purpose="entry"),),
        scene_frames=(SceneFrame(scene_id="1A", situation="The room is ready.", pressure="Inspect the tray"),),
        knowledge=(
            KnowledgeDefinition(
                id="lens_detail",
                statement="The calibrated lens is clear.",
                entity_ids=("lens",),
                reach_entity_ids=("lens",),
                aliases=("clear lens",),
                audience=Audience(kind="public", player_visible=True),
                available_in_scenes=("1A",),
                establishes=(RouteOperation(op="assert", fact_id="scene_1a_entry_known", value=True),),
                source=RevealSource(kind="scene_entry"),
            ),
        ),
    )
    indexes = KnowledgeIndexes(
        by_id={},
        facts_to_knowledge={},
        source_to_knowledge={},
        scene_to_candidates={"1A": ()},
        alias_to_knowledge={},
        audience_to_known_terms={},
        prerequisite_dependents={},
    )
    return StoryPackage(
        story_id="second_story",
        protagonist_id="hero",
        characters=(Character(id="hero", name="Ari", bio="A traveler."),),
        scenes=(scene,),
        world=world,
        pacing=PacingSource(
            budget_seconds=10,
            scenes=(ScenePacing(scene_id="1A", min_turns=0, nudge_after_turns=1, handoff_after_turns=1),),
            transitions=(),
        ),
        storylets=(),
        storylet_routes=StoryletRoutesSource(
            story_id="second_story", canonical_scene_chain=("1A",), sole_ending_scene_id="1A", storylets=()
        ),
        knowledge=catalog,
        knowledge_indexes=indexes,
        deliveries=(),
    )


def _synthetic_provider():
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
    provider._pending_item_facts_present = True
    return state, provider


@pytest.mark.parametrize(("score", "expected_accepted"), ((1.0, True), (0.0, False)))
def test_preview_synthetic_story_accepts_rejects_and_restores_provider(score, expected_accepted):
    state, provider = _synthetic_provider()
    _set_raw(provider, {"calibrated lens": {"place": "survey tray"}})
    before = _provider_snapshot(provider)
    capture, _calls = _capture(provider, None, score)

    result = capture.preview_commit(
        "Inspect the survey tray.", "The calibrated lens catches the light.", copy.deepcopy(state), entered_scene=False
    )

    assert result.accepted is expected_accepted
    assert result.verdicts[0]["thing"] == "calibrated lens"
    assert _provider_snapshot(provider) == before


def test_preview_synthetic_story_flags_unrelated_move():
    state, provider = _synthetic_provider()
    _set_raw(provider, {"remote marker": {"place": "the far field"}})
    candidate = copy.deepcopy(state)
    capture, _calls = _capture(provider, None, 1.0)

    result = capture.preview_commit(
        "Inspect the survey tray.", "The calibrated lens catches the light.", candidate, entered_scene=False
    )

    assert result.accepted is False
    assert result.outcome == "unrelated_move"
    assert result.moved_unrelated == ("remote marker",)


def test_preview_replays_match_and_confirm_without_second_billed_call(monkeypatch: pytest.MonkeyPatch):
    state, provider = _provider()
    raw = {"new pebble": {"place": "driver's seat"}}
    _set_raw(provider, raw)
    match_calls = []

    def match(_provider, _payload):
        match_calls.append(True)
        return {"same_as": {"new pebble": "Kristin's laptop"}}

    monkeypatch.setattr(CloudflareTurnProvider, "_request_item_facts", match)
    confirm_calls = []

    def ask(state_arg, questions):
        confirm_calls.append((state_arg, questions))
        return {key: {"noul": 1.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture.enforcing_verifier = ObservationVerifier(ask)
    narration = "The laptop is visible."
    candidate = copy.deepcopy(state)
    capture.preview_commit("Inspect the truck.", narration, candidate, entered_scene=False)
    record = capture.after_commit("Inspect the truck.", narration, entered_scene=False)

    assert len(match_calls) == 1
    assert len(confirm_calls) == 2
    assert record["observation_preview"]["accepted"] is True
    assert record["observation_diverged"] is False


def test_different_take_preview_arguments_drop_memo(monkeypatch: pytest.MonkeyPatch):
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    match_calls = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: match_calls.append(True) or {"same_as": {}},
    )
    capture, _calls = _capture(provider, None, 1.0)
    capture.preview_commit("Inspect the truck.", "The laptop is visible.", copy.deepcopy(state), entered_scene=False)

    capture.after_commit("Inspect the truck.", "A different narration.", entered_scene=False)

    assert capture._pending_preview is None


def test_preview_diverges_when_real_state_changes_before_commit():
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    capture, _calls = _capture(provider, None, 1.0)
    narration = "The laptop is visible."
    capture.preview_commit("Inspect the truck.", narration, copy.deepcopy(state), entered_scene=False)

    world_for(state.package, state.facts).set_conditions("kristin_laptop", ["tampered"])
    record = capture.after_commit("Inspect the truck.", narration, entered_scene=False)

    assert record["observation_diverged"] is True


def test_preview_verifier_budget_resets_at_before_turn(monkeypatch: pytest.MonkeyPatch):
    state, provider = _provider()
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    calls = []
    capture = WorldCapture(provider, _ask(1.0, calls))
    capture.enforcing_verifier = ObservationVerifier(capture.ask, max_requests_per_turn=2)

    first = capture.preview_commit("Inspect the truck.", "One.", copy.deepcopy(state), entered_scene=False)
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    second = capture.preview_commit("Inspect the truck.", "Two.", copy.deepcopy(state), entered_scene=False)
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    third = capture.preview_commit("Inspect the truck.", "Three.", copy.deepcopy(state), entered_scene=False)

    assert first.outcome == "ok"
    assert second.outcome == "ok"
    assert third.outcome == "budget_exhausted"

    provider.observe_automatically = False
    capture.before_turn("Inspect the truck.")
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    _set_raw(provider, {"Kristin's laptop": {"place": "driver's seat"}})
    reset = capture.preview_commit("Inspect the truck.", "Reset.", copy.deepcopy(state), entered_scene=False)
    assert reset.outcome == "ok"


def test_shadow_only_keeps_original_record_shape():
    state, provider = _provider()
    capture = WorldCapture(provider, _ask(1.0, []))
    capture.shadow_verifier = ObservationVerifier(capture.ask)
    record = capture.after_commit("Inspect the truck.", "The truck is quiet.", entered_scene=False)

    assert "observation_preview" not in record
    assert "observation_diverged" not in record


def test_call_memo_deepcopies_answers_and_round_trips():
    memo = CallMemo()
    answer = {"nested": [1]}
    assert memo.remember("match", {"b": 2, "a": 1}, lambda: answer) == answer
    answer["nested"].append(2)
    replay = memo.remember("match", {"a": 1, "b": 2}, lambda: {"wrong": True})

    assert replay == {"nested": [1]}
    assert memo.hits == 1
    assert memo.misses == 1
    restored = CallMemo.from_json(memo.to_json())
    assert restored.remember("match", {"a": 1, "b": 2}, lambda: {"wrong": True}) == {"nested": [1]}
