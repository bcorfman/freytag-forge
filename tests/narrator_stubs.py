from __future__ import annotations


class StubNarrator:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def generate(self, _context) -> str:  # noqa: ANN001
        return self._text
