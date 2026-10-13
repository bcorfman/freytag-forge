from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from storygame.runtime.jev import JevClient
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
REFUSAL = "Kristin tries to move the workstation, but it is fixed in place and does not budge."


class _Narrator:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls
        self.last_prompt = {"system": "fake", "user": "fake"}

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The search begins."}]}

    def __call__(self, command: str) -> dict[str, object]:
        self.calls.append(command)
        return {"segments": [{"kind": "narration", "text": "The room waits."}]}


class _Jev:
    def __init__(self, *, other_action: bool = False) -> None:
        self.other_action = other_action

    def ask(self, _state: object, questions: object) -> dict[str, object]:
        answers = {}
        for key in questions:
            answers[key] = {"noul": 1.0 if key == "relocates_thing" else 0.0}
            if key == "names_other_action":
                answers[key] = {"noul": 1.0 if self.other_action else 0.0}
        return answers


def _app(monkeypatch, tmp_path, calls: list[str], *, other_action: bool = False):
    monkeypatch.setenv("FREYTAG_WORLD_CAPTURE", "1")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://fake.worker")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test")
    fake_jev = _Jev(other_action=other_action)
    monkeypatch.setattr(JevClient, "from_environment", classmethod(lambda cls: fake_jev))
    narrator = _Narrator(calls)
    return create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: narrator,
    )


def _session(client: TestClient) -> str:
    response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
    assert response.status_code == 200
    return response.json()["session_id"]


def _turn(client: TestClient, session_id: str, command: str):
    response = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": command})
    assert response.status_code == 200
    return response


def test_refusal_is_on_by_default_with_world_capture(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FREYTAG_FIXED_REFUSAL", raising=False)
    calls: list[str] = []
    app = _app(monkeypatch, tmp_path, calls)
    with TestClient(app) as client:
        session_id = _session(client)
        response = _turn(client, session_id, "Carry the workstation to the truck.")

    assert response.json()["lines"] == [REFUSAL]
    assert calls == []


def test_refusal_kill_switch_turns_it_off(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_FIXED_REFUSAL", "0")
    calls: list[str] = []
    app = _app(monkeypatch, tmp_path, calls)
    with TestClient(app) as client:
        session_id = _session(client)
        response = _turn(client, session_id, "Carry the workstation to the truck.")

    assert response.json()["lines"] == ["The room waits."]
    assert calls == ["Carry the workstation to the truck."]


def test_refused_turn_works_with_knowledge_audit_and_prompt_exposure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_EXPOSE_KNOWLEDGE_AUDIT", "1")
    monkeypatch.setenv("FREYTAG_EXPOSE_PROMPT", "1")
    calls: list[str] = []
    app = _app(monkeypatch, tmp_path, calls)
    with TestClient(app) as client:
        session_id = _session(client)
        response = _turn(client, session_id, "Carry the workstation to the truck.")

    payload = response.json()
    assert payload["knowledge_audit"]["provider_selected_ids"] == []
    assert payload["knowledge_audit"]["resolved_source_ids"] == []
    assert payload["attempt_bundle"]["outcome"] == "rejected"
    assert response.status_code == 200
    assert calls == []


def test_multi_turn_refusal_sequence_through_the_api(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    app = _app(monkeypatch, tmp_path, calls)
    store = RuntimeStateSqliteStore(tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        session_id = _session(client)
        state = store.load(session_id, PACKAGE)
        state.staged_cue_fact_id = "continuity_initiative_known"
        store.save(session_id, state)
        commands = [
            "Inspect the kitchen.",
            "Carry the workstation to the truck.",
            "Inspect the kitchen again.",
            "Carry the workstation to the truck.",
            "Listen to the room.",
        ]
        responses = [_turn(client, session_id, command) for command in commands]
        states = [store.load(session_id, PACKAGE)]
        for response, expected_index in zip(responses, (1, 1, 2, 2, 3), strict=True):
            assert response.json()["state"]["turn_index"] == expected_index
            states.append(store.load(session_id, PACKAGE))

    assert calls == [commands[0], commands[2], commands[4]]
    assert [response.json()["state"]["turn_index"] for response in responses] == [1, 1, 2, 2, 3]
    assert states[1].facts == states[2].facts
    assert states[3].facts == states[4].facts
    assert states[-1].delivered_cue_ids.count("continuity_initiative_known") == 1


def test_refused_mixed_turn_then_normal_turn_through_the_api(monkeypatch, tmp_path) -> None:
    calls: list[str] = []
    app = _app(monkeypatch, tmp_path, calls, other_action=True)
    with TestClient(app) as client:
        session_id = _session(client)
        refused = _turn(client, session_id, "Carry the workstation, then open my laptop.")
        normal = _turn(client, session_id, "Inspect the kitchen.")

    clarification = "Nothing else in that command was done. Say what you want to do next."
    assert refused.json()["lines"][0].endswith(clarification)
    assert clarification not in normal.text
    assert calls == ["Inspect the kitchen."]
