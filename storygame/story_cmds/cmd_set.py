"""Edit one authored YAML value in a story source tree."""

from __future__ import annotations

import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from storygame.story_source import check_source_tree
from storygame.story_source.compiler import compile_source_tree
from storygame.story_source.yamlio import dumps_document, load_document


@dataclass
class _Location:
    """A mutable YAML value and the file that owns it."""

    path: Path
    document: Any
    parent: Any
    key: str | int
    missing: bool = False

    @property
    def value(self) -> Any:
        if self.missing:
            raise _AddressError(str(self.key))
        return self.parent[self.key]

    @value.setter
    def value(self, value: Any) -> None:
        self.parent[self.key] = value


class _AddressError(Exception):
    """An address cannot be resolved to an authored YAML value."""


class _Refused(Exception):
    """The requested source field is intentionally not author-editable."""


def add_parser(commands: Any, add_global_options: Any) -> None:
    """Register the ``set`` command with the story CLI parser."""

    parser = commands.add_parser("set", help="edit one authored YAML value")
    add_global_options(parser, defaults=False)
    parser.add_argument("address")
    parser.add_argument("yaml_value", nargs="?")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--add")
    operation.add_argument("--drop")


def _parse_address(address: str) -> tuple[str, str, list[tuple[str, int | None]]]:
    kind, separator, rest = address.partition(":")
    if not separator or not kind or not rest:
        raise _AddressError(address)
    identifier, _, field_text = rest.partition(".")
    fields: list[tuple[str, int | None]] = []
    for part in field_text.split(".") if field_text else []:
        if "[" in part:
            name, selector = part.rsplit("[", 1)
            if not selector.endswith("]") or not selector[:-1].lstrip("-").isdigit():
                raise _AddressError(address)
            fields.append((name, int(selector[:-1])))
        else:
            fields.append((part, None))
    return kind, identifier, fields


def _walk(document: Any, path: list[tuple[str, int | None]], address: str) -> _Location:
    current = document
    parent: Any = None
    key: str | int = ""
    for index, (name, selector) in enumerate(path):
        if not isinstance(current, dict) or name not in current:
            if index == len(path) - 1 and selector is None and isinstance(current, dict):
                return _Location(Path(), document, current, name, missing=True)
            raise _AddressError(address)
        parent, key = current, name
        current = current[name]
        if selector is not None:
            if not isinstance(current, list) or not -len(current) <= selector < len(current):
                raise _AddressError(address)
            parent, key = current, selector
            current = current[selector]
    if parent is None:
        raise _AddressError(address)
    return _Location(Path(), document, parent, key)


def _record(doc: Any, path: list[tuple[str, int | None]], address: str) -> _Location:
    return _walk(doc, path, address)


def _scene_files(root: Path) -> list[Path]:
    return sorted(path for path in (root / "scenes").glob("*.yaml") if ".match." not in path.name)


