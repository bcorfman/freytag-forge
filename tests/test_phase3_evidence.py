"""Redacted, deterministic Phase 3 knowledge-projection evidence."""

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
ARTIFACT = Path("artifacts/phase3-knowledge-evidence.json")


class _EvidenceProvider:
    def __init__(self, selected_ids: list[str], grounding_ids: list[str], text: str) -> None:
        self.selected_ids = selected_ids
        self.grounding_ids = grounding_ids
        self.text = text
        self.context_candidate_ids: list[str] = []

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The kitchen settles."}]}

    def __call__(self, player_input: str) -> dict[str, object]:
        state = self.state
        projection = KnowledgeProjector().project(state, "player", player_input)
        self.context_candidate_ids = sorted(item.id for item in projection.candidates)
        return {
            "segments": [{"kind": "narration", "text": self.text, "grounding_ids": self.grounding_ids}],
            "selected_knowledge_ids": self.selected_ids,
        }


def _fact_keys(store_path: Path, session_id: str) -> list[str]:
    state = RuntimeStateSqliteStore(store_path).load(session_id, PACKAGE)
    return sorted({fact.predicate for fact in state.facts.asserted})


def _run_case(tmp_path: Path, case: str, player_input: str, provider: _EvidenceProvider) -> dict[str, object]:
    store_path = tmp_path / f"{case}.sqlite"

    def provider_factory(state):
        state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
        state.active_event_ids.add("SL-1A-B")
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
        record = {
            "case": case,
            "input": player_input,
            "context_candidate_ids": audit["context_candidate_ids"],
            "provider_selected_ids": audit["provider_selected_ids"],
            "resolved_source_ids": audit["resolved_source_ids"],
            "fact_keys_before": audit["fact_keys_before"],
            "fact_keys_after": audit["fact_keys_after"],
            "accepted_segments": audit["accepted_segments"],
            "result": audit["result"],
            "rejection_code": audit["rejection_code"],
            "http_status": response.status_code,
            "sqlite_unchanged": None,
        }
    else:
        rejection_code = response.headers.get("X-Freytag-Rejection-Code")
        assert response.status_code in (409, 422), f"{case} returned an unexpected status"
        if response.status_code == 409:
            assert rejection_code is not None
            assert rejection_code in KNOWN_REJECTION_CODES
        else:
            assert rejection_code is None
            rejection_code = "contract_schema_violation"
        record = {
            "case": case,
            "input": player_input,
            "context_candidate_ids": provider.context_candidate_ids,
            "provider_selected_ids": sorted(provider.selected_ids),
            "resolved_source_ids": [],
            "fact_keys_before": before,
            "fact_keys_after": after,
            "accepted_segments": [],
            "result": "rejected",
            "rejection_code": rejection_code,
            "http_status": response.status_code,
            "sqlite_unchanged": bytes_before == bytes_after,
        }
    return record


def test_phase3_knowledge_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FREYTAG_EXPOSE_KNOWLEDGE_AUDIT", "1")
    ordinary_text = "The room gives no warning."
    turns = [
        _run_case(
            tmp_path,
            "physical_search",
            "Search the kitchen.",
            _EvidenceProvider([], [], ordinary_text),
        ),
        _run_case(
            tmp_path,
            "phone",
            "Examine Michelle's phone.",
            _EvidenceProvider([], [], ordinary_text),
        ),
        _run_case(
            tmp_path,
            "drawer_recording_committed",
            "Search the drawer.",
            _EvidenceProvider(
                ["k_sl_1a_b_r2"],
                ["k_sl_1a_b_r2"],
                "Michelle's damaged memory card recording warns Kristin not to trust emergency broadcasts.",
            ),
        ),
        _run_case(
            tmp_path,
            "future_id_rejected",
            "Check the gate.",
            _EvidenceProvider(["k_future_unavailable"], [], "The gate gives no answer."),
        ),
        _run_case(
            tmp_path,
            "duplicate_id_rejected",
            "Inspect the drawer.",
            _EvidenceProvider(["k_sl_1a_b_r2", "k_sl_1a_b_r2"], ["k_sl_1a_b_r2"], "The recording crackles."),
        ),
        _run_case(
            tmp_path,
            "unselected_id_rejected",
            "Check the recorder.",
            _EvidenceProvider([], ["k_sl_1a_b_r2"], "The recorder crackles."),
        ),
    ]

    committed = turns[2]
    assert committed["result"] == "committed"
    assert committed["provider_selected_ids"] == ["k_sl_1a_b_r2"]
    assert committed["resolved_source_ids"] == ["SL-1A-B/SL-1A-B-R2"]
    assert "michelle_warning_known" not in committed["fact_keys_before"]
    assert "michelle_warning_known" in committed["fact_keys_after"]
    assert committed["accepted_segments"]
    assert all(turn["result"] == "committed" for turn in turns[:3])

    for turn in (turns[0], turns[1]):
        assert "michelle_warning_known" not in turn["fact_keys_after"]
    for turn in turns[3:]:
        assert turn["result"] == "rejected"
        assert turn["fact_keys_before"] == turn["fact_keys_after"]
        assert turn["accepted_segments"] == []
        assert turn["rejection_code"]
        assert turn["sqlite_unchanged"] is True

    ARTIFACT.parent.mkdir(exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(
            {"generated_by": "tests/test_phase3_evidence.py", "story_id": "continuity_initiative", "turns": turns},
            indent=2,
        )
        + "\n"
    )
