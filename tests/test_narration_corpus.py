"""Regression coverage for narration accepted by the hosted blind-player runs."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parent.parent
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
CORPUS_PATH = ROOT / "tests/fixtures/narration_corpus.json"
VERDICTS_PATH = ROOT / "tests/fixtures/narration_corpus_verdicts.json"


def _scene_order() -> dict[str, int]:
    return {scene.metadata.scene_id: index for index, scene in enumerate(PACKAGE.scenes)}


def _fact_value(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _late_scene_state(scene_id: str) -> RuntimeState:
    order = _scene_order()
    scene_index = order[scene_id]
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)

    for earlier_scene in PACKAGE.scenes[:scene_index]:
        state._assert_scene_entry_fact(earlier_scene.metadata.scene_id)
    state._assert_scene_entry_fact(scene_id)

    for item in PACKAGE.knowledge.knowledge:
        if not item.available_in_scenes or not all(
            order[available] <= scene_index for available in item.available_in_scenes
        ):
            continue
        for operation in item.establishes:
            fact = Fact(predicate=operation.fact_id, subject="story", value=_fact_value(operation.value))
            if operation.op == "assert":
                state.facts.assert_fact(fact)
    return state


_SCENE_STATES = {scene.metadata.scene_id: _late_scene_state(scene.metadata.scene_id) for scene in PACKAGE.scenes}


def build_state(entry: dict[str, str]) -> RuntimeState:
    """Build the realistic offline state used for one corpus entry."""

    return copy.deepcopy(_SCENE_STATES[entry["scene"]])


def verdict(entry: dict[str, str]) -> str:
    state = build_state(entry)

    def provider(_player_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": entry["text"]}], "selected_knowledge_ids": []}

    try:
        RuntimeEngine(state, provider).turn(entry["input"])
    except ProposalValidationError as error:
        return error.code or type(error).__name__
    return "ok"


def load_corpus() -> list[dict[str, str]]:
    return json.loads(CORPUS_PATH.read_text())


def load_verdicts() -> dict[str, str]:
    return json.loads(VERDICTS_PATH.read_text())


def test_corpus_and_snapshot_have_identical_ids() -> None:
    corpus_ids = {entry["id"] for entry in load_corpus()}
    verdict_ids = set(load_verdicts())
    assert corpus_ids == verdict_ids, (
        "Corpus and snapshot IDs differ; run scripts/regenerate_narration_corpus_verdicts.py"
    )


def test_golden_ok_entries_remain_accepted() -> None:
    corpus = load_corpus()
    golden = load_verdicts()
    offenders = []
    for entry in corpus:
        if golden[entry["id"]] != "ok":
            continue
        current = verdict(entry)
        if current != "ok":
            offenders.append(f"{entry['scene']} {entry['id']} {current}: {entry['text'][:80]}")
    assert not offenders, (
        "Narration corpus entries newly rejected:\n"
        + "\n".join(offenders)
        + "\nAn intentional new guard requires regenerating the snapshot in the same change and reviewing the diff."
    )


def test_golden_snapshot_is_at_least_90_percent_accepted() -> None:
    verdicts = load_verdicts().values()
    ok_rate = sum(verdict == "ok" for verdict in verdicts) / len(load_verdicts())
    assert ok_rate >= 0.9, f"Golden narration corpus ok rate is {ok_rate:.1%}, below 90%"
