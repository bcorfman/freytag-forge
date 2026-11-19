"""Run the deterministic world-need check for a factory ticket."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.checks.world_need import check_needs, tickets_for
from factory.line import StationHandler, StationResult
from storygame.story_package.loader import load_story_package


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(root: Path, value: object) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("path must be a string")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _reason(prefix: str, error: BaseException) -> str:
    detail = str(error).replace("\n", " ").strip()
    return f"{prefix}: {detail}" if detail else prefix


def world_need_handler(root: Path | None = None) -> StationHandler:
    """Return a handler that checks the needs belonging to a ticket's scene."""

    repository_root = Path(root) if root is not None else _repository_root()

    def handle(ticket, now: datetime) -> StationResult:
        del now
        if "contract" not in ticket.payload:
            return StationResult(False, "world_need", "missing payload key: contract")

        try:
            contract_path = _resolve(repository_root, ticket.payload["contract"])
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return StationResult(False, "world_need", _reason("invalid contract JSON", error))
        except (OSError, TypeError, ValueError) as error:
            return StationResult(False, "world_need", _reason("could not read contract", error))

        try:
            story_value = ticket.payload.get("story_root", DEFAULT_ROOT)
            story_root = _resolve(repository_root, story_value)
            package = load_story_package(story_root)
        except json.JSONDecodeError as error:
            return StationResult(False, "world_need", _reason("invalid story JSON", error))
        except (OSError, TypeError, ValueError, KeyError) as error:
            return StationResult(False, "world_need", _reason("could not load story package", error))

        results = check_needs(contract, package)
        scenes = contract.get("scenes") if isinstance(contract, dict) else None
        scene_ids = (
            {
                scene.get("scene_id")
                for scene in scenes
                if isinstance(scene, dict) and isinstance(scene.get("scene_id"), str)
            }
            if isinstance(scenes, list)
            else set()
        )
        if ticket.scene in scene_ids:
            results = [result for result in results if result.scene_id == ticket.scene]

        tickets = tickets_for(results)
        output = "\n".join(
            f"{item['kind']} {item['scene_id']} {item['need_id']}: {item['summary']}" for item in tickets
        )
        return StationResult(not tickets, "world_need", output)

    return handle
