from __future__ import annotations

from typing import Protocol


class OutputEditor(Protocol):
    def review_opening(self, lines: list[str], active_goal: str) -> list[str]: ...

    def review_turn(self, lines: list[str], active_goal: str, turn_index: int, debug: bool = False) -> list[str]: ...


class PassthroughOutputEditor:
    """Keeps validated player-facing prose intact without another model request."""

    def review_opening(self, lines: list[str], active_goal: str) -> list[str]:  # noqa: ARG002
        return list(lines)

    def review_turn(
        self,
        lines: list[str],
        active_goal: str,  # noqa: ARG002
        turn_index: int,  # noqa: ARG002
        debug: bool = False,  # noqa: ARG002
    ) -> list[str]:
        return list(lines)


def build_output_editor() -> OutputEditor:
    return PassthroughOutputEditor()
