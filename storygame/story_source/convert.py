"""Assemble the independent legacy-package converters into a source tree."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from storygame.story_package.models import StoryPackage

from .convert_catalog import convert_catalog, convert_story
from .convert_facts import convert_facts
from .convert_reveals import convert_reveals
from .convert_scene import convert_scenes

_SCENE_KEYS = (
    "schema",
    "scene",
    "title",
    "location",
    "objective",
    "freytag_phase",
    "situation",
    "pressure",
    "turns",
    "scripted_opening",
    "companions",
    "participants",
    "items",
    "setting",
    "prop_pool",
    "entry",
    "entry_additions",
    "entry_claims",
    "brief",
    "outline",
    "facts",
    "placements",
    "beats",
    "reveals",
    "bridge",
    "incidents",
    "exit",
    "ending",
)
_MATCH_KEYS = ("schema", "scene", "lexicon", "plural_twins", "shared", "claims", "deliveries")


def _ordered_document(fields: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Return a document in contract order, omitting optional absent fields."""

    return {key: fields[key] for key in keys if key in fields}


def _merge_scene_documents(*documents: Mapping[str, Any]) -> dict[str, Any]:
    """Merge disjoint converter fragments into one scene document."""

    merged: dict[str, Any] = {}
    for document in documents:
        for key, value in document.items():
            if key in merged:
                raise ValueError(f"scene converter fragments collide on key {key!r}")
            merged[key] = value
    return _ordered_document({"schema": 1, **merged}, _SCENE_KEYS)


def _merge_match_documents(*documents: Mapping[str, Any]) -> dict[str, Any]:
    """Merge match fragments while rejecting duplicate claim or delivery IDs."""

    merged: dict[str, Any] = {}
    for document in documents:
        for key, value in document.items():
            if key in {"claims", "deliveries"}:
                current = merged.setdefault(key, {})
                for item_id, item in value.items():
                    if item_id in current:
                        raise ValueError(f"match converter fragments collide on {key} entry {item_id!r}")
                    current[item_id] = item
            elif key in merged:
                raise ValueError(f"match converter fragments collide on key {key!r}")
            else:
                merged[key] = value
    return _ordered_document({"schema": 1, **merged}, _MATCH_KEYS)


def convert_package(package: StoryPackage) -> dict[str, dict]:
    """Convert a loaded legacy package into deterministic relative-path documents."""

    facts = convert_facts(package)
    reveals = convert_reveals(package)
    scenes = convert_scenes(package)
    documents: dict[str, dict] = {
        "story.yaml": convert_story(package),
        "catalog.yaml": convert_catalog(package, facts.unplaced_facts),
    }
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        documents[f"scenes/{scene_id}.yaml"] = _merge_scene_documents(
            scenes.scene_docs[scene_id], facts.scene_docs[scene_id], reveals.scene_docs[scene_id]
        )
        documents[f"scenes/{scene_id}.match.yaml"] = _merge_match_documents(
            reveals.match_docs[scene_id], scenes.match_docs.get(scene_id, {})
        )
    return documents


def write_source_tree(package: StoryPackage, root: Path) -> None:
    """Write the converted package as deterministic YAML documents below ``root``."""

    (root / "scenes").mkdir(parents=True, exist_ok=True)
    for relative_path, document in convert_package(package).items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=1000),
            encoding="utf-8",
        )
