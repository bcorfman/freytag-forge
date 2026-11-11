from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any, get_args

import pytest
import yaml
from pydantic import BaseModel

from storygame.story_package import impact_report
from storygame.story_package.dependencies import producers
from storygame.story_package.impact_report import render_impact_report
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    ActivationRule,
    CanonicalRouteEvent,
    Connection,
    DeliveryVariant,
    DisclosureGuard,
    EndingVariant,
    EntryTextVariant,
    FactPredicate,
    ItemPlacement,
    KnowledgeDefinition,
    PacingEvent,
    PacingRealization,
    SceneMetadata,
    StoryEnding,
    Storylet,
    StoryletRoute,
    Transition,
)

ROOT = Path("data/stories/continuity-initiative")
FACT = "kristin_marked_by_patrol"
CLAIM = "k_sl_1a_b_r0w"
EVENT = "officer_presses_1a"
TRANSITION = "t_1a_1b"
STORYLET = "SL-1A-E"


def _section(text: str, heading: str) -> str:
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize(
    ("subject", "headings"),
    (
        (FACT, ("## Set by", "## Read by", "## Claims", "## Tests that name it")),
        (CLAIM, ("## Requires", "## Establishes", "## Source", "## Tests that name it")),
        (EVENT, ("## Reads", "## Sets", "## Tests that name it")),
        (TRANSITION, ("## Reads", "## Sets", "## Tests that name it")),
        (STORYLET, ("## Reads", "## Sets", "## Tests that name it")),
    ),
)
def test_each_subject_kind_renders_all_sections(subject: str, headings: tuple[str, ...]) -> None:
    text = render_impact_report(ROOT, subject)

    assert text.startswith(f"# Impact report: {subject}\n")
    assert all(heading in text for heading in headings)


def test_fact_set_by_matches_shared_lookup() -> None:
    package = load_story_package(ROOT)
    text = render_impact_report(ROOT, FACT)
    section = _section(text, "## Set by")

    expected = {
        f"- kind: {item.kind}; record: `{item.record_id}`; scene: `{item.scene_id or 'none'}`; text: {item.text}"
        for item in producers(package, FACT)
    }
    actual = {line.split(" [source:", 1)[0] for line in section.splitlines() if line.startswith("- kind:")}
    assert actual == expected


def test_empty_producer_list_prints_none(monkeypatch) -> None:
    monkeypatch.setattr(impact_report, "producers", lambda *_args, **_kwargs: [])

    text = render_impact_report(ROOT, FACT)

    assert "## Set by\n\n- none\n" in text


def test_unknown_and_ambiguous_subjects_raise(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"unknown subject 'missing_subject'"):
        render_impact_report(ROOT, "missing_subject")

    package_root = tmp_path / "package"
    shutil.copytree(ROOT, package_root)
    pacing_path = package_root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    pacing["events"][0]["id"] = FACT
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=rf"ambiguous subject '{FACT}': fact, pacing event"):
        render_impact_report(package_root, FACT)


def test_render_is_deterministic() -> None:
    assert render_impact_report(ROOT, FACT) == render_impact_report(ROOT, FACT)


def test_render_does_not_change_story_files() -> None:
    before = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}

    render_impact_report(ROOT, FACT)

    after = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}
    assert before == after


