"""Project a loaded story package into the legacy frontend authoring view."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from storygame.story_package.loader import load_story_package
from storygame.story_package.models import CanonicalRouteEvent, Scene, StoryPackage


def _route_event(event: CanonicalRouteEvent) -> dict[str, Any]:
    """Translate compiled route operations to the legacy ``produces`` field."""

    result = event.model_dump(mode="json")
    result["produces"] = result.pop("operations")
    return result


def _frames(scenes: tuple[Scene, ...]) -> dict[str, dict[str, Any]]:
    return {
        scene.metadata.scene_id: {
            "scene_id": scene.metadata.scene_id,
            "entry_text": scene.metadata.entry_text,
            "entry_variants": [variant.model_dump(mode="json") for variant in scene.metadata.entry_variants],
            "bridge_text": dict(scene.metadata.bridge_text),
        }
        for scene in scenes
    }


def authoring_view(package: StoryPackage) -> dict[str, object]:
    """Return a deterministic, JSON-serialisable view for legacy frontend tools."""

    routes = package.storylet_routes
    return {
        "knowledge": package.knowledge.model_dump(mode="json"),
        "pacing": package.pacing.model_dump(mode="json"),
        "handoffs": {"deliveries": [delivery.model_dump(mode="json") for delivery in package.deliveries]},
        "routes": {
            "canonical_bridge_events": [_route_event(event) for event in routes.bridge_events],
            "canonical_resolution_events": [_route_event(event) for event in routes.resolution_events],
            "storylets": [storylet.model_dump(mode="json") for storylet in routes.storylets],
        },
        "frames": _frames(package.scenes),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story_root", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.story_root.is_dir():
        print(f"story root does not exist: {args.story_root}", file=sys.stderr)
        return 1
    try:
        view = authoring_view(load_story_package(args.story_root))
    except Exception as exc:
        print(f"could not load story root {args.story_root}: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(view, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        print(rendered, end="")
    else:
        args.out.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
