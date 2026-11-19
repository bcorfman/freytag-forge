"""Act-contract validation."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from factory.contracts.lint import Problem, lint_contract, load_rules

__all__ = ["Problem", "lint_contract", "load_rules"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from factory.contracts import lint

        return getattr(lint, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
