from types import SimpleNamespace

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact, FactStore
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


def _provider(candidates, ask, *, true_facts=()):
    facts = FactStore(asserted={Fact(predicate=fact_id, subject="story", value="true") for fact_id in true_facts})
    state = SimpleNamespace(
        facts=facts,
        package=SimpleNamespace(knowledge_indexes=SimpleNamespace(by_id={})),
    )
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, semantic_ask=ask)
    provider.last_projection = SimpleNamespace(candidates=tuple(candidates))
    return provider


def _knowledge(*fact_ids):
    return SimpleNamespace(
        establishes=[SimpleNamespace(op="assert", fact_id=fact_id, value=True) for fact_id in fact_ids]
    )


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
    assert "search the drawer" in captured["questions"]["r0"]["instructions"]


def test_reaches_reveals_caps_and_deduplicates_names_and_excludes_protagonist():
    captured = {}

    def ask(_state, questions):
        captured["question"] = questions["r1"]
        return _yes("r1")

    reaches_reveals(
        ask,
        "Examine the initials-marked drawer.",
        [("r1", "search the KMS drawer", ["Kristin", "KMS drawer", "KMS drawer", *[f"name-{i}" for i in range(12)]])],
    )

    instructions = captured["question"]["instructions"]
    assert "Kristin" in instructions
    assert instructions.count("KMS drawer") == 2
    assert "name-10" not in instructions
    assert "The story says: search the KMS drawer." in instructions


def test_reaches_reveals_accepts_alias_in_candidate_names():
    def ask(_state, questions):
        return _yes("r1") if "initials-marked drawer" in questions["r1"]["instructions"] else {}

    assert reaches_reveals(
        ask,
        "Search my initials-marked drawer for hidden clues.",
        [("r1", "search the KMS drawer", ["KMS drawer", "initials-marked drawer"])],
    ) == {"r1"}


def test_semantic_no_clue_rule_requires_an_eligible_entity_name():
    provider = _provider([_candidate("r1")], lambda *_args: {})
    provider.last_semantic_match = {"ran": True, "matched": None}
    provider._semantic_candidate_names = lambda _candidate: ("initials-marked drawer",)

    assert provider._semantic_no_clue_rules("Search my initials-marked drawer.") == [
        "The player found nothing new here.",
        "Show only what the story already says about it.",
    ]
    assert provider._semantic_no_clue_rules("Search the desk.") == []
    assert provider._semantic_no_clue_rules("Do not search my initials-marked drawer.") == []

    provider.last_semantic_match["matched"] = "r1"
    assert provider._semantic_no_clue_rules("Search my initials-marked drawer.") == []

    provider.last_semantic_match["matched"] = None
    provider.authored_handoff = SimpleNamespace(candidate=_candidate("r1"))
    assert provider._semantic_no_clue_rules("Search my initials-marked drawer.") == []


def test_semantic_fallback_matches_exactly_one_candidate():
    calls = []
    provider = _provider([_candidate("r1")], lambda state, questions: calls.append((state, questions)) or _yes("r1"))

    handoff = provider._semantic_authored_handoff("Search the drawer.")

    assert handoff is not None
    assert handoff.candidate.id == "r1"
    assert len(calls) == 1
    assert provider.last_semantic_match == {"ran": True, "matched": "r1"}


def test_semantic_fallback_offers_candidate_when_only_some_establishes_are_true():
    candidate = _candidate("r1")
    provider = _provider([candidate], lambda _state, questions: _yes(next(iter(questions))))
    provider.state.package.knowledge_indexes.by_id["r1"] = _knowledge("already_known", "still_new")
    provider.state.facts.assert_fact(Fact(predicate="already_known", subject="story", value="true"))

    handoff = provider._semantic_authored_handoff("Search the drawer.")

    assert handoff is not None
    assert handoff.candidate.id == "r1"


def test_semantic_fallback_skips_candidate_when_all_establishes_are_true():
    candidate = _candidate("r1")
    calls = []
    provider = _provider(
        [candidate], lambda *_args: calls.append(True) or _yes("r1"), true_facts=("known_a", "known_b")
    )
    provider.state.package.knowledge_indexes.by_id["r1"] = _knowledge("known_a", "known_b")

    assert provider._semantic_authored_handoff("Search the drawer.") is None
    assert calls == []


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