def _find_record(
    root: Path, kind: str, identifier: str, address: str
) -> tuple[Path, Any, list[tuple[str, int | None]]]:
    paths = _scene_files(root)
    if kind == "scene":
        path = root / "scenes" / f"{identifier}.yaml"
        if path.is_file():
            return path, load_document(path), []
    if kind in {"fact", "delivery"}:
        for path in [root / "catalog.yaml", *paths]:
            doc = load_document(path)
            for section in ("facts", "unplaced_facts"):
                records = doc.get(section) if isinstance(doc, dict) else None
                if isinstance(records, dict) and identifier in records:
                    path_parts = [(section, None), (identifier, None)]
                    if kind == "delivery":
                        path_parts.append(("delivery", None))
                    return path, doc, path_parts
        if kind == "delivery":
            for path in paths:
                match_path = path.with_name(path.stem + ".match.yaml")
                if not match_path.is_file():
                    continue
                doc = load_document(match_path)
                deliveries = doc.get("deliveries", {}) if isinstance(doc, dict) else {}
                if isinstance(deliveries, dict) and identifier in deliveries:
                    return match_path, doc, [("deliveries", None), (identifier, None)]
    if kind == "claim":
        match_paths = [path for path in paths if path.with_name(path.stem + ".match.yaml").is_file()]
        for path in paths:
            doc = load_document(path)
            for index, claim in enumerate(doc.get("entry_claims", []) or []):
                if isinstance(claim, dict) and claim.get("claim_id") == identifier:
                    return path, doc, [("entry_claims", index)]
            for reveal_index, reveal in enumerate(doc.get("reveals", []) or []):
                for variant_name, variant in (reveal.get("variants", {}) or {}).items():
                    if variant.get("claim_id") == identifier:
                        return path, doc, [("reveals", reveal_index), ("variants", None), (variant_name, None)]
                    for extra_index, claim in enumerate(variant.get("extra_claims", []) or []):
                        if isinstance(claim, dict) and claim.get("claim_id") == identifier:
                            return (
                                path,
                                doc,
                                [
                                    ("reveals", reveal_index),
                                    ("variants", None),
                                    (variant_name, None),
                                    ("extra_claims", extra_index),
                                ],
                            )
            for bridge_index, bridge in enumerate(doc.get("bridge", []) or []):
                if isinstance(bridge.get("claim"), dict) and bridge["claim"].get("claim_id") == identifier:
                    return path, doc, [("bridge", bridge_index), ("claim", None)]
        for path in match_paths:
            doc = load_document(path)
            claims = doc.get("claims", {}) if isinstance(doc, dict) else {}
            if identifier in claims:
                return path, doc, [("claims", None), (identifier, None)]
    if kind == "entity":
        path = root / "catalog.yaml"
        doc = load_document(path)
        for section in ("places", "characters", "groups", "items", "props", "kinds"):
            if identifier in (doc.get(section) or {}):
                return path, doc, [(section, None), (identifier, None)]
    if kind in {"beat", "outline", "bridge", "exit", "reveal", "variant", "part", "outcome"}:
        for path in paths:
            doc = load_document(path)
            if kind in {"beat", "outline"}:
                for section in ("beats", "outline"):
                    for index, item in enumerate(doc.get(section, []) or []):
                        if item.get("id") == identifier:
                            return path, doc, [(section, index)]
            if kind == "exit" and isinstance(doc.get("exit"), dict) and doc["exit"].get("id") == identifier:
                return path, doc, [("exit", None)]
            for index, item in enumerate(doc.get("bridge", []) or []):
                if kind == "bridge" and item.get("id") == identifier:
                    return path, doc, [("bridge", index)]
            for reveal_index, reveal in enumerate(doc.get("reveals", []) or []):
                reveal_id = reveal.get("id", reveal.get("storylet_id"))
                if kind == "reveal" and reveal_id == identifier:
                    return path, doc, [("reveals", reveal_index)]
                reveal_id, _, variant_id = identifier.partition("/")
                if reveal.get("id", reveal.get("storylet_id")) == reveal_id:
                    variants = reveal.get("variants", {}) or {}
                    if kind == "variant" and variant_id in variants:
                        return path, doc, [("reveals", reveal_index), ("variants", None), (variant_id, None)]
                    parts = reveal.get("parts", {}) or {}
                    if kind == "part" and variant_id in parts:
                        return path, doc, [("reveals", reveal_index), ("parts", None), (variant_id, None)]
            if kind == "outcome":
                incident_id, _, outcome_id = identifier.partition("/")
                for incident in doc.get("incidents", []) or []:
                    if incident.get("id") == incident_id:
                        reveal_id = incident.get("reveal")
                        for reveal in doc.get("reveals", []) or []:
                            if reveal.get("id", reveal.get("storylet_id")) == reveal_id:
                                for variant_name, variant in (reveal.get("variants", {}) or {}).items():
                                    if (
                                        isinstance(variant.get("outcome"), dict)
                                        and variant["outcome"].get("id") == outcome_id
                                    ):
                                        return (
                                            path,
                                            doc,
                                            [
                                                ("reveals", doc["reveals"].index(reveal)),
                                                ("variants", None),
                                                (variant_name, None),
                                                ("outcome", None),
                                            ],
                                        )
    if kind == "ending":
        for path in reversed(paths):
            doc = load_document(path)
            if "ending" in doc:
                return path, doc, [("ending", None)]
    raise _AddressError(address)


