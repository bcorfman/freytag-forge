"""Static CI guard against embedded story-specific shared-runtime data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoryDataAuditFinding:
    path: str
    line: int
    rule: str
    classification: str
    owner_phase: str
    replacement_schema: str
    removal_phase: str
    text: str


_TARGETS = (
    "storygame/engine",
    "storygame/llm",
    "storygame/cli.py",
)

# These are rejection patterns. Any match fails the migration audit.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "genre-branch",
        re.compile(r"(?:story_)?genre\s*[!=]=\s*['\"](?:mystery|fantasy|romance|sci-fi)['\"]"),
    ),
    (
        "named-story-entity",
        re.compile(
            r"(?i)\b(?:daria(?:_stone| stone)?|mansion|front_steps|arrival_sedan|case_file|ledger_page|"
            r"emma vale|dark sedan|victim_(?:name|identity|timeline)|lead_suspect|strongest_lead)\b"
        ),
    ),
    (
        "story-specific-prompt",
        re.compile(r"(?i)for mystery stories|named male detective"),
    ),
)


AUDIT_MANIFEST: dict[tuple[str, str], dict[str, str]] = {}


def audit_story_specific_branches(repo_root: Path) -> tuple[StoryDataAuditFinding, ...]:
    """Return every inventory-pattern match in the shared runtime surfaces."""
    findings: list[StoryDataAuditFinding] = []
    for target in _TARGETS:
        target_path = repo_root / target
        paths = (target_path,) if target_path.is_file() else sorted(target_path.rglob("*.py"))
        for path in paths:
            relative_path = path.relative_to(repo_root).as_posix()
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for rule, pattern in _RULES:
                    if not pattern.search(line):
                        continue
                    metadata = AUDIT_MANIFEST.get((relative_path, rule), {})
                    findings.append(
                        StoryDataAuditFinding(
                            path=relative_path,
                            line=line_number,
                            rule=rule,
                            classification=metadata.get("classification", "undocumented"),
                            owner_phase=metadata.get("owner_phase", "undocumented"),
                            replacement_schema=metadata.get("replacement_schema", "undocumented"),
                            removal_phase=metadata.get("removal_phase", "undocumented"),
                            text=line.strip(),
                        )
                    )
    return tuple(findings)