def test_test_name_scan_accepts_synthetic_tests_dir(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_synthetic.py").write_text(f"# {FACT}\n", encoding="utf-8")

    text = render_impact_report(ROOT, FACT, tests_dir=tests_dir)

    assert "tests/test_synthetic.py:1" in text


def test_new_report_files_contain_no_story_words() -> None:
    paths = (
        Path("storygame/story_package/dependencies.py"),
        Path("storygame/story_package/impact_report.py"),
        Path("scripts/impact_report.py"),
    )
    forbidden = ("memory_card", "kristin", "patrol", "laptop", "k_sl_", "t_1a", "pursuit_1b", "continuity")
    for path in paths:
        contents = path.read_text(encoding="utf-8").casefold()
        assert not any(word in contents for word in forbidden), path


_CONDITION_FIELDS = {
    (ActivationRule, "all_facts_true"),
    (ActivationRule, "any_of"),
    (PacingEvent, "when"),
    (PacingRealization, "when"),
    (Transition, "triggers"),
    (StoryletRoute, "activation_conditions"),
    (KnowledgeDefinition, "requires"),
    (CanonicalRouteEvent, "activation"),
    (StoryEnding, "when"),
    (EndingVariant, "requires"),
    (DeliveryVariant, "requires"),
    (EntryTextVariant, "requires"),
    (DisclosureGuard, "unlock_fact"),
    (Connection, "access_fact_id"),
    (ItemPlacement, "while_fact_false"),
    (ItemPlacement, "while_fact_true"),
}

_DELIBERATELY_NOT_READ = {
    (PacingEvent, "effects"): "event effects write facts rather than read them",
    (Storylet, "sections"): "free-form author prose; executable route conditions live in typed route fields",
    (SceneMetadata, "setting_facts"): "scene prompt context, not a runtime condition",
}


def _contains(annotation: Any, target: type[BaseModel]) -> bool:
    if annotation is target:
        return True
    return any(_contains(argument, target) for argument in get_args(annotation))


def _condition_field(model_type: type[BaseModel], field_name: str, annotation: Any) -> bool:
    if (model_type, field_name) in _DELIBERATELY_NOT_READ:
        return False
    if _contains(annotation, FactPredicate):
        return True
    if _contains(annotation, ActivationRule):
        return True
    if model_type is ActivationRule and field_name in {"all_facts_true", "any_of"}:
        return True
    return field_name in {
        "access_fact_id",
        "requires",
        "unlock_fact",
        "when",
        "while_fact_false",
        "while_fact_true",
    }


def _reachable_condition_fields(value: Any) -> set[tuple[type[BaseModel], str]]:
    found: set[tuple[type[BaseModel], str]] = set()

    def visit(current: Any) -> None:
        if isinstance(current, BaseModel):
            model_type = type(current)
            for field_name, field in model_type.model_fields.items():
                if _condition_field(model_type, field_name, field.annotation):
                    found.add((model_type, field_name))
                visit(getattr(current, field_name))
        elif isinstance(current, dict):
            for child in current.values():
                visit(child)
        elif isinstance(current, (list, tuple, set, frozenset)):
            for child in current:
                visit(child)

    visit(value)
    return found


def _condition_values(value: Any) -> Iterator[str]:
    if isinstance(value, FactPredicate):
        yield value.fact_id
    elif isinstance(value, ActivationRule):
        yield from value.all_facts_true
        yield from value.any_of
    elif isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            yield from _condition_values(child)


def _condition_occurrences(package: Any) -> Iterator[tuple[str, str | None]]:
    def visit(current: Any, record_id: str | None = None) -> Iterator[tuple[str, str | None]]:
        if isinstance(current, BaseModel):
            current_record = getattr(current, "id", None) or getattr(current, "scene_id", None) or record_id
            model_type = type(current)
            for field_name, field in model_type.model_fields.items():
                child = getattr(current, field_name)
                if _condition_field(model_type, field_name, field.annotation):
                    for fact_id in _condition_values(child):
                        yield fact_id, current_record
                yield from visit(child, current_record)
        elif isinstance(current, dict):
            for key, child in current.items():
                yield from visit(child, key if isinstance(key, str) else record_id)
        elif isinstance(current, (list, tuple, set, frozenset)):
            for child in current:
                yield from visit(child, record_id)

    yield from visit(package)


def test_condition_fields_are_complete_and_real_reads_have_consumers() -> None:
    package = load_story_package(ROOT)
    discovered = _reachable_condition_fields(package)
    allowed = set(_CONDITION_FIELDS) | set(_DELIBERATELY_NOT_READ)

    assert discovered <= allowed
    for fact_id, record_id in _condition_occurrences(package):
        found = impact_report.consumers(package, fact_id)
        assert found, (fact_id, record_id)
        if record_id is not None:
            assert record_id in {consumer.record_id for consumer in found}, (fact_id, record_id)
