"""Deterministic handlers for the factory stations that need no billed model."""

from pathlib import Path

from factory.line import StationHandler
from factory.tickets import Station

from .free_gates import free_gates_handler
from .prompt_snapshot import prompt_snapshot_handler
from .triage import triage_handler
from .world_need import world_need_handler


def build_handlers(root: Path | None = None) -> dict[Station, StationHandler]:
    """Build the handlers implemented in this factory round."""

    return {
        Station.WORLD_NEED: world_need_handler(root),
        Station.FREE_GATES: free_gates_handler(root),
        Station.PROMPT_SNAPSHOT: prompt_snapshot_handler(root),
        Station.TRIAGE: triage_handler(root),
    }


# Stations 0, 1, 3, 4, 7 and 9 are built in later rounds.
