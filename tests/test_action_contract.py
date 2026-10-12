from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.jev_questions import reaches_reveal_contract
from storygame.runtime.knowledge import RevealCandidate
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActionContract

CONTRACT = ActionContract(
    targets=("copied files",),
    act="Check or copy the copied files.",
    positive=("Check the copied files.",),
    near_miss=("Send the copied files.",),
)


def test_action_contract_rejects_empty_and_overlapping_examples():
    with pytest.raises(ValidationError):
        ActionContract(targets=("",), act="Check files.", positive=("Check files.",), near_miss=("Send files.",))
    with pytest.raises(ValidationError):
        ActionContract(targets=("files",), act="Check files.", positive=("Check files.",), near_miss=("check FILES.",))


def test_old_knowledge_definition_still_has_no_contract():
    package = load_story_package(Path("data/stories/continuity-initiative"))
    old = package.knowledge_indexes.by_id["k_sl_2c_c_r2"]
    assert old.action_contract is None
    assert package.knowledge_indexes.by_id["k_sl_2c_c_r1"].action_contract is not None


def test_contract_question_contains_examples_without_bookkeeping_words():
    captured = {}

    def ask(state, questions):
        captured.update(state=state, questions=questions)
        return {"reveal": {"noul": 1.0}}

    assert reaches_reveal_contract(ask, "Check the copied files.", "reveal", CONTRACT, "check files") is True
    text = str(captured["questions"]["reveal"])
    assert "Check the copied files." in text
    assert "Send the copied files." in text
    assert "contract" not in text.casefold()
    assert "fact_id" not in text.casefold()


def test_shadow_disabled_without_provider_call(monkeypatch):
    candidate = RevealCandidate(
        id="reveal",
        statement="The files are ready.",
        earn_when="check files",
        must_convey=(),
        action_evidence=(("check",), ("files",)),
        delivery_text="The files are ready.",
        action_contract=CONTRACT,
    )
    state = SimpleNamespace(package=SimpleNamespace(knowledge_indexes=SimpleNamespace(by_id={})))
    calls = []

    def ask(*_args):
        calls.append(True)
        return {"reveal": {"noul": 1.0}}

    provider = CloudflareTurnProvider(worker_url="", token="", state=state, semantic_ask=ask)
    projection = SimpleNamespace(candidates=(candidate,), reveal_universe=(candidate,))
    provider.projector = SimpleNamespace(project=lambda *_args: projection)
    provider.last_projection = projection
    provider._run_contract_shadow("Check the copied files.")
    assert calls == []
    assert provider.last_contract_shadow["skipped"] == "disabled"
