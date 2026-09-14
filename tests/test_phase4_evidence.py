"""Redacted deterministic Phase 4 narration-safety evidence."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app
from tests._rejection_codes import KNOWN_REJECTION_CODES

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
ARTIFACT = Path("artifacts/phase4-knowledge-evidence.json")


class _EvidenceProvider:
    def __init__(self, selected_ids: list[str], grounding_ids: list[str], text: str) -> None:
        self.selected_ids = selected_ids
        self.grounding_ids = grounding_ids
        self.text = text
        self.context_candidate_ids: list[str] = []

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The kitchen settles."}]}

    def __call__(self, player_input: str) -> dict[str, object]:
        projection = KnowledgeProjector().project(self.state, "player", player_input)
        self.context_candidate_ids = sorted(item.id for item in projection.candidates)
        return {
            "segments": [{"kind": "narration", "text": self.text, "grounding_ids": self.grounding_ids}],
            "selected_knowledge_ids": self.selected_ids,
        }


def _fact_keys(store_path: Path, session_id: str) -> list[str]:
    state = RuntimeStateSqliteStore(store_path).load(session_id, PACKAGE)
    return sorted({fact.predicate for fact in state.facts.asserted})


def _run_case(tmp_path: Path, name: str, player_input: str, provider: _EvidenceProvider) -> dict[str, object]:
    store_path = tmp_path / f"{name}.sqlite"

    def provider_factory(state):
        state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
        state.active_event_ids.update({"SL-1A-B", "SL-1A-C"})
        provider.state = state
        return provider

    app = create_demo_app(store_path=store_path, provider_factory=provider_factory)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        before = _fact_keys(store_path, session_id)
        bytes_before = store_path.read_bytes()
        response = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": player_input})
        after = _fact_keys(store_path, session_id)
        bytes_after = store_path.read_bytes()

    if response.status_code == 200:
        audit = response.json()["knowledge_audit"]
        return {
            "case": name,
            "input": player_input,
            "candidate_ids": audit["context_candidate_ids"],
            "selected_ids": audit["provider_selected_ids"],
            "resolved_ids": audit["resolved_source_ids"],
            "fact_keys_before": audit["fact_keys_before"],
            "fact_keys_after": audit["fact_keys_after"],
            "accepted_segments": audit["accepted_segments"],
            "result": audit["result"],
            "rejection_reason": audit["rejection_code"],
        }

    rejection_code = response.headers.get("X-Freytag-Rejection-Code")
    assert response.status_code in (409, 422)
    if response.status_code == 409:
        assert rejection_code in KNOWN_REJECTION_CODES
    else:
        rejection_code = "contract_schema_violation"
    return {
        "case": name,
        "input": player_input,
        "candidate_ids": provider.context_candidate_ids,
        "selected_ids": sorted(provider.selected_ids),
        "resolved_ids": [],
        "fact_keys_before": before,
        "fact_keys_after": after,
        "accepted_segments": [],
        "result": "rejected",
        "rejection_reason": rejection_code,
        "sqlite_unchanged": bytes_before == bytes_after,
    }


def test_phase4_knowledge_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FREYTAG_EXPOSE_KNOWLEDGE_AUDIT", "1")
    turns = [
        _run_case(
            tmp_path,
            "ordinary_local_clue",
            "Search the desk drawer.",
            _EvidenceProvider([], [], "A loose screw glints beside the desk."),
        ),
        _run_case(
            tmp_path,
            "invented_future_dependency_clue",
            "Inspect the evidence shelf.",
            _EvidenceProvider([], [], "The hidden memory card proves the Regional facility is already open."),
        ),
        _run_case(
            tmp_path,
            "premature_warning",
            "Listen to the recording.",
            _EvidenceProvider([], [], "The damaged recording warns against emergency broadcasts."),
        ),
        _run_case(
            tmp_path,
            "patrol_tape_without_arrival",
            "Inspect the gate.",
            _EvidenceProvider([], [], "Reflective tape marks the gate after the patrol arrives."),
        ),
        _run_case(
            tmp_path,
            "grounded_recording_reveal",
            "Search the desk drawer.",
            _EvidenceProvider(
                ["k_sl_1a_b_r2"],
                ["k_sl_1a_b_r2"],
                (
                    "Kristin secures Michelle's memory card under the KMS drawer and plays its damaged recording: "
                    "do not trust emergency broadcasts."
                ),
            ),
        ),
    ]

    assert turns[0]["result"] == "committed"
    for turn in turns[1:4]:
        assert turn["result"] == "rejected"
        assert turn["fact_keys_before"] == turn["fact_keys_after"]
        assert turn["accepted_segments"] == []
        assert turn["sqlite_unchanged"] is True
        assert turn["rejection_reason"]
    assert turns[4]["result"] == "committed"
    assert turns[4]["selected_ids"] == ["k_sl_1a_b_r2"]
    assert turns[4]["resolved_ids"] == ["SL-1A-B/SL-1A-B-R2"]
    assert "michelle_warning_known" in turns[4]["fact_keys_after"]
    assert turns[4]["accepted_segments"]

    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(
            {"generated_by": "tests/test_phase4_evidence.py", "story_id": "continuity_initiative", "turns": turns},
            indent=2,
        )
        + "\n"
    )
