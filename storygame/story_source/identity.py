"""Check declarative packages against the frozen save-identity manifest."""

from __future__ import annotations

import warnings
from collections.abc import Iterable, Mapping


def check_save_identity(
    package: object,
    manifest: object,
    *,
    retired_ids: Mapping[str, Mapping[str, str]] | None = None,
) -> None:
    """Warn once for each frozen identifier absent from a package."""

    frozen = _manifest_ids(manifest)
    package_ids = _package_ids(package)
    for kind, identifiers in frozen.items():
        present = package_ids.get(kind, frozenset())
        retired = _retired_for(retired_ids, kind)
        for identifier in identifiers:
            if identifier not in present and identifier not in retired:
                warnings.warn(
                    f"frozen {kind} id {identifier!r} is missing from the package",
                    UserWarning,
                    stacklevel=2,
                )


def _manifest_ids(manifest: object) -> dict[str, tuple[str, ...]]:
    """Read the manifest's kind-to-list mapping without trusting its shape."""

    try:
        ids = manifest.get("ids") if isinstance(manifest, Mapping) and "ids" in manifest else manifest
        if not isinstance(ids, Mapping):
            return {}
        return {
            str(kind): tuple(identifier for identifier in values if isinstance(identifier, str))
            for kind, values in ids.items()
            if isinstance(values, Iterable) and not isinstance(values, (str, bytes))
        }
    except Exception:
        return {}


def _package_ids(package: object) -> dict[str, frozenset[str]]:
    """Collect package identifiers using the test-double and package shapes."""

    try:
        explicit = package.get("ids") if isinstance(package, Mapping) else getattr(package, "ids", None)
        if isinstance(explicit, Mapping):
            return {
                str(kind): frozenset(value for value in values if isinstance(value, str))
                for kind, values in explicit.items()
                if isinstance(values, Iterable) and not isinstance(values, (str, bytes))
            }
        return _model_ids(package)
    except Exception:
        return {}


def _model_ids(package: object) -> dict[str, frozenset[str]]:
    """Collect identifiers from the public StoryPackage collections."""

    result: dict[str, frozenset[str]] = {}
    knowledge = getattr(package, "knowledge", None)
    world = getattr(package, "world", None)
    result["fact"] = _ids(
        getattr(package, "fact_ids", None) or getattr(knowledge, "facts", None) or getattr(world, "facts", None)
    )
    result["claim"] = _ids(getattr(knowledge, "knowledge", None))
    result["storylet"] = _ids(getattr(package, "storylets", None))
    result["incident"] = _ids(getattr(package, "incidents", None))
    result["entity"] = _world_entity_ids(world)
    result["beat"], result["outline"] = _scene_ids(getattr(package, "scenes", None))
    result["realization"] = _realization_ids(getattr(package, "storylet_routes", None))
    result["exit"] = _transition_ids(getattr(package, "scenes", None))
    return result


def _ids(value: object) -> frozenset[str]:
    """Extract mapping keys or record IDs from a package collection."""

    if isinstance(value, Mapping):
        return frozenset(key for key in value if isinstance(key, str))
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return frozenset(
            item if isinstance(item, str) else item.id
            for item in value
            if isinstance(item, str) or isinstance(getattr(item, "id", None), str)
        )
    return frozenset()


def _world_entity_ids(world: object) -> frozenset[str]:
    """Collect all catalog entity identifiers from the world source."""

    kinds = ("locations", "npcs", "groups", "items", "kinds", "props")
    return frozenset(identifier for kind in kinds for identifier in _ids(getattr(world, kind, None)))


def _scene_ids(scenes: object) -> tuple[frozenset[str], frozenset[str]]:
    """Collect beat IDs and their equivalent outline IDs from scenes."""

    beats = frozenset(identifier for scene in scenes or () for identifier in _ids(getattr(scene, "beats", None)))
    return beats, beats


def _realization_ids(routes: object) -> frozenset[str]:
    """Collect realization identifiers nested under storylet routes."""

    return frozenset(
        realization.id
        for route in routes or ()
        for realization in getattr(route, "realizations", ())
        if isinstance(getattr(realization, "id", None), str)
    )


def _transition_ids(scenes: object) -> frozenset[str]:
    """Collect transition IDs from scene metadata."""

    return frozenset(
        transition_id
        for scene in scenes or ()
        for transition_id in getattr(getattr(scene, "metadata", None), "transition_ids", ())
        if isinstance(transition_id, str)
    )


def _retired_for(retired_ids: object, kind: str) -> frozenset[str]:
    """Return retired IDs for one kind, treating malformed data as empty."""

    try:
        values = retired_ids.get(kind) if isinstance(retired_ids, Mapping) else None
        return frozenset(values) if isinstance(values, Mapping) else frozenset()
    except Exception:
        return frozenset()
