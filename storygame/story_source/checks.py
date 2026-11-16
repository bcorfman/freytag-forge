"""Registration and deterministic execution of story-source validation checks."""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

from .diagnostics import Diagnostic
from .reader import SourceTree

Check = Callable[[SourceTree], list[Diagnostic]]
_REGISTRY: dict[str, list[Check]] = {}


def _register(fn: Check) -> Check:
    _REGISTRY.setdefault(fn.__module__, []).append(fn)
    return fn


def layer1_check(fn: Check) -> Check:
    """Register a layer 1 check."""

    return _register(fn)


def layer2_check(fn: Check) -> Check:
    """Register a layer 2 check."""

    return _register(fn)


def discover() -> None:
    """Import every layer check module in the story-source package."""

    package = importlib.import_module(__package__)
    module_names = sorted(
        module_info.name
        for module_info in pkgutil.iter_modules(package.__path__, f"{package.__name__}.")
        if module_info.name.rsplit(".", 1)[-1].startswith(("l1_", "l2_"))
    )

    package_prefix = f"{package.__name__}."
    discovered = set(module_names)
    for module_name in tuple(_REGISTRY):
        if module_name.startswith(package_prefix) and module_name not in discovered:
            del _REGISTRY[module_name]

    for module_name in module_names:
        importlib.import_module(module_name)


def _run(prefix: str, tree: SourceTree) -> list[Diagnostic]:
    groups: list[list[Diagnostic]] = []
    for module_name in sorted(_REGISTRY):
        if module_name.rsplit(".", 1)[-1].startswith(prefix):
            groups.extend(check(tree) for check in _REGISTRY[module_name])
    return [diagnostic for group in groups for diagnostic in group]


def run_layer1(tree: SourceTree) -> list[Diagnostic]:
    """Run all registered layer 1 checks in deterministic order."""

    return _run("l1_", tree)


def run_layer2(tree: SourceTree) -> list[Diagnostic]:
    """Run all registered layer 2 checks in deterministic order."""

    return _run("l2_", tree)
