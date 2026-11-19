"""Create records in an authored story-source scene."""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

from storygame.story_source import check_source_tree
from storygame.story_source.compiler import compile_source_tree
from storygame.story_source.diagnostics import SourceError
from storygame.story_source.yamlio import dumps_document, load_document

_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def add_parser(commands: Any, add_global_options: Any) -> None:
    """Register the ``new`` command and its record kinds."""

    parser = commands.add_parser("new", help="create an authored source record")
    add_global_options(parser, defaults=False)
    kinds = parser.add_subparsers(dest="kind", required=True)

    fact = kinds.add_parser("fact", help="create a scene fact")
    fact.add_argument("scene")
    fact.add_argument("fact_id")
    fact.add_argument("--purpose", required=True)

    beat = kinds.add_parser("beat", help="create a pacing event")
    beat.add_argument("scene")
    beat.add_argument("event_id")
    beat.add_argument("--say", required=True)

    claim = kinds.add_parser("claim", help="add a claim to a reveal variant")
    claim.add_argument("scene")
    claim.add_argument("reveal")
    claim.add_argument("variant_key")
    claim.add_argument("claim_id")
    claim.add_argument("--says", required=True)


def _scene_path(root: Path, scene: str) -> Path:
    return root / "scenes" / f"{scene}.yaml"


def _match_path(root: Path, scene: str) -> Path:
    return root / "scenes" / f"{scene}.match.yaml"


def _scene_ids(root: Path) -> set[str]:
    story = load_document(root / "story.yaml")
    scenes = story.get("scenes", []) if isinstance(story, dict) else []
    return {str(scene) for scene in scenes} if isinstance(scenes, list) else set()


def _walk_strings(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                result.add(key)
            result.update(_walk_strings(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_walk_strings(child))
    elif isinstance(value, str):
        result.add(value)
    return result


def _used_ids(root: Path) -> set[str]:
    used: set[str] = set()
    for path in root.rglob("*.yaml"):
        used.update(_walk_strings(load_document(path)))
    return used


def _fail(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def _diagnostic_text(diagnostic: Any) -> str:
    return f"{diagnostic.name}: {diagnostic.file}:{diagnostic.address}.{diagnostic.field}: {diagnostic.message}"


def _validate_id(value: str, label: str) -> int | None:
    if not _ID.fullmatch(value):
        return _fail(f"invalid {label}: {value!r}", 2)
    return None


def _append_record(document: dict[str, Any], key: str, record: dict[str, Any]) -> None:
    values = document.setdefault(key, [])
    if not isinstance(values, list):
        raise ValueError(f"{key} is not a list")
    values.append(record)


def _make_fact(args: Any, scene: dict[str, Any]) -> None:
    facts = scene.setdefault("facts", {})
    if not isinstance(facts, dict):
        raise ValueError("facts is not a map")
    facts[args.fact_id] = {"purpose": args.purpose}


def _make_beat(args: Any, scene: dict[str, Any]) -> None:
    facts = scene.get("facts", {})
    default_fact = next(iter(facts)) if isinstance(facts, dict) and facts else None
    if default_fact is None:
        raise ValueError("scene has no declared fact for the beat effect")
    _append_record(
        scene,
        "beats",
        {
            "id": args.event_id,
            "at_turn": 0,
            "sets": {default_fact: False},
            "say": args.say,
        },
    )


def _make_claim(args: Any, scene: dict[str, Any], match: dict[str, Any]) -> None:
    reveals = scene.get("reveals", [])
    reveal = next((item for item in reveals if isinstance(item, dict) and item.get("id") == args.reveal), None)
    if reveal is None:
        raise KeyError(f"unknown reveal id: {args.reveal}")
    variants = reveal.get("variants", {})
    variant = variants.get(args.variant_key) if isinstance(variants, dict) else None
    if not isinstance(variant, dict):
        raise KeyError(f"unknown variant: {args.reveal}/{args.variant_key}")
    if "claim_id" in variant:
        raise ValueError(f"variant already has a claim: {args.reveal}/{args.variant_key}")
    variant["claim_id"] = args.claim_id
    variant["says"] = args.says
    if "audience" not in variant and "audience" not in reveal:
        variant["audience"] = "public"

    claims = match.setdefault("claims", {})
    if not isinstance(claims, dict):
        raise ValueError("match claims is not a map")
    claims[args.claim_id] = {"aliases": [args.says]}


def _write_and_check(root: Path, changes: dict[Path, tuple[bytes, str]]) -> tuple[int, str]:
    for path, (_, text) in changes.items():
        path.write_text(text, encoding="utf-8")
    diagnostics = check_source_tree(root)
    if diagnostics:
        for path, (original, _) in changes.items():
            path.write_bytes(original)
        for diagnostic in diagnostics:
            print(_diagnostic_text(diagnostic), file=sys.stderr)
        return 1, ""
    try:
        compile_source_tree(root)
    except SourceError as error:
        for path, (original, _) in changes.items():
            path.write_bytes(original)
        for diagnostic in error.diagnostics:
            print(_diagnostic_text(diagnostic), file=sys.stderr)
        return 1, ""
    except Exception as error:
        for path, (original, _) in changes.items():
            path.write_bytes(original)
        print(str(error), file=sys.stderr)
        return 1, ""
    diff_parts: list[str] = []
    for path, (original, text) in changes.items():
        diff_parts.extend(
            difflib.unified_diff(
                original.decode("utf-8").splitlines(keepends=True),
                text.splitlines(keepends=True),
                fromfile=path.relative_to(root).as_posix(),
                tofile=path.relative_to(root).as_posix(),
            )
        )
    return 0, "".join(diff_parts)


def run(args: Any, root: Path) -> int:
    """Create one fact, pacing beat, or reveal claim."""

    if args.scene not in _scene_ids(root):
        return _fail(f"unknown scene id: {args.scene}", 2)
    scene_path = _scene_path(root, args.scene)
    match_path = _match_path(root, args.scene)
    used = _used_ids(root)
    identifier = args.fact_id if args.kind == "fact" else args.event_id if args.kind == "beat" else args.claim_id
    if (bad_id := _validate_id(identifier, f"{args.kind} id")) is not None:
        return bad_id
    if identifier in used:
        return _fail(f"id already used: {identifier}")

    scene = load_document(scene_path)
    match = load_document(match_path) if match_path.is_file() else {"schema": 1, "scene": args.scene}
    original_scene = scene_path.read_bytes()
    original_match = match_path.read_bytes() if match_path.is_file() else None
    try:
        if args.kind == "fact":
            _make_fact(args, scene)
        elif args.kind == "beat":
            _make_beat(args, scene)
        else:
            _make_claim(args, scene, match)
    except (KeyError, ValueError) as error:
        return _fail(str(error), 2 if isinstance(error, KeyError) else 1)

    changes = {scene_path: (original_scene, dumps_document(scene))}
    if args.kind == "claim":
        changes[match_path] = (original_match or b"", dumps_document(match))
    code, diff = _write_and_check(root, changes)
    if code:
        if args.kind == "claim" and original_match is None and match_path.is_file():
            match_path.unlink()
        return code
    changed = [path.relative_to(root).as_posix() for path in changes]
    if args.json:
        print(json.dumps({"changed": changed, "diff": diff}, ensure_ascii=False))
    else:
        print(diff, end="")
    return 0
