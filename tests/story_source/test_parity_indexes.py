"""Parity behavior for derived knowledge indexes."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from storygame.story_source.parity import check_parity


@dataclass(frozen=True)
class _PackageDump:
    records: dict[str, object]

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return self.records


def _operation(fact_id: str, value: bool = True) -> dict[str, object]:
    return {"op": "assert", "fact_id": fact_id, "value": value}


def _package(
    upstream: list[dict[str, object]],
    indexed: list[dict[str, object]],
    fact_effects: dict[str, list[dict[str, str]]] | None = None,
) -> _PackageDump:
    return _PackageDump(
        {
            "knowledge": {"knowledge": [{"id": "claim", "establishes": upstream}]},
            "knowledge_indexes": {"by_id": {"claim": {"establishes": indexed}}},
            "world": {"fact_effects": fact_effects or {}},
        }
    )


def test_provable_upstream_operation_reorder_is_removed_from_index_parity() -> None:
    legacy_operations = [_operation("first"), _operation("second")]
    compiled_operations = [_operation("second"), _operation("first")]

    report = check_parity(
        _package(legacy_operations, legacy_operations),
        _package(compiled_operations, compiled_operations),
    )

    assert [difference["path"] for difference in report["differences"]] == ["knowledge.knowledge.claim.establishes"]
    assert report["differences"][0]["class"] == "op_order"
    assert report["summary"]["pass"] is True


@pytest.mark.parametrize(
    ("compiled_upstream", "compiled_index", "fact_effects"),
    [
        ([_operation("first"), _operation("second")], [_operation("first"), _operation("other")], {}),
        (
            [_operation("first"), _operation("second")],
            [_operation("first", value=False), _operation("second")],
            {},
        ),
        (
            [_operation("second"), _operation("first")],
            [_operation("second"), _operation("first")],
            {"first": [{"move": "shared"}], "second": [{"move": "shared"}]},
        ),
    ],
)
def test_unproved_index_changes_fail_and_cannot_be_reviewed(
    compiled_upstream: list[dict[str, object]],
    compiled_index: list[dict[str, object]],
    fact_effects: dict[str, list[dict[str, str]]],
) -> None:
    legacy_operations = [_operation("first"), _operation("second")]
    report = check_parity(
        _package(legacy_operations, legacy_operations, fact_effects),
        _package(compiled_upstream, compiled_index, fact_effects),
        reviews=[{"path": "knowledge_indexes", "class": "representation", "reason": "not reviewable"}],
    )

    index_difference = next(item for item in report["differences"] if item["path"] == "knowledge_indexes")
    assert index_difference["reviewed"] is False
    assert report["summary"]["pass"] is False
