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
