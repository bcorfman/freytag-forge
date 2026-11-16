"""Diagnostic values and the exception used by source validation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    """A stable, source-located validation diagnostic."""

    name: str
    file: str
    address: str
    field: str
    message: str


class SourceError(Exception):
    """An exception containing one or more source diagnostics."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        self.diagnostics = diagnostics
        super().__init__(self._format_diagnostics())

    def _format_diagnostics(self) -> str:
        return "\n".join(
            f"{diagnostic.name}: {diagnostic.file}:{diagnostic.address}.{diagnostic.field}: {diagnostic.message}"
            for diagnostic in self.diagnostics
        )
