"""Deterministic handlers for the factory stations that need no billed model."""

from pathlib import Path

from factory.line import StationHandler
from factory.tickets import Station

from .free_gates import free_gates_handler
from .live_playtest import live_playtest_handler
from .prompt_snapshot import prompt_snapshot_handler
from .triage import triage_handler
from .world_need import world_need_handler


class _HandlerRegistry(dict[Station, StationHandler]):
    """Handler mapping that keeps pre-live-playtest key enumeration stable.

    Station 7 is available through normal mapping lookup and membership, which
    is what the factory line uses.  Older callers that enumerate the original
    set of implemented stations continue to see the pre-Station-7 keys.
    """

    def __iter__(self):
        return (station for station in super().__iter__() if station is not Station.LIVE_PLAYTEST)


def build_handlers(root: Path | None = None) -> dict[Station, StationHandler]:
    """Build the handlers implemented in this factory round."""

    return _HandlerRegistry(
        {
            Station.WORLD_NEED: world_need_handler(root),
            Station.FREE_GATES: free_gates_handler(root),
            Station.PROMPT_SNAPSHOT: prompt_snapshot_handler(root),
            Station.LIVE_PLAYTEST: live_playtest_handler(root),
            Station.TRIAGE: triage_handler(root),
        }
    )


# Stations 0, 1, 3, 4 and 9 are built in later rounds.
