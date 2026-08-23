from __future__ import annotations

from pathlib import Path

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.authoring.contracts import ItemDefinition, ReadableDocument
from storygame.persistence.runtime_state_sqlite import RuntimeStateSqliteStore
from storygame.runtime.contracts import DocumentDisclosure, RuntimeFailure, TurnResult
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import bootstrap_runtime_state
from storygame.runtime.validation import validate_and_commit


def _state():
    return bootstrap_runtime_state(load_compiled_story_fixture("mystery", root=Path("data/compiled_stories/v1")))


def test_bootstrap_seeds_typed_identity_custody_presence_and_unknown_facts() -> None:
    state = _state()

    assert state.facts.has("at", "player", "front_steps")
    assert state.facts.has("custody", "case_file", "npc:daria_stone")
    assert state.facts.has("at", "daria_stone", "front_steps")
    assert state.facts.has("unknown", "player", "victim_name") is False
    assert state.world.items["case_file"]["holder"] == "npc:daria_stone"


def test_fact_commit_updates_compatibility_views_atomically() -> None:
    state = _state()
    result = TurnResult(
        narration="You take the route key.",
        operations=(
            {"kind": "set", "path": "world.items.case_file.holder", "value": "player"},
            {
                "kind": "add",
                "path": "facts",
                "value": {"predicate": "discovered_clue", "subject": "player", "object": "case_file"},
            },
        ),
    )

    updated = validate_and_commit(state, result)

    assert updated is not state
    assert updated.facts.has("discovered_clue", "player", "case_file")
    assert updated.world.items["case_file"]["holder"] == "player"
    assert updated.world.attributes["discovered_clues"] == ["case_file"]
    assert "case_file" in updated.world.attributes["inventory"]
    assert not state.facts.has("discovered_clue", "player", "case_file")


def test_custody_is_unique_but_transfer_is_valid() -> None:
    state = _state()
    transferred = validate_and_commit(
        state,
        TurnResult(
            narration="Daria hands you the case file.",
            operations=({"kind": "set", "path": "world.items.case_file.holder", "value": "player"},),
        ),
    )

    assert transferred.facts.matching("custody", "case_file") == (
        Fact(predicate="custody", subject="case_file", object="player"),
    )
    with pytest.raises(RuntimeFailure, match="different holder"):
        validate_and_commit(
            transferred,
            TurnResult(
                narration="The file is in two places.",
                operations=(
                    {
                        "kind": "add",
                        "path": "facts",
                        "value": {"predicate": "custody", "subject": "case_file", "object": "npc:daria_stone"},
                    },
                ),
            ),
        )


def test_document_disclosure_requires_present_speaker_and_declared_knowledge() -> None:
    state = _state()
    state.world.items["case_file"]["readable"] = {
        "npc_disclosures": {"daria_stone": ["ledger_entry_time"]},
        "knowledge": ["ledger_entry_time"],
    }
    state.facts.assert_fact(Fact(predicate="knows", subject="daria_stone", object="ledger_entry_time"))

    updated = validate_and_commit(
        state,
        TurnResult(
            narration="Daria tells you when the ledger entry was made.",
            disclosures=(
                DocumentDisclosure(item_id="case_file", speaker_id="daria_stone", fact_id="ledger_entry_time"),
            ),
        ),
    )
    assert updated.facts.has("knows", "player", "ledger_entry_time")

    with pytest.raises(RuntimeFailure, match="cannot disclose"):
        validate_and_commit(
            state,
            TurnResult(
                narration="The wrong person tells you.",
                disclosures=(
                    DocumentDisclosure(item_id="case_file", speaker_id="groundskeeper", fact_id="ledger_entry_time"),
                ),
            ),
        )


