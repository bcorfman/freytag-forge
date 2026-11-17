"""Public entry points for reading and checking declarative story sources."""

from pathlib import Path

from . import checks
from .diagnostics import Diagnostic, SourceError
from .reader import SourceTree, read_source_tree

__all__ = [
    "Diagnostic",
    "SourceError",
    "SourceTree",
    "check_source_tree",
    "read_source_tree",
]


def check_source_tree(root: Path) -> list[Diagnostic]:
    """Read and validate a source tree, returning stable, sorted diagnostics."""

    tree, reader_diagnostics = read_source_tree(root)
    checks.discover()
    diagnostics = [*reader_diagnostics, *checks.run_layer1(tree)]
    if not any(diagnostic.name in {"L1.syntax", "L1.duplicate_key"} for diagnostic in reader_diagnostics):
        diagnostics.extend(checks.run_layer2(tree))
    return sorted(diagnostics, key=lambda diagnostic: (diagnostic.file, diagnostic.address, diagnostic.name))


from .compiler import COMPILER_VERSION, compile_source_tree  # noqa: E402
from .digest import source_digest  # noqa: E402

__all__ += ["COMPILER_VERSION", "compile_source_tree", "source_digest"]

_LAZY = {
    "check_parity": "parity",
    "check_save_identity": "identity",
    "override_ratio": "ratio",
    "pass2_gate": "ratio",
    "check_examples": "examples",
    "story_text": "lookup",
    "story_value": "lookup",
}


def __getattr__(name: str) -> object:
    """Resolve the later-round APIs from their modules on first use."""

    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(name)
    import importlib

    try:
        module = importlib.import_module(f"{__name__}.{module_name}")
    except ModuleNotFoundError as error:
        if error.name != f"{__name__}.{module_name}":
            raise
        raise AttributeError(name) from error
    return getattr(module, name)
