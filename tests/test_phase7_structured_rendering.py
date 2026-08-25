from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.persistence.runtime_state_sqlite import RuntimeStateSqliteStore
from storygame.persistence.story_state import artifact_bundle
from storygame.runtime.contracts import ActionSegment, SpeechSegment
from storygame.runtime.engine import RuntimeEngine
from storygame.web_demo import create_demo_app
from tests.test_causal_spatial_projection_phase4 import _projection
from tests.test_phase5_interaction import _proposal, _state
from tests.test_phase6_group_scene_interaction import _group_proposal, _group_state


class _Model:
    def __init__(self, proposal: object, narration: str = "The relay groans around the crew.") -> None:
        self.proposal = proposal
        self.narration = narration

    def play_turn(self, context: object, *, json_object: bool) -> object:
        return {"narration": self.narration, "interaction": self.proposal.model_dump(mode="json")}


def test_individual_segments_preserve_narration_attribution_and_compatibility_lines() -> None:
    proposal = _proposal(
        segments=(
            SpeechSegment(
                speaker_id="engineer",
                addressee_ids=("player",),
                used_fact_ids=("failure",),
                text="The relay will fail unless we choose the repair now.",
            ),
            ActionSegment(actor_id="engineer", grounding="expressive", text="She checks the warning display."),
            SpeechSegment(
                speaker_id="engineer",
                addressee_ids=("player",),
                used_fact_ids=("failure",),
                text="Decide with me, now.",
            ),
        )
    )
    engine = RuntimeEngine(_state(), _Model(proposal))

    response = engine.turn("What will it cost?")

    assert response.ok
    assert [segment["kind"] for segment in response.segments] == ["speech", "action", "speech"]
    assert response.segments[0]["speaker"] == {"id": "engineer", "name": "Iris Vale"}
    assert response.segments[0]["addressees"] == [{"id": "player", "name": "You"}]
    assert response.segments[1]["grounding"] == "expressive"
    assert response.segments[2]["speaker"] == {"id": "engineer", "name": "Iris"}
    assert response.lines == (
        "The relay groans around the crew.",
        "Iris Vale: \u201cThe relay will fail unless we choose the repair now.\u201d",
        "Iris — She checks the warning display.",
        "Iris: \u201cDecide with me, now.\u201d",
    )
    assert "failure" not in str(response.segments)


def test_group_segment_order_and_artifacts_and_save_load_survive_projection(tmp_path) -> None:
    engine = RuntimeEngine(_group_state(), _Model(_group_proposal()))

    response = engine.turn("What is our safest route?")
    bundle = artifact_bundle(engine.state)

    assert [segment["speaker"]["name"] for segment in response.segments] == ["Iris Vale", "Tomas Reed"]
    assert bundle["transcript.json"][0]["segments"] == list(response.segments)
    assert bundle["trace.json"]["events"][0]["segments"] == list(response.segments)
    assert "Iris Vale" in bundle["STORY.md"]

    store = RuntimeStateSqliteStore(tmp_path / "state.sqlite", namespace="phase7")
    store.save("session", engine.state)
    restored = store.load("session", _projection())
    store.close()
    assert restored.recent_events[0].segments == response.segments


def test_hosted_api_exposes_accepted_segments_and_keeps_non_dialogue_lines_compatible(tmp_path, monkeypatch) -> None:
    import storygame.web_demo as web_demo

    proposal = _proposal()
    monkeypatch.setattr(web_demo, "bootstrap_runtime_state", lambda story: _state())
    app = create_demo_app(save_db_path=tmp_path / "runtime.sqlite", model=_Model(proposal), channel="test")

    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"genre": "mystery"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I listen."})

    payload = response.json()
    assert response.status_code == 200
    assert payload["segments"][0]["speaker"]["name"] == "Iris Vale"
    assert payload["lines"] == [
        "The relay groans around the crew.",
        "Iris Vale: “The relay will fail unless we choose the repair now.”",
        "Iris — The engineer checks the warning display.",
    ]