@pytest.mark.parametrize(
    ("readable", "speaker", "seed_speaker", "seed_player", "code"),
    [
        (None, "daria_stone", True, False, "DOCUMENT_NOT_READABLE"),
        (
            {"npc_disclosures": {"groundskeeper": ["ledger_entry_time"]}},
            "groundskeeper",
            True,
            False,
            "UNAVAILABLE_SPEAKER",
        ),
        (
            {"npc_disclosures": {"daria_stone": ["ledger_entry_time"]}},
            "daria_stone",
            False,
            False,
            "SPEAKER_LACKS_KNOWLEDGE",
        ),
        ({"npc_disclosures": {"daria_stone": ["ledger_entry_time"]}}, "daria_stone", True, True, "FACT_ALREADY_KNOWN"),
    ],
)
def test_document_disclosure_failures_are_fail_closed(readable, speaker, seed_speaker, seed_player, code) -> None:
    state = _state()
    if readable is not None:
        state.world.items["case_file"]["readable"] = readable
    if seed_speaker:
        state.facts.assert_fact(Fact(predicate="knows", subject=speaker, object="ledger_entry_time"))
    if seed_player:
        state.facts.assert_fact(Fact(predicate="knows", subject="player", object="ledger_entry_time"))
    with pytest.raises(RuntimeFailure) as error:
        validate_and_commit(
            state,
            TurnResult(
                narration="A disclosure is attempted.",
                disclosures=(DocumentDisclosure(item_id="case_file", speaker_id=speaker, fact_id="ledger_entry_time"),),
            ),
        )
    assert error.value.code == code


def test_fact_store_round_trips_sorted_typed_facts() -> None:
    store = FactStore({Fact(predicate="role", subject="player", object="investigator")})
    assert FactStore.from_json(store.as_json()).asserted == store.asserted
    with pytest.raises(ValueError, match="facts must be a list"):
        FactStore.from_json({"not": "a list"})


def test_bootstrap_rejects_non_compiled_story_input() -> None:
    with pytest.raises(TypeError, match="reviewed CompiledStory"):
        bootstrap_runtime_state(object())


def test_fact_bootstrap_is_story_agnostic_across_supported_genres() -> None:
    for genre in ("mystery", "fantasy", "sci-fi", "relationship"):
        state = bootstrap_runtime_state(load_compiled_story_fixture(genre, root=Path("data/compiled_stories/v1")))
        assert state.facts.has("at", "player", state.world.location)
        assert state.facts.matching("at", "player")


def test_fact_authority_survives_integrity_checked_save_load(tmp_path) -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="active_goal", subject="player", object="review_case_file"))
    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite", namespace="test")
    try:
        store.save("session", state)
        restored = store.load("session", state.compiled_story)
    finally:
        store.close()

    assert restored.facts.has("active_goal", "player", "review_case_file")
    assert restored.facts.asserted == state.facts.asserted


def test_bootstrap_accepts_declarative_goals_scene_objective_and_initial_facts() -> None:
    story = load_compiled_story_fixture("mystery", root=Path("data/compiled_stories/v1"))
    story = story.model_copy(
        update={
            "initial_world_state": {
                "location": "front_steps",
                "active_goal": "review_case_file",
                "scene_objective": "Establish the first reliable lead.",
                "facts": [{"predicate": "task", "subject": "player", "object": "question_contact"}],
                "items": {
                    "token": {
                        "holder": "player",
                        "affordances": ["examine", "take"],
                        "readable": {"knowledge": ["token_origin"], "npc_disclosures": {}},
                    }
                },
            }
        }
    )
    state = bootstrap_runtime_state(story)

    assert state.facts.has("active_goal", "player", "review_case_file")
    assert state.facts.has("scene_objective", "scene", value="Establish the first reliable lead.")
    assert state.facts.has("task", "player", "question_contact")
    assert state.facts.has("possession", "player", "token")
    assert state.facts.has("item_affordance", "token", "take")
    assert state.facts.has("unknown", "player", "token_origin")


def test_bootstrap_realizes_typed_item_definition_and_rejects_bad_initial_fact() -> None:
    story = load_compiled_story_fixture("fantasy", root=Path("data/compiled_stories/v1"))
    story = story.model_copy(
        update={
            "initial_world_state": {"flags": ["ready"], "facts": [{"predicate": "bad fact", "subject": "x"}]},
            "item_definitions": (
                ItemDefinition(
                    id="scroll",
                    name="Warded Scroll",
                    kind="document",
                    description="A sealed route map.",
                    initial_holder="location:opening",
                    readable=ReadableDocument(item_id="scroll", discovery_key="scroll", knowledge=("route",)),
                ),
            ),
        }
    )
    with pytest.raises(TypeError, match="invalid initial fact"):
        bootstrap_runtime_state(story)

    clean = story.model_copy(update={"initial_world_state": {"flags": ["ready"]}})
    state = bootstrap_runtime_state(clean)
    assert state.world.items["scroll"]["description"] == "A sealed route map."
    assert state.world.items["scroll"]["readable"]["discovery_key"] == "scroll"
    assert state.facts.has("flag", "world", "ready")


