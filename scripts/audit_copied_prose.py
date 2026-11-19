from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')).strip()


def _sentences(text: str) -> list[str]:
    return [sentence for sentence in re.split(r"(?<=[.!?])\s+", _norm(text)) if len(sentence) >= 45]


def _words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9' ]+", " ", _norm(s).lower()).split()


def _string_constants_blob(test_text: str) -> str:
    try:
        tree = ast.parse(test_text)
    except SyntaxError:
        return ""
    constants = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)),
        key=lambda node: (node.lineno, node.col_offset),
    )
    joined = " ".join(node.value for node in constants)
    return " " + " ".join(_words(joined)) + " "


def find_copied_sentences(package: Any, tests_dir: Path) -> dict[str, list[tuple[str, str]]]:
    passages: dict[str, str] = {}
    for claim in package.knowledge.knowledge:
        if claim.delivery_text:
            passages[f"claim:{claim.id}.text"] = claim.delivery_text
        if claim.statement:
            passages[f"claim:{claim.id}.says"] = claim.statement
    for event in package.pacing.events:
        for index, realization in enumerate(event.realizations):
            passages[f"beat:{event.id}.say[{index}].text"] = realization.text

    sentences: dict[str, str] = {}
    for address, text in passages.items():
        for sentence in _sentences(text):
            sentences.setdefault(sentence, address)

    copied: dict[str, list[tuple[str, str]]] = {}
    for test_path in tests_dir.glob("test_*.py"):
        raw_test_text = test_path.read_text(encoding="utf-8")
        test_text = _norm(raw_test_text)
        constants_blob = _string_constants_blob(raw_test_text)
        hits = [
            (address, sentence)
            for sentence, address in sentences.items()
            if sentence in test_text or " " + " ".join(_words(sentence)) + " " in constants_blob
        ]
        if hits:
            copied[test_path.name] = hits
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if "storygame" not in sys.modules:
        try:
            __import__("storygame")
        except ModuleNotFoundError:
            sys.path.insert(0, str(repo))

    from storygame.story_package.loader import load_story_package

    package = load_story_package(repo / "data/stories/continuity-initiative")
    tests_dir = repo / "tests"
    report = find_copied_sentences(package, tests_dir)
    if args.test:
        selected = set(args.test)
        report = {name: pairs for name, pairs in report.items() if name in {Path(item).name for item in selected}}

    if args.json:
        print(
            json.dumps({name: [[address, sentence] for address, sentence in pairs] for name, pairs in report.items()})
        )
    else:
        for name, pairs in report.items():
            for address, sentence in pairs:
                print(f"tests/{name}: {address} :: {sentence}")
        print(f"{len(report)} test files copy {sum(len(pairs) for pairs in report.values())} authored sentences")
    return 1 if report else 0


if __name__ == "__main__":
    raise SystemExit(main())
