import json
from pathlib import Path

import pytest

import bench.core as core
import storygame.runtime.cloudflare as cloudflare
from storygame.runtime.facts import Fact
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "stories" / "continuity-initiative"
STORY_PACKAGE = load_story_package(PACKAGE)
VARIATION_PATH = ROOT / "bench" / "variations" / "seeding-test.json"


def _variation(entry_state: str | None = None, entry_facts: list[str] | None = None) -> dict[str, object]:
    raw: dict[str, object] = {
        "name": "seeding-test",
        "story_package": str(PACKAGE),
    }
    if entry_state is not None:
        raw["entry_state"] = entry_state
    if entry_facts is not None:
        raw["entry_facts"] = entry_facts
    return core.resolve_variation(raw, VARIATION_PATH)


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_first_scene_thorough_seeding_returns_bootstrap_without_worker(monkeypatch) -> None:
    monkeypatch.setattr(cloudflare, "urlopen", lambda *_args, **_kwargs: pytest.fail("worker call"))
    package, state = core.seeded_state_for_scene(_variation("thorough"), "1A")

    assert state.package is package
    assert state.current_scene_id == "1A"
    assert state.turn_index == state.scene_entered_at_turn == 0


def test_unknown_entry_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="entry_state must be bare or thorough"):
        _variation("psychic")


def test_missing_entry_state_keeps_bare_behavior() -> None:
    variation = _variation()
    package, seeded = core.seeded_state_for_scene(variation, "3B")
    expected_package, expected = core.package_and_state(variation, "3B")

    assert package.story_id == expected_package.story_id
    assert seeded.current_scene_id == expected.current_scene_id
    assert seeded.turn_index == expected.turn_index == 0
    assert seeded.facts == expected.facts
    assert core.entry_state(seeded)["seeded_by"] == "bare"


@pytest.mark.parametrize("entry_state", [None, "thorough"])
def test_entry_facts_are_asserted_for_bare_and_thorough_seeding(entry_state: str | None) -> None:
    fact_id = "evidence_gap_processing_numbers"
    _, state = core.seeded_state_for_scene(_variation(entry_state, [fact_id]), "3C")

    assert Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


def test_unknown_entry_fact_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown-entry-fact"):
        _variation(entry_facts=["unknown-entry-fact"])


def test_missing_entry_facts_keeps_bare_behavior() -> None:
    variation = _variation()
    _, seeded = core.seeded_state_for_scene(variation, "3B")
    _, expected = core.package_and_state(variation, "3B")

    assert seeded.facts == expected.facts
