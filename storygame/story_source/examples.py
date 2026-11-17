"""Check player-language examples against compiled story matchers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.validation import unconveyed_terms

from .compiler import compile_source_tree


@dataclass(frozen=True)
class ExampleFailure:
    """One example line whose expected matcher result was not observed."""

    claim_id: str
    kind: Literal["accept", "reject"]
    line: str
    group: int
    missing: str


_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)


def check_examples(root: Path, examples_path: Path) -> list[ExampleFailure]:
    """Compile ``root`` and check all accept/reject lines in an examples file."""

    package = compile_source_tree(Path(root))
    examples = _load_examples(Path(examples_path))
    shared = _shared_lines(examples.get("shared", {}))
    definitions = package.knowledge_indexes.by_id
    failures: list[ExampleFailure] = []
    for claim_id, claim in examples.get("claims", {}).items():
        definition = definitions[claim_id]
        lines = _claim_lines(claim, shared.get(claim_id, ()))
        failures.extend(_check_claim(definition, claim_id, lines))
    return failures


def _load_examples(path: Path) -> dict[str, Any]:
    """Read the small, external examples document."""

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _claim_lines(claim: Any, shared: tuple[tuple[str, list[str]], ...]) -> list[tuple[str, str]]:
    """Return local and shared lines in their authored order."""

    lines: list[tuple[str, str]] = []
    if isinstance(claim, dict):
        for kind in ("accept", "reject"):
            lines.extend((kind, line) for line in _lines(claim.get(kind, [])))
    for kind, shared_lines in shared:
        lines.extend((kind, line) for line in shared_lines)
    return lines


def _lines(value: Any) -> list[str]:
    """Return string entries from one examples list."""

    if not isinstance(value, list):
        return []
    return [line for line in value if isinstance(line, str)]


def _shared_lines(value: Any) -> dict[str, tuple[tuple[str, list[str]], ...]]:
    """Expand shared blocks, each of which names the claims receiving its lines."""

    blocks = _shared_blocks(value)
    result: dict[str, list[tuple[str, list[str]]]] = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue
        claim_ids = block.get("claims", block.get("claim_ids", block.get("for", ())))
        if isinstance(claim_ids, str):
            claim_ids = [claim_ids]
        if not isinstance(claim_ids, list):
            continue
        for claim_id in claim_ids:
            if not isinstance(claim_id, str):
                continue
            entries = result.setdefault(claim_id, [])
            for kind in ("accept", "reject"):
                lines = _lines(block.get(kind, []))
                if lines:
                    entries.append((kind, lines))
    return {claim_id: tuple(entries) for claim_id, entries in result.items()}


def _shared_blocks(value: Any) -> list[dict[str, Any]]:
    """Accept list blocks and named mapping blocks from the examples schema."""

    if isinstance(value, list):
        return [block for block in value if isinstance(block, dict)]
    if not isinstance(value, dict):
        return []
    target_keys = {"claims", "claim_ids", "for"}
    if target_keys & value.keys():
        return [value]
    blocks: list[dict[str, Any]] = []
    for name, block in value.items():
        if not isinstance(block, dict):
            continue
        item = dict(block)
        item.setdefault("claims", [name])
        blocks.append(item)
    return blocks


def _check_claim(definition: Any, claim_id: str, lines: list[tuple[str, str]]) -> list[ExampleFailure]:
    """Check one claim's expected outcomes and explain failed accepts."""

    failures: list[ExampleFailure] = []
    for kind, line in lines:
        matched = _matches(definition, line)
        if (kind == "accept" and not matched) or (kind == "reject" and matched):
            group = _failed_group(definition, line) if kind == "accept" else -1
            missing = _missing_word(definition, line, group) if kind == "accept" else ""
            failures.append(ExampleFailure(claim_id, kind, line, group, missing))
    return failures


def _matches(definition: Any, line: str) -> bool:
    """Use the runtime's exact authored-handoff matcher for one definition."""

    return uniquely_matched_authored_handoff(line, (definition,)) is not None and not unconveyed_terms(
        definition.must_convey, line
    )


def _failed_group(definition: Any, line: str) -> int:
    """Return the first matcher group absent from an accept line."""

    if uniquely_matched_authored_handoff(line, (definition,)) is None:
        return _failed_action_group(definition, line)
    for index, group in enumerate(definition.must_convey):
        if unconveyed_terms((group,), line):
            return index
    return -1


def _failed_action_group(definition: Any, line: str) -> int:
    """Return the first action-evidence group absent from an accept line."""

    for index, group in enumerate(definition.action_evidence):
        candidate = definition.model_copy(update={"action_evidence": (group,)})
        if uniquely_matched_authored_handoff(line, (candidate,)) is None:
            return index
    return -1


def _missing_word(definition: Any, line: str, group_index: int) -> str:
    """Find the shortest authored word that makes the failed group match."""

    if group_index < 0:
        return ""
    groups = definition.must_convey
    if uniquely_matched_authored_handoff(line, (definition,)) is None:
        groups = definition.action_evidence
    group = groups[group_index]
    words = sorted(
        {word for phrase in group for word in _WORD.findall(phrase)}, key=lambda word: (len(word), word.casefold())
    )
    for word in words:
        if groups is definition.action_evidence:
            candidate = definition.model_copy(update={"action_evidence": (group,)})
            matches = uniquely_matched_authored_handoff(f"{line} {word}", (candidate,)) is not None
        else:
            matches = not unconveyed_terms((group,), f"{line} {word}")
        if matches:
            return word
    return words[0] if words else ""
