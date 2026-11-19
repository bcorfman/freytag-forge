"""Command-line tools for inspecting and maintaining story source trees."""

from __future__ import annotations

import argparse
import inspect
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from storygame.story_cmds import discover

_DEFAULT_STORY = "continuity-initiative"
_STUB_COMMAND_NAMES = {"set", "rename", "impact", "new", "fmt"}


def _add_global_options(parser: argparse.ArgumentParser, *, defaults: bool) -> None:
    default = _DEFAULT_STORY if defaults else argparse.SUPPRESS
    parser.add_argument("--story", default=default, help="story identifier")
    json_default = False if defaults else argparse.SUPPRESS
    parser.add_argument("--json", action="store_true", default=json_default, help="emit machine-readable output")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="story")
    _add_global_options(parser, defaults=True)
    commands = parser.add_subparsers(dest="command", required=True)

    show = commands.add_parser("show", help="show an authored record")
    _add_global_options(show, defaults=False)
    show.add_argument("address")

    parity = commands.add_parser("parity", help="compare a source scene with its legacy package")
    _add_global_options(parity, defaults=False)
    parity.add_argument("scene")

    lock = commands.add_parser("lock", help="refresh pass-2 lock entries")
    _add_global_options(lock, defaults=False)
    lock.add_argument("scene", nargs="?")
    lock.add_argument("--all", action="store_true")
    lock.add_argument("--adopt", action="store_true")
    lock.add_argument("--dry-run", action="store_true")

    expand = commands.add_parser("expand", help="materialize pass-2 values")
    _add_global_options(expand, defaults=False)
    expand.add_argument("scene")

    command_modules = discover()
    for module in command_modules.values():
        module.add_parser(commands, _add_global_options)

    for name in sorted(_STUB_COMMAND_NAMES - command_modules.keys()):
        command = commands.add_parser(name, help=f"{name} (not built yet)")
        _add_global_options(command, defaults=False)
        command.add_argument("arguments", nargs="*")
        command.add_argument("--add", action="append", default=[])
        command.add_argument("--drop", action="append", default=[])

    return parser


def _source_root(story: str) -> Path | None:
    current = Path.cwd()
    candidates = (
        current if (current / "story.yaml").is_file() else None,
        current / "data" / "stories" / story / "source",
        current / "data" / "story-pilot" / story / "source",
    )
    return next((candidate for candidate in candidates if candidate is not None and candidate.is_dir()), None)


def _require_source_root(story: str) -> Path | None:
    root = _source_root(story)
    if root is None:
        print(f"source root not found for story {story}", file=sys.stderr)
    return root


def _load_story_yaml(root: Path) -> dict[str, Any]:
    with (root / "story.yaml").open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    return value if isinstance(value, dict) else {}


def _scene_ids(root: Path) -> list[str]:
    scenes = _load_story_yaml(root).get("scenes", [])
    if isinstance(scenes, dict):
        return [str(scene) for scene in scenes]
    return [str(scene) for scene in scenes] if isinstance(scenes, list) else []


def _compile(root: Path) -> Any:
    from storygame.story_source.compiler import compile_source_tree

    return compile_source_tree(root)


def _print_source_error(error: Exception) -> None:
    print(str(error), file=sys.stderr)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _address_id(address: str) -> tuple[str, str]:
    kind, separator, rest = address.partition(":")
    if not separator or not kind or not rest:
        raise KeyError(address)
    return kind, rest.split(".", 1)[0].split("[", 1)[0]


