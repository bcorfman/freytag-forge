from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from tests.test_richer_3a import _engine, _entries

COMMITTED = ("k_sl_3a_a_r1", "k_sl_3a_b_r2", "k_sl_3a_d_r1", "k_sl_3a_c_r1")
SPEAKERS = "Dr. Michelle McGehee, Brandon Corfman and Imprisoned senior official"
MARK = " may say this aloud: "


def _commit(state, entry_ids: tuple[str, ...]) -> None:
    entries = _entries()
    for entry_id in entry_ids:
        for requirement in entries[entry_id].requires:
            state.facts.assert_fact(
                Fact(predicate=requirement.fact_id, subject="story", value=str(requirement.equals).lower())
            )
        for operation in entries[entry_id].establishes:
            state.facts.assert_fact(
                Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower())
            )


def _constraint_lines() -> list[str]:
    state, _engine_instance = _engine()
    _commit(state, COMMITTED)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    prompt = provider.assemble_turn_prompt("Look at the captives.")["context"]
    text = provider._section_user_prompt(prompt)
    constraints = text[text.index("CONSTRAINTS:") :].split("\n\n")[0]
    return [line for line in constraints.splitlines() if MARK in line]


def test_a_statement_every_present_speaker_may_say_is_listed_once_with_all_their_names():
    lines = _constraint_lines()
    entries = _entries()
    for entry_id in COMMITTED:
        statement = entries[entry_id].statement
        matching = [line for line in lines if line.endswith(f"{MARK}{statement}")]
        assert matching == [f"- {SPEAKERS}{MARK}{statement}"], entry_id


def test_the_speaker_lines_no_longer_repeat_each_statement_per_speaker():
    lines = _constraint_lines()
    statements = [line.split(MARK, 1)[1] for line in lines]
    assert len(statements) == len(set(statements))
    assert not any(line.startswith("- Dr. Michelle McGehee may say") for line in lines)
    assert not any(line.startswith("- Brandon Corfman may say") for line in lines)
