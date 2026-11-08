from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from tests.test_richer_3a import _engine, _entries

COMMITTED = ("k_sl_3a_a_r1", "k_sl_3a_b_r2", "k_sl_3a_d_r1", "k_sl_3a_c_r1")


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
        if entries[entry_id].voiceable:
            state.facts.assert_fact(Fact(predicate="knowledge_narrated", subject=entry_id, value="true"))


def _provider_and_context(command: str = "Look at the captives."):
    state, _engine_instance = _engine()
    _commit(state, COMMITTED)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    return provider, provider.assemble_turn_prompt(command)["context"]


def _constraint_lines(context, provider) -> list[str]:
    text = provider._section_user_prompt(context)
    return text[text.index("CONSTRAINTS:") :].split("\n\n")[0].splitlines()


def _sayable(*statements: str) -> dict:
    return {"sayable_knowledge": [{"id": f"k{index}", "statement": text} for index, text in enumerate(statements)]}


def test_each_present_speaker_gets_one_line_per_statement_they_may_say():
    # Grouping the speakers under one header or one line moved the narrator's lead-in (it stopped letting Michelle
    # speak first on the proof turn, 0/6 against 16/16 for one line per speaker per statement), so the format stays.
    provider, context = _provider_and_context()
    lines = _constraint_lines(context, provider)
    expected = []
    for speaker_id, speaker in context["knowledge_context"]["speakers"].items():
        if speaker_id == provider.state.package.protagonist_id:
            continue
        for item in speaker["sayable_knowledge"]:
            expected.append(
                f"- {provider._display_name(speaker_id)} may say this aloud: {item.get('spoken', item['statement'])}"
            )
    assert len({line.split(" may say")[0] for line in expected}) >= 2, "the state must list several speakers"
    assert len(expected) >= 6
    assert [line for line in lines if " may say " in line] == expected
    assert not any("may say these aloud" in line for line in lines)
    assert not any(line.startswith("  - ") for line in lines)


def test_a_speaker_who_is_neither_present_nor_named_is_not_listed():
    provider, _context = _provider_and_context()
    assert provider._is_present("rebecca") is False
    speakers = {"michelle": _sayable("Michelle one."), "rebecca": _sayable("Rebecca one.", "Rebecca two.")}
    assert provider._speaker_constraint_lines(speakers, "Look around.") == [
        "Dr. Michelle McGehee may say this aloud: Michelle one."
    ]


def test_a_speaker_the_command_names_is_listed_even_when_absent():
    provider, _context = _provider_and_context()
    assert provider._is_present("rebecca") is False
    speakers = {"michelle": _sayable("Michelle one."), "rebecca": _sayable("Rebecca one.", "Rebecca two.")}
    assert provider._speaker_constraint_lines(speakers, "Ask Rebecca about the lemon cake.") == [
        "Dr. Michelle McGehee may say this aloud: Michelle one.",
        "Rebecca Jenkins may say this aloud: Rebecca one.",
        "Rebecca Jenkins may say this aloud: Rebecca two.",
    ]


def test_the_protagonist_is_never_listed_as_a_speaker():
    provider, _context = _provider_and_context()
    speakers = {"kristin": _sayable("Kristin one."), "michelle": _sayable("Michelle one.")}
    assert provider._speaker_constraint_lines(speakers, "Look around.") == [
        "Dr. Michelle McGehee may say this aloud: Michelle one."
    ]


def test_the_turn_prompt_applies_the_limit_with_the_player_s_command():
    # The wiring: _section_user_prompt passes the command to the speaker lines.
    for command, listed in (("Look around.", False), ("Ask Rebecca about the lemon cake.", True)):
        provider, context = _provider_and_context(command)
        context["knowledge_context"]["speakers"]["rebecca"] = _sayable("Rebecca one.")
        lines = _constraint_lines(context, provider)
        assert ("- Rebecca Jenkins may say this aloud: Rebecca one." in lines) is listed, command


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
