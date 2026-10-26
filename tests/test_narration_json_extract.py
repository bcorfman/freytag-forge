"""Extract complete JSON objects from model replies without guessing."""

from __future__ import annotations

from storygame.runtime.narration_json import extract_json_object

EXPECTED_ITEM_MATCH = {"refers": [], "same_as": {}, "kind": {}}


def test_extracts_the_first_measured_wrapped_reply() -> None:
    reply = (
        "Since there are no new names in the command, the response would be:\n\n"
        '{"refers": [], "same_as": {}, "kind": {}}'
    )

    assert extract_json_object(reply) == EXPECTED_ITEM_MATCH


def test_extracts_the_second_measured_wrapped_reply() -> None:
    reply = (
        'Since there are no new names in the command "Look around", the response will be empty for "same_as" and '
        '"kind". The "refers" section will also be empty because the command does not mention any specific things '
        "from the list. \n\n"
        "{\n"
        '"refers": [],\n'
        '"same_as": {},\n'
        '"kind": {}\n'
        "}"
    )

    assert extract_json_object(reply) == EXPECTED_ITEM_MATCH


def test_extracts_clean_json() -> None:
    assert extract_json_object('{"refers": [], "same_as": {}, "kind": {}}') == EXPECTED_ITEM_MATCH


def test_extracts_object_between_prose() -> None:
    assert extract_json_object('Before {"answer": 1} after') == {"answer": 1}


def test_braces_and_escaped_quotes_inside_strings_do_not_confuse_scanner() -> None:
    assert extract_json_object(r'{"a": "}{ \"x\" {"}') == {"a": '}{ "x" {'}


def test_repairs_stray_quotes_inside_object_between_prose() -> None:
    reply = 'Before {"text":"She says, "hello" and leaves"} after'

    assert extract_json_object(reply) == {"text": 'She says, "hello" and leaves'}


def test_two_objects_are_ambiguous() -> None:
    assert extract_json_object('Before {"answer": 1} and {"answer": 2}') is None


def test_no_object_is_not_extracted() -> None:
    assert extract_json_object("plain text") is None


def test_empty_text_is_not_extracted() -> None:
    assert extract_json_object("") is None


def test_unusual_incomplete_inputs_do_not_raise() -> None:
    assert extract_json_object("{") is None
    assert extract_json_object("}") is None
    assert extract_json_object("\\") is None


def test_cut_off_outer_object_does_not_extract_nested_object() -> None:
    reply = '{"segments": [{"text": "a"}, {"text": "b'

    assert extract_json_object(reply) is None


def test_array_or_string_in_prose_is_not_extracted() -> None:
    assert extract_json_object('Before [1, 2] and "answer" after') is None


def test_prose_quotes_before_object_do_not_affect_extraction() -> None:
    assert extract_json_object('A character\'s note says "unfinished {"answer": 1}') == {"answer": 1}
