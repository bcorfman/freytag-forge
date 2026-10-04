from types import SimpleNamespace

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.jev_questions import reaches_reveals
from storygame.runtime.knowledge import RevealCandidate


def _candidate(candidate_id="reveal", *, delivery="It is revealed.", earn_when="search the drawer"):
    return RevealCandidate(
        id=candidate_id,
        statement="The drawer contains the clue.",
        earn_when=earn_when,
        must_convey=(),
        action_evidence=(("under",),),
        delivery_text=delivery,
    )


def _provider(candidates, ask):
    facts = SimpleNamespace(matching=lambda *_args: ())
    state = SimpleNamespace(
        facts=facts,
        package=SimpleNamespace(knowledge_indexes=SimpleNamespace(by_id={})),
    )
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, semantic_ask=ask)
    provider.last_projection = SimpleNamespace(candidates=tuple(candidates))
    return provider


def _yes(*ids):
    return {candidate_id: {"noul": 1.0} for candidate_id in ids}


def test_reaches_reveals_asks_once_and_caps_candidates_at_six():
    captured = {}

    def ask(state, questions):
        captured["state"] = state
        captured["questions"] = questions
        return _yes("r0")

    matched = reaches_reveals(ask, "Search the drawer.", [(f"r{i}", "search the drawer") for i in range(8)])

    assert matched == {"r0"}
    assert captured["state"] == {"command": "Search the drawer."}
    assert list(captured["questions"]) == [f"r{i}" for i in range(6)]
    assert all(question["type"] == "noul" for question in captured["questions"].values())


def test_semantic_fallback_matches_exactly_one_candidate():
    calls = []
    provider = _provider([_candidate("r1")], lambda state, questions: calls.append((state, questions)) or _yes("r1"))

    handoff = provider._semantic_authored_handoff("Search the drawer.")

    assert handoff is not None
    assert handoff.candidate.id == "r1"
    assert len(calls) == 1
    assert provider.last_semantic_match == {"ran": True, "matched": "r1"}


@pytest.mark.parametrize(
    "answers",
    [None, {}, {"r1": {"noul": 1.0}, "r2": {"noul": 1.0}}],
)
def test_semantic_fallback_fails_closed_without_one_yes(answers):
    provider = _provider([_candidate("r1"), _candidate("r2")], lambda *_args: answers)

    assert provider._semantic_authored_handoff("Search the drawer.") is None


def test_semantic_fallback_fails_closed_on_exception():
    def ask(*_args):
        raise TimeoutError

    provider = _provider([_candidate()], ask)

    assert provider._semantic_authored_handoff("Search the drawer.") is None
    assert provider.last_semantic_match["ran"] is True


def test_semantic_fallback_skips_negated_and_ineligible_commands():
    calls = []

    def ask(*_args):
        calls.append(True)
        return _yes("r1")

    provider = _provider([_candidate("r1")], ask)

    assert provider._semantic_authored_handoff("Do not search the drawer.") is None
    assert _provider([_candidate("r1", delivery="")], ask)._semantic_authored_handoff("Search the drawer.") is None
    assert calls == []


def test_semantic_fallback_session_cap_and_environment_disable(monkeypatch):
    calls = []
    provider = _provider([_candidate()], lambda *_args: calls.append(True) or _yes("reveal"))
    provider.semantic_fallback_calls = 40
    assert provider._semantic_authored_handoff("Search the drawer.") is None
    assert calls == []

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    provider.semantic_fallback_calls = 0
    assert provider._semantic_authored_handoff("Search the drawer.") is None
    assert calls == []


def test_semantic_fallback_reuses_authored_candidate_and_delivery():
    candidate = _candidate("r1", earn_when=None)
    provider = _provider([candidate], lambda *_args: _yes("r1"))

    handoff = provider._semantic_authored_handoff("Search the drawer.")

    assert handoff is not None
    assert handoff.candidate is candidate
    assert handoff.delivery_text == candidate.delivery_text
