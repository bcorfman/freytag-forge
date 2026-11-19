from __future__ import annotations

import copy
import pickle
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import KnowledgeDefinition
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def _source() -> KnowledgeDefinition:
    return next(item for item in PACKAGE.knowledge.knowledge if item.id == "k_sl_3a_a_r1")


def _definition(**updates: object) -> KnowledgeDefinition:
    data = _source().model_dump(mode="json")
    data.update(updates)
    return KnowledgeDefinition.model_validate(data)


def _package_with(item: KnowledgeDefinition):
    catalog = PACKAGE.knowledge.model_copy(update={"knowledge": (item,)})
    indexes = PACKAGE.knowledge_indexes.model_copy(update={"by_id": {item.id: item}})
    return PACKAGE.model_copy(update={"knowledge": catalog, "knowledge_indexes": indexes})


def test_speaker_text_is_immutable_optional_and_excluded_when_empty() -> None:
    item = next(item for item in PACKAGE.knowledge.knowledge if not item.speaker_text)
    assert "speaker_text" not in item.model_dump(mode="json")
    assert item.speaker_text == {}
    assert _definition(speaker_text={"michelle": "I saw it."}).speaker_text == {"michelle": "I saw it."}


def test_empty_speaker_text_keeps_the_package_dump_free_of_the_optional_field() -> None:
    plain_items = tuple(item.model_copy(update={"speaker_text": {}}) for item in PACKAGE.knowledge.knowledge)
    plain_package = PACKAGE.model_copy(
        update={"knowledge": PACKAGE.knowledge.model_copy(update={"knowledge": plain_items})}
    )
    dumped_items = plain_package.model_dump(mode="json")["knowledge"]["knowledge"]
    assert all("speaker_text" not in item for item in dumped_items)


def test_speaker_text_is_hashable_and_cannot_be_mutated() -> None:
    item = _definition(speaker_text={"michelle": "I saw it."})
    assert hash(item)
    with pytest.raises(TypeError):
        item.speaker_text["michelle"] = "Changed."


def test_loaded_speaker_text_survives_copy_and_pickle_as_immutable() -> None:
    speaker_text = next(item.speaker_text for item in PACKAGE.knowledge.knowledge if item.speaker_text)

    for copied in (copy.copy(speaker_text), copy.deepcopy(speaker_text), pickle.loads(pickle.dumps(speaker_text))):
        assert copied == speaker_text
        assert type(copied) is type(speaker_text)
        with pytest.raises(TypeError):
            copied["michelle"] = "Changed."


@pytest.mark.parametrize("value", ["", "  ", 42])
def test_speaker_text_values_must_be_non_blank_strings(value: object) -> None:
    with pytest.raises(ValueError):
        _definition(speaker_text={"michelle": value})


@pytest.mark.parametrize("key", [42, "not-valid"])
def test_speaker_text_keys_must_be_string_ids(key: object) -> None:
    with pytest.raises(ValueError):
        _definition(speaker_text={key: "I saw it."})


def test_speaker_text_requires_voiceable() -> None:
    with pytest.raises(ValueError):
        _definition(voiceable=False, speaker_text={"michelle": "I saw it."})


def test_loader_rejects_unknown_speaker_and_accepts_declared_speaker(tmp_path: Path) -> None:
    destination = compiled_story_copy(tmp_path)
    patch_source(
        destination,
        "source/scenes/3A.yaml",
        "reveals[sl_3a_a].variants.r1.speaker_text",
        {"unknown_speaker": "I saw it."},
    )
    with pytest.raises(SourceError, match="LOADER:.*k_sl_3a_a_r1.*unknown_speaker"):
        load_compiled_copy(destination)

    patch_source(
        destination,
        "source/scenes/3A.yaml",
        "reveals[sl_3a_a].variants.r1.speaker_text",
        {"michelle": "I saw it."},
    )
    load_compiled_copy(destination)


def test_speaker_lines_use_only_the_listed_speaker_text() -> None:
    item = _definition(
        speaker_text={"michelle": "I saw it.", "brandon": "Dr. McGehee saw it."},
    )
    provider = CloudflareTurnProvider(worker_url="", token="", state=RuntimeState.bootstrap(_package_with(item)))
    speakers = {
        "michelle": {"sayable_knowledge": [{"id": item.id, "statement": item.statement, "spoken": "I saw it."}]},
        "brandon": {
            "sayable_knowledge": [{"id": item.id, "statement": item.statement, "spoken": "Dr. McGehee saw it."}]
        },
    }
    lines = provider._speaker_constraint_lines(speakers, "Ask Michelle and Brandon.")
    assert lines == [
        "Dr. Michelle McGehee may say this aloud: I saw it.",
        "Brandon Corfman may say this aloud: Dr. McGehee saw it.",
    ]
    assert item.statement not in "\n".join(lines)
    assert "Dr. McGehee saw it." not in lines[0]


def test_speaker_lines_fall_back_to_the_statement_without_authored_text() -> None:
    item = _definition()
    provider = CloudflareTurnProvider(worker_url="", token="", state=RuntimeState.bootstrap(_package_with(item)))
    speakers = {"michelle": {"sayable_knowledge": [{"id": item.id, "statement": item.statement}]}}
    assert provider._speaker_constraint_lines(speakers, "Ask Michelle.") == [
        f"Dr. Michelle McGehee may say this aloud: {item.statement}"
    ]


def test_real_package_has_exact_speaker_text_and_unchanged_canonical_material() -> None:
    expected_ids = {
        "k_sl_3a_a_r1",
        "k_sl_3a_a_r2",
        "k_sl_3a_b_r1",
        "k_sl_3a_b_r2",
        "k_sl_3a_c_r1",
        "k_sl_3a_c_r2",
        "k_sl_3a_d_r1",
        "k_sl_3a_d_r2",
        "k_sl_3a_e_r1",
    }
    actual = {item.id: item.speaker_text for item in PACKAGE.knowledge.knowledge if item.speaker_text}
    assert set(actual) == expected_ids
    assert all(set(speaker_text) == {"michelle", "brandon", "senior_official"} for speaker_text in actual.values())
    assert all(
        all(isinstance(text, str) and text.strip() for text in speaker_text.values())
        for speaker_text in actual.values()
    )
    assert all(
        isinstance(item.statement, str) and item.statement.strip() and item.id in expected_ids
        for item in PACKAGE.knowledge.knowledge
        if item.id in expected_ids
    )


def test_authored_speaker_text_does_not_change_projected_statement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3A"
    state.phase = "crisis"
    state.facts.assert_fact(Fact(predicate="michelle_reached", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="uprising_prepared", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="knowledge_narrated", subject="k_sl_3a_a_r1", value="true"))

    projection = KnowledgeProjector().project(state, "brandon", "Ask Brandon what Michelle did.")
    claim = next(claim for claim in projection.sayable_knowledge if claim.id == "k_sl_3a_a_r1")
    assert claim.statement == _source().statement
    assert "I've been organizing" not in claim.statement
