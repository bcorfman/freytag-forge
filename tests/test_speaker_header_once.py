from __future__ import annotations

import re

from storygame.runtime.cloudflare import CloudflareTurnProvider
from tests.test_richer_3a import _engine
from tests.test_speaker_lines_grouped import _commit

COMMITTED = (
    "k_sl_3a_a_r1",
    "k_sl_3a_b_r2",
    "k_sl_3a_d_r1",
    "k_sl_3a_c_r1",
    "k_sl_3a_f_r1",
    "k_sl_3a_g_r1",
    "k_sl_3a_h_r1",
    "k_sl_3a_i_r1",
    "k_sl_3a_e_r1",
)
HEADER = re.compile(r"^- (?P<names>.+) may say these aloud:$")
NESTED = re.compile(r"^  - (?P<statement>.+)$")
INLINE = re.compile(r"^- (?P<names>.+) may say this aloud: (?P<statement>.+)$")


def _prompt_and_speakers():
    state, _engine_instance = _engine()
    _commit(state, COMMITTED)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    user = provider.assemble_turn_prompt("Look at the captives.")["context"]
    return provider, user, provider._section_user_prompt(user)


def _expected_groups(provider, user) -> dict[str, list[str]]:
    """Statements by the speakers who may say them, as the prompt must now group them."""

    names_by_statement: dict[str, list[str]] = {}
    for speaker_id, speaker in user["knowledge_context"]["speakers"].items():
        if speaker_id == provider.state.package.protagonist_id:
            continue
        name = provider._display_name(speaker_id)
        for item in speaker["sayable_knowledge"]:
            names = names_by_statement.setdefault(item["statement"], [])
            if name not in names:
                names.append(name)
    groups: dict[str, list[str]] = {}
    for statement, names in names_by_statement.items():
        joined = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
        groups.setdefault(joined, []).append(statement)
    return groups


def _parsed(text: str) -> dict[str, list[str]]:
    block = text[text.index("CONSTRAINTS:") :].split("\n\n")[0].splitlines()
    groups: dict[str, list[str]] = {}
    header = None
    for line in block:
        if match := HEADER.match(line):
            header = match["names"]
            assert header not in groups, f"header written twice: {header}"
            groups[header] = []
        elif (match := NESTED.match(line)) and header is not None:
            groups[header].append(match["statement"])
        else:
            header = None
            if match := INLINE.match(line):
                assert match["names"] not in groups, f"names written twice: {match['names']}"
                groups[match["names"]] = [match["statement"]]
    return groups


def test_every_set_of_speakers_is_named_once_above_all_the_statements_they_may_say():
    provider, user, text = _prompt_and_speakers()
    expected = _expected_groups(provider, user)
    assert any(len(statements) > 1 for statements in expected.values()), "the state must exercise a shared header"
    assert _parsed(text) == expected


def _sayable(*statements: str) -> dict:
    return {"sayable_knowledge": [{"id": f"k{index}", "statement": text} for index, text in enumerate(statements)]}


def test_a_set_with_a_single_statement_keeps_the_one_line_form():
    provider, _user, _text = _prompt_and_speakers()
    speakers = {
        "michelle": _sayable("Shared one.", "Michelle only."),
        "brandon": _sayable("Shared one.", "Brandon only."),
    }
    assert provider._speaker_constraint_lines(speakers) == [
        "Dr. Michelle McGehee and Brandon Corfman may say this aloud: Shared one.",
        "Dr. Michelle McGehee may say this aloud: Michelle only.",
        "Brandon Corfman may say this aloud: Brandon only.",
    ]


def test_a_set_with_several_statements_gets_one_header_and_nested_lines():
    provider, _user, _text = _prompt_and_speakers()
    speakers = {
        "michelle": _sayable("Shared one.", "Shared two.", "Michelle only."),
        "brandon": _sayable("Shared one.", "Shared two."),
    }
    assert provider._speaker_constraint_lines(speakers) == [
        "Dr. Michelle McGehee and Brandon Corfman may say these aloud:\n  - Shared one.\n  - Shared two.",
        "Dr. Michelle McGehee may say this aloud: Michelle only.",
    ]


def test_the_repeated_header_is_gone():
    provider, user, text = _prompt_and_speakers()
    for names, statements in _expected_groups(provider, user).items():
        if len(statements) > 1:
            assert text.count(f"{names} may say") == 1
