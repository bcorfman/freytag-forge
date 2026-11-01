from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import StoryPackageError, _story_package_fingerprint, load_story_package

LIGHTHOUSE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"
BASE_DELIVERY = "  delivery_text: Ada copies the chart.\n"
BASE_VARIANT = "  delivery_variants:\n  - requires: [brass_key_found]\n    text: Ada copies the chart carefully.\n"


def _copy(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "story"
    shutil.copytree(LIGHTHOUSE, target)
    return target


def _package_with_variants(tmp_path: Path, variants: str = BASE_VARIANT, *, include_base: bool = True):
    root = _copy(tmp_path)
    knowledge = root / "knowledge.yaml"
    source = knowledge.read_text(encoding="utf-8")
    replacement = (BASE_DELIVERY if include_base else "") + variants
    knowledge.write_text(source.replace(BASE_DELIVERY, replacement, 1), encoding="utf-8")
    return root, load_story_package(root)


def _state(package) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-A")
    return state


def _copy_candidate(package, state: RuntimeState, player_input: str = "Inspect the chart."):
    projection = KnowledgeProjector().project(state, "player", player_input)
    return next(candidate for candidate in projection.candidates if candidate.id == "k_copy_chart")


def test_no_variants_preserves_delivery_projection_and_package_serialization(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    fingerprint = _story_package_fingerprint(root)
    package = load_story_package(root)
    state = _state(package)

    candidate = _copy_candidate(package, state)

    assert candidate.delivery_text == "Ada copies the chart."
    assert all("delivery_variants" not in item for item in package.knowledge.model_dump()["knowledge"])
    assert _story_package_fingerprint(root) == fingerprint


@pytest.mark.parametrize(
    ("true_facts", "expected"),
    [
        ((), "Ada copies the chart."),
        (("brass_key_found",), "Ada copies the chart carefully."),
    ],
)
def test_variant_resolution_uses_exactly_the_matching_fact_set(
    tmp_path: Path, true_facts: tuple[str, ...], expected: str
) -> None:
    _root, package = _package_with_variants(tmp_path)
    state = _state(package)
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    assert _copy_candidate(package, state).delivery_text == expected


def test_two_matching_variants_omit_the_candidate(tmp_path: Path) -> None:
    variants = (
        "  delivery_variants:\n"
        "  - requires: [scene_1a_entry_known]\n"
        "    text: Ada copies the chart in the first light.\n"
        "  - requires: [brass_key_found]\n"
        "    text: Ada copies the chart by the shore.\n"
    )
    _root, package = _package_with_variants(tmp_path, variants)
    state = _state(package)
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))

    projection = KnowledgeProjector().project(state, "player", "Inspect the chart.")

    assert "k_copy_chart" not in {candidate.id for candidate in projection.candidates}


@pytest.mark.parametrize(
    ("variants", "include_base", "message"),
    [
        ("  - requires: [missing_fact]\n    text: Ada copies the chart.\n", True, "unknown fact IDs"),
        ("  - requires: []\n    text: Ada copies the chart.\n", True, "requires"),
        ("  - requires: [brass_key_found]\n    text: '   '\n", True, "delivery variant text"),
        (BASE_VARIANT, False, "requires non-blank delivery_text"),
        (
            "  - requires: [brass_key_found]\n    text: Ada waits.\n",
            True,
            "misses must_convey",
        ),
        (
            "  - requires: [brass_key_found]\n    text: Ada copies the chart with candidate_id.\n",
            True,
            "implementation-only token",
        ),
    ],
)
def test_loader_rejects_invalid_delivery_variants(
    tmp_path: Path, variants: str, include_base: bool, message: str
) -> None:
    block = "  delivery_variants:\n" + variants

    with pytest.raises(StoryPackageError, match=message):
        _package_with_variants(tmp_path, block, include_base=include_base)


def test_loader_rejects_duplicate_variant_requires_sets(tmp_path: Path) -> None:
    variants = (
        "  delivery_variants:\n"
        "  - requires: [brass_key_found, scene_1a_entry_known]\n"
        "    text: Ada copies the chart in the first light.\n"
        "  - requires: [scene_1a_entry_known, brass_key_found]\n"
        "    text: Ada copies the chart by the shore.\n"
    )

    with pytest.raises(StoryPackageError, match="duplicate delivery variant requires sets"):
        _package_with_variants(tmp_path, variants)


def test_variants_do_not_change_eligibility_effects_or_action_evidence(tmp_path: Path) -> None:
    plain_root = _copy(tmp_path / "plain")
    plain_package = load_story_package(plain_root)
    _variant_root, variant_package = _package_with_variants(tmp_path / "variant")
    plain_state = _state(plain_package)
    variant_state = _state(variant_package)

    plain_item = plain_package.knowledge_indexes.by_id["k_copy_chart"]
    variant_item = variant_package.knowledge_indexes.by_id["k_copy_chart"]
    assert _copy_candidate(plain_package, plain_state).id == _copy_candidate(variant_package, variant_state).id
    assert variant_item.establishes == plain_item.establishes
    assert variant_item.action_evidence == plain_item.action_evidence

    variant_state.active_event_ids.clear()
    assert "k_copy_chart" not in {
        candidate.id
        for candidate in KnowledgeProjector().project(variant_state, "player", "Inspect the chart.").candidates
    }


def test_exact_matcher_consumes_selected_variant_text(tmp_path: Path) -> None:
    _root, package = _package_with_variants(tmp_path)
    state = _state(package)
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    candidate = _copy_candidate(package, state)

    handoff = uniquely_matched_authored_handoff("Copy the chart.", (candidate,))

    assert handoff is not None
    assert handoff.delivery_text == "Ada copies the chart carefully."


def test_semantic_matcher_consumes_selected_variant_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _root, package = _package_with_variants(tmp_path)
    state = _state(package)
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    projection = KnowledgeProjector().project(state, "player", "Inspect the chart.")
    target = next(candidate for candidate in projection.candidates if candidate.id == "k_copy_chart")
    provider = CloudflareTurnProvider(
        worker_url="",
        token="",
        state=state,
        semantic_ask=lambda _state, _questions: {target.id: {"noul": 1.0}},
    )
    provider.last_projection = projection
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "1")

    handoff = provider._semantic_authored_handoff("Inspect the chart.")

    assert handoff is not None
    assert handoff.delivery_text == "Ada copies the chart carefully."


def test_save_restore_recomputes_variant_text_without_runtime_variant_state(tmp_path: Path) -> None:
    _root, package = _package_with_variants(tmp_path)
    state = _state(package)
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    store = RuntimeStateSqliteStore(tmp_path / "state.sqlite")
    store.save("session", state)

    restored = store.load("session", package)

    assert _copy_candidate(package, state).delivery_text == _copy_candidate(package, restored).delivery_text
    assert "delivery_variants" not in RuntimeState.model_fields
    assert "delivery_variants" not in state.snapshot().model_fields


def test_variant_text_is_not_serialized_in_narrator_context_before_delivery(tmp_path: Path) -> None:
    _root, package = _package_with_variants(tmp_path)
    state = _state(package)
    variant_text = "Ada copies the chart carefully."

    projection = KnowledgeProjector().project(state, "player", "Inspect the chart.")

    assert variant_text not in projection.model_dump_json()
