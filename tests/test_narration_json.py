"""Pure repairs for narration JSON containing unescaped speech quotes."""

from __future__ import annotations

import json

import pytest

from storygame.runtime.narration_json import escape_stray_quotes

FIXTURE_1 = '{"segments":[{"kind":"narration","text":"Kristin looks around the truck, her eyes falling on her laptop on the passenger seat."},{"kind":"narration","text":"She says to herself, "I need to find some clues about Shelly\'s disappearance.""},{"kind":"narration","text":"She reaches for her laptop, saying, "Maybe I can find something on here.""}],"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver\'s seat"},"Kristin\'s laptop":{"place":"passenger seat"}}}'  # noqa: E501
FIXTURE_2 = '{"segments":[{"kind":"narration","text":"Kristin looks around the truck, taking in her surroundings."},{"kind":"narration","text":"Her eyes land on her laptop, which is sitting on the passenger seat."},{"kind":"narration","text":"She says to herself, "I should check if I have any messages from Shelly," and reaches for the laptop."}],"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver\'s seat"},"Kristin\'s laptop":{"place":"passenger seat"}}}'  # noqa: E501
FIXTURE_3 = '{"segments":[{"kind":"narration","text":"Kristin looks around the truck, taking in her surroundings."},{"kind":"narration","text":"Her eyes land on her laptop, which is sitting on the passenger seat."},{"kind":"narration","text":"She says to herself, "I should check if I have any messages from Shelly.""}],"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"driver\'s seat"},"Kristin\'s laptop":{"place":"passenger seat"}}}'  # noqa: E501


@pytest.mark.parametrize(
    "document",
    [
        '{"outer":{"inner":["a",{"value":"b"}]}}',
        '{"text":"She said \\"hi\\""}',
        '{"text":"Kristin\'s laptop"}',
        '{"empty":"","nested":{"empty":""}}',
        r'{"text":"ends with backslash\\"}',
        '{"text":"comma, colon: stay inside"}',
    ],
)
def test_valid_json_is_byte_identical(document: str) -> None:
    assert json.loads(document)
    assert escape_stray_quotes(document) == document


@pytest.mark.parametrize("fixture", [FIXTURE_1, FIXTURE_2, FIXTURE_3])
def test_provider_fixtures_become_valid_json(fixture: str) -> None:
    repaired = escape_stray_quotes(fixture)

    decoded = json.loads(repaired)

    assert decoded["item_facts"]["Kristin's laptop"]["place"] == "passenger seat"


def test_repaired_speech_preserves_quoted_words() -> None:
    first = json.loads(escape_stray_quotes(FIXTURE_1))
    second = json.loads(escape_stray_quotes(FIXTURE_2))
    third = json.loads(escape_stray_quotes(FIXTURE_3))

    assert first["segments"][1]["text"] == (
        'She says to herself, "I need to find some clues about Shelly\'s disappearance."'
    )
    assert second["segments"][2]["text"].endswith('Shelly," and reaches for the laptop.')
    assert third["segments"][2]["text"].endswith('Shelly."')


def test_quote_followed_by_comma_and_word_is_stray() -> None:
    document = '{"text":"She says, "hello", and leaves"}'

    repaired = escape_stray_quotes(document)

    assert json.loads(repaired)["text"] == 'She says, "hello", and leaves'


def test_real_quote_before_comma_and_quote_is_not_stray() -> None:
    document = '{"first":"one","second":"two"}'

    assert escape_stray_quotes(document) == document


def test_garbage_is_returned_without_raising() -> None:
    garbage = 'not json "with "quotes'

    repaired = escape_stray_quotes(garbage)

    assert isinstance(repaired, str)
    with pytest.raises(json.JSONDecodeError):
        json.loads(repaired)


@pytest.mark.parametrize("fixture", [FIXTURE_1, FIXTURE_2, FIXTURE_3])
def test_repair_is_idempotent(fixture: str) -> None:
    once = escape_stray_quotes(fixture)

    assert escape_stray_quotes(once) == once


def test_truncated_document_stays_truncated_and_only_gains_escapes() -> None:
    truncated = '{"segments":[{"kind":"narration","text":"She says, "I need clue'

    repaired = escape_stray_quotes(truncated)

    assert repaired.endswith("clue")
    assert not repaired.endswith(("}", "]"))
    assert len(repaired) - len(truncated) == repaired.count('\\"') - truncated.count('\\"')
    with pytest.raises(json.JSONDecodeError):
        json.loads(repaired)
