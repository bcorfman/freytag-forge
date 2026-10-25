"""Small, conservative repairs for narration JSON."""

from __future__ import annotations


def _next_non_whitespace(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _quote_closes_string(text: str, index: int) -> bool:
    next_index = _next_non_whitespace(text, index + 1)
    if next_index == len(text):
        return True

    next_char = text[next_index]
    if next_char in ":}]":
        return True
    if next_char != ",":
        return False

    after_comma = _next_non_whitespace(text, next_index + 1)
    return after_comma == len(text) or text[after_comma] in '"{['


def escape_stray_quotes(text: str) -> str:
    """Escape unescaped speech quotes while leaving valid JSON unchanged."""

    repaired: list[str] = []
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if not in_string:
            repaired.append(char)
            if char == '"':
                in_string = True
            index += 1
            continue

        if char == "\\":
            repaired.append(char)
            if index + 1 < len(text):
                repaired.append(text[index + 1])
                index += 2
            else:
                index += 1
            continue

        if char == '"':
            if _quote_closes_string(text, index):
                repaired.append(char)
                in_string = False
            else:
                repaired.extend(("\\", '"'))
            index += 1
            continue

        repaired.append(char)
        index += 1

    return "".join(repaired)
