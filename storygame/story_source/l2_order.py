"""Layer-two checks for explicit per-scene record order."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .checks import layer2_check
from .diagnostics import Diagnostic
from .l2_story import _MATCH_FILE, _SCENE_FILE
from .reader import SourceTree

_KINDS = ("storylets", "deliveries", "knowledge", "pacing_events")


def _mapping(value: object) -> dict[Any, Any] | None:
    return value if isinstance(value, dict) else None


def _diagnostic(file: str, scene_id: str, kind: str, message: str) -> Diagnostic:
    return Diagnostic("L2.order_id", file, f"scene:{scene_id}.order", kind, message)


def _ids(scene: Mapping[str, Any], match: Mapping[str, Any], kind: str) -> set[str]:
    if kind == "storylets":
        return {
            reveal["storylet_id"]
            for reveal in scene.get("reveals", ())
            if isinstance(reveal, dict) and isinstance(reveal.get("storylet_id"), str)
        }
    if kind in {"deliveries", "knowledge"}:
        section = match.get("deliveries" if kind == "deliveries" else "claims")
        return set(section) if isinstance(section, dict) else set()
    return {beat["id"] for beat in scene.get("beats", ()) if isinstance(beat, dict) and isinstance(beat.get("id"), str)}


@layer2_check
def check_order_ids(tree: SourceTree) -> list[Diagnostic]:
    """Reject unknown and duplicate IDs in each scene's order mapping."""

    diagnostics: list[Diagnostic] = []
    for file, value in sorted(tree.files.items()):
        if not _SCENE_FILE.fullmatch(file) or _MATCH_FILE.fullmatch(file):
            continue
        scene = _mapping(value)
        if scene is None or not isinstance(scene.get("scene"), str):
            continue
        order = _mapping(scene.get("order"))
        if order is None:
            continue
        scene_id = scene["scene"]
        match = _mapping(tree.files.get(f"scenes/{scene_id}.match.yaml")) or {}
        for kind in _KINDS:
            values = order.get(kind)
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                continue
            valid_ids = _ids(scene, match, kind)
            seen: set[str] = set()
            for item_id in values:
                if item_id in seen:
                    diagnostics.append(_diagnostic(file, scene_id, kind, f"duplicate {kind} order ID {item_id!r}"))
                seen.add(item_id)
                if item_id not in valid_ids:
                    diagnostics.append(_diagnostic(file, scene_id, kind, f"unknown {kind} order ID {item_id!r}"))
    return diagnostics