def _locate(root: Path, address: str) -> _Location:
    kind, identifier, fields = _parse_address(address)
    if kind == "fact" and identifier in {f"scene_{path.stem.lower()}_entry_known" for path in _scene_files(root)}:
        raise _Refused("generated entry facts cannot be edited")
    if kind == "delivery" and fields and fields[0][0] == "must_convey":
        for scene_path in _scene_files(root):
            match_path = scene_path.with_name(scene_path.stem + ".match.yaml")
            if not match_path.is_file():
                continue
            match = load_document(match_path)
            deliveries = match.get("deliveries", {}) if isinstance(match, dict) else {}
            if isinstance(deliveries, dict) and identifier in deliveries:
                location = _walk(deliveries[identifier], fields, address)
                location.path = match_path
                location.document = match
                return location
    path, doc, record_path = _find_record(root, kind, identifier, address)
    if not fields:
        raise _AddressError(address)
    if kind == "claim" and fields[0][0] in {"aliases", "action_evidence", "must_convey", "leak_terms", "earn_when"}:
        match_path = path if path.name.endswith(".match.yaml") else path.with_name(path.stem + ".match.yaml")
        if not match_path.is_file():
            raise _AddressError(address)
        match = load_document(match_path)
        claim = match.get("claims", {}).get(identifier)
        if not isinstance(claim, dict):
            raise _AddressError(address)
        owner = claim
        if fields[0][0] not in owner and isinstance(owner.get("use"), str):
            shared = match.get("shared", {}).get(owner["use"])
            if isinstance(shared, dict):
                owner = shared
        if fields[0][0] in owner:
            location = _walk(owner, fields, address)
            location.path = match_path
            location.document = match
            return location
    aliases = {"says": "says", "text": "text"}
    if fields[0][0] in aliases:
        fields[0] = (aliases[fields[0][0]], fields[0][1])
    location = _walk(doc, record_path + fields, address)
    location.path = path
    return location


def _refusal(address: str, location: _Location) -> None:
    kind, _, _ = _parse_address(address)
    if location.path.name.endswith(".lock.yaml"):
        raise _Refused("lock-file entries are generated")
    field_names = [name for name, _ in _parse_address(address)[2]]
    frozen = {"id", "claim_id", "realization_id", "anchor"}
    if any(name in frozen for name in field_names):
        raise _Refused("frozen id fields cannot be edited")
    if kind == "fact" and location.parent is location.document:
        raise _Refused("generated entry facts cannot be edited")


def _diagnostics(root: Path) -> list[Any]:
    diagnostics = check_source_tree(root)
    if diagnostics:
        return diagnostics
    try:
        compile_source_tree(root)
    except Exception as error:
        return getattr(error, "diagnostics", [error])
    return []


def _print_diagnostics(diagnostics: list[Any]) -> None:
    for diagnostic in diagnostics:
        print(str(diagnostic), file=sys.stderr)


def run(args: Any, root: Path) -> int:
    """Set, append, or remove one authored YAML value."""

    if args.yaml_value is None and args.add is None and args.drop is None:
        print(f"missing value for address: {args.address}", file=sys.stderr)
        return 2
    if args.yaml_value is not None and (args.add is not None or args.drop is not None):
        print("set accepts a replacement or --add/--drop, not both", file=sys.stderr)
        return 2
    try:
        location = _locate(root, args.address)
        _refusal(args.address, location)
        if location.missing and args.yaml_value is None:
            raise _AddressError(args.address)
        original = location.path.read_bytes()
        old_text = original.decode("utf-8")
        if args.add is not None or args.drop is not None:
            value = location.value
            if not isinstance(value, list):
                raise _Refused("--add and --drop require a list field")
            item_text = args.add if args.add is not None else args.drop
            item = yaml.safe_load(item_text)
            if args.add is not None:
                if item in value:
                    print(f"value already present at {args.address}", file=sys.stderr)
                    return 1
                value.append(item)
            else:
                try:
                    value.remove(item)
                except ValueError:
                    print(f"value not present at {args.address}", file=sys.stderr)
                    return 1
        else:
            location.value = yaml.safe_load(args.yaml_value)
        new_text = dumps_document(location.document)
        location.path.write_text(new_text, encoding="utf-8")
        diagnostics = _diagnostics(root)
        if diagnostics:
            location.path.write_bytes(original)
            _print_diagnostics(diagnostics)
            return 1
    except yaml.YAMLError as error:
        print(f"invalid YAML value for {args.address}: {error}", file=sys.stderr)
        return 2
    except _AddressError:
        print(f"unknown address or missing field: {args.address}", file=sys.stderr)
        return 2
    except _Refused as error:
        print(f"refused {args.address}: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 1
    relative = location.path.relative_to(root).as_posix()
    diff = "".join(
        difflib.unified_diff(old_text.splitlines(True), new_text.splitlines(True), fromfile=relative, tofile=relative)
    )
    if args.json:
        print(json.dumps({"changed": [location.path.relative_to(root).as_posix()], "diff": diff}, ensure_ascii=False))
    else:
        print(diff, end="")
    return 0
