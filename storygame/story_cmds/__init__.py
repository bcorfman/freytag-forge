"""Discoverable story CLI command modules."""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType


def discover() -> dict[str, ModuleType]:
    """Import every ``cmd_<name>`` module in this package."""

    commands: dict[str, ModuleType] = {}
    for entry in pkgutil.iter_modules(__path__):
        if entry.name.startswith("cmd_"):
            name = entry.name.removeprefix("cmd_")
            commands[name] = importlib.import_module(f"{__name__}.{entry.name}")
    return commands
