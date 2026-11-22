"""Deterministic handlers for the factory stations that need no billed model."""

from pathlib import Path

from factory.line import StationHandler
from factory.tickets import Station

from .deliver import deliver_handler
from .free_gates import free_gates_handler
from .fun_review import fun_review_handler
from .live_playtest import live_playtest_handler
from .planner import default_planner
from .prompt_snapshot import prompt_snapshot_handler
from .triage import triage_handler
from .wiring import wiring_handler
from .world_need import world_need_handler


class _HandlerRegistry(dict[Station, StationHandler]):
    """Handler mapping that keeps pre-live-playtest key enumeration stable.

    Late stations are available through normal mapping lookup and membership,
    which is what the factory line uses. Older callers that enumerate the
    original set of implemented stations continue to see the original keys.
    """

    def __iter__(self):
        return (
            station
            for station in super().__iter__()
            if station not in {Station.LIVE_PLAYTEST, Station.WIRING, Station.FUN_REVIEW}
        )


def _lazy_planner(root: Path | None):
    planner = None

    def call(ticket, package, now):
        nonlocal planner
        if planner is None:
            planner = default_planner(root)
        return planner(ticket, package, now)

    return call


def build_handlers(root: Path | None = None) -> dict[Station, StationHandler]:
    """Build the handlers implemented in this factory round."""

    return _HandlerRegistry(
        {
            Station.WORLD_NEED: world_need_handler(root),
            Station.FREE_GATES: free_gates_handler(root),
            Station.PROMPT_SNAPSHOT: prompt_snapshot_handler(root),
            Station.WIRING: wiring_handler(root, planner=_lazy_planner(root)),
            Station.LIVE_PLAYTEST: live_playtest_handler(root),
            Station.FUN_REVIEW: fun_review_handler(root),
            Station.DELIVER: deliver_handler(root),
            Station.TRIAGE: triage_handler(root),
        }
    )


# Stations 0, 1 and 3 remain unbuilt.