def _source_references(root: Path, identifier: str) -> list[dict[str, str]]:
    """Return authored YAML locations that mention one record identifier."""

    all_references: list[dict[str, str]] = []
    references: list[dict[str, str]] = []

    def collect(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key) == identifier:
                    references.append({"path": child_path})
                collect(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                collect(child, f"{path}[{index}]")
        elif value == identifier:
            references.append({"path": path})

    for path in sorted(root.rglob("*.yaml")):
        file_references: list[dict[str, str]] = []
        references = file_references
        try:
            with path.open(encoding="utf-8") as stream:
                collect(yaml.safe_load(stream))
        except (OSError, yaml.YAMLError):
            continue
        for reference in file_references:
            reference["file"] = path.relative_to(root).as_posix()
        all_references.extend(file_references)
    return all_references


def _test_mentions(identifier: str) -> list[str]:
    tests = Path("tests")
    if not tests.is_dir():
        return []
    matches: list[str] = []
    for path in sorted(item for item in tests.rglob("*") if item.is_file()):
        try:
            if identifier in path.read_text(encoding="utf-8"):
                matches.append(path.as_posix())
        except (OSError, UnicodeDecodeError):
            continue
    return matches


def _show(args: argparse.Namespace, root: Path) -> int:
    from storygame.story_source.lookup import story_text, story_value

    try:
        package = _compile(root)
        authored = story_text(args.address, package=package, source=True)
        value = story_value(args.address, package=package)
        _, identifier = _address_id(args.address)
    except (KeyError, ValueError):
        print(f"unknown address: {args.address}", file=sys.stderr)
        return 2
    references = _source_references(root, identifier)
    location = (references[0]["file"], references[0]["path"]) if references else None
    producer_keys = {"sets", "commits", "on_assert", "facts", "delivery", "entry_claims"}
    producers = [item for item in references if any(key in item["path"].split(".") for key in producer_keys)]
    consumers = [item for item in references if item not in producers]
    record = {
        "address": args.address,
        "authored": authored,
        "value": _jsonable(value),
        "source_file": location[0] if location else None,
        "yaml_path": location[1] if location else None,
        "match": {"file": location[0], "yaml_path": location[1]} if location else None,
        "producers": producers,
        "consumers": consumers,
        "tests": _test_mentions(identifier),
    }
    if args.json:
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    else:
        print(f"{args.address}: {authored}")
        print(f"source: {record['source_file'] or 'not found'} ({record['yaml_path'] or 'unknown path'})")
        print(f"match: {json.dumps(record['match'], ensure_ascii=False, sort_keys=True)}")
        print(f"producers: {json.dumps(producers, ensure_ascii=False, sort_keys=True)}")
        print(f"consumers: {json.dumps(consumers, ensure_ascii=False, sort_keys=True)}")
        print(f"value: {json.dumps(record['value'], ensure_ascii=False, sort_keys=True)}")
        print("tests: " + (", ".join(record["tests"]) if record["tests"] else "none"))
    return 0


def _legacy_root(story: str, source_root: Path) -> Path:
    if source_root.name == "source":
        return source_root.parent
    return Path("data") / "stories" / story


def _difference_matches_scene(path: str, scene: str) -> bool:
    if path == "knowledge_indexes":
        return True
    marker = re.compile(rf"(?:^|[.\[/_-]){re.escape(scene)}(?:$|[.\]/_-])")
    return bool(marker.search(path))


def _scene_report(report: dict[str, Any], legacy: Any, compiled: Any, scene: str) -> dict[str, Any]:
    differences = [
        item for item in report.get("differences", []) if _difference_matches_scene(item.get("path", ""), scene)
    ]
    dumped_legacy = _jsonable(legacy)
    dumped_compiled = _jsonable(compiled)
    knowledge_equal = dumped_legacy.get("knowledge_indexes") == dumped_compiled.get("knowledge_indexes")
    auto_classes = {"op_order", "condition_order", "collection_order"}
    auto = sum(item.get("class") in auto_classes and item.get("reviewed", False) for item in differences)
    reviewed = sum(item.get("reviewed", False) and item.get("class") not in auto_classes for item in differences)
    summary = dict(report.get("summary", {}))
    summary.update(
        differences=len(differences),
        auto=auto,
        reviewed=reviewed,
        unreviewed=len(differences) - auto - reviewed,
    )
    summary["pass"] = summary["unreviewed"] == 0 and knowledge_equal
    return {"differences": [{"scene": scene, **item} for item in differences], "summary": summary}


def _parity(args: argparse.Namespace, root: Path) -> int:
    try:
        compiled = _compile(root)
        from storygame.story_package.loader import load_story_package
        from storygame.story_source.parity import check_parity, load_review_file

        legacy = load_story_package(_legacy_root(args.story, root))
        review_path = Path("tests") / "fixtures" / "parity" / args.story / f"{args.scene}.reviewed.yaml"
        reviews = load_review_file(review_path) if review_path.is_file() else None
        if "scene" in inspect.signature(check_parity).parameters:
            report = check_parity(legacy, compiled, scene=args.scene, reviews=reviews)
        else:
            report = _scene_report(check_parity(legacy, compiled, reviews=reviews), legacy, compiled, args.scene)
        report = {
            **report,
            "differences": [
                item if "scene" in item else {"scene": args.scene, **item} for item in report.get("differences", [])
            ],
        }
    except Exception as error:
        from storygame.story_source.diagnostics import SourceError

        if isinstance(error, SourceError):
            _print_source_error(error)
            return 2
        print(str(error), file=sys.stderr)
        return 2
    for difference in report.get("differences", []):
        print(json.dumps(difference, ensure_ascii=False, sort_keys=True))
    print(json.dumps({"scene": args.scene, "summary": report.get("summary", {})}, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("summary", {}).get("pass") else 1


def _lock_module() -> Any:
    try:
        from storygame.story_source import lock
    except ImportError:
        return None
    return lock


def _lock_report(report: Any, scene: str, as_json: bool) -> bool:
    changed = list(getattr(report, "changed", []))
    mismatches = list(getattr(report, "mismatches", []))
    if as_json:
        for claim_id, field in changed:
            print(json.dumps({"scene": scene, "changed": [claim_id, field]}))
        for mismatch in mismatches:
            print(json.dumps({"scene": scene, "mismatch": mismatch}))
    else:
        for claim_id, field in changed:
            print(f"changed: {scene} {claim_id}.{field}")
        for mismatch in mismatches:
            print(mismatch)
    return bool(mismatches)


def _run_lock(lock: Any, root: Path, scene: str, adopt: bool, dry_run: bool, as_json: bool) -> bool:
    if not dry_run:
        return _lock_report(lock.lock_scene(root, scene, adopt=adopt), scene, as_json)
    with tempfile.TemporaryDirectory(prefix="story-lock-") as temporary:
        copy = Path(temporary) / "source"
        shutil.copytree(root, copy)
        report = lock.lock_scene(copy, scene, adopt=adopt)
        return _lock_report(report, scene, as_json)


def _lock(args: argparse.Namespace, root: Path) -> int:
    lock = _lock_module()
    if lock is None:
        print("lock layer not built")
        return 2
    if args.all and args.scene:
        print("lock: choose a scene or --all", file=sys.stderr)
        return 2
    scenes = _scene_ids(root) if args.all else ([args.scene] if args.scene else [])
    if not scenes:
        print("lock: a scene or --all is required", file=sys.stderr)
        return 2
    mismatched = any(_run_lock(lock, root, scene, args.adopt, args.dry_run, args.json) for scene in scenes)
    return 1 if mismatched else 0


def _expand(args: argparse.Namespace, root: Path) -> int:
    lock = _lock_module()
    if lock is None:
        print("lock layer not built")
        return 2
    lock.expand_scene(root, args.scene)
    return 0


def _not_built(name: str) -> int:
    print(f"{name}: not built yet")
    return 2


def main(argv: list[str] | None = None) -> int:
    """Parse and run one story command, returning its process exit code."""

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    command_modules = discover()
    if args.command in command_modules:
        root = _require_source_root(args.story)
        if root is None:
            return 2
        try:
            return command_modules[args.command].run(args, root)
        except Exception as error:
            from storygame.story_source.diagnostics import SourceError

            if isinstance(error, SourceError):
                _print_source_error(error)
            else:
                print(str(error), file=sys.stderr)
            return 2
    if args.command in _STUB_COMMAND_NAMES:
        return _not_built(args.command)
    root = _require_source_root(args.story)
    if root is None:
        return 2
    if args.command == "show":
        try:
            return _show(args, root)
        except Exception as error:
            from storygame.story_source.diagnostics import SourceError

            if isinstance(error, SourceError):
                _print_source_error(error)
                return 2
            raise
    if args.command == "parity":
        return _parity(args, root)
    if args.command == "lock":
        return _lock(args, root)
    if args.command == "expand":
        try:
            return _expand(args, root)
        except Exception as error:
            print(str(error), file=sys.stderr)
            return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
