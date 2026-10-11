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


def test_thorough_seeding_reaches_late_scenes_without_worker_calls(monkeypatch) -> None:
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("thorough seeding must not call the narration worker")

    monkeypatch.setattr(cloudflare, "urlopen", forbidden)
    variation = _variation("thorough")

    for scene_id in ("1B", "3B"):
        package, state = core.seeded_state_for_scene(variation, scene_id)
        bare_package, bare_state = core.package_and_state(variation, scene_id)

        assert state.package is package
        assert package.knowledge == bare_package.knowledge
        assert package.knowledge_indexes == bare_package.knowledge_indexes
        assert state.current_scene_id == scene_id
        assert state.turn_index == state.scene_entered_at_turn
        assert len(state.facts.asserted) > len(bare_state.facts.asserted)
        assert (
            core.entry_state(state, seeded_by="thorough")["earned_knowledge_count"]
            > core.entry_state(bare_state)["earned_knowledge_count"]
        )

    assert calls == 0


def test_run_scene_seeding_prevents_midstory_opening_rejection(monkeypatch) -> None:
    prose = "Michelle and Brandon watch the JANUS selection records as alarms sound."
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test")
    monkeypatch.setattr(
        cloudflare,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"segments": [{"kind": "narration", "text": prose}]}),
    )
    script = {"name": "opening", "inputs": ["Inspect the relay room."]}

    bare = core.run_scene(_variation(), "3B", script, max_turns=2)
    seeded = core.run_scene(_variation("thorough"), "3B", script, max_turns=2)

    assert bare["status"] == "failed"
    assert "protected knowledge" in bare["failure_reason"] or "unavailable entity" in bare["failure_reason"]
    cue = next(item.cue_text for item in STORY_PACKAGE.deliveries if item.fact_id == seeded["turns"][0]["cue_fact_id"])
    assert seeded["turns"][0]["narration"] == f"{prose} {cue}"
    assert "protected knowledge" not in seeded.get("failure_reason", "")
    assert "unavailable entity" not in seeded.get("failure_reason", "")
    assert seeded["opening"]
    assert bare["entry_state"]["seeded_by"] == "none"
    assert seeded["entry_state"]["seeded_by"] == "thorough"


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