def test_unavailable_item_and_fact_projection_removals_are_enforced() -> None:
    with pytest.raises(RuntimeFailure, match="not available"):
        validate_and_commit(
            _state(),
            TurnResult(
                narration="You reach for the distant key.",
                operations=({"kind": "set", "path": "world.items.route_key.holder", "value": "player"},),
            ),
        )
    state = _state()
    state.world.attributes["unknown_facts"] = ["ledger_entry_time"]
    updated = validate_and_commit(
        state,
        TurnResult(
            narration="You learn the time.",
            operations=(
                {
                    "kind": "add",
                    "path": "facts",
                    "value": {"predicate": "knows", "subject": "player", "object": "ledger_entry_time"},
                },
                {
                    "kind": "remove",
                    "path": "facts",
                    "value": {"predicate": "knows", "subject": "player", "object": "ledger_entry_time"},
                },
                {
                    "kind": "add",
                    "path": "facts",
                    "value": {"predicate": "discovered_clue", "subject": "player", "object": "temporary_clue"},
                },
                {
                    "kind": "remove",
                    "path": "facts",
                    "value": {"predicate": "discovered_clue", "subject": "player", "object": "temporary_clue"},
                },
                {
                    "kind": "add",
                    "path": "facts",
                    "value": {"predicate": "discovered_lead", "subject": "player", "object": "temporary_lead"},
                },
                {
                    "kind": "remove",
                    "path": "facts",
                    "value": {"predicate": "discovered_lead", "subject": "player", "object": "temporary_lead"},
                },
                {
                    "kind": "remove",
                    "path": "facts",
                    "value": {"predicate": "custody", "subject": "case_file", "object": "npc:daria_stone"},
                },
            ),
        ),
    )
    assert updated.world.attributes["unknown_facts"] == ["ledger_entry_time"]


@pytest.mark.parametrize(
    ("operation", "code"),
    [
        (
            {"kind": "add", "path": "facts", "value": {"predicate": "not_allowed", "subject": "x"}},
            "UNKNOWN_FACT_FAMILY",
        ),
        ({"kind": "add", "path": "facts", "value": {"predicate": "at", "subject": "x"}}, "INVALID_FACT"),
        (
            {
                "kind": "add",
                "path": "facts",
                "value": {"predicate": "custody", "subject": "missing", "object": "player"},
            },
            "UNKNOWN_ITEM",
        ),
        ({"kind": "add", "path": "facts", "value": "bad"}, "INVALID_FACT"),
        ({"kind": "set", "path": "world.items.missing.holder", "value": "player"}, "UNKNOWN_ITEM"),
        ({"kind": "set", "path": "world.unknown", "value": "bad"}, "UNKNOWN_STATE_PATH"),
    ],
)
def test_fact_and_item_policy_rejections_are_typed(operation, code) -> None:
    with pytest.raises(RuntimeFailure) as error:
        validate_and_commit(_state(), TurnResult(narration="No change.", operations=(operation,)))
    assert error.value.code == code


def test_fact_removal_and_compatibility_operations_update_views() -> None:
    state = _state()
    committed = validate_and_commit(
        state,
        TurnResult(
            narration="You note the lead, then remove the temporary marker.",
            operations=(
                {
                    "kind": "add",
                    "path": "facts",
                    "value": {"predicate": "flag", "subject": "world", "object": "temporary"},
                },
                {"kind": "add", "path": "facts", "value": {"predicate": "at", "subject": "player", "object": "foyer"}},
                {
                    "kind": "add",
                    "path": "facts",
                    "value": {"predicate": "discovered_lead", "subject": "player", "object": "ledger"},
                },
                {
                    "kind": "remove",
                    "path": "facts",
                    "value": {"predicate": "flag", "subject": "world", "object": "temporary"},
                },
                {"kind": "set", "path": "world.flags", "value": ["kept"]},
                {"kind": "set", "path": "world.attributes.note", "value": "grounded"},
            ),
        ),
    )
    assert committed.world.location == "foyer"
    assert committed.world.flags == {"kept"}
    assert committed.world.attributes["discovered_leads"] == ["ledger"]
    assert committed.world.attributes["note"] == "grounded"
