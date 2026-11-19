"""Regression tests for deep comparison of reordered keyed collections."""

from __future__ import annotations

from dataclasses import dataclass

from storygame.story_source.parity import check_parity


@dataclass(frozen=True)
class _PackageDump:
    records: dict[str, object]

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return self.records


def _report(legacy: dict[str, object], compiled: dict[str, object]) -> dict[str, object]:
    return check_parity(_PackageDump(legacy), _PackageDump(compiled))


def _difference(report: dict[str, object], path: str) -> dict[str, object]:
    differences = report["differences"]
    assert isinstance(differences, list)
    return next(difference for difference in differences if difference["path"] == path)


def test_reordered_keyed_items_with_identical_content_are_auto_accepted() -> None:
    items = [{"id": "first", "value": 1}, {"id": "second", "value": 2}]

    report = _report({"storylets": items}, {"storylets": list(reversed(items))})

    assert [difference["path"] for difference in report["differences"]] == ["storylets"]
    assert report["differences"][0]["class"] == "collection_order"
    assert report["differences"][0]["reviewed"] is True
    assert report["summary"]["pass"] is True


def test_reordered_keyed_items_do_not_hide_nested_list_content() -> None:
    legacy = {"storylets": [{"id": "first", "tags": ["one"]}, {"id": "second", "tags": ["two"]}]}
    compiled = {"storylets": [{"id": "second", "tags": ["two"]}, {"id": "first", "tags": ["one", "extra"]}]}

    report = _report(legacy, compiled)

    assert _difference(report, "storylets")["class"] == "collection_order"
    content_difference = _difference(report, "storylets.first.tags")
    assert content_difference["class"] == "representation"
    assert content_difference["reviewed"] is False
    assert report["summary"]["pass"] is False


def test_reordered_keyed_items_do_not_hide_scalar_content() -> None:
    legacy = {"storylets": [{"id": "first", "title": "Legacy"}, {"id": "second", "title": "Same"}]}
    compiled = {"storylets": [{"id": "second", "title": "Same"}, {"id": "first", "title": "Compiled"}]}

    report = _report(legacy, compiled)

    content_difference = _difference(report, "storylets.first.title")
    assert content_difference["class"] == "representation"
    assert content_difference["reviewed"] is False
    assert report["summary"]["pass"] is False


def test_reordered_events_do_not_hide_added_effect_fact() -> None:
    legacy = {
        "pacing": {
            "events": [
                {"id": "first", "effects": ["existing_fact"]},
                {"id": "second", "effects": ["other_fact"]},
            ]
        }
    }
    compiled = {
        "pacing": {
            "events": [
                {"id": "second", "effects": ["other_fact"]},
                {"id": "first", "effects": ["existing_fact", "new_fact"]},
            ]
        }
    }

    report = _report(legacy, compiled)

    assert _difference(report, "pacing.events")["class"] == "collection_order"
    content_difference = _difference(report, "pacing.events.first.effects")
    assert content_difference["class"] == "representation"
    assert content_difference["reviewed"] is False
    assert report["summary"]["pass"] is False


def test_reordered_keyed_items_preserve_operation_and_condition_auto_classes() -> None:
    legacy = {
        "knowledge": {
            "knowledge": [
                {
                    "id": "first",
                    "operations": [{"fact_id": "one"}, {"fact_id": "two"}],
                    "requires": ["one", "two"],
                },
                {"id": "second", "operations": [{"fact_id": "three"}], "requires": ["three"]},
            ]
        }
    }
    compiled = {
        "knowledge": {
            "knowledge": [
                {"id": "second", "operations": [{"fact_id": "three"}], "requires": ["three"]},
                {
                    "id": "first",
                    "operations": [{"fact_id": "two"}, {"fact_id": "one"}],
                    "requires": ["two", "one"],
                },
            ]
        }
    }

    report = _report(legacy, compiled)

    assert {difference["class"] for difference in report["differences"]} == {
        "collection_order",
        "op_order",
        "condition_order",
    }
    assert all(difference["reviewed"] for difference in report["differences"])
    assert report["summary"]["pass"] is True
