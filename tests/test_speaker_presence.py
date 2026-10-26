from pathlib import Path

import pytest

from storygame.runtime.capture import build_capture_provider
from storygame.runtime.cloudflare import _speaker_present_in_prose
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.mark.parametrize(
    ("prose", "aliases", "expected"),
    [
        (
            "Aster finds a recording. In it, Aster says hello to Bram.",
            ("Aster",),
            False,
        ),
        (
            "Cora hears a phone message. In it, Cora speaks to Dax.",
            ("Cora",),
            False,
        ),
    ],
)
def test_evidence_sentence_inherits_to_following_sentence(prose, aliases, expected) -> None:
    assert _speaker_present_in_prose(prose, aliases) is expected


def test_plain_present_sentence_is_present() -> None:
    assert _speaker_present_in_prose("Aster says hello to Bram.", ("Aster",)) is True


def test_evidence_for_someone_else_does_not_inherit() -> None:
    assert _speaker_present_in_prose("Bram finds a card. Aster says hello.", ("Aster",)) is True


def test_non_evidence_predecessor_does_not_inherit() -> None:
    assert _speaker_present_in_prose("Aster walks in. In it, Aster says hello.", ("Aster",)) is True


def test_inherited_skip_is_not_transitive() -> None:
    prose = "Aster finds a recording. In it, Aster says hello. Aster speaks to Bram."

    assert _speaker_present_in_prose(prose, ("Aster",)) is True


EXPECTED_PRESENCE = {
    "1A": {"kristin": True, "michelle": False, "patrol_officer": False},
    "1B": {"kristin": True, "brandon": True, "michelle": False},
    "1C": {"kristin": True, "brandon": True, "michelle": False},
    "2A": {"kristin": True, "brandon": True},
    "2B": {"kristin": True, "brandon": False, "michelle": False},
    "2C": {"kristin": True, "brandon": True, "michelle": True, "rebecca": False},
    "3A": {
        "kristin": True,
        "michelle": True,
        "brandon": True,
        "senior_official": False,
        "rebecca": False,
    },
    "3B": {"kristin": True, "michelle": True, "brandon": True, "rebecca": False, "charles": False},
    "3C": {"kristin": True, "michelle": True, "rebecca": True, "brandon": False},
}


def test_continuity_initiative_presence_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    npc_ids = {npc.id for npc in PACKAGE.world.npcs}

    for scene in PACKAGE.scenes:
        scene_id = scene.metadata.scene_id
        state = RuntimeState.bootstrap(PACKAGE)
        state.current_scene_id = scene_id
        provider = build_capture_provider(state)
        actual = {
            npc_id: provider._is_present(npc_id) for npc_id in scene.metadata.participant_ids if npc_id in npc_ids
        }

        assert actual == EXPECTED_PRESENCE[scene_id]


def test_1a_speaker_context_excludes_michelle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1A"
    provider = build_capture_provider(state)

    assert "michelle" not in provider._speaker_contexts("inspect the drawer")


def _patrol_in_house_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-E")
    state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    return state


def test_1a_placed_patrol_officer_is_present_in_speaker_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    state = _patrol_in_house_state()
    provider = build_capture_provider(state)

    assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "kitchen"
    assert provider._is_present("patrol_officer") is True
    assert "patrol_officer" in provider._speaker_contexts("Search the kitchen for signs of a struggle.")


def test_1a_officer_placed_elsewhere_is_not_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    state = _patrol_in_house_state()
    world = world_for(PACKAGE, state.facts)
    assert world.area("kristin") == "mcgehee_home"
    assert world.move("patrol_officer", "outside_house").ok
    provider = build_capture_provider(state)

    assert world_for(PACKAGE, state.facts).together("kristin", "patrol_officer") is False
    assert provider._is_present("patrol_officer") is False


def test_1a_unplaced_michelle_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = build_capture_provider(state)

    assert world_for(PACKAGE, state.facts).parent("michelle") is None
    assert provider._is_present("michelle") is False
