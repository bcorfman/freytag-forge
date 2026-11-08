from __future__ import annotations

import copy
import pickle
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package import StoryPackageError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import KnowledgeDefinition

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
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE_ROOT, destination)
    source = destination / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    item = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_3a_a_r1")
    item["speaker_text"] = {"unknown_speaker": "I saw it."}
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="k_sl_3a_a_r1.*unknown_speaker"):
        load_story_package(destination)

    item["speaker_text"] = {"michelle": "I saw it."}
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    load_story_package(destination)


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
    expected = {
        "k_sl_3a_a_r1": {
            "michelle": "I've been organizing everyone with secret announcements over our stolen radios.",
            "brandon": "Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.",
            "senior_official": (
                "Dr. McGehee's been organizing everyone with secret announcements over the stolen radios."
            ),
        },
        "k_sl_3a_a_r2": {
            "michelle": "Freeing this block doesn't mean much unless we expose the other sites too.",
            "brandon": "Dr. McGehee says freeing this block means little unless we expose the other sites.",
            "senior_official": "Dr. McGehee says freeing this block means little unless we expose the other sites.",
        },
        "k_sl_3a_b_r1": {
            "michelle": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
            "brandon": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
            "senior_official": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
        },
        "k_sl_3a_b_r2": {
            "michelle": (
                "The medical level is where they ran memory, compliance, and resistance experiments on the prisoners."
            ),
            "brandon": (
                "The medical level is where they ran memory, compliance, and resistance experiments on the prisoners."
            ),
            "senior_official": (
                "The medical level is where they ran memory, compliance, and resistance experiments on the prisoners."
            ),
        },
        "k_sl_3a_e_r1": {
            "michelle": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
            "brandon": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
            "senior_official": (
                'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
            ),
        },
        "k_sl_3a_d_r1": {
            "michelle": (
                "That authorization opens the emergency surface gates, but only once. It expires when Charles "
                "activates his new authority."
            ),
            "brandon": (
                "That authorization opens the emergency surface gates, but only once. It expires when Charles "
                "activates his new authority."
            ),
            "senior_official": (
                "That authorization opens the emergency surface gates, but only once. It expires when Charles "
                "activates his new authority."
            ),
        },
        "k_sl_3a_d_r2": {
            "michelle": (
                "The authorization is real, but the panel's brief response shows the one-use code is about to expire."
            ),
            "brandon": (
                "The authorization is real, but the panel's brief response shows the one-use code is about to expire."
            ),
            "senior_official": (
                "The authorization is real, but the panel's brief response shows the one-use code is about to expire."
            ),
        },
        "k_sl_3a_c_r1": {
            "michelle": (
                "Your signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the "
                "command and broadcast levels."
            ),
            "brandon": (
                "The signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the "
                "command and broadcast levels."
            ),
            "senior_official": (
                "The signal worked. The prisoners have the checkpoints, and they're fighting their way up toward the "
                "command and broadcast levels."
            ),
        },
        "k_sl_3a_c_r2": {
            "michelle": "Good thing we didn't wait. That authorization was about to run out.",
            "brandon": "Dr. McGehee didn't wait. The authorization was about to expire.",
            "senior_official": "Dr. McGehee didn't wait. The authorization was about to expire.",
        },
    }
    expected_statements = {
        "k_sl_3a_a_r1": (
            "Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and secret "
            "messages."
        ),
        "k_sl_3a_a_r2": "Michelle has explained that freeing this block means little without exposing the other sites.",
        "k_sl_3a_b_r1": (
            'Michelle shows Kristin experiment records proving planned "survivors" were conditioned to support '
            "Charles's story."
        ),
        "k_sl_3a_e_r1": (
            'Michelle shows Kristin experiment records proving planned "survivors" were conditioned to support '
            "Charles's story."
        ),
        "k_sl_3a_b_r2": (
            "Michelle shows Kristin the medical level where prisoners were subjected to memory, compliance, and "
            "resistance experiments."
        ),
        "k_sl_3a_d_r1": (
            "The senior official Charles framed gives Kristin one-use authorization for the emergency surface gates, "
            "which will expire when Charles activates his new authority."
        ),
        "k_sl_3a_d_r2": (
            "The framed official proves the emergency gate authorization is real, but its brief response makes clear "
            "that the one-use code is about to expire."
        ),
        "k_sl_3a_c_r1": (
            "Michelle hands Kristin the stolen radio and Kristin gives the signal; prisoners seize checkpoints and "
            "open a fighting route toward the command and broadcast levels."
        ),
        "k_sl_3a_c_r2": (
            "With the emergency-gate authorization about to expire under Charles's new authority, Michelle hands "
            "Kristin the stolen radio and Kristin gives the signal rather than wait."
        ),
    }
    actual = {item.id: item.speaker_text for item in PACKAGE.knowledge.knowledge if item.speaker_text}
    assert actual == expected
    assert set(actual) == set(expected_statements)
    assert all(set(speaker_text) == {"michelle", "brandon", "senior_official"} for speaker_text in actual.values())
    assert {
        item.id: item.statement for item in PACKAGE.knowledge.knowledge if item.id in expected_statements
    } == expected_statements


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
