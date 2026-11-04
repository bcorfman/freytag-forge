from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from tests.test_richer_3a import _engine, _entries

COMMITTED = ("k_sl_3a_a_r1", "k_sl_3a_b_r2", "k_sl_3a_d_r1", "k_sl_3a_c_r1")
SPEAKERS = "Dr. Michelle McGehee, Brandon Corfman and Imprisoned senior official"


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
    return constraints.splitlines()


def test_a_statement_every_present_speaker_may_say_is_listed_once_with_all_their_names():
    lines = _constraint_lines()
    entries = _entries()
    for entry_id in COMMITTED:
        statement = entries[entry_id].statement
        assert lines.count(f"  - {statement}") == 1, entry_id
    assert lines.count(f"- {SPEAKERS} may say these aloud:") == 1


def test_the_speaker_lines_no_longer_repeat_each_statement_per_speaker():
    lines = _constraint_lines()
    statements = [line[4:] for line in lines if line.startswith("  - ")]
    assert len(statements) == len(set(statements))
    assert not any("Dr. Michelle McGehee may say this aloud" in line for line in lines)
    assert not any("Brandon Corfman may say this aloud" in line for line in lines)


def speaker_may_say(prompt: str, name: str, statement: str) -> bool:
    """True when the prompt lets `name` say `statement` aloud, in either the one-line or the grouped form."""

    header = None
    for line in prompt.splitlines():
        if line.endswith(f" may say this aloud: {statement}"):
            names = line.removeprefix("- ").split(" may say this aloud: ")[0]
            if name in names.replace(" and ", ", ").split(", "):
                return True
        elif line.endswith(" may say these aloud:"):
            header = line.removeprefix("- ").removesuffix(" may say these aloud:")
        elif line == f"  - {statement}" and header is not None:
            if name in header.replace(" and ", ", ").split(", "):
                return True
        elif not line.startswith("  - "):
            header = None
    return False
